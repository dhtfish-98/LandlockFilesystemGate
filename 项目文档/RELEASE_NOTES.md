# Release notes

## v0.1.0 — local candidate

Initial self-authored Landlock filesystem gate for one trusted directory, with ABI 3 minimum to cover truncation. Includes a real Linux baseline/guard probe, macOS Apple Virtualization runner using a pinned Alpine ARM64 kernel, native Linux runner, source archive builder, and machine-readable receipts. Both runners now use the CMake Linux test target and require a static ELF before the inherited child re-execution check. VM runs retain separate binaries, serial logs and receipts. CVP evidence remains OPEN. Formal public release requires independent review, exact-commit main/tag CI success and downloaded asset digest verification.
