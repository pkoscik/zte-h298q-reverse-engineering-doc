#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

static const char *ctype(const char *p) {
  const char *d = strrchr(p, '.');
  if (!d) {
    return "application/octet-stream";
  }
  if (!strcmp(d, ".html")) {
    return "text/html; charset=utf-8";
  }
  if (!strcmp(d, ".txt")) {
    return "text/plain; charset=utf-8";
  }
  if (!strcmp(d, ".js")) {
    return "application/javascript";
  }
  if (!strcmp(d, ".css")) {
    return "text/css";
  }
  if (!strcmp(d, ".mp4")) {
    return "video/mp4";
  }
  if (!strcmp(d, ".png")) {
    return "image/png";
  }
  return "application/octet-stream";
}

static void reply(int c, const char *status, const char *ct, const char *body,
                  long len) {
  char hdr[256];
  int n = snprintf(hdr, sizeof hdr,
                   "HTTP/1.0 %s\r\nServer: owned\r\nContent-Type: %s\r\n"
                   "Content-Length: %ld\r\nConnection: close\r\n\r\n",
                   status, ct, len);
  write(c, hdr, n);
  if (body && len) {
    write(c, body, len);
  }
}

static void serve(int c, const char *root) {
  char buf[2048];
  ssize_t n = read(c, buf, sizeof buf - 1);
  if (n <= 0) {
    return;
  }
  buf[n] = 0;

  char *p = buf;
  if (strncmp(p, "GET ", 4)) {
    reply(c, "405 Method Not Allowed", "text/plain", "no\n", 3);
    return;
  }
  p += 4;
  char *sp = strchr(p, ' ');
  if (sp) {
    *sp = 0;
  }
  char *q = strchr(p, '?');
  if (q) {
    *q = 0;
  }
  if (strstr(p, "..")) {
    reply(c, "403 Forbidden", "text/plain", "no\n", 3);
    return;
  }
  if (!strcmp(p, "/")) {
    p = (char *)"/index.html";
  }

  char path[1024];
  snprintf(path, sizeof path, "%s%s", root, p);
  int fd = open(path, O_RDONLY);
  if (fd < 0) {
    reply(c, "404 Not Found", "text/plain", "404\n", 4);
    return;
  }
  struct stat st;
  fstat(fd, &st);
  reply(c, "200 OK", ctype(path), NULL, (long)st.st_size);
  char b[8192];
  ssize_t r;
  while ((r = read(fd, b, sizeof b)) > 0) {
    ssize_t off = 0;
    while (off < r) {
      ssize_t w = write(c, b + off, r - off);
      if (w <= 0) {
        break;
      }
      off += w;
    }
  }
  close(fd);
}

int main(int argc, char **argv) {
  int port = argc > 1 ? atoi(argv[1]) : 80;
  const char *root = argc > 2 ? argv[2] : ".";
  signal(SIGCHLD, SIG_IGN);
  signal(SIGPIPE, SIG_IGN);

  int s = socket(AF_INET, SOCK_STREAM, 0);
  int one = 1;
  setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
  struct sockaddr_in a = {0};
  a.sin_family = AF_INET;
  a.sin_addr.s_addr = INADDR_ANY;
  a.sin_port = htons(port);
  if (bind(s, (struct sockaddr *)&a, sizeof a) < 0) {
    perror("bind");
    return 1;
  }
  if (listen(s, 16) < 0) {
    perror("listen");
    return 1;
  }
  fprintf(stderr, "owned httpd on :%d serving %s\n", port, root);

  for (;;) {
    int c = accept(s, NULL, NULL);
    if (c < 0) {
      continue;
    }
    if (fork() == 0) {
      close(s);
      serve(c, root);
      close(c);
      _exit(0);
    }
    close(c);
  }
}
