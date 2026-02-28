#!/usr/bin/env python3
"""
Interactive firmware resilience transformation script
Output folder is fixed to ./brikuu
"""

import os
import struct
import zlib

HEADER_SIZE      = 0x200
NULL_START       = 0x200
NULL_END         = 0x20000
CHECKSUM_SCAN_SZ = 1024

OUTPUT_DIR  = "brikuu"
OUTPUT_NAME = "resilience_failover_test.dev"


def read_original(path):
    print("[+] Reading original firmware")
    with open(path, "rb") as f:
        return f.read()


def build_modified_image(original):
    original_size = len(original)

    if original_size < NULL_END:
        raise ValueError(
            f"Firmware too small ({original_size} bytes) for nullification region"
        )

    print("[+] Preserving header (0x000–0x1FF)")
    output = bytearray(original[:HEADER_SIZE])

    print("[+] Nullifying boot region (0x200–0x20000)")
    output.extend(b"\x00" * (NULL_END - NULL_START))

    print("[+] Filling remaining space with entropy")
    remaining = original_size - len(output)
    output.extend(os.urandom(remaining))

    return output


def find_and_patch_crc32(image):
    print("[+] Scanning for CRC32 field")
    scan_region = min(CHECKSUM_SCAN_SZ, len(image))

    for offset in range(0, scan_region - 4, 4):
        stored = struct.unpack_from("<I", image, offset)[0]

        test_image = bytearray(image)
        struct.pack_into("<I", test_image, offset, 0)

        computed = zlib.crc32(test_image) & 0xFFFFFFFF

        if computed == stored:
            print(f"[+] CRC32 field identified at offset 0x{offset:04X}")
            struct.pack_into("<I", image, offset, computed)
            return True

    print("[-] No CRC32 field identified (may still flash if unchecked)")
    return False


def main():
    input_path = input("Enter path to original firmware file: ").strip()

    if not os.path.isfile(input_path):
        print("[-] Input file not found")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    original = read_original(input_path)
    modified = build_modified_image(original)

    find_and_patch_crc32(modified)

    output_path = os.path.join(OUTPUT_DIR, OUTPUT_NAME)
    with open(output_path, "wb") as f:
        f.write(modified)

    print("[✓] Firmware transformation complete")
    print(f"[✓] Output file : {output_path}")
    print(f"[✓] Final size  : {len(modified)} bytes")


if __name__ == "__main__":
    main()
