/* Native Rhythm Doctor analysis backend.
 *
 * A direct port of tools/rhythm_doctor/dsp_drum_backend.py, so that a stock
 * Norns can analyse a capture with no Python packages installed. The Python
 * backend remains the reference implementation and the two are checked against
 * each other on the corpus; this file must not drift from it silently.
 *
 * The FFT is numpy's own pocketfft, vendored beside this file, so the
 * spectrogram is computed by the same code the reference uses.
 *
 * Speaks the worker contract: --request <json> --result <json>.
 */
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pocketfft.c"

#define SR 44100
#define NFFT 2048
#define HOP 512
#define BINS (NFFT / 2 + 1)
#define HARMONIC_RANK 10
#define ITERATIONS 20
#define EPSF 1e-10f

/* Boeck, Krebs & Schedl offline peak-picking window sizes, in frames. */
enum { W1 = 3, W2 = 3, W3 = 8, W4 = 1, W5 = 2 };

#define BPM_MIN 40.0
#define BPM_MAX 240.0
#define DEFAULT_BPM 120.0

#define PITCH_CONFIDENCE_CUT 0.15
#define PITCH_WINDOW_SECONDS 0.080
#define BASS_F0_MIN 35.0
#define BASS_F0_MAX 300.0

#define BACKEND_ID "nmf-pfnmf-drums-v1"

static const char *const LANES[4] = {"BD", "SD", "CYM", "BASS"};
static const float DEFAULT_DELTA[4] = {0.40f, 0.35f, 0.15f, 0.40f};

static void *xalloc(size_t n) {
  void *p = calloc(n ? n : 1, 1);
  if (!p) { fprintf(stderr, "out of memory\n"); exit(2); }
  return p;
}

/* --- template dictionary -------------------------------------------------- */

typedef struct { int bins, lanes, window, hop; char names[8][8]; float *data; } templates_t;

static int load_templates(const char *path, templates_t *out) {
  FILE *f = fopen(path, "rb");
  if (!f) return -1;
  unsigned char magic[8];
  uint32_t head[4];
  if (fread(magic, 1, 8, f) != 8 || memcmp(magic, "RDTPL\0\0\1", 8) ||
      fread(head, sizeof(uint32_t), 4, f) != 4) { fclose(f); return -1; }
  out->bins = (int)head[0]; out->lanes = (int)head[1];
  out->window = (int)head[2]; out->hop = (int)head[3];
  if (out->bins != BINS || out->lanes < 1 || out->lanes > 8 ||
      out->window != NFFT || out->hop != HOP) { fclose(f); return -1; }
  memset(out->names, 0, sizeof out->names);
  for (int i = 0; i < out->lanes; i++)
    if (fread(out->names[i], 1, 8, f) != 8) { fclose(f); return -1; }
  size_t count = (size_t)out->bins * out->lanes;
  out->data = xalloc(count * sizeof(float));
  if (fread(out->data, sizeof(float), count, f) != count) { fclose(f); return -1; }
  fclose(f);
  for (size_t i = 0; i < count; i++)
    if (!isfinite(out->data[i])) return -1;
  return 0;
}

static int template_column(const templates_t *t, const char *name) {
  for (int i = 0; i < t->lanes; i++)
    if (!strncmp(t->names[i], name, 8)) return i;
  return -1;
}

/* --- STFT ----------------------------------------------------------------- */

/* Magnitude spectrogram, bins-major: V[bin * frames + frame]. */
static float *stft_magnitude(const float *x, size_t n, int *frames_out) {
  int frames = (n >= NFFT) ? 1 + (int)((n - NFFT) / HOP) : 0;
  *frames_out = frames;
  if (frames <= 0) return NULL;
  double *window = xalloc(NFFT * sizeof(double));
  for (int i = 0; i < NFFT; i++)            /* np.hanning: symmetric, N-1 */
    window[i] = 0.5 - 0.5 * cos(2.0 * M_PI * i / (double)(NFFT - 1));
  float *V = xalloc((size_t)BINS * frames * sizeof(float));
  double *buf = xalloc(NFFT * sizeof(double));
  rfft_plan plan = make_rfft_plan(NFFT);
  if (!plan) { fprintf(stderr, "fft plan failed\n"); exit(2); }
  for (int f = 0; f < frames; f++) {
    const float *seg = x + (size_t)f * HOP;
    for (int i = 0; i < NFFT; i++) buf[i] = (double)seg[i] * window[i];
    if (rfft_forward(plan, buf, 1.0)) { fprintf(stderr, "fft failed\n"); exit(2); }
    /* pocketfft halfcomplex: r0, (r1,i1), (r2,i2), ... and rN/2 when even. */
    V[(size_t)0 * frames + f] = (float)fabs(buf[0]);
    for (int k = 1; k < NFFT / 2; k++)
      V[(size_t)k * frames + f] = (float)hypot(buf[2 * k - 1], buf[2 * k]);
    V[(size_t)(NFFT / 2) * frames + f] = (float)fabs(buf[NFFT - 1]);
  }
  destroy_rfft_plan(plan);
  free(buf); free(window);
  return V;
}

