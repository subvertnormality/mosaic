/* RD-02 streaming aubio tempo feasibility CLI; raw mono float32 PCM in, JSON out. */
#include <aubio/aubio.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_BEATS 1024
#define MAX_HOPS 8192
#define MIN_BPM 40.0
#define MAX_BPM 240.0
#define CONFIDENCE_MIN 0.10

struct beat { uint32_t frame; double bpm, confidence; };
struct candidate {
  const char *status, *reason; double bpm, phase_ms, half_bpm, double_bpm, grid_score, half_score, double_score;
  uint32_t origin, end, used, grid_support, offbeat_residual;
};

static int compare_double(const void *left, const void *right) {
  double a = *(const double *)left, b = *(const double *)right;
  return (a > b) - (a < b);
}
static double median3(double a, double b, double c) {
  double values[3] = {a, b, c}; qsort(values, 3, sizeof(values[0]), compare_double); return values[1];
}
/* A beat grid can be supported by onsets while other onsets remain legitimate subdivisions. */
static double score_grid(const struct beat *beats, size_t first, size_t count, double bpm, uint32_t rate,
                         unsigned *support, unsigned *residual, double *maximum_phase) {
  if (bpm < MIN_BPM || bpm > MAX_BPM || count < 2) return INFINITY;
  double period = rate * 60.0 / bpm, origin = beats[first].frame;
  unsigned aligned = 0, offbeat = 0, unique_cells = 0;
  double max_phase = 0, previous_cell = -1;
  for (size_t i = 0; i < count; ++i) {
    double cell = round((beats[first + i].frame - origin) / period);
    double phase = fabs(beats[first + i].frame - (origin + cell * period)) * 1000.0 / rate;
    if (phase <= 50.0) {
      ++aligned;
      if (phase > max_phase) max_phase = phase;
      if (cell != previous_cell) { ++unique_cells; previous_cell = cell; }
    } else ++offbeat;
  }
  unsigned expected = (unsigned)floor((beats[first + count - 1].frame - origin) / period) + 1;
  if (support) *support = aligned;
  if (residual) *residual = offbeat;
  if (maximum_phase) *maximum_phase = max_phase;
  return 1.0 - (double)unique_cells / expected;
}
/* Cheap onset-phase autocorrelation over the locally measured PCM energy peaks. */
static double infer_onset_bpm(const struct beat *onsets, size_t count, uint32_t rate) {
  if (count < 8) return 0;
  double best_bpm = 0, best_residual = INFINITY;
  unsigned best_matches = 0;
  double tolerance = rate * .050; /* same independent phase bound as the candidate gate */
  for (double bpm = MIN_BPM; bpm <= MAX_BPM; bpm += .25) {
    double period = rate * 60.0 / bpm, residual = 0;
    unsigned matches = 0;
    for (size_t i = 0; i + 1 < count; ++i) {
      double target = onsets[i].frame + period, nearest = INFINITY;
      for (size_t j = i + 1; j < count && onsets[j].frame <= target + tolerance; ++j) {
        double error = fabs(onsets[j].frame - target);
        if (error < nearest) nearest = error;
      }
      if (nearest <= tolerance) { ++matches; residual += nearest; }
    }
    if (matches > best_matches || (matches == best_matches && residual < best_residual)) {
      best_matches = matches; best_residual = residual; best_bpm = bpm;
    }
  }
  if (best_matches < 4) return 0;
  /* Fold onset strengths by their observed sequence cells, allowing integer gaps. */
  double nominal = (onsets[count - 1].frame - onsets[0].frame) / (double)(count - 1);
  double cell = 0, sum_x = 0, sum_y = 0, sum_xx = 0, sum_xy = 0;
  for (size_t i = 0; i < count; ++i) {
    if (i) {
      double increment = round((onsets[i].frame - onsets[i - 1].frame) / nominal);
      cell += increment < 1 ? 1 : increment;
    }
    double frame = onsets[i].frame - onsets[0].frame;
    sum_x += cell; sum_y += frame; sum_xx += cell * cell; sum_xy += cell * frame;
  }
  double denominator = count * sum_xx - sum_x * sum_x;
  if (fabs(denominator) < 1e-9) return 0;
  double fitted_period = (count * sum_xy - sum_x * sum_y) / denominator;
  double fitted_bpm = rate * 60.0 / fitted_period;
  if (fabs(log2(fitted_bpm / best_bpm)) > .25) return 0; /* reject a fitted octave unrelated to autocorrelation */
  if (fitted_bpm < MIN_BPM - .5 || fitted_bpm > MAX_BPM + .5) return 0;
  if (fitted_bpm < MIN_BPM) fitted_bpm = MIN_BPM;
  if (fitted_bpm > MAX_BPM) fitted_bpm = MAX_BPM;
  return fitted_bpm;
}
static struct candidate choose_candidate(const struct beat *beats, size_t count, uint32_t frames, uint32_t rate) {
  struct candidate result = {"UNCERTAIN", "insufficient-beats", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
  if (count < 8) return result;
  int saw_stable = 0, saw_complete = 0, saw_unstable = 0, saw_support = 0;
  for (size_t stable = 0; stable + 2 < count; ++stable) {
    for (size_t middle = stable + 1; middle + 1 < count; ++middle) {
      for (size_t late = middle + 1; late < count; ++late) {
        const struct beat *a = &beats[stable], *b = &beats[middle], *c = &beats[late];
        if (c->frame - a->frame < rate * 4) continue; /* estimates are independently spaced, not consecutive */
        double minimum = fmin(a->bpm, fmin(b->bpm, c->bpm));
        double maximum = fmax(a->bpm, fmax(b->bpm, c->bpm));
        if (minimum < MIN_BPM || maximum > MAX_BPM || a->confidence < CONFIDENCE_MIN ||
            b->confidence < CONFIDENCE_MIN || c->confidence < CONFIDENCE_MIN || maximum / minimum > 1.02) continue;
        saw_stable = 1;
        double bpm = median3(a->bpm, b->bpm, c->bpm), period = rate * 60.0 / bpm;
        for (size_t first = stable; first < count; ++first) {
          double end = beats[first].frame + 16.0 * period; /* four complete bars are sixteen intervals */
          if (end > frames) continue;
          saw_complete = 1;
          double low = beats[first].bpm, high = beats[first].bpm;
          for (size_t i = first; i < count; ++i) { /* validate the complete retained stable span */
            if (beats[i].bpm < low) low = beats[i].bpm;
            if (beats[i].bpm > high) high = beats[i].bpm;
          }
          if (high / low > 1.02) { saw_unstable = 1; continue; }
          unsigned grid_support = 0, offbeat_residual = 0;
          double maximum_phase = 0;
          double main_score = score_grid(beats, first, count - first, bpm, rate,
                                         &grid_support, &offbeat_residual, &maximum_phase);
          if (grid_support < 8) { saw_support = 1; continue; }
          double half_score = score_grid(beats, first, count - first, bpm / 2.0, rate, NULL, NULL, NULL);
          double double_score = score_grid(beats, first, count - first, bpm * 2.0, rate, NULL, NULL, NULL);
          result.bpm = bpm; result.half_bpm = bpm / 2.0; result.double_bpm = bpm * 2.0;
          result.grid_score = main_score; result.half_score = half_score; result.double_score = double_score;
          result.origin = beats[first].frame; result.end = (uint32_t)end; result.used = grid_support;
          result.grid_support = grid_support; result.offbeat_residual = offbeat_residual; result.phase_ms = maximum_phase;
          if (fabs(main_score - half_score) < .10 || fabs(main_score - double_score) < .10) {
            result.reason = "half-double-ambiguous"; return result;
          }
          result.status = "READY"; result.reason = "stable"; return result;
        }
      }
    }
  }
  if (saw_support) result.reason = "insufficient-grid-support";
  else if (saw_unstable || !saw_stable) result.reason = "unstable-estimates";
  else if (saw_complete) result.reason = "unstable-estimates";
  else result.reason = "no-complete-four-bars";
  return result;
}
static void print_candidate(const struct candidate *candidate) {
  double half_score = isfinite(candidate->half_score) ? candidate->half_score : -1;
  double double_score = isfinite(candidate->double_score) ? candidate->double_score : -1;
  printf("{\"candidate\":{\"status\":\"%s\",\"reason\":\"%s\",\"bpm\":%.8g,\"half_bpm\":%.8g,\"double_bpm\":%.8g,\"grid_score\":%.8g,\"half_score\":%.8g,\"double_score\":%.8g,\"origin_frame\":%u,\"region_end_frame\":%u,\"beats_used\":%u,\"grid_support\":%u,\"offbeat_residual\":%u,\"phase_error_ms\":%.8g}}\n", candidate->status, candidate->reason, candidate->bpm, candidate->half_bpm, candidate->double_bpm, candidate->grid_score, half_score, double_score, candidate->origin, candidate->end, candidate->used, candidate->grid_support, candidate->offbeat_residual, candidate->phase_ms);
}
static int parse_u32(const char *text, uint32_t *value) {
  char *end = NULL; unsigned long parsed = strtoul(text, &end, 10);
  if (!end || *end || parsed > UINT32_MAX) return 0;
  *value = (uint32_t)parsed; return 1;
}
static void usage(const char *name) {
  fprintf(stderr, "usage: %s --raw-f32 FILE SAMPLE_RATE [METHOD|onset-ac] | --candidate-beats FILE SAMPLE_RATE FRAMES\n", name);
}
int main(int argc, char **argv) {
  if (argc == 5 && !strcmp(argv[1], "--candidate-beats")) {
    uint32_t rate, frames;
    if (!parse_u32(argv[3], &rate) || !parse_u32(argv[4], &frames) || !rate) { usage(argv[0]); return 2; }
    FILE *table = fopen(argv[2], "r"); if (!table) { perror(argv[2]); return 2; }
    struct beat beats[MAX_BEATS]; size_t count = 0;
    while (count < MAX_BEATS && fscanf(table, "%u %lf %lf", &beats[count].frame, &beats[count].bpm, &beats[count].confidence) == 3) ++count;
    fclose(table);
    struct candidate candidate = choose_candidate(beats, count, frames, rate);
    print_candidate(&candidate); return 0;
  }
  if ((argc != 4 && argc != 5) || strcmp(argv[1], "--raw-f32")) { usage(argv[0]); return 2; }
  uint32_t rate;
  if (!parse_u32(argv[3], &rate) || rate < 8000 || rate > 192000) { usage(argv[0]); return 2; }
  FILE *file = fopen(argv[2], "rb"); if (!file) { perror(argv[2]); return 2; }
  const char *method = argc == 5 ? argv[4] : "energy";
  int onset_ac = !strcmp(method, "onset-ac");
  aubio_tempo_t *tempo = onset_ac ? NULL : new_aubio_tempo(method, 1024, 512, rate);
  fvec_t *input = new_fvec(512), *output = new_fvec(1);
  if ((!tempo && !onset_ac) || !input || !output) { fprintf(stderr, "aubio allocation failed\n"); return 3; }
  struct beat beats[MAX_BEATS]; size_t beat_count = 0; uint32_t frames = 0;
  float onset_strength[MAX_HOPS]; size_t hop_count = 0;
  while (1) {
    size_t got = fread(input->data, sizeof(float), input->length, file);
    if (!got) break;
    if (got < input->length) memset(input->data + got, 0, (input->length - got) * sizeof(float));
    if (onset_ac) {
      float energy = 0; for (uint_t i = 0; i < input->length; ++i) energy += input->data[i] * input->data[i];
      if (hop_count < MAX_HOPS) onset_strength[hop_count++] = energy;
    } else aubio_tempo_do(tempo, input, output);
    frames += (uint32_t)got;
    if (!onset_ac && output->data[0] != 0 && beat_count < MAX_BEATS) {
      beats[beat_count].frame = aubio_tempo_get_last(tempo);
      beats[beat_count].bpm = aubio_tempo_get_bpm(tempo);
      beats[beat_count].confidence = aubio_tempo_get_confidence(tempo);
      if (!beat_count || beats[beat_count].frame > beats[beat_count - 1].frame) ++beat_count;
    }
    if (got < input->length) break;
  }
  fclose(file);
  if (onset_ac && hop_count) {
    double mean = 0; for (size_t i = 0; i < hop_count; ++i) mean += onset_strength[i]; mean /= hop_count;
    for (size_t i = 0; i < hop_count && beat_count < MAX_BEATS; ++i) {
      float before = i ? onset_strength[i - 1] : 0;
      float after = i + 1 < hop_count ? onset_strength[i + 1] : 0;
      if (onset_strength[i] >= before && onset_strength[i] > after && onset_strength[i] > mean * 3.0) {
        beats[beat_count++] = (struct beat){(uint32_t)(i * 512), 0, 1};
      }
    }
  }
  double reported = onset_ac ? infer_onset_bpm(beats, beat_count, rate) : aubio_tempo_get_bpm(tempo);
  double confidence = onset_ac ? (reported ? 1.0 : 0.0) : aubio_tempo_get_confidence(tempo);
  if (onset_ac) for (size_t i = 0; i < beat_count; ++i) beats[i].bpm = reported;
  struct candidate candidate = choose_candidate(beats, beat_count, frames, rate);
  printf("{\"fixture_contract\":\"streaming-raw-f32\",\"method\":\"%s\",\"sample_rate\":%u,\"frames\":%u,\"reported_bpm\":%.8g,\"reported_confidence\":%.8g,\"beats\":[", method, rate, frames, reported, confidence);
  for (size_t i = 0; i < beat_count; ++i)
    printf("%s{\"frame\":%u,\"bpm\":%.8g,\"confidence\":%.8g}", i ? "," : "", beats[i].frame, beats[i].bpm, beats[i].confidence);
  double half_score = isfinite(candidate.half_score) ? candidate.half_score : -1;
  double double_score = isfinite(candidate.double_score) ? candidate.double_score : -1;
  printf("],\"candidate\":{\"status\":\"%s\",\"reason\":\"%s\",\"bpm\":%.8g,\"half_bpm\":%.8g,\"double_bpm\":%.8g,\"grid_score\":%.8g,\"half_score\":%.8g,\"double_score\":%.8g,\"origin_frame\":%u,\"region_end_frame\":%u,\"beats_used\":%u,\"grid_support\":%u,\"offbeat_residual\":%u,\"phase_error_ms\":%.8g}}\n", candidate.status, candidate.reason, candidate.bpm, candidate.half_bpm, candidate.double_bpm, candidate.grid_score, half_score, double_score, candidate.origin, candidate.end, candidate.used, candidate.grid_support, candidate.offbeat_residual, candidate.phase_ms);
  if (tempo) del_aubio_tempo(tempo);
  del_fvec(input); del_fvec(output); aubio_cleanup(); return 0;
}
