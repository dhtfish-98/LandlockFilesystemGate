# Origin and attribution

This C library, probe, packaging and VM automation were written for this project by **dhtfish98**. The implementation uses Linux's published Landlock syscall interface and tests a separate, owned process. It does not copy or translate source files from the Rust crate below.

The fixed research reference is [`landlock-lsm/rust-landlock@3dd4c82bf0a852086747e434aae9aa4b8ffe590d`](https://github.com/landlock-lsm/rust-landlock/tree/3dd4c82bf0a852086747e434aae9aa4b8ffe590d), crate version 0.4.7. Its pinned [`Cargo.toml`](https://github.com/landlock-lsm/rust-landlock/blob/3dd4c82bf0a852086747e434aae9aa4b8ffe590d/Cargo.toml) declares `MIT OR Apache-2.0`; its [`COPYRIGHT`](https://github.com/landlock-lsm/rust-landlock/blob/3dd4c82bf0a852086747e434aae9aa4b8ffe590d/COPYRIGHT) names **Mickaël Salaün, Copyright 2020**. These third-party facts are retained because independently writing this project's code does not erase another author's rights. See [THIRD_PARTY.md](THIRD_PARTY.md).

The project's own code is licensed under its [MIT license](LICENSE). Linux kernel, Alpine, Zig and Apple Virtualization components are test/build environment dependencies and are not bundled in the source archive. This project does not assert that the referenced upstream has a defect.
