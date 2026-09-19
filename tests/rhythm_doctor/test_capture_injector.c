#define _DEFAULT_SOURCE
#include <jack/jack.h>
#include <signal.h>
#include <stdint.h>
#include <unistd.h>

static volatile sig_atomic_t keep_running = 1;
static uint64_t frame_index;

static void stop(int ignored) { (void)ignored; keep_running = 0; }

static int process(jack_nframes_t count, void *ignored) {
  jack_default_audio_sample_t *left = jack_port_get_buffer((jack_port_t *)((void **)ignored)[0], count);
  jack_default_audio_sample_t *right = jack_port_get_buffer((jack_port_t *)((void **)ignored)[1], count);
  for (jack_nframes_t i = 0; i < count; ++i) {
    left[i] = (jack_default_audio_sample_t)((frame_index % 1000) / 1000.0);
    right[i] = -left[i];
    ++frame_index;
  }
  return 0;
}

int main(void) {
  jack_status_t status;
  jack_client_t *client = jack_client_open("rd-capture-injector", JackNoStartServer, &status);
  if (!client) return 2;
  jack_port_t *ports[] = {
    jack_port_register(client, "left", JACK_DEFAULT_AUDIO_TYPE, JackPortIsOutput, 0),
    jack_port_register(client, "right", JACK_DEFAULT_AUDIO_TYPE, JackPortIsOutput, 0)
  };
  if (!ports[0] || !ports[1] || jack_set_process_callback(client, process, ports) || jack_activate(client)) {
    jack_client_close(client); return 3;
  }
  signal(SIGTERM, stop); signal(SIGINT, stop);
  for (int i = 0; keep_running && i < 100; ++i) usleep(50000);
  jack_deactivate(client); jack_client_close(client);
  return 0;
}
