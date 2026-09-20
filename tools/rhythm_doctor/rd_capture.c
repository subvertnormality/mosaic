/* RD-01 standalone JACK capture spike: no Mosaic routing, monitoring or output calls. */
#define _POSIX_C_SOURCE 200809L
#include <jack/jack.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <time.h>

_Static_assert(ATOMIC_INT_LOCK_FREE == 2, "RD capture requires lock-free int atomics");
_Static_assert(sizeof(unsigned int) == 4, "RD capture requires 32-bit frame counters");

enum rd_capture_state { RD_CAPTURE_READY, RD_CAPTURE_ARMED, RD_CAPTURE_CAPTURING,
  RD_CAPTURE_STOP_REQUESTED, RD_CAPTURE_COMPLETED, RD_CAPTURE_CANCELLED, RD_CAPTURE_FAILED };
enum rd_capture_error { RD_CAPTURE_OK, RD_CAPTURE_ERROR_BAD_COMMAND, RD_CAPTURE_ERROR_OVERFLOW,
  RD_CAPTURE_ERROR_XRUN, RD_CAPTURE_ERROR_PUBLISH, RD_CAPTURE_ERROR_DISCONTINUITY,
  RD_CAPTURE_ERROR_SERVER_SHUTDOWN };
/* Why a preflight failed.  "Busy" was once the answer to every one of these,
   which sent a player looking at their inputs when the audio server was
   simply unreachable. */
enum rd_preflight_reason { RD_PREFLIGHT_OK, RD_PREFLIGHT_AUDIO_SERVER_UNAVAILABLE,
  RD_PREFLIGHT_UNSUPPORTED_RATE, RD_PREFLIGHT_OUT_OF_MEMORY, RD_PREFLIGHT_INPUT_UNAVAILABLE };

struct rd_capture {
  jack_client_t *client; jack_port_t *input[2]; float *left, *right;
  uint32_t capacity, sample_rate;
  atomic_uint frames, start_frame, end_frame, expected_frame;
  atomic_uint outcome, callback_refs;
  _Atomic int server_dead, destroying, pcm_locked;
  uint64_t preflight_nanoseconds;
};

#define RD_OUTCOME_SHIFT 8u
#define RD_OUTCOME(state, error) (((unsigned)(state) << RD_OUTCOME_SHIFT) | (unsigned)(error))
#define RD_OUTCOME_STATE(outcome) ((int)((outcome) >> RD_OUTCOME_SHIFT))
#define RD_OUTCOME_ERROR(outcome) ((int)((outcome) & 0xffu))

/* Never overwrite a cancellation or completed result with a late callback failure. */
static int fail_active(struct rd_capture *c, int error) {
  unsigned outcome = atomic_load_explicit(&c->outcome, memory_order_acquire);
  int state = RD_OUTCOME_STATE(outcome);
  while (state == RD_CAPTURE_ARMED || state == RD_CAPTURE_CAPTURING || state == RD_CAPTURE_STOP_REQUESTED) {
    if (atomic_compare_exchange_weak_explicit(&c->outcome, &outcome, RD_OUTCOME(RD_CAPTURE_FAILED, error),
        memory_order_acq_rel, memory_order_acquire)) {
      return 1;
    }
    state = RD_OUTCOME_STATE(outcome);
  }
  return 0;
}

static int callback_acquire(struct rd_capture *c) {
  if (atomic_load_explicit(&c->destroying, memory_order_acquire)) return 0;
  atomic_fetch_add_explicit(&c->callback_refs, 1, memory_order_acq_rel);
  if (atomic_load_explicit(&c->destroying, memory_order_acquire)) {
    atomic_fetch_sub_explicit(&c->callback_refs, 1, memory_order_release); return 0;
  }
  return 1;
}
static void callback_release(struct rd_capture *c) {
  atomic_fetch_sub_explicit(&c->callback_refs, 1, memory_order_release);
}

