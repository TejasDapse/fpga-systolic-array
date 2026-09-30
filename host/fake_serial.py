#!/usr/bin/env python3
"""Serve the software board model (host.py FakeBoard) on a pseudo-terminal.

Lets the serial-port hosts (host.py, mm_host) be tested without hardware:

    python3 host/fake_serial.py --n 4 &          # prints e.g. /dev/pts/7
    host/mm_host --port /dev/pts/7 --vectors model/vectors/n4.hex
"""
import argparse
import os
import sys
import tty
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from host import FakeBoard  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--k-max", type=int, default=64)
    args = ap.parse_args()
    master, slave = os.openpty()
    tty.setraw(slave)
    print(os.ttyname(slave), flush=True)
    board = FakeBoard(n=args.n, k_max=args.k_max)
    while True:
        data = os.read(master, 4096)
        if not data:
            break
        board.write(data)
        out = board.read(len(board.outbuf))
        if out:
            os.write(master, out)


if __name__ == "__main__":
    main()
