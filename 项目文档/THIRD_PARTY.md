# Third-party rights and runtime provenance

| Component | Use | Rights and attribution |
| --- | --- | --- |
| `landlock-lsm/rust-landlock` at `3dd4c82bf0a852086747e434aae9aa4b8ffe590d` | Fixed research reference only; no source included | `MIT OR Apache-2.0` in pinned `Cargo.toml`; `COPYRIGHT` credits Mickaël Salaün, Copyright 2020. [MIT](https://github.com/landlock-lsm/rust-landlock/blob/3dd4c82bf0a852086747e434aae9aa4b8ffe590d/LICENSE-MIT), [Apache-2.0](https://github.com/landlock-lsm/rust-landlock/blob/3dd4c82bf0a852086747e434aae9aa4b8ffe590d/LICENSE-APACHE). |
| Linux Landlock UAPI | Public kernel interface and behavior reference | [Linux documentation](https://docs.kernel.org/6.17/userspace-api/landlock.html); Linux rights belong to their respective authors. No kernel source is bundled. |
| Alpine Linux 3.23 ARM64 netboot | Pinned disposable VM kernel and initramfs, downloaded during the macOS live test | [Official Alpine image directory](https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/aarch64/netboot/); component licenses remain with Alpine/kernel/BusyBox authors. Images are not bundled in the source archive. |
| Zig 0.13.0 ARM64 macOS | Pinned cross-compiler downloaded during the macOS live test | [Official Zig download](https://ziglang.org/download/0.13.0/); compiler and bundled library licenses remain with their authors. Not bundled. |
| Apple Virtualization.framework | macOS host VM API | System framework supplied by Apple, not bundled. |

The macOS runner checks downloaded SHA-256 values before use. The checked Alpine netboot files are `vmlinuz-virt` `06196d2cf51e9a2bac421564bb64c63a8b7146c9a22755dd22a713e337023013`, `initramfs-virt` `b0be51c9de43d582da897df3583114192933872a7e219218752b18082d75b6cb`, and `config-6.18.52-0-virt` `18bb325df712efc698503ab3442f4c41017d9799a728464b7ec8a5b86ea9cf10`. The official Zig archive is pinned to `46fae219656545dfaf4dce12fb4e8685cec5b51d721beee9389ab4194d43394c`.