/* This function is the whole audio-thread capture path: atomics plus bounded PCM copies. */
static int capture_process(struct rd_capture *c, uint64_t frame_time,
                           const float *left, const float *right, uint32_t count) {
  unsigned outcome = atomic_load_explicit(&c->outcome, memory_order_acquire);
  int state = RD_OUTCOME_STATE(outcome);
  if (state == RD_CAPTURE_ARMED) {
    unsigned expected = RD_OUTCOME(RD_CAPTURE_ARMED, RD_CAPTURE_OK);
    if (atomic_compare_exchange_strong_explicit(&c->outcome, &expected, RD_OUTCOME(RD_CAPTURE_CAPTURING, RD_CAPTURE_OK),
                                                memory_order_acq_rel, memory_order_acquire)) {
      uint32_t frame = (uint32_t)frame_time;
      atomic_store_explicit(&c->start_frame, frame, memory_order_release);
      atomic_store_explicit(&c->end_frame, frame, memory_order_release);
      atomic_store_explicit(&c->expected_frame, frame, memory_order_release);
      atomic_store_explicit(&c->frames, 0, memory_order_release); state = RD_CAPTURE_CAPTURING;
    } else state = RD_OUTCOME_STATE(expected);
  }
  if (state == RD_CAPTURE_STOP_REQUESTED) {
    unsigned expected = RD_OUTCOME(RD_CAPTURE_STOP_REQUESTED, RD_CAPTURE_OK);
    atomic_compare_exchange_strong_explicit(&c->outcome, &expected, RD_OUTCOME(RD_CAPTURE_COMPLETED, RD_CAPTURE_OK),
      memory_order_acq_rel, memory_order_acquire);
    return 0;
  }
  if (state != RD_CAPTURE_CAPTURING) return 0;
  uint32_t offset = atomic_load_explicit(&c->frames, memory_order_relaxed);
  uint32_t frame = (uint32_t)frame_time;
  if (frame != atomic_load_explicit(&c->expected_frame, memory_order_acquire)) {
    fail_active(c, RD_CAPTURE_ERROR_DISCONTINUITY); return 0;
  }
  if (offset > c->capacity) { fail_active(c, RD_CAPTURE_ERROR_OVERFLOW); return 0; }
  uint32_t copied = count;
  if (copied > c->capacity - offset) copied = c->capacity - offset;
  memcpy(c->left + offset, left, (size_t)copied * sizeof(*left));
  memcpy(c->right + offset, right, (size_t)copied * sizeof(*right));
  offset += copied;
  atomic_store_explicit(&c->end_frame,
    frame + copied, memory_order_release);
  atomic_store_explicit(&c->expected_frame, frame + count, memory_order_release);
  atomic_store_explicit(&c->frames, offset, memory_order_release);
  if (offset == c->capacity) {
    unsigned expected = RD_OUTCOME(RD_CAPTURE_CAPTURING, RD_CAPTURE_OK);
    atomic_compare_exchange_strong_explicit(&c->outcome, &expected, RD_OUTCOME(RD_CAPTURE_COMPLETED, RD_CAPTURE_OK),
      memory_order_acq_rel, memory_order_acquire);
  }
  return 0;
}

static int jack_process(jack_nframes_t count, void *context) {
  struct rd_capture *c = context;
  if (!callback_acquire(c)) return 0;
  int result = capture_process(c, jack_last_frame_time(c->client),
    jack_port_get_buffer(c->input[0], count), jack_port_get_buffer(c->input[1], count), count);
  callback_release(c); return result;
}
static int jack_xrun(void *context) {
  struct rd_capture *c = context; if (!callback_acquire(c)) return 0;
  int state = RD_OUTCOME_STATE(atomic_load_explicit(&c->outcome, memory_order_acquire));
  if (state == RD_CAPTURE_ARMED || state == RD_CAPTURE_CAPTURING || state == RD_CAPTURE_STOP_REQUESTED)
    fail_active(c, RD_CAPTURE_ERROR_XRUN);
  callback_release(c);
  return 0;
}
static void jack_shutdown(void *context) {
  struct rd_capture *c = context;
  if (!callback_acquire(c)) return;
  atomic_store_explicit(&c->server_dead, 1, memory_order_release);
  fail_active(c, RD_CAPTURE_ERROR_SERVER_SHUTDOWN);
  callback_release(c);
}
static struct rd_capture *allocate_capture(uint32_t rate, uint32_t seconds) {
  if (!rate || !seconds || seconds > 45 || (uint64_t)rate * seconds > UINT32_MAX ||
      (uint64_t)rate * seconds > SIZE_MAX / sizeof(float)) return NULL;
  struct rd_capture *c = calloc(1, sizeof(*c)); if (!c) return NULL;
  c->capacity = rate * seconds; c->sample_rate = rate;
  c->left = calloc((size_t)c->capacity, sizeof(*c->left)); c->right = calloc((size_t)c->capacity, sizeof(*c->right));
  if (!c->left || !c->right) { free(c->left); free(c->right); free(c); return NULL; }
  atomic_init(&c->frames, 0); atomic_init(&c->start_frame, 0); atomic_init(&c->end_frame, 0); atomic_init(&c->expected_frame, 0);
  atomic_init(&c->outcome, RD_OUTCOME(RD_CAPTURE_READY, RD_CAPTURE_OK)); atomic_init(&c->callback_refs, 0);
  atomic_init(&c->server_dead, 0); atomic_init(&c->destroying, 0); atomic_init(&c->pcm_locked, 0);
  if (!atomic_is_lock_free(&c->frames) || !atomic_is_lock_free(&c->start_frame) ||
      !atomic_is_lock_free(&c->end_frame) || !atomic_is_lock_free(&c->expected_frame) ||
      !atomic_is_lock_free(&c->outcome) || !atomic_is_lock_free(&c->callback_refs)) {
    free(c->left); free(c->right); free(c); return NULL;
  }
  long page_size = sysconf(_SC_PAGESIZE); if (page_size <= 0) page_size = 4096;
  size_t stride = (size_t)page_size / sizeof(float); if (!stride) stride = 1;
  volatile float *left = c->left, *right = c->right;
  for (size_t i = 0; i < c->capacity; i += stride) { left[i] = 0.0f; right[i] = 0.0f; }
  left[c->capacity - 1] = 0.0f; right[c->capacity - 1] = 0.0f;
  int left_locked = !mlock(c->left, (size_t)c->capacity * sizeof(*c->left));
  int right_locked = !mlock(c->right, (size_t)c->capacity * sizeof(*c->right));
  if (left_locked && right_locked) atomic_store(&c->pcm_locked, 1);
  else {
    if (left_locked) munlock(c->left, (size_t)c->capacity * sizeof(*c->left));
    if (right_locked) munlock(c->right, (size_t)c->capacity * sizeof(*c->right));
  }
  return c;
}

