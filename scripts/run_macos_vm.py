"""Reproduce the Landlock comparison in a real, isolated ARM64 Linux VM.

Runtime downloads, images, toolchains, binaries and logs stay inside Build.
Pinned external bytes are verified before extraction or execution.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import pty
import re
import select
import shlex
import shutil
import subprocess
import sys
import tarfile
import time

# Keep imported-helper bytecode out of the source checkout.
sys.dont_write_bytecode = True
from elf_check import require_static_elf


ALPINE = "https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/aarch64/netboot"
ZIG = "https://ziglang.org/download/0.13.0/zig-macos-aarch64-0.13.0.tar.xz"
PINS = {
    "vmlinuz-virt": "06196d2cf51e9a2bac421564bb64c63a8b7146c9a22755dd22a713e337023013",
    "initramfs-virt": "b0be51c9de43d582da897df3583114192933872a7e219218752b18082d75b6cb",
    "config-6.18.52-0-virt": "18bb325df712efc698503ab3442f4c41017d9799a728464b7ec8a5b86ea9cf10",
    "Image-6.18.52-0-virt": "8dfe2ce7e5bfe4d0efcf2fed0a01a692b5a5d5217e9a55587a17d92203ab7b0d",
    "zig-macos-aarch64-0.13.0.tar.xz": "46fae219656545dfaf4dce12fb4e8685cec5b51d721beee9389ab4194d43394c",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def checked_download(url: str, destination: Path, expected: str) -> None:
    if destination.exists() and digest(destination) == expected:
        return
    temp = destination.with_name(destination.name + ".part")
    subprocess.run(["curl", "-fL", "--retry", "2", url, "-o", str(temp)], check=True)
    if digest(temp) != expected:
        temp.unlink(missing_ok=True)
        raise ValueError(f"pinned archive digest mismatch: {destination.name}")
    temp.replace(destination)


def run_vm(executable: Path, kernel: Path, initramfs: Path, log: Path) -> tuple[int, str]:
    commands = """/bin/busybox mount -t proc proc /proc
