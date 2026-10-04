#!/usr/bin/env bash
# Lint all RTL with Verilator (-Wall) and Verible (style).   tools/lint.sh
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${FPGA_ENV:-$HOME/miniconda3/envs/fpga}/bin"
cd "$ROOT"
echo "== Verilator --lint-only -Wall (top_de10lite, N = 4 / 8 / 16)"
for n in 4 8 16; do
    "$BIN/verilator" --lint-only -Wall -Wno-UNUSEDSIGNAL -Wno-PROCASSINIT -GN=$n \
        rtl/common/*.sv rtl/core/*.sv rtl/top/*.sv --top-module top_de10lite 2>&1 \
        | grep -E "^%(Warning|Error)" | grep -v "rtl/common" || echo "   N=$n: clean (rtl/core, rtl/top)"
done
echo "== Verible style lint"
"$BIN/verible-verilog-lint" rtl/common/*.sv rtl/core/*.sv rtl/top/*.sv && echo "   clean"