/* Call at mode entry, before Record, to reserve the JACK client and 45s stereo PCM. */
struct rd_capture *rd_capture_preflight_because(uint32_t seconds, int *reason) {
  int ignored; if (!reason) reason = &ignored;
  *reason = RD_PREFLIGHT_OK;
  struct timespec began, ended; clock_gettime(CLOCK_MONOTONIC, &began);
  jack_status_t status = 0; jack_client_t *client = jack_client_open("mosaic-rd-capture", JackNoStartServer, &status);
  if (!client) { *reason = RD_PREFLIGHT_AUDIO_SERVER_UNAVAILABLE; return NULL; }
  if (jack_get_sample_rate(client) < 8000 || jack_get_sample_rate(client) > 192000) {
    jack_client_close(client); *reason = RD_PREFLIGHT_UNSUPPORTED_RATE; return NULL;
  }
  struct rd_capture *c = allocate_capture(jack_get_sample_rate(client), seconds);
  if (!c) { jack_client_close(client); *reason = RD_PREFLIGHT_OUT_OF_MEMORY; return NULL; }
  c->client = client;
  c->input[0] = jack_port_register(client, "input_l", JACK_DEFAULT_AUDIO_TYPE, JackPortIsInput, 0);
  c->input[1] = jack_port_register(client, "input_r", JACK_DEFAULT_AUDIO_TYPE, JackPortIsInput, 0);
  if (!c->input[0] || !c->input[1] || jack_set_process_callback(client, jack_process, c) ||
      jack_set_xrun_callback(client, jack_xrun, c) || (jack_on_shutdown(client, jack_shutdown, c), 0) || jack_activate(client)) {
    if (c->input[0]) jack_port_unregister(client, c->input[0]);
    if (c->input[1]) jack_port_unregister(client, c->input[1]);
    jack_client_close(client); free(c->left); free(c->right); free(c);
    *reason = RD_PREFLIGHT_INPUT_UNAVAILABLE; return NULL;
  }
  clock_gettime(CLOCK_MONOTONIC, &ended);
  int64_t elapsed = ((int64_t)ended.tv_sec - (int64_t)began.tv_sec) * 1000000000ll +
                    ((int64_t)ended.tv_nsec - (int64_t)began.tv_nsec);
  c->preflight_nanoseconds = elapsed > 0 ? (uint64_t)elapsed : 0;
  return c;
}
/* The original one-argument entry point, kept for callers that only need to
   know whether a capture could be acquired. */
