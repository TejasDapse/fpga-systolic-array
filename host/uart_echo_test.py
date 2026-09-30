#!/usr/bin/env python3
"""Hardware test for Foundations 04 (UART echo) -- run on the Mac.

Sends random bytes to the DE10-Lite, reads the echo back and counts errors.

    python host/uart_echo_test.py                      # auto-detect port, 10,000 bytes
    python host/uart_echo_test.py --port /dev/tty.usbserial-0001 --count 50000
"""
import argparse
import glob
import os
import sys
import time

import serial

CHUNK = 64      # send a chunk, read it back -> the FPGA's FIFO never overflows


def find_port():
    patterns = ["/dev/ttyUSB*", "/dev/ttyACM*",                        # Linux
                "/dev/tty.usbserial*", "/dev/tty.SLAB*",                   # macOS
                "/dev/tty.wchusbserial*", "/dev/tty.usbmodem*"]
    candidates = sorted(p for pat in patterns for p in glob.glob(pat))
    if not candidates:
        sys.exit("No USB-UART adapter found. Plug it in and check: ls /dev/tty.*")
    if len(candidates) > 1:
        print(f"Several ports found, using {candidates[0]}: {candidates}")
    return candidates[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=115_200)
    ap.add_argument("--count", type=int, default=10_000)
    args = ap.parse_args()

    port = args.port or find_port()
    print(f"Port {port} @ {args.baud} baud, sending {args.count} bytes")

    errors, sent = 0, 0
    with serial.Serial(port, args.baud, timeout=1) as s:
        s.reset_input_buffer()
        start = time.time()
        while sent < args.count:
            n = min(CHUNK, args.count - sent)
            data = os.urandom(n)
            s.write(data)
            back = s.read(n)
            if len(back) != n:
                sys.exit(f"Timeout: sent {n} bytes, got {len(back)} back after {sent} bytes. "
                         "Check wiring (TX<->RX crossed, GND) and that the design is loaded.")
            errors += sum(a != b for a, b in zip(data, back))
            sent += n
        elapsed = time.time() - start

    rate = 2 * sent / elapsed     # bytes moved in both directions
    print(f"Done: {sent} bytes, {errors} errors, {elapsed:.2f} s ({rate:.0f} B/s both ways)")
    print("PASS" if errors == 0 else "FAIL")
    print(f"The board's HEX5..HEX2 should now show {sent & 0xFFFF:04X} (bytes received, hex)")
    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