/* --- PFNMF ---------------------------------------------------------------- */

/* The reference seeds numpy's PCG64 so a capture analysed twice gives the same
 * transcription. That property is what matters, not the particular stream, so
 * this uses its own deterministic generator rather than reproducing PCG64. The
 * two backends are therefore compared on detection accuracy over the corpus,
 * not bit equality; test_native_backend_equivalence pins that. */
static uint64_t rng_state;
static void rng_seed(uint64_t s) { rng_state = s + 0x9E3779B97F4A7C15ull; }
static float rng_uniform(void) {
  uint64_t z = (rng_state += 0x9E3779B97F4A7C15ull);
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
  z ^= z >> 31;
  return (float)((z >> 11) * (1.0 / 9007199254740992.0));
}

/* KL multiplicative updates with the drum dictionary held fixed. Returns the
 * drum activations, drums x frames. */
static float *pfnmf(const float *V, const float *Bd, int drums, int frames) {
  const int bins = BINS, hr = HARMONIC_RANK;
  size_t cells = (size_t)bins * frames;
  float *Bh = xalloc((size_t)hr * bins * sizeof(float));
  float *Gd = xalloc((size_t)drums * frames * sizeof(float));
  float *Gh = xalloc((size_t)hr * frames * sizeof(float));
  float *ratio = xalloc(cells * sizeof(float));
  float *numD = xalloc((size_t)drums * frames * sizeof(float));
  float *numH = xalloc((size_t)hr * frames * sizeof(float));
  float *upd = xalloc((size_t)hr * bins * sizeof(float));
  float *colsum = xalloc((size_t)(drums + hr) * sizeof(float));
  float *rowsum = xalloc((size_t)hr * sizeof(float));

  rng_seed(0);
  for (size_t i = 0; i < (size_t)hr * bins; i++) Bh[i] = rng_uniform() + 0.1f;
  for (size_t i = 0; i < (size_t)drums * frames; i++) Gd[i] = rng_uniform() + 0.1f;
  for (size_t i = 0; i < (size_t)hr * frames; i++) Gh[i] = rng_uniform() + 0.1f;

  for (int it = 0; it < ITERATIONS; it++) {
    /* ratio = V / (B @ G + eps), fused so the product is never materialised. */
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < bins; i++) {
      for (int f = 0; f < frames; f++) {
        float s = 0.f;
        for (int k = 0; k < drums; k++) s += Bd[(size_t)k * bins + i] * Gd[(size_t)k * frames + f];
        for (int h = 0; h < hr; h++)    s += Bh[(size_t)h * bins + i] * Gh[(size_t)h * frames + f];
        ratio[(size_t)i * frames + f] = V[(size_t)i * frames + f] / (s + EPSF);
      }
    }
    /* B.T @ ones is a column sum of B repeated across frames, so it is taken
     * directly rather than as a bins x frames multiply. */
    for (int k = 0; k < drums; k++) {
      float s = 0.f; for (int i = 0; i < bins; i++) s += Bd[(size_t)k * bins + i];
      colsum[k] = s;
    }
    for (int h = 0; h < hr; h++) {
      float s = 0.f; for (int i = 0; i < bins; i++) s += Bh[(size_t)h * bins + i];
      colsum[drums + h] = s;
    }
    #pragma omp parallel for schedule(static)
    for (int k = 0; k < drums; k++)
      for (int f = 0; f < frames; f++) {
        float s = 0.f;
        for (int i = 0; i < bins; i++) s += Bd[(size_t)k * bins + i] * ratio[(size_t)i * frames + f];
        numD[(size_t)k * frames + f] = s;
      }
    #pragma omp parallel for schedule(static)
    for (int h = 0; h < hr; h++)
      for (int f = 0; f < frames; f++) {
        float s = 0.f;
        for (int i = 0; i < bins; i++) s += Bh[(size_t)h * bins + i] * ratio[(size_t)i * frames + f];
        numH[(size_t)h * frames + f] = s;
      }
    for (int k = 0; k < drums; k++)
      for (int f = 0; f < frames; f++)
        Gd[(size_t)k * frames + f] *= numD[(size_t)k * frames + f] / (colsum[k] + EPSF);
    for (int h = 0; h < hr; h++)
      for (int f = 0; f < frames; f++)
        Gh[(size_t)h * frames + f] *= numH[(size_t)h * frames + f] / (colsum[drums + h] + EPSF);

    /* Second ratio, with the updated activations. */
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < bins; i++) {
      for (int f = 0; f < frames; f++) {
        float s = 0.f;
        for (int k = 0; k < drums; k++) s += Bd[(size_t)k * bins + i] * Gd[(size_t)k * frames + f];
        for (int h = 0; h < hr; h++)    s += Bh[(size_t)h * bins + i] * Gh[(size_t)h * frames + f];
        ratio[(size_t)i * frames + f] = V[(size_t)i * frames + f] / (s + EPSF);
      }
    }
    /* ones @ G_H.T is a row sum of G_H repeated down the bins. */
    for (int h = 0; h < hr; h++) {
      float s = 0.f; for (int f = 0; f < frames; f++) s += Gh[(size_t)h * frames + f];
      rowsum[h] = s;
    }
    #pragma omp parallel for schedule(static)
    for (int h = 0; h < hr; h++)
      for (int i = 0; i < bins; i++) {
        float s = 0.f;
        for (int f = 0; f < frames; f++) s += ratio[(size_t)i * frames + f] * Gh[(size_t)h * frames + f];
        upd[(size_t)h * bins + i] = s;
      }
    for (size_t idx = 0; idx < (size_t)hr * bins; idx++)
      Bh[idx] *= upd[idx] / (rowsum[idx / bins] + EPSF);
    for (int h = 0; h < hr; h++) {          /* column-normalise B_H */
      double nrm = 0.0;
      for (int i = 0; i < bins; i++) { double v = Bh[(size_t)h * bins + i]; nrm += v * v; }
      nrm = sqrt(nrm);
      for (int i = 0; i < bins; i++) Bh[(size_t)h * bins + i] /= (float)(nrm + EPSF);
    }
  }
  free(Bh); free(Gh); free(ratio); free(numD); free(numH); free(upd); free(colsum); free(rowsum);
  return Gd;
}

