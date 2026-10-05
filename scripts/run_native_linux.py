"""Run the self-authored baseline/guard comparison on a real Linux kernel.

The CMake build, fixture directories, captured output and receipt stay in Build.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


EXPECTED = (
    "BASE_DENY_READ=PASS",
    "BASE_DENY_WRITE_OPEN=PASS",
    "ALLOW_READ=PASS ALLOW_WRITE=PASS DENY_READ=PASS DENY_WRITE=PASS errno_read=13 errno_write=13",
    "ALLOW_CREATE=PASS DENY_CREATE=PASS errno=13",
    "ALLOW_TRUNCATE=PASS DENY_TRUNCATE=PASS errno=13",
    "EXEC_CHILD_DENY_READ=PASS errno=13",
    "CHILD_INHERITED_DENIAL=PASS",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-root", required=True, type=Path)
    args = parser.parse_args()
    build_root = args.build_root.resolve()
    if "Build" not in build_root.parts:
        parser.error("build root must be inside Build")
    project = Path(__file__).resolve().parents[1]
    case = build_root / "LandlockFilesystemGate-native"
    case.mkdir(parents=True, exist_ok=True)
    receipt = {
        "status": "OPEN",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(project),
        "build_root": str(build_root),
        "platform": platform.platform(),
    }
    output = case / "probe-output.txt"
    try:
        if sys.platform != "linux":
            raise RuntimeError("real Linux kernel required")
        compiled = case / "compiled"
        subprocess.run(["cmake", "-S", str(project), "-B", str(compiled), "-DCMAKE_BUILD_TYPE=Release"], check=True)
        subprocess.run(["cmake", "--build", str(compiled), "--parallel", "2"], check=True)
        binary = compiled / "landlock-live"
        allowed = case / "fixture/allow"
        denied = case / "fixture/deny"
        allowed.mkdir(parents=True, exist_ok=True)
        denied.mkdir(parents=True, exist_ok=True)
        (allowed / "data").write_bytes(b"allow-marker")
        target = denied / "data"
        target.write_bytes(b"deny-marker")
        (allowed / "new").unlink(missing_ok=True)
        (denied / "new").unlink(missing_ok=True)
        before = digest(target)
        completed = subprocess.run([str(binary), str(allowed), str(denied), str(binary)], capture_output=True, text=True)
        output.write_text(completed.stdout + "\n[stderr]\n" + completed.stderr)
        after = digest(target)
        match = re.search(r"^LANDLOCK_ABI=(\d+)$", completed.stdout, re.MULTILINE)
        receipt.update({
            "kernel_release": platform.release(),
            "binary_sha256": digest(binary),
            "probe_output": str(output),
            "probe_output_sha256": digest(output),
            "probe_returncode": completed.returncode,
            "denied_file_sha256_before": before,
            "denied_file_sha256_after": after,
        })
        if completed.returncode == 77 and "LANDLOCK_APPLY=OPEN" in completed.stdout:
            receipt["error"] = "Landlock ABI below 3 or unavailable"
        elif completed.returncode != 0 or match is None or int(match.group(1)) < 3:
            receipt.update(status="FAIL", error="live Landlock probe failed")
        elif not all(marker in completed.stdout for marker in EXPECTED):
            receipt.update(status="FAIL", error="required permission result missing")
        elif before != after or not (allowed / "new").exists() or (denied / "new").exists():
            receipt.update(status="FAIL", error="fixture integrity failed")
        else:
            receipt.update(status="PASS", landlock_abi=int(match.group(1)), checks=list(EXPECTED))
    except Exception as error:
        receipt.update(status="OPEN" if sys.platform != "linux" else "FAIL", error=f"{type(error).__name__}: {error}")
    path = case / "receipt.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(f"{receipt['status']} {path}")
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
