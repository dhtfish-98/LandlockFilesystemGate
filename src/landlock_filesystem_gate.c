#define _GNU_SOURCE
#include "landlock_filesystem_gate.h"

#include <errno.h>
#include <stddef.h>

#ifdef __linux__
#include <fcntl.h>
#include <stdint.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <unistd.h>

/* Linux Landlock UAPI numbers and filesystem access bit positions. */
#ifndef __NR_landlock_create_ruleset
#define __NR_landlock_create_ruleset 444
#endif
#ifndef __NR_landlock_add_rule
#define __NR_landlock_add_rule 445
#endif
#ifndef __NR_landlock_restrict_self
#define __NR_landlock_restrict_self 446
#endif
#define LFG_CREATE_RULESET_VERSION 1
#define LFG_RULE_PATH_BENEATH 1
#define LFG_ACCESS_WRITE_FILE (1ULL << 1)
#define LFG_ACCESS_READ_FILE (1ULL << 2)
#define LFG_ACCESS_READ_DIR (1ULL << 3)
#define LFG_ACCESS_MAKE_REG (1ULL << 8)
#define LFG_ACCESS_TRUNCATE (1ULL << 14)

struct lfg_ruleset_attr {
    uint64_t handled_access_fs;
};

struct lfg_path_beneath_attr {
    uint64_t allowed_access;
    int32_t parent_fd;
    uint32_t reserved;
};

static int add_path_rule(int ruleset_fd, const char *path, int open_flags, uint64_t access) {
    int path_fd = open(path, open_flags | O_CLOEXEC);
    if (path_fd < 0) return -errno;
    struct lfg_path_beneath_attr rule = {
        .allowed_access = access,
        .parent_fd = path_fd,
    };
    int result = syscall(__NR_landlock_add_rule, ruleset_fd, LFG_RULE_PATH_BENEATH, &rule, 0);
    int saved_errno = errno;
    close(path_fd);
    return result == 0 ? 0 : -saved_errno;
}

int lfg_apply_readwrite(const char *allowed_directory,
                        const char *trusted_reexec,
                        int *abi_out) {
    if (abi_out != NULL) *abi_out = 0;
    if (allowed_directory == NULL || allowed_directory[0] == '\0') return -EINVAL;
    int abi = syscall(__NR_landlock_create_ruleset, NULL, 0, LFG_CREATE_RULESET_VERSION);
    if (abi < 0) return -errno;
    if (abi_out != NULL) *abi_out = abi;
    if (abi < 3) return -EOPNOTSUPP;

    const uint64_t rights = LFG_ACCESS_WRITE_FILE | LFG_ACCESS_READ_FILE |
                            LFG_ACCESS_READ_DIR | LFG_ACCESS_MAKE_REG |
                            LFG_ACCESS_TRUNCATE;
    struct lfg_ruleset_attr ruleset = {.handled_access_fs = rights};
    int ruleset_fd = syscall(__NR_landlock_create_ruleset, &ruleset, sizeof(ruleset), 0);
    if (ruleset_fd < 0) return -errno;

    int status = add_path_rule(ruleset_fd, allowed_directory, O_PATH | O_DIRECTORY, rights);
    if (status == 0 && trusted_reexec != NULL) {
        status = add_path_rule(ruleset_fd, trusted_reexec, O_PATH, LFG_ACCESS_READ_FILE);
    }
    if (status == 0 && prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) status = -errno;
    if (status == 0 && syscall(__NR_landlock_restrict_self, ruleset_fd, 0) != 0) status = -errno;
    close(ruleset_fd);
    return status;
}

#else
int lfg_apply_readwrite(const char *allowed_directory,
                        const char *trusted_reexec,
                        int *abi_out) {
    (void)allowed_directory;
    (void)trusted_reexec;
    if (abi_out != NULL) *abi_out = 0;
    return -ENOTSUP;
}
#endif
