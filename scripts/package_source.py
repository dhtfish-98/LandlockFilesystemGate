"""Package exactly the tracked repository source and centralized documentation."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess


def git(*args: str, root: Path, binary: bool = False):
    result = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return result.stdout if binary else result.stdout.decode().strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-root", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    build_root = args.build_root.resolve()
    if "Build" not in build_root.parts:
        parser.error("build root must be inside Build")
    version = (root / "VERSION").read_text().strip()
    if not version or any(character not in "0123456789." for character in version):
        raise ValueError("VERSION must be numeric dotted text")
    if f"VERSION {version}" not in (root / "CMakeLists.txt").read_text():
        raise ValueError("CMake project version differs from VERSION")
    tracked = [name.decode() for name in git("ls-files", "-z", root=root, binary=True).split(b"\0") if name]
    needed = {"VERSION", "CMakeLists.txt", "项目文档/README.md", "项目文档/LICENSE", "项目文档/THIRD_PARTY.md", "src/landlock_filesystem_gate.c", "tests/live_probe.c"}
    if not needed.issubset(tracked):
        raise ValueError("source or rights documentation missing from tracked files")
    if any(name.startswith(("Build/", "环境/", "验证/")) or name.endswith((".pem", ".key", ".p12")) for name in tracked):
        raise ValueError("build output or key tracked in source repository")
    commit = git("rev-parse", "HEAD", root=root)
    prefix = f"LandlockFilesystemGate-{version}/"
    raw = git("archive", "--format=tar", f"--prefix={prefix}", "HEAD", root=root, binary=True)
    destination = build_root / "发行"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f"LandlockFilesystemGate-{version}.tar.gz"
    archive.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    receipt = {
        "version": version,
        "commit": commit,
        "tracked_files": tracked,
        "archive": str(archive),
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    path = destination / "source-package-receipt.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(f"{archive} {receipt['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
