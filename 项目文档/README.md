# LandlockFilesystemGate

Version 0.1.0. Author: **dhtfish98**.

This project applies a narrow Linux Landlock filesystem policy to an owned process before it launches any worker threads. It allows file reads, writes, creation of regular files and truncation beneath one trusted directory; the same operations elsewhere are denied. An optional exact executable path can be granted read access for a harmless child re-execution test. It is a defensive lab, not a complete filesystem sandbox.

The live comparison checks a real Linux kernel: before restriction, the test process can read and open a fixture outside the allowed directory; after restriction, it can read and write inside the allowed directory, while outside reads, writes, creates and truncation return `EACCES`. A re-executed child inherits the denial. The outside fixture's SHA-256 is checked before and after.

On Linux with Landlock ABI 3 or newer, from the repository checkout:

```sh
python3 scripts/run_native_linux.py --build-root /absolute/path/to/Build
```

On Apple silicon macOS with Apple Virtualization.framework, run the pinned Alpine ARM64 Linux VM comparison:

```sh
python3 scripts/run_macos_vm.py --build-root /absolute/path/to/Build
```

The macOS script downloads pinned Alpine Linux kernel/initramfs and Zig into `Build/环境/LandlockFilesystemGate-20261006`; every download is checked against a declared SHA-256. It uses the same CMake Linux test target as the native runner, cross-builds a static ELF and rejects binaries with an ELF interpreter or shared-library dependencies before starting the disposable VM. Each run gets a separate `Build/验证/LandlockFilesystemGate-20261006/run-...` directory containing its ELF, serial log and machine receipt; pass `--run-id NAME` to choose a stable review label. The first run needs network access; the Linux native runner needs CMake and a C compiler with static C runtime support. No system-wide installation is needed.

To build the C library directly, keep output under Build:

```sh
cmake -S . -B /absolute/path/to/Build/LandlockFilesystemGate-cmake -DCMAKE_BUILD_TYPE=Release
cmake --build /absolute/path/to/Build/LandlockFilesystemGate-cmake
```

From a committed Git checkout, `python3 scripts/package_source.py --build-root /absolute/path/to/Build` creates a source archive and SHA-256 receipt in `Build/发行`. Unpack it under Build and run the same native or macOS VM script from the extracted tree. The repository's CI performs the real Linux comparison both in checkout and in the unpacked archive, rejecting a dynamically linked test executable before applying the policy. A successful local VM run does not imply CI, publication or CVP acceptance.

See [DESIGN.md](DESIGN.md) for the exact authority boundary, [ORIGIN.md](ORIGIN.md) for provenance, and [CVP_STATUS.md](CVP_STATUS.md) for evidence status.
