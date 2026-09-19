/* Rhythm Doctor owned capture worker. Blocking IPC and file work stays outside Lua. */
#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
#include "rd_capture.c"

#define RD1_MAX_MESSAGE 1024
#define RD1_ID_MAX 64
#define RD1_ARG_MAX 511

struct rd1_message {
  char job[RD1_ID_MAX + 1], project[RD1_ID_MAX + 1], command[16], argument[RD1_ARG_MAX + 1];
  uint32_t generation, revision;
};
struct worker {
  int server, peer, running, terminal_reported;
  char root[sizeof(((struct sockaddr_un *)0)->sun_path)], socket_path[sizeof(((struct sockaddr_un *)0)->sun_path)];
  char left_source[256], right_source[256], published_path[sizeof(((struct sockaddr_un *)0)->sun_path) + RD1_ID_MAX + 8];
  struct rd_capture *capture;
  struct rd1_message owner;
};
static volatile sig_atomic_t interrupted = 0;
static void on_signal(int value) { (void)value; interrupted = 1; }

static int safe_identity(const char *value) {
  size_t length = strlen(value);
  if (!length || length > RD1_ID_MAX) return 0;
  for (size_t i = 0; i < length; ++i)
    if (!(isalnum((unsigned char)value[i]) || value[i] == '_' || value[i] == '-')) return 0;
  return 1;
}
static int decimal_u32(const char *value, uint32_t *output) {
  if (!*value) return 0;
  uint64_t number = 0;
  for (const char *p = value; *p; ++p) {
    if (!isdigit((unsigned char)*p)) return 0;
    number = number * 10u + (unsigned)(*p - '0');
    if (number > UINT32_MAX) return 0;
  }
  *output = (uint32_t)number; return 1;
}
static int known_command(const char *value) {
  static const char *commands[] = { "PREFLIGHT", "START", "STOP", "CANCEL", "PUBLISH", "RELEASE", "EXIT" };
  for (size_t i = 0; i < sizeof(commands) / sizeof(commands[0]); ++i)
    if (!strcmp(value, commands[i])) return 1;
  return 0;
}
/* Exact seven-field wire record: RD1/job/project/generation/revision/command/argument. */
static int rd1_parse(const char *bytes, size_t length, struct rd1_message *message) {
  if (!bytes || !message || !length || length >= RD1_MAX_MESSAGE || memchr(bytes, '\0', length) ||
      memchr(bytes, '\r', length) || memchr(bytes, '\n', length)) return -1;
  char copy[RD1_MAX_MESSAGE]; memcpy(copy, bytes, length); copy[length] = '\0';
  char *fields[7], *cursor = copy;
  for (size_t i = 0; i < 7; ++i) {
    fields[i] = cursor; char *tab = strchr(cursor, '\t');
    if (i < 6) { if (!tab) return -1; *tab = '\0'; cursor = tab + 1; }
    else if (tab) return -1;
  }
  if (strcmp(fields[0], "RD1") || !safe_identity(fields[1]) || !safe_identity(fields[2]) ||
      !decimal_u32(fields[3], &message->generation) || !decimal_u32(fields[4], &message->revision) ||
      !known_command(fields[5]) || strlen(fields[5]) >= sizeof(message->command) ||
      strlen(fields[6]) > RD1_ARG_MAX || strpbrk(fields[6], "\t\r\n")) return -1;
  strcpy(message->job, fields[1]); strcpy(message->project, fields[2]);
  strcpy(message->command, fields[5]); strcpy(message->argument, fields[6]); return 0;
}
static int same_owner(const struct worker *worker, const struct rd1_message *message) {
  return *worker->owner.job && !strcmp(worker->owner.job, message->job) && !strcmp(worker->owner.project, message->project) &&
    worker->owner.generation == message->generation && worker->owner.revision == message->revision;
}
static int respond_to(int peer, const struct rd1_message *message, const char *status, const char *detail) {
  char output[RD1_MAX_MESSAGE];
  int count = snprintf(output, sizeof(output), "RD1\t%s\t%s\t%u\t%u\t%s\t%s\t%s",
    message ? message->job : "invalid", message ? message->project : "invalid",
    message ? message->generation : 0, message ? message->revision : 0,
    message ? message->command : "EVENT", status, detail ? detail : "");
  return count > 0 && (size_t)count < sizeof(output) && send(peer, output, (size_t)count, MSG_NOSIGNAL) == count ? 0 : -1;
}
static int parse_seconds(const char *argument, uint32_t *seconds) {
  char number[4]; size_t n = strcspn(argument, ",");
  if (!n || n >= sizeof(number)) return 0;
  memcpy(number, argument, n); number[n] = '\0';
  uint32_t value; if (!decimal_u32(number, &value) || value < 1 || value > 45) return 0;
  if (argument[n] && strcmp(argument + n + 1, "auto") && strcmp(argument + n + 1, "manual")) return 0;
  *seconds = value; return 1;
}
static void destroy_capture(struct worker *worker) {
  if (worker->capture) { rd_capture_destroy(worker->capture); worker->capture = NULL; }
  worker->terminal_reported = 0;
}
static void reset_job(struct worker *worker) {
  destroy_capture(worker);
  if (*worker->published_path) unlink(worker->published_path);
  worker->published_path[0] = '\0'; memset(&worker->owner, 0, sizeof(worker->owner));
}
static int sha256_file(const char *path, char digest[65]) {
  int pipefd[2]; if (pipe(pipefd)) return -1;
  pid_t child = fork();
  if (child < 0) { close(pipefd[0]); close(pipefd[1]); return -1; }
  if (!child) {
    if (dup2(pipefd[1], STDOUT_FILENO) < 0) _exit(127);
    close(pipefd[0]); close(pipefd[1]); execl("/usr/bin/sha256sum", "sha256sum", "--", path, (char *)NULL); _exit(127);
  }
  close(pipefd[1]); size_t used = 0;
  while (used < 64) { ssize_t got = read(pipefd[0], digest + used, 64 - used); if (got <= 0) break; used += (size_t)got; }
  close(pipefd[0]); int status = 0;
  if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status) || used != 64) return -1;
  digest[64] = '\0'; for (size_t i = 0; i < 64; ++i) if (!isxdigit((unsigned char)digest[i])) return -1;
  return 0;
}
static int handle_message(struct worker *worker, const struct rd1_message *message) {
  if (!strcmp(message->command, "PREFLIGHT")) {
    uint32_t seconds;
    if (worker->capture) return respond_to(worker->peer, message, "FAILED", "BUSY");
    reset_job(worker);
    if (!parse_seconds(message->argument, &seconds)) return respond_to(worker->peer, message, "FAILED", "INVALID_DURATION");
    worker->capture = rd_capture_preflight(seconds);
    if (!worker->capture) return respond_to(worker->peer, message, "FAILED", "INPUT_RESOURCE_BUSY");
    worker->owner = *message;
    if (jack_connect(worker->capture->client, worker->left_source, rd_capture_input_port(worker->capture, 0)) ||
        jack_connect(worker->capture->client, worker->right_source, rd_capture_input_port(worker->capture, 1))) {
      reset_job(worker); return respond_to(worker->peer, message, "FAILED", "INPUT_ROUTE_FAILED");
    }
    return respond_to(worker->peer, message, "READY", "");
  }
  if (!same_owner(worker, message)) return respond_to(worker->peer, message, "STALE", "STALE_JOB");
  if (!strcmp(message->command, "START")) {
    if (rd_capture_start(worker->capture)) return respond_to(worker->peer, message, "FAILED", "BAD_STATE");
    return respond_to(worker->peer, message, "STARTED", "");
  }
  if (!strcmp(message->command, "STOP")) {
    if (rd_capture_stop(worker->capture)) return respond_to(worker->peer, message, "FAILED", "BAD_STATE");
    return 0;
  }
  if (!strcmp(message->command, "CANCEL")) {
    if (rd_capture_cancel(worker->capture) && rd_capture_state(worker->capture) != RD_CAPTURE_CANCELLED)
      return respond_to(worker->peer, message, "FAILED", "BAD_STATE");
    return 0;
  }
  if (!strcmp(message->command, "PUBLISH")) {
    int count = snprintf(worker->published_path, sizeof(worker->published_path), "%s/%s.wav", worker->root, worker->owner.job);
    if (count < 0 || (size_t)count >= sizeof(worker->published_path) || !worker->capture ||
        rd_capture_publish_wav(worker->capture, worker->published_path))
      return respond_to(worker->peer, message, "FAILED", "PUBLISH_FAILED");
    char digest[65], detail[sizeof(worker->published_path) + 128];
    if (sha256_file(worker->published_path, digest)) return respond_to(worker->peer, message, "FAILED", "HASH_FAILED");
    count = snprintf(detail, sizeof(detail), "%s,%s,%llu,%u", worker->published_path, digest,
      (unsigned long long)rd_capture_frames(worker->capture), rd_capture_sample_rate(worker->capture));
    if (count < 0 || (size_t)count >= sizeof(detail)) return respond_to(worker->peer, message, "FAILED", "PUBLISH_FAILED");
    return respond_to(worker->peer, message, "PUBLISHED", detail);
  }
  if (!strcmp(message->command, "RELEASE")) { destroy_capture(worker); return respond_to(worker->peer, message, "RELEASED", ""); }
  if (!strcmp(message->command, "EXIT")) { reset_job(worker); worker->running = 0; return respond_to(worker->peer, message, "BYE", ""); }
  return respond_to(worker->peer, message, "FAILED", "BAD_COMMAND");
}
static int report_terminal(struct worker *worker) {
  if (!worker->capture || worker->terminal_reported) return 0;
  int state = rd_capture_state(worker->capture);
  if (state == RD_CAPTURE_COMPLETED) {
    worker->terminal_reported = 1; struct rd1_message event = worker->owner; strcpy(event.command, "EVENT");
    return respond_to(worker->peer, &event, "COMPLETED", "");
  }
  if (state == RD_CAPTURE_FAILED) {
    worker->terminal_reported = 1; struct rd1_message event = worker->owner; strcpy(event.command, "EVENT");
    char error[32]; snprintf(error, sizeof(error), "CAPTURE_ERROR_%d", rd_capture_error(worker->capture));
    return respond_to(worker->peer, &event, "FAILED", error);
  }
  return 0;
}
static int setup_server(struct worker *worker, char *root_template) {
  char *root = mkdtemp(root_template); if (!root || chmod(root, 0700)) return -1;
  if (strlen(root) + 13 >= sizeof(worker->socket_path)) { errno = ENAMETOOLONG; goto fail; }
  strcpy(worker->root, root); snprintf(worker->socket_path, sizeof(worker->socket_path), "%s/worker.sock", root);
  worker->server = socket(AF_UNIX, SOCK_SEQPACKET, 0); if (worker->server < 0) goto fail;
  struct sockaddr_un address; memset(&address, 0, sizeof(address)); address.sun_family = AF_UNIX; strcpy(address.sun_path, worker->socket_path);
  if (bind(worker->server, (struct sockaddr *)&address, sizeof(address)) || chmod(worker->socket_path, 0600) || listen(worker->server, 1)) goto fail;
  printf("%s\n", worker->socket_path); fflush(stdout); return 0;
fail: {
    int problem = errno;
    if (*worker->socket_path) unlink(worker->socket_path);
    if (worker->server >= 0) { close(worker->server); worker->server = -1; }
    rmdir(root); worker->root[0] = worker->socket_path[0] = '\0';
    errno = problem; return -1;
  }
}
int main(int argc, char **argv) {
  if (argc != 4 || strlen(argv[2]) >= sizeof(((struct worker *)0)->left_source) || strlen(argv[3]) >= sizeof(((struct worker *)0)->right_source)) {
    fprintf(stderr, "usage: %s ROOT-XXXXXX LEFT-JACK-PORT RIGHT-JACK-PORT\n", argv[0]); return 2;
  }
  struct worker worker; memset(&worker, 0, sizeof(worker)); worker.server = worker.peer = -1; worker.running = 1;
  strcpy(worker.left_source, argv[2]); strcpy(worker.right_source, argv[3]);
  signal(SIGINT, on_signal); signal(SIGTERM, on_signal); signal(SIGHUP, on_signal); signal(SIGPIPE, SIG_IGN);
  if (setup_server(&worker, argv[1])) { perror("worker setup"); return 1; }
  worker.peer = accept(worker.server, NULL, NULL); if (worker.peer < 0) worker.running = 0;
  while (worker.running && !interrupted) {
    struct pollfd descriptor = { worker.peer, POLLIN, 0 }; int ready = poll(&descriptor, 1, 20);
    if (ready < 0) { if (errno == EINTR) continue; break; }
    if (ready && (descriptor.revents & (POLLHUP | POLLERR | POLLNVAL))) break;
    if (ready && (descriptor.revents & POLLIN)) {
      char input[RD1_MAX_MESSAGE]; ssize_t length = recv(worker.peer, input, sizeof(input), 0); if (length <= 0) break;
      struct rd1_message message;
      if (rd1_parse(input, (size_t)length, &message)) { if (respond_to(worker.peer, NULL, "ERROR", "BAD_PROTOCOL")) break; }
      else if (handle_message(&worker, &message)) break;
    }
    if (report_terminal(&worker)) break;
  }
  reset_job(&worker); if (worker.peer >= 0) close(worker.peer); if (worker.server >= 0) close(worker.server);
  if (*worker.socket_path) unlink(worker.socket_path);
  if (*worker.root) rmdir(worker.root);
  return interrupted ? 130 : 0;
}