/* --- SHA-256 -------------------------------------------------------------- */

typedef struct { uint32_t h[8]; uint64_t len; unsigned char buf[64]; size_t n; } sha256_t;

static uint32_t ror32(uint32_t x, int c) { return (x >> c) | (x << (32 - c)); }

static void sha256_block(sha256_t *s, const unsigned char *p) {
  static const uint32_t K[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
  uint32_t w[64], a, b, c, d, e, f, g, hh;
  for (int i = 0; i < 16; i++)
    w[i] = (uint32_t)p[4*i] << 24 | (uint32_t)p[4*i+1] << 16 | (uint32_t)p[4*i+2] << 8 | p[4*i+3];
  for (int i = 16; i < 64; i++) {
    uint32_t s0 = ror32(w[i-15],7) ^ ror32(w[i-15],18) ^ (w[i-15] >> 3);
    uint32_t s1 = ror32(w[i-2],17) ^ ror32(w[i-2],19) ^ (w[i-2] >> 10);
    w[i] = w[i-16] + s0 + w[i-7] + s1;
  }
  a=s->h[0]; b=s->h[1]; c=s->h[2]; d=s->h[3]; e=s->h[4]; f=s->h[5]; g=s->h[6]; hh=s->h[7];
  for (int i = 0; i < 64; i++) {
    uint32_t S1 = ror32(e,6) ^ ror32(e,11) ^ ror32(e,25);
    uint32_t ch = (e & f) ^ (~e & g);
    uint32_t t1 = hh + S1 + ch + K[i] + w[i];
    uint32_t S0 = ror32(a,2) ^ ror32(a,13) ^ ror32(a,22);
    uint32_t mj = (a & b) ^ (a & c) ^ (b & c);
    uint32_t t2 = S0 + mj;
    hh=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
  }
  s->h[0]+=a; s->h[1]+=b; s->h[2]+=c; s->h[3]+=d;
  s->h[4]+=e; s->h[5]+=f; s->h[6]+=g; s->h[7]+=hh;
}

static void sha256_init(sha256_t *s) {
  static const uint32_t iv[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
                                 0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
  memcpy(s->h, iv, sizeof iv); s->len = 0; s->n = 0;
}

static void sha256_update(sha256_t *s, const unsigned char *p, size_t n) {
  s->len += n;
  while (n) {
    size_t take = 64 - s->n; if (take > n) take = n;
    memcpy(s->buf + s->n, p, take);
    s->n += take; p += take; n -= take;
    if (s->n == 64) { sha256_block(s, s->buf); s->n = 0; }
  }
}

static void sha256_hex(sha256_t *s, char out[65]) {
  uint64_t bits = s->len * 8;
  unsigned char pad = 0x80;
  sha256_update(s, &pad, 1);
  unsigned char zero = 0;
  while (s->n != 56) sha256_update(s, &zero, 1);
  unsigned char tail[8];
  for (int i = 0; i < 8; i++) tail[i] = (unsigned char)(bits >> (56 - 8*i));
  sha256_update(s, tail, 8);
  for (int i = 0; i < 8; i++) sprintf(out + i*8, "%08x", s->h[i]);
  out[64] = 0;
}

static int sha256_file(const char *path, char out[65]) {
  FILE *f = fopen(path, "rb");
  if (!f) return -1;
  sha256_t s; sha256_init(&s);
  unsigned char block[1 << 16]; size_t n;
  while ((n = fread(block, 1, sizeof block, f)) > 0) sha256_update(&s, block, n);
  fclose(f);
  sha256_hex(&s, out);
  return 0;
}

/* --- peak picking --------------------------------------------------------- */

static int cmp_float(const void *a, const void *b) {
  float x = *(const float *)a, y = *(const float *)b;
  return (x > y) - (x < y);
}

/* numpy's default linear interpolation between order statistics. */
static float percentile(const float *v, int n, double q) {
  if (n <= 0) return 1.0f;
  float *s = xalloc((size_t)n * sizeof(float));
  memcpy(s, v, (size_t)n * sizeof(float));
  qsort(s, (size_t)n, sizeof(float), cmp_float);
  double pos = (n - 1) * (q / 100.0);
  int lo = (int)floor(pos), hi = (int)ceil(pos);
  double frac = pos - lo;
  float out = (float)(s[lo] * (1.0 - frac) + s[hi] * frac);
  free(s);
  return out;
}

/* Boeck's three-condition picker over a robustly normalised curve. */
static int pick_peaks(const float *curve, int n, float delta, int *picked) {
  if (n < 5) return 0;
  float *positive = xalloc((size_t)n * sizeof(float));
  int m = 0;
  for (int i = 0; i < n; i++) if (curve[i] > 0) positive[m++] = curve[i];
  float scale = m ? percentile(positive, m, 95.0) : 1.0f;
  free(positive);
  float *a = xalloc((size_t)n * sizeof(float));
  for (int i = 0; i < n; i++) a[i] = curve[i] / (scale + EPSF);
  double *cum = xalloc(((size_t)n + 1) * sizeof(double));
  cum[0] = 0.0;
  for (int i = 0; i < n; i++) cum[i + 1] = cum[i] + a[i];
  int count = 0, last = -1000000000;
  for (int i = 0; i < n; i++) {
    int lo = i - W1 < 0 ? 0 : i - W1, hi = i + W2 + 1 > n ? n : i + W2 + 1;
    float peak = a[lo];
    for (int j = lo + 1; j < hi; j++) if (a[j] > peak) peak = a[j];
    if (a[i] < peak) continue;
    int lo3 = i - W3 < 0 ? 0 : i - W3, hi3 = i + W4 + 1 > n ? n : i + W4 + 1;
    int span = hi3 - lo3 < 1 ? 1 : hi3 - lo3;
    double mean = (cum[hi3] - cum[lo3]) / span;
    if (a[i] < mean + delta) continue;
    if (i - last <= W5) continue;
    picked[count++] = i;
    last = i;
  }
  free(a); free(cum);
  return count;
}

/* --- autocorrelation helpers ---------------------------------------------- */

/* Normalised autocorrelation peak in a lag range; shared by tempo and pitch. */
static double autocorr_peak(const double *x, int n, int lo, int hi, int *best_lag) {
  if (n < 4) return 0.0;
  double zero = 0.0;
  for (int i = 0; i < n; i++) zero += x[i] * x[i];
  if (zero <= 0.0) return 0.0;
  if (hi > n - 1) hi = n - 1;
  if (hi <= lo) return 0.0;
  double best = -1e30; int at = lo;
  for (int lag = lo; lag <= hi; lag++) {
    double s = 0.0;
    for (int i = 0; i + lag < n; i++) s += x[i] * x[i + lag];
    s /= zero;
    if (s > best) { best = s; at = lag; }
  }
  if (best_lag) *best_lag = at;
  return best;
}

static double pitch_confidence(const float *seg, int n, double rate) {
  if (n < 64) return 0.0;
  int any = 0;
  for (int i = 0; i < n; i++) if (seg[i] != 0.f) { any = 1; break; }
  if (!any) return 0.0;
  double *x = xalloc((size_t)n * sizeof(double)), mean = 0.0;
  for (int i = 0; i < n; i++) mean += seg[i];
  mean /= n;
  for (int i = 0; i < n; i++) x[i] = seg[i] - mean;
  int lo = (int)(rate / BASS_F0_MAX), hi = (int)(rate / BASS_F0_MIN);
  double peak = autocorr_peak(x, n, lo, hi, NULL);
  free(x);
  return peak;
}

static double estimate_bpm(const double *env, int n, double fps, int *detected) {
  *detected = 0;
  if (n < 8) return DEFAULT_BPM;
  int any = 0;
  for (int i = 0; i < n; i++) if (env[i] > 0.0) { any = 1; break; }
  if (!any) return DEFAULT_BPM;
  double *x = xalloc((size_t)n * sizeof(double)), mean = 0.0;
  for (int i = 0; i < n; i++) mean += env[i];
  mean /= n;
  for (int i = 0; i < n; i++) x[i] = env[i] - mean;
  int lo = (int)lround(60.0 * fps / BPM_MAX); if (lo < 1) lo = 1;
  int hi = (int)lround(60.0 * fps / BPM_MIN);
  int best = lo;
  double peak = autocorr_peak(x, n, lo, hi, &best);
  free(x);
  if (peak <= 0.1) return DEFAULT_BPM;          /* no usable periodicity */
  double bpm = 60.0 * fps / best;
  while (bpm < BPM_MIN) bpm *= 2.0;
  while (bpm > BPM_MAX) bpm /= 2.0;
  if (!(bpm >= BPM_MIN && bpm <= BPM_MAX)) return DEFAULT_BPM;
  *detected = 1;
  return bpm;
}

/* --- velocity ------------------------------------------------------------- */

static void velocities(const float *row, int n, const int *frames, int count,
                       double fps, int *out) {
  if (!count) return;
  int half = (int)lround(0.025 * fps); if (half < 1) half = 1;
  float *peaks = xalloc((size_t)count * sizeof(float));
  float top = 0.f;
  for (int i = 0; i < count; i++) {
    int lo = frames[i] - half < 0 ? 0 : frames[i] - half;
    int hi = frames[i] + half + 1 > n ? n : frames[i] + half + 1;
    float p = 0.f;
    for (int j = lo; j < hi; j++) if (row[j] > p) p = row[j];
    peaks[i] = p;
    if (p > top) top = p;
  }
  for (int i = 0; i < count; i++) {
    if (top <= 0.f) { out[i] = 64; continue; }
    long v = lround(1.0 + 126.0 * (peaks[i] / top));
    out[i] = (int)(v < 1 ? 1 : v > 127 ? 127 : v);
  }
  free(peaks);
}

/* --- capture WAV ---------------------------------------------------------- */

static uint32_t rd_u32(const unsigned char *p) {
  return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint16_t rd_u16(const unsigned char *p) { return (uint16_t)(p[0] | p[1] << 8); }

/* Accepts WAVE_FORMAT_IEEE_FLOAT (tag 3, the native recorder's output) and
 * integer PCM, exactly as the reference reader does. */
static float *read_capture_wav(const char *path, size_t *count, int *rate) {
  FILE *f = fopen(path, "rb");
  if (!f) return NULL;
  fseek(f, 0, SEEK_END); long size = ftell(f); fseek(f, 0, SEEK_SET);
  if (size < 12) { fclose(f); return NULL; }
  unsigned char *raw = xalloc((size_t)size);
  if (fread(raw, 1, (size_t)size, f) != (size_t)size) { fclose(f); free(raw); return NULL; }
  fclose(f);
  if (memcmp(raw, "RIFF", 4) || memcmp(raw + 8, "WAVE", 4)) { free(raw); return NULL; }
  int tag = 0, channels = 0, bits = 0; *rate = 0;
  const unsigned char *data = NULL; size_t data_size = 0;
  size_t pos = 12;
  while (pos + 8 <= (size_t)size) {
    uint32_t chunk = rd_u32(raw + pos + 4);
    if (pos + 8 + chunk > (size_t)size) chunk = (uint32_t)((size_t)size - pos - 8);
    if (!memcmp(raw + pos, "fmt ", 4) && chunk >= 16) {
      tag = rd_u16(raw + pos + 8); channels = rd_u16(raw + pos + 10);
      *rate = (int)rd_u32(raw + pos + 12); bits = rd_u16(raw + pos + 22);
    } else if (!memcmp(raw + pos, "data", 4)) {
      data = raw + pos + 8; data_size = chunk;
    }
    pos += 8 + chunk + (chunk & 1);
  }
  if (!data || !*rate || (channels != 1 && channels != 2)) { free(raw); return NULL; }
  size_t total = 0; float *samples = NULL;
  if (tag == 3 && bits == 32) {
    total = data_size / 4;
    samples = xalloc(total * sizeof(float));
    memcpy(samples, data, total * 4);
  } else if (tag == 1 && bits == 16) {
    total = data_size / 2;
    samples = xalloc(total * sizeof(float));
    for (size_t i = 0; i < total; i++)
      samples[i] = (float)(int16_t)rd_u16(data + i * 2) / 32768.0f;
  } else if (tag == 1 && bits == 24) {
    /* What softcut writes. Three little-endian bytes, sign-extended by hand
       because there is no 24-bit integer to widen from. */
    total = data_size / 3;
    samples = xalloc(total * sizeof(float));
    for (size_t i = 0; i < total; i++) {
      const unsigned char *at = data + i * 3;
      int32_t value = (int32_t)((uint32_t)at[0] | ((uint32_t)at[1] << 8) | ((uint32_t)at[2] << 16));
      if (value & 0x800000) value -= 0x1000000;
      samples[i] = (float)value / 8388608.0f;
    }
  } else if (tag == 1 && bits == 32) {
    total = data_size / 4;
    samples = xalloc(total * sizeof(float));
    for (size_t i = 0; i < total; i++)
      samples[i] = (float)(int32_t)rd_u32(data + i * 4) / 2147483648.0f;
  } else { free(raw); return NULL; }
  free(raw);
  total = (total / channels) * channels;
  for (size_t i = 0; i < total; i++)
    if (!isfinite(samples[i])) { free(samples); return NULL; }
  if (channels == 2) {
    size_t n = total / 2;
    for (size_t i = 0; i < n; i++) samples[i] = 0.5f * (samples[2*i] + samples[2*i+1]);
    total = n;
  }
  *count = total;
  return samples;
}

/* Linear interpolation onto the analysis rate, matching np.interp over a
 * linspace of the same length the reference builds. */
static float *resample(const float *x, size_t n, int from, int to, size_t *out_n) {
  if (from == to || n == 0) {
    float *copy = xalloc((n ? n : 1) * sizeof(float));
    memcpy(copy, x, n * sizeof(float));
    *out_n = n;
    return copy;
  }
  size_t m = (size_t)llround((double)n * to / (double)from);
  if (m < 1) m = 1;
  float *out = xalloc(m * sizeof(float));
  for (size_t i = 0; i < m; i++) {
    double pos = (m > 1) ? (double)i * (n - 1) / (double)(m - 1) : 0.0;
    size_t lo = (size_t)pos;
    if (lo >= n - 1) { out[i] = x[n - 1]; continue; }
    double frac = pos - lo;
    out[i] = (float)(x[lo] * (1.0 - frac) + x[lo + 1] * frac);
  }
  *out_n = m;
  return out;
}

/* --- request and result --------------------------------------------------- */

/* The request is written by the worker, not by a user, so this only needs to
 * find the few fields the contract defines. */
static const char *find_key(const char *json, const char *key) {
  size_t n = strlen(key);
  for (const char *p = json; (p = strchr(p, '"')); p++) {
    if (!strncmp(p + 1, key, n) && p[1 + n] == '"') {
      const char *q = p + 2 + n;
      while (*q && *q != ':') q++;
      return *q ? q + 1 : NULL;
    }
  }
  return NULL;
}

static int read_string(const char *at, char *out, size_t cap) {
  while (*at == ' ' || *at == '\t' || *at == '\n' || *at == '\r') at++;
  if (*at != '"') return -1;
  at++;
  size_t i = 0;
  while (*at && *at != '"') {
    if (*at == '\\' && at[1]) at++;
    if (i + 1 >= cap) return -1;
    out[i++] = *at++;
  }
  out[i] = 0;
  return *at == '"' ? 0 : -1;
}

static int read_number(const char *at, double *out) {
  char *end = NULL;
  double v = strtod(at, &end);
  if (end == at) return -1;
  *out = v;
  return 0;
}

typedef struct { const char *lane; long sample_index; int velocity; double confidence; } candidate_t;

static int cmp_candidate(const void *a, const void *b) {
  const candidate_t *x = a, *y = b;
  if (x->sample_index != y->sample_index) return x->sample_index < y->sample_index ? -1 : 1;
  int xi = 0, yi = 0;
  for (int i = 0; i < 4; i++) { if (!strcmp(x->lane, LANES[i])) xi = i; if (!strcmp(y->lane, LANES[i])) yi = i; }
  return xi - yi;
}

int main(int argc, char **argv) {
  const char *request_path = NULL, *result_path = NULL, *source_path = NULL, *template_path = NULL;
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--request") && i + 1 < argc) request_path = argv[++i];
    else if (!strcmp(argv[i], "--result") && i + 1 < argc) result_path = argv[++i];
    else if (!strcmp(argv[i], "--source") && i + 1 < argc) source_path = argv[++i];
    else if (!strcmp(argv[i], "--templates") && i + 1 < argc) template_path = argv[++i];
  }
  if (!request_path || !result_path) {
    fprintf(stderr, "usage: %s --request FILE --result FILE [--source FILE] [--templates FILE]\n", argv[0]);
    return 2;
  }
  /* The worker invokes a backend with only --request and --result, so the
   * launcher bakes the data paths in when it compiles this. */
#ifdef RD_TEMPLATE_PATH
  if (!template_path) template_path = RD_TEMPLATE_PATH;
#else
  if (!template_path) template_path = "data/nmf_drum_templates.bin";
#endif
#ifdef RD_SOURCE_PATH
  if (!source_path) source_path = RD_SOURCE_PATH;
#endif

  FILE *rf = fopen(request_path, "rb");
  if (!rf) { fprintf(stderr, "cannot read request\n"); return 2; }
  fseek(rf, 0, SEEK_END); long rsize = ftell(rf); fseek(rf, 0, SEEK_SET);
  char *request = xalloc((size_t)rsize + 1);
  if (fread(request, 1, (size_t)rsize, rf) != (size_t)rsize) { fclose(rf); return 2; }
  fclose(rf);
  request[rsize] = 0;

  char wav_path[4096];
  const char *at = find_key(request, "wav_path");
  if (!at || read_string(at, wav_path, sizeof wav_path)) { fprintf(stderr, "wav_path is required\n"); return 2; }

  /* A correction the player accepted outranks the automatic estimate. */
  int have_alignment = 0; double aligned_bpm = 0.0, aligned_origin = 0.0;
  const char *align = find_key(request, "alignment");
  if (align) {
    const char *b = find_key(align, "bpm"), *o = find_key(align, "origin_sample");
    if (b && !read_number(b, &aligned_bpm) && isfinite(aligned_bpm) &&
        aligned_bpm >= BPM_MIN && aligned_bpm <= BPM_MAX) {
      have_alignment = 1;
      if (!o || read_number(o, &aligned_origin) || !isfinite(aligned_origin) || aligned_origin < 0)
        aligned_origin = 0.0;
      else aligned_origin = floor(aligned_origin + 0.5);
    }
  }

  templates_t tpl;
  if (load_templates(template_path, &tpl)) { fprintf(stderr, "cannot read templates\n"); return 2; }
  char backend_hex[65] = {0}, template_hex[65] = {0};
  if (sha256_file(template_path, template_hex)) { fprintf(stderr, "cannot hash templates\n"); return 2; }
  if (source_path && sha256_file(source_path, backend_hex)) { fprintf(stderr, "cannot hash source\n"); return 2; }

  size_t n = 0; int source_rate = 0;
  float *mono = read_capture_wav(wav_path, &n, &source_rate);
  if (!mono) { fprintf(stderr, "cannot read capture\n"); return 2; }

  double bpm = have_alignment ? aligned_bpm : DEFAULT_BPM;
  int detected = have_alignment;
  long origin = have_alignment ? (long)aligned_origin : 0;
  const char *mode = have_alignment ? "manual" : "auto";

  candidate_t *cands = NULL; int ncand = 0;
  int any = 0;
  for (size_t i = 0; i < n; i++) if (mono[i] != 0.f) { any = 1; break; }
  if (any) {
    size_t an = 0;
    float *analysis = resample(mono, n, source_rate, SR, &an);
    int frames = 0;
    float *V = stft_magnitude(analysis, an, &frames);
    if (V && frames >= 5) {
      float *Gd = pfnmf(V, tpl.data, tpl.lanes, frames);
      double fps = (double)SR / HOP;
      double *envelope = xalloc((size_t)frames * sizeof(double));
      int *picked = xalloc((size_t)frames * sizeof(int));
      int *vel = xalloc((size_t)frames * sizeof(int));
      cands = xalloc((size_t)frames * 4 * sizeof(candidate_t));
      static const char *const column[3] = {"BD", "SD", "CHH"};
      static const char *const lane_name[3] = {"BD", "SD", "CYM"};
      int *low_frames = xalloc((size_t)frames * sizeof(int));
      int low_count = 0; const float *low_row = NULL;
      for (int lane = 0; lane < 3; lane++) {
        int col = template_column(&tpl, column[lane]);
        if (col < 0) continue;
        const float *row = Gd + (size_t)col * frames;
        float top = 0.f;
        for (int f = 0; f < frames; f++) if (row[f] > top) top = row[f];
        for (int f = 0; f < frames; f++) envelope[f] += row[f] / (top + EPSF);
        int count = pick_peaks(row, frames, DEFAULT_DELTA[lane], picked);
        velocities(row, frames, picked, count, fps, vel);
        if (lane == 0) { memcpy(low_frames, picked, (size_t)count * sizeof(int)); low_count = count; low_row = row; }
        for (int i = 0; i < count; i++) {
          double conf = row[picked[i]] / (top + EPSF);
          cands[ncand++] = (candidate_t){lane_name[lane],
            lround((double)picked[i] * HOP * source_rate / (double)SR),
            vel[i], conf > 1.0 ? 1.0 : conf};
        }
      }
      /* BASS reclassifies low-band onsets that hold a stable pitch; the lanes
       * are deliberately not exclusive. */
      int span = (int)(PITCH_WINDOW_SECONDS * source_rate);
      int *bass = xalloc((size_t)(low_count ? low_count : 1) * sizeof(int));
      int bass_count = 0;
      for (int i = 0; i < low_count; i++) {
        long start = lround((double)low_frames[i] * HOP * source_rate / (double)SR);
        if (start < 0 || (size_t)start >= n) continue;
        int avail = (int)(n - (size_t)start); if (avail > span) avail = span;
        if (pitch_confidence(mono + start, avail, source_rate) >= PITCH_CONFIDENCE_CUT)
          bass[bass_count++] = low_frames[i];
      }
      if (bass_count && low_row) {
        velocities(low_row, frames, bass, bass_count, fps, vel);
        float top = 0.f;
        for (int f = 0; f < frames; f++) if (low_row[f] > top) top = low_row[f];
        for (int i = 0; i < bass_count; i++) {
          double conf = low_row[bass[i]] / (top + EPSF);
          cands[ncand++] = (candidate_t){"BASS",
            lround((double)bass[i] * HOP * source_rate / (double)SR),
            vel[i], conf > 1.0 ? 1.0 : conf};
        }
      }
      if (!have_alignment) bpm = estimate_bpm(envelope, frames, fps, &detected);
      free(bass); free(low_frames); free(vel); free(picked); free(envelope); free(Gd);
    }
    free(V); free(analysis);
  }
  qsort(cands, (size_t)ncand, sizeof(candidate_t), cmp_candidate);

  FILE *out = fopen(result_path, "wb");
  if (!out) { fprintf(stderr, "cannot write result\n"); return 2; }
  fprintf(out, "{\"bpm\":%.10g,\"tempo_detected\":%s,\"origin_sample\":%ld,\"tempo_mode\":\"%s\",",
          bpm, detected ? "true" : "false", origin, mode);
  fprintf(out, "\"detector\":{\"backend_id\":\"%s\",\"backend_sha256\":\"%s\",\"template_sha256\":\"%s\"},",
          BACKEND_ID, backend_hex, template_hex);
  fprintf(out, "\"lane_onset_gates\":{");
  for (int i = 0; i < 4; i++)
    fprintf(out, "%s\"%s\":%.10g", i ? "," : "", LANES[i], (double)DEFAULT_DELTA[i]);
  fprintf(out, "},\"candidates\":[");
  for (int i = 0; i < ncand; i++)
    fprintf(out, "%s{\"lane\":\"%s\",\"sample_index\":%ld,\"velocity\":%d,\"confidence\":%.10g}",
            i ? "," : "", cands[i].lane, cands[i].sample_index, cands[i].velocity, cands[i].confidence);
  fprintf(out, "]}\n");
  fclose(out);
  free(cands); free(mono); free(tpl.data); free(request);
  return 0;
}
