# Release notes

## v0.1.0

Initial self-authored Landlock filesystem gate for one trusted directory, with ABI 3 minimum to cover truncation. Includes a real Linux baseline/guard probe, macOS Apple Virtualization runner using a pinned Alpine ARM64 kernel, native Linux runner, source archive builder, and machine-readable receipts. Both runners use the CMake Linux test target and require a static ELF before the inherited child re-execution check. VM runs retain separate binaries, serial logs and receipts. The native runner preserves and prints failure diagnostics; its CI artifact upload also runs when a test fails. The source packager normalizes the gzip OS header field for cross-platform package comparison. CVP eligibility and acceptance remain OPEN; see [CVP_STATUS.md](CVP_STATUS.md).
