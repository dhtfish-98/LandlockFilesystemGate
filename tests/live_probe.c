#define _GNU_SOURCE
#include "landlock_filesystem_gate.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int joined(char *destination, size_t length, const char *directory) {
    int count = snprintf(destination, length, "%s/data", directory);
    return count > 0 && (size_t)count < length;
}

static int can_read(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return 0;
    char byte;
    int ok = read(fd, &byte, 1) == 1;
    close(fd);
    return ok;
}

static int can_append(const char *path) {
    int fd = open(path, O_WRONLY | O_APPEND);
    if (fd < 0) return 0;
    int ok = write(fd, "X", 1) == 1;
    close(fd);
    return ok;
}

static int denied_open(const char *path, int flags) {
    errno = 0;
    int fd = open(path, flags, 0600);
    if (fd >= 0) {
        close(fd);
        return 0;
    }
    return errno == EACCES;
}

static int denied_truncate(const char *path) {
    errno = 0;
    return truncate(path, 0) == -1 && errno == EACCES;
}

static int create_file(const char *path) {
    int fd = open(path, O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (fd < 0) return 0;
    close(fd);
    return 1;
}

int main(int argc, char **argv) {
    if (argc == 3 && strcmp(argv[1], "--child") == 0) {
        int ok = denied_open(argv[2], O_RDONLY);
        printf("EXEC_CHILD_DENY_READ=%s errno=%d\n", ok ? "PASS" : "FAIL", errno);
        fflush(stdout);
        return ok ? 0 : 1;
    }
    if (argc != 4) {
        fprintf(stderr, "usage: landlock-live <allowed-dir> <denied-dir> <self-executable>\n");
        return 2;
    }
    char allowed[PATH_MAX], denied[PATH_MAX], allowed_new[PATH_MAX], denied_new[PATH_MAX];
    if (!joined(allowed, sizeof(allowed), argv[1]) || !joined(denied, sizeof(denied), argv[2])) return 2;
    if (snprintf(allowed_new, sizeof(allowed_new), "%s/new", argv[1]) >= (int)sizeof(allowed_new) ||
        snprintf(denied_new, sizeof(denied_new), "%s/new", argv[2]) >= (int)sizeof(denied_new)) return 2;
    if (!can_read(denied)) return 1;
    puts("BASE_DENY_READ=PASS");
    int baseline_fd = open(denied, O_WRONLY | O_APPEND);
    if (baseline_fd < 0) return 1;
    close(baseline_fd);
    puts("BASE_DENY_WRITE_OPEN=PASS");

    int abi = 0;
    int status = lfg_apply_readwrite(argv[1], argv[3], &abi);
    if (status < 0) {
        printf("LANDLOCK_APPLY=%s errno=%d abi=%d\n",
               status == -ENOSYS || status == -EOPNOTSUPP || status == -ENOTSUP ? "OPEN" : "FAIL",
               -status, abi);
        return status == -ENOSYS || status == -EOPNOTSUPP || status == -ENOTSUP ? 77 : 1;
    }
    printf("LANDLOCK_ABI=%d\n", abi);
    int allow_read = can_read(allowed);
    int allow_write = can_append(allowed);
    int deny_read = denied_open(denied, O_RDONLY);
    int read_errno = errno;
    int deny_write = denied_open(denied, O_WRONLY | O_APPEND);
    int write_errno = errno;
    int allow_create = create_file(allowed_new);
    int deny_create = denied_open(denied_new, O_CREAT | O_EXCL | O_WRONLY);
    int create_errno = errno;
    int allow_truncate = truncate(allowed, 1) == 0;
    int deny_truncate = denied_truncate(denied);
    int truncate_errno = errno;
    printf("ALLOW_READ=%s ALLOW_WRITE=%s DENY_READ=%s DENY_WRITE=%s errno_read=%d errno_write=%d\n",
           allow_read ? "PASS" : "FAIL", allow_write ? "PASS" : "FAIL",
           deny_read ? "PASS" : "FAIL", deny_write ? "PASS" : "FAIL", read_errno, write_errno);
    printf("ALLOW_CREATE=%s DENY_CREATE=%s errno=%d\n",
           allow_create ? "PASS" : "FAIL", deny_create ? "PASS" : "FAIL", create_errno);
    printf("ALLOW_TRUNCATE=%s DENY_TRUNCATE=%s errno=%d\n",
           allow_truncate ? "PASS" : "FAIL", deny_truncate ? "PASS" : "FAIL", truncate_errno);
    fflush(stdout);
    if (!(allow_read && allow_write && deny_read && deny_write &&
          allow_create && deny_create && allow_truncate && deny_truncate)) return 1;

    pid_t child = fork();
    if (child < 0) return 1;
    if (child == 0) {
        execl(argv[3], argv[3], "--child", denied, (char *)NULL);
        printf("EXEC_CHILD=FAIL errno=%d\n", errno);
        fflush(stdout);
        _exit(1);
    }
    int child_status = 0;
    if (waitpid(child, &child_status, 0) != child) return 1;
    int ok = WIFEXITED(child_status) && WEXITSTATUS(child_status) == 0;
    printf("CHILD_INHERITED_DENIAL=%s\n", ok ? "PASS" : "FAIL");
    fflush(stdout);
    return ok ? 0 : 1;
}
