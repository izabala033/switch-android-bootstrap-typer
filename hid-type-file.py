#!/usr/bin/env python3
"""Type bootstrap.bas through NetHunter's 8-byte USB HID keyboard.

Run as root inside NetHunter Kali. Default layout: Spanish (Spain).
The receiver must use the same layout, Caps Lock off, auto-indent off.
--check validates the entire file without opening HID or typing anything.
"""
import argparse
import errno
import os
from pathlib import Path
import select
import stat
import sys
import time

RELEASE = bytes(8)


def keyboard_map(layout):
    mapping = {}

    def add(chars, keys, modifier=0):
        for char, key in zip(chars, keys):
            mapping[char] = (modifier, key)

    add("abcdefghijklmnopqrstuvwxyz", range(4, 30))
    add("ABCDEFGHIJKLMNOPQRSTUVWXYZ", range(4, 30), 2)
    add("1234567890", range(30, 40))
    add(" \n", [44, 40])
    if layout == "us":
        add("-=[];',./", [45, 46, 47, 48, 51, 52, 54, 55, 56])
        add("!#$&*()", [30, 32, 33, 36, 37, 38, 39], 2)
        add('+|:"<>', [46, 49, 51, 52, 54, 55], 2)
    else:
        add("'+,.-", [45, 48, 54, 55, 56])
        add('!"$&/()=', [30, 31, 33, 35, 36, 37, 38, 39], 2)
        add("*;:", [48, 54, 55], 2)
        add("|#[]", [30, 32, 47, 48], 64)
        add("<", [100])
        add(">", [100], 2)
    return mapping


def report(modifier, key):
    return bytes([modifier, 0, key, 0, 0, 0, 0, 0])


def write_report(fd, data, timeout=3):
    deadline = time.monotonic() + timeout
    while True:
        try:
            written = os.write(fd, data)
            if written != 8:
                raise OSError("Incomplete HID report")
            return
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("HID stopped accepting reports; check the USB connection and kernel")
            # Bounded polling: some old gadget drivers report writable too early.
            select.select([], [fd], [], min(remaining, 0.05))
            time.sleep(0.005)
        except OSError as error:
            if error.errno in (errno.EIO, errno.ENODEV, errno.ESHUTDOWN):
                raise OSError("HID device unavailable. Reconnect/recheck kernel HID errors.") from error
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, default=Path("/sdcard/Download/bootstrap.bas"))
    parser.add_argument("--layout", choices=["es", "us"], default="es")
    parser.add_argument("--device", default="/dev/hidg0")
    parser.add_argument("--character-ms", type=int, default=80)
    parser.add_argument("--newline-ms", type=int, default=250)
    parser.add_argument("--countdown", type=int, default=5)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.character_ms < 40 or args.newline_ms < 40 or args.countdown < 0:
        parser.error("delays must be at least 40 ms and countdown cannot be negative")
    text = args.file.read_text(encoding="utf-8-sig")
    mapping = keyboard_map(args.layout)
    unsupported = sorted(set(text) - mapping.keys())
    if unsupported:
        parser.error("Unsupported characters: " + ", ".join(repr(c) for c in unsupported))
    duration = args.countdown + sum(
        (args.newline_ms if c == "\n" else args.character_ms) / 1000
        for c in text
    )
    print(f"{len(text)} characters | layout={args.layout} | about {duration / 60:.1f} minutes", flush=True)
    if args.check:
        print("Validation passed. No HID device opened; no keystrokes sent.")
        return
    if not stat.S_ISCHR(os.stat(args.device).st_mode):
        parser.error("HID path is not a character device")
    print("Focus the receiving editor. Caps Lock and auto-indent OFF. Ctrl+C stops typing.", flush=True)
    for seconds in range(args.countdown, 0, -1):
        print(f"Starting in {seconds}...", flush=True)
        time.sleep(1)
    fd = os.open(args.device, os.O_WRONLY | os.O_NONBLOCK)
    done = 0
    try:
        write_report(fd, RELEASE)
        for char in text:
            interval = (args.newline_ms if char == "\n" else args.character_ms) / 1000
            modifier, key = mapping[char]
            write_report(fd, report(modifier, key))
            time.sleep(0.02)
            write_report(fd, RELEASE)
            time.sleep(interval - 0.02)
            done += 1
            if done % 100 == 0:
                print(f"\rTyped {done}/{len(text)} characters", end="", flush=True)
        print(f"\nFinished: {done} characters.", flush=True)
    finally:
        # Best-effort release also on Ctrl+C, disconnect, or write errors.
        try:
            write_report(fd, RELEASE, timeout=0.3)
        except OSError:
            pass
        os.close(fd)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        sys.exit(130)
    except (OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
