"""Check that a Linux test ELF has no runtime loader or shared libraries."""

from __future__ import annotations

from pathlib import Path
import struct


def static_elf_details(path: Path) -> dict[str, int | bool]:
    data = path.read_bytes()
    if len(data) < 52 or data[:4] != b"\x7fELF":
        raise ValueError("test binary is not an ELF file")
    if data[5] != 1:
        raise ValueError("only little-endian ELF is supported")
    if data[4] == 2:
        if len(data) < 64:
            raise ValueError("incomplete ELF64 header")
        header = struct.unpack_from("<Q", data, 32)[0], *struct.unpack_from("<HH", data, 54)
        dynamic_entry_size = 16
        dynamic_format = "<qQ"
    elif data[4] == 1:
        header = struct.unpack_from("<I", data, 28)[0], *struct.unpack_from("<HH", data, 42)
        dynamic_entry_size = 8
        dynamic_format = "<iI"
    else:
        raise ValueError("unsupported ELF class")
    phoff, phentsize, phnum = header
    minimum_phentsize = 56 if data[4] == 2 else 32
    if phentsize < minimum_phentsize or phoff + phentsize * phnum > len(data):
        raise ValueError("invalid ELF program-header table")
    interpreter = False
    needed = 0
    for index in range(phnum):
        offset = phoff + index * phentsize
        program_type = struct.unpack_from("<I", data, offset)[0]
        if program_type == 3:  # PT_INTERP
            interpreter = True
        if program_type != 2:  # PT_DYNAMIC
            continue
        if data[4] == 2:
            segment_offset, segment_size = struct.unpack_from("<QQ", data, offset + 8)[0], struct.unpack_from("<Q", data, offset + 32)[0]
        else:
            segment_offset = struct.unpack_from("<I", data, offset + 4)[0]
            segment_size = struct.unpack_from("<I", data, offset + 16)[0]
        if segment_offset + segment_size > len(data):
            raise ValueError("invalid ELF dynamic segment")
        for entry in range(segment_offset, segment_offset + segment_size, dynamic_entry_size):
            if entry + dynamic_entry_size > segment_offset + segment_size:
                raise ValueError("incomplete ELF dynamic entry")
            tag, _ = struct.unpack_from(dynamic_format, data, entry)
            if tag == 0:  # DT_NULL
                break
            if tag == 1:  # DT_NEEDED
                needed += 1
    return {"elf_class": 64 if data[4] == 2 else 32, "program_headers": phnum, "has_interpreter": interpreter, "needed_libraries": needed, "static": not interpreter and needed == 0}


def require_static_elf(path: Path) -> dict[str, int | bool]:
    details = static_elf_details(path)
    if not details["static"]:
        raise ValueError("Landlock re-exec test requires a static ELF")
    return details
