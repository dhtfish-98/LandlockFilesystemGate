#ifndef LANDLOCK_FILESYSTEM_GATE_H
#define LANDLOCK_FILESYSTEM_GATE_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Restrict this calling thread and its future children to file read/write
 * beneath allowed_directory. trusted_reexec may be NULL; if present, exactly
 * that executable receives file-read access so a child can re-exec it.
 *
 * Requires Landlock ABI >= 3 to cover file truncation. Return 0 and write
 * the negotiated ABI on success, or return -errno. ABI < 3 fails closed.
 * This change is irreversible for the thread and inherited descendants.
 * Invoke before creating threads. The caller must abort on any error.
 */
int lfg_apply_readwrite(const char *allowed_directory,
                        const char *trusted_reexec,
                        int *abi_out);

#ifdef __cplusplus
}
#endif

#endif