struct rd_capture *rd_capture_preflight(uint32_t seconds) {
  return rd_capture_preflight_because(seconds, NULL);
}
void rd_capture_destroy(struct rd_capture *c) {
  if (!c) return;
  atomic_store_explicit(&c->destroying, 1, memory_order_release);
  atomic_store_explicit(&c->outcome, RD_OUTCOME(RD_CAPTURE_CANCELLED, RD_CAPTURE_OK), memory_order_release);
  if (c->client && !atomic_load_explicit(&c->server_dead, memory_order_acquire)) jack_deactivate(c->client);
  while (atomic_load_explicit(&c->callback_refs, memory_order_acquire)) { }
  if (c->client) jack_client_close(c->client);
  if (atomic_load_explicit(&c->pcm_locked, memory_order_acquire)) {
    munlock(c->left, (size_t)c->capacity * sizeof(*c->left));
    munlock(c->right, (size_t)c->capacity * sizeof(*c->right));
  }
  free(c->left); free(c->right); free(c);
}
int rd_capture_start(struct rd_capture *c) {
  if (!c) return -1;
  unsigned expected = RD_OUTCOME(RD_CAPTURE_READY, RD_CAPTURE_OK);
  return atomic_compare_exchange_strong_explicit(&c->outcome, &expected, RD_OUTCOME(RD_CAPTURE_ARMED, RD_CAPTURE_OK),
    memory_order_acq_rel, memory_order_acquire) ? 0 : -1;
}
int rd_capture_stop(struct rd_capture *c) {
  if (!c) return -1;
  unsigned expected = RD_OUTCOME(RD_CAPTURE_ARMED, RD_CAPTURE_OK);
  if (atomic_compare_exchange_strong_explicit(&c->outcome, &expected, RD_OUTCOME(RD_CAPTURE_STOP_REQUESTED, RD_CAPTURE_OK),
      memory_order_acq_rel, memory_order_acquire)) return 0;
  expected = RD_OUTCOME(RD_CAPTURE_CAPTURING, RD_CAPTURE_OK);
  return atomic_compare_exchange_strong_explicit(&c->outcome, &expected, RD_OUTCOME(RD_CAPTURE_STOP_REQUESTED, RD_CAPTURE_OK),
    memory_order_acq_rel, memory_order_acquire) ? 0 : -1;
}
int rd_capture_cancel(struct rd_capture *c) {
  if (!c) return -1;
  unsigned outcome = atomic_load_explicit(&c->outcome, memory_order_acquire);
  int state = RD_OUTCOME_STATE(outcome);
  while (state == RD_CAPTURE_ARMED || state == RD_CAPTURE_CAPTURING || state == RD_CAPTURE_STOP_REQUESTED)
    if (atomic_compare_exchange_weak_explicit(&c->outcome, &outcome, RD_OUTCOME(RD_CAPTURE_CANCELLED, RD_CAPTURE_OK),
      memory_order_acq_rel, memory_order_acquire)) return 0;
    else state = RD_OUTCOME_STATE(outcome);
  return -1;
}
int rd_capture_state(const struct rd_capture *c) { return c ? RD_OUTCOME_STATE(atomic_load_explicit(&c->outcome, memory_order_acquire)) : RD_CAPTURE_FAILED; }
int rd_capture_error(const struct rd_capture *c) { return c ? RD_OUTCOME_ERROR(atomic_load_explicit(&c->outcome, memory_order_acquire)) : RD_CAPTURE_ERROR_BAD_COMMAND; }
uint64_t rd_capture_frames(const struct rd_capture *c) { return c ? atomic_load_explicit(&c->frames, memory_order_acquire) : 0; }
uint64_t rd_capture_start_frame(const struct rd_capture *c) { return c ? atomic_load_explicit(&c->start_frame, memory_order_acquire) : 0; }
uint64_t rd_capture_end_frame(const struct rd_capture *c) { return c ? atomic_load_explicit(&c->end_frame, memory_order_acquire) : 0; }
uint32_t rd_capture_sample_rate(const struct rd_capture *c) { return c ? c->sample_rate : 0; }
uint64_t rd_capture_preflight_nanoseconds(const struct rd_capture *c) { return c ? c->preflight_nanoseconds : 0; }
int rd_capture_pcm_locked(const struct rd_capture *c) { return c && atomic_load_explicit(&c->pcm_locked, memory_order_acquire); }
const char *rd_capture_input_port(const struct rd_capture *c, unsigned channel) {
  return c && channel < 2 && c->input[channel] ? jack_port_name(c->input[channel]) : NULL;
}