/bin/busybox printf 'KERNEL_RELEASE='; /bin/busybox uname -r
/bin/busybox mkdir -p /tmp/allow /tmp/deny
printf 'allow-marker' > /tmp/allow/data
printf 'deny-marker' > /tmp/deny/data
/bin/busybox sha256sum /tmp/deny/data
/bin/landlock-live /tmp/allow /tmp/deny /bin/landlock-live
printf 'TEST_EXIT=%s\\n' "$?"
/bin/busybox sha256sum /tmp/deny/data
/bin/busybox poweroff -f
"""
    master, slave = pty.openpty()
    process = subprocess.Popen(
        [str(executable), str(kernel), str(initramfs)], stdin=slave, stdout=slave, stderr=slave
    )
    os.close(slave)
    captured = bytearray()
    sent = False
    deadline = time.monotonic() + 30
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                try:
                    block = os.read(master, 8192)
                except OSError:
                    break
                if not block:
                    break
                captured.extend(block)
                if not sent and b"~ #" in captured:
                    os.write(master, commands.encode())
                    sent = True
            if process.poll() is not None:
                break
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
    finally:
        os.close(master)
        log.write_bytes(captured)
    if not sent:
        raise RuntimeError("Linux guest shell never became available")
    return process.returncode, captured.decode(errors="replace")


def verify_log(log: str, returncode: int) -> dict:
    log = log.replace("\r\n", "\n").replace("\r", "\n")
    required = (
        "BASE_DENY_READ=PASS",
        "BASE_DENY_WRITE_OPEN=PASS",
        "ALLOW_READ=PASS ALLOW_WRITE=PASS DENY_READ=PASS DENY_WRITE=PASS errno_read=13 errno_write=13",
        "ALLOW_CREATE=PASS DENY_CREATE=PASS errno=13",
        "ALLOW_TRUNCATE=PASS DENY_TRUNCATE=PASS errno=13",
        "EXEC_CHILD_DENY_READ=PASS errno=13",
        "CHILD_INHERITED_DENIAL=PASS",
        "TEST_EXIT=0",
        "KERNEL_RELEASE=6.18.52-0-virt",
    )
    abi = re.search(r"^LANDLOCK_ABI=(\d+)$", log, re.MULTILINE)
    hashes = re.findall(r"^([0-9a-f]{64})  /tmp/deny/data$", log, re.MULTILINE)
    if returncode != 0 or abi is None or int(abi.group(1)) < 3:
        raise AssertionError("real Linux VM or Landlock ABI did not complete")
    if not all(marker in log for marker in required) or len(hashes) != 2 or hashes[0] != hashes[1]:
        raise AssertionError("live access or file-integrity comparison failed")
    return {"landlock_abi": int(abi.group(1)), "denied_file_sha256_before": hashes[0], "denied_file_sha256_after": hashes[1], "checks": list(required)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-root", type=Path, required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    build_root = args.build_root.resolve()
    if "Build" not in build_root.parts:
        parser.error("build root must be inside Build")
    env_dir = build_root / "环境/LandlockFilesystemGate-20261006"
    run_id = args.run_id or f"run-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{os.getpid()}"
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", run_id) is None:
        parser.error("run-id must be a short path-safe name")
    verify_dir = build_root / "验证/LandlockFilesystemGate-20261006" / run_id
    env_dir.mkdir(parents=True, exist_ok=True)
    verify_dir.mkdir(parents=True, exist_ok=False)
    receipt: dict = {"status": "OPEN", "created_utc": datetime.now(timezone.utc).isoformat(), "run_id": run_id, "source_root": str(root), "build_root": str(build_root), "platform": platform.platform()}
    log = verify_dir / "vm-serial.log"
    try:
        if sys.platform != "darwin" or platform.machine() != "arm64":
            raise RuntimeError("requires Apple silicon macOS with Virtualization.framework")
        for name in ("vmlinuz-virt", "initramfs-virt", "config-6.18.52-0-virt"):
            checked_download(f"{ALPINE}/{name}", env_dir / name, PINS[name])
        config = (env_dir / "config-6.18.52-0-virt").read_text()
        if "CONFIG_SECURITY_LANDLOCK=y" not in config:
            raise RuntimeError("the pinned Linux kernel lacks Landlock")
        kernel = env_dir / "Image-6.18.52-0-virt"
        if not kernel.exists() or digest(kernel) != PINS[kernel.name]:
            compressed = (env_dir / "vmlinuz-virt").read_bytes()
            offset = compressed.find(b"\x1f\x8b\x08")
            if offset < 0:
                raise ValueError("no gzip payload in pinned Alpine kernel")
            import zlib
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            image = decoder.decompress(compressed[offset:]) + decoder.flush()
            if not decoder.eof or image[0x38:0x3c] != b"ARMd":
                raise ValueError("not an uncompressed ARM64 Linux Image")
            kernel.write_bytes(image)
            if digest(kernel) != PINS[kernel.name]:
                raise ValueError("uncompressed kernel digest mismatch")
        zig_archive = env_dir / "zig-macos-aarch64-0.13.0.tar.xz"
        checked_download(ZIG, zig_archive, PINS[zig_archive.name])
        zig = env_dir / "zig-macos-aarch64-0.13.0" / "zig"
        if not zig.exists():
            with tarfile.open(zig_archive) as archive:
                archive.extractall(env_dir, filter="data")
        zig_env = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(env_dir / "zig-cache-global"), ZIG_LOCAL_CACHE_DIR=str(env_dir / "zig-cache-local"))
        compiler = verify_dir / "zig-cc"
        compiler.write_text(f"#!/bin/sh\nexec {shlex.quote(str(zig))} cc -target aarch64-linux-musl \"$@\"\n")
        compiler.chmod(0o755)
        archiver = verify_dir / "zig-ar"
        archiver.write_text(f"#!/bin/sh\nexec {shlex.quote(str(zig))} ar \"$@\"\n")
        archiver.chmod(0o755)
        ranlib = verify_dir / "zig-ranlib"
        ranlib.write_text(f"#!/bin/sh\nexec {shlex.quote(str(zig))} ranlib \"$@\"\n")
        ranlib.chmod(0o755)
        cmake_build = verify_dir / "cmake-linux"
        subprocess.run(["cmake", "-S", str(root), "-B", str(cmake_build), "-DCMAKE_SYSTEM_NAME=Linux", f"-DCMAKE_C_COMPILER={compiler}", f"-DCMAKE_AR={archiver}", f"-DCMAKE_RANLIB={ranlib}", "-DCMAKE_BUILD_TYPE=Release"], check=True, env=zig_env)
        subprocess.run(["cmake", "--build", str(cmake_build), "--parallel", "2"], check=True, env=zig_env)
        guest_probe = cmake_build / "landlock-live"
        receipt["binary_elf"] = require_static_elf(guest_probe)
        overlay = verify_dir / "overlay-final"
        if overlay.exists():
            shutil.rmtree(overlay)
        (overlay / "usr/bin").mkdir(parents=True)
        shutil.copy2(guest_probe, overlay / "usr/bin/landlock-live")
        entries = b".\n./usr\n./usr/bin\n./usr/bin/landlock-live\n"
        archive = subprocess.run(["cpio", "-o", "-H", "newc"], input=entries, cwd=overlay, check=True, capture_output=True).stdout
        initramfs = env_dir / "initramfs-with-probe.gz"
        initramfs.write_bytes(gzip.compress(gzip.decompress((env_dir / "initramfs-virt").read_bytes()) + archive, compresslevel=9, mtime=0))
        host_vm = verify_dir / "host_vm"
        subprocess.run(["swiftc", "-parse-as-library", "-framework", "Virtualization", str(root / "tests/host_vm.swift"), "-o", str(host_vm)], check=True)
        subprocess.run(["codesign", "--force", "--sign", "-", "--entitlements", str(root / "tests/virtualization.entitlements"), str(host_vm)], check=True, capture_output=True)
        result, serial = run_vm(host_vm, kernel, initramfs, log)
        receipt.update(verify_log(serial, result))
        receipt.update({"status": "PASS", "linux_kernel": "6.18.52-0-virt", "pinned_kernel_image_sha256": digest(kernel), "pinned_initramfs_sha256": digest(env_dir / "initramfs-virt"), "guest_probe_sha256": digest(guest_probe), "serial_log": str(log), "serial_log_sha256": digest(log), "vm_returncode": result})
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        if log.exists():
            receipt["serial_log"] = str(log)
            receipt["serial_log_sha256"] = digest(log)
        print(receipt["error"], file=sys.stderr)
    path = verify_dir / "receipt.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(f"{receipt['status']} {path}")
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