/* Atomic publication: the completed recording is written to a sibling .tmp then renamed. */
static int fsync_parent_directory(const char *path) {
  const char *slash = strrchr(path, '/');
  char *directory;
  if (!slash) directory = strdup(".");
  else if (slash == path) directory = strdup("/");
  else {
    size_t length = (size_t)(slash - path);
    directory = malloc(length + 1);
    if (directory) { memcpy(directory, path, length); directory[length] = '\0'; }
  }
  if (!directory) return -1;
  int fd = open(directory, O_RDONLY | O_DIRECTORY); free(directory);
  if (fd < 0) return -1;
  int result = fsync(fd); close(fd); return result;
}
int rd_capture_publish_wav(struct rd_capture *c, const char *path) {
  if (!c || !path || rd_capture_state(c) != RD_CAPTURE_COMPLETED) return -1;
  if (c->sample_rate < 8000 || c->sample_rate > 192000) return -1;
  size_t length = strlen(path); char *temporary = malloc(length + 12); if (!temporary) return -1;
  memcpy(temporary, path, length); memcpy(temporary + length, ".tmp.XXXXXX", 12);
  int temporary_fd = mkstemp(temporary); FILE *f = temporary_fd >= 0 ? fdopen(temporary_fd, "wb") : NULL;
  if (!f && temporary_fd >= 0) { close(temporary_fd); temporary_fd = -1; }
  uint64_t frames = rd_capture_frames(c); uint64_t byte_count = frames * 8;
  if (byte_count > UINT32_MAX - 36) { if (f) fclose(f); if (temporary_fd >= 0) remove(temporary); free(temporary); return -1; }
  uint32_t bytes = (uint32_t)byte_count;
  int ok = f && fwrite("RIFF", 1, 4, f) == 4 && fwrite(&(uint32_t){36 + bytes}, 4, 1, f) == 1 &&
    fwrite("WAVEfmt ", 1, 8, f) == 8 && fwrite(&(uint32_t){16}, 4, 1, f) == 1 &&
    fwrite(&(uint16_t){3}, 2, 1, f) == 1 && fwrite(&(uint16_t){2}, 2, 1, f) == 1 &&
    fwrite(&c->sample_rate, 4, 1, f) == 1 && fwrite(&(uint32_t){c->sample_rate * 8}, 4, 1, f) == 1 &&
    fwrite(&(uint16_t){8}, 2, 1, f) == 1 && fwrite(&(uint16_t){32}, 2, 1, f) == 1 &&
    fwrite("data", 1, 4, f) == 4 && fwrite(&bytes, 4, 1, f) == 1;
  for (uint64_t i = 0; ok && i < frames; ++i)
    ok = fwrite(c->left + i, sizeof(float), 1, f) == 1 && fwrite(c->right + i, sizeof(float), 1, f) == 1;
  if (f) {
    if (fflush(f) || fsync(fileno(f))) ok = 0;
    if (fclose(f)) ok = 0;
  }
  f = NULL;
  /* link is atomic name publication and refuses to overwrite a prior asset. */
  if (!ok || link(temporary, path) || remove(temporary) || fsync_parent_directory(path)) {
    remove(temporary); free(temporary);
    unsigned expected = RD_OUTCOME(RD_CAPTURE_COMPLETED, RD_CAPTURE_OK);
    atomic_compare_exchange_strong_explicit(&c->outcome, &expected,
      RD_OUTCOME(RD_CAPTURE_COMPLETED, RD_CAPTURE_ERROR_PUBLISH), memory_order_acq_rel, memory_order_acquire);
    return -1;
  }
  free(temporary); return 0;
}

#ifdef RD_CAPTURE_TESTING
struct rd_capture *rd_capture_test_create(uint32_t rate, uint32_t seconds) { return allocate_capture(rate, seconds); }
void rd_capture_test_destroy(struct rd_capture *c) { rd_capture_destroy(c); }
void rd_capture_test_process(struct rd_capture *c, uint64_t time, const float *l, const float *r, uint32_t n) { capture_process(c, time, l, r, n); }
void rd_capture_test_xrun(struct rd_capture *c) { jack_xrun(c); }
uint32_t rd_capture_test_copy(const struct rd_capture *c, float *l, float *r, uint32_t max) {
  uint64_t n = rd_capture_frames(c); if (n > max) n = max;
  memcpy(l, c->left, (size_t)n * sizeof(*l)); memcpy(r, c->right, (size_t)n * sizeof(*r)); return (uint32_t)n;
}
#endif
