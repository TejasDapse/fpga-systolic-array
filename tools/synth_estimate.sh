#!/usr/bin/env bash
# Pre-Quartus resource estimate with open-source tools: sv2v -> Yosys coarse synthesis.
# Counts what Quartus maps to hard blocks (8x8 multipliers -> DSP 9x9, RAMs -> M9K).
# NOT a substitute for Quartus: no MAX 10 mapping, no timing.     tools/synth_estimate.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${FPGA_ENV:-$HOME/miniconda3/envs/fpga}/bin"
SV2V="${SV2V:-$HOME/tools/sv2v/sv2v-Linux/sv2v}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cd "$ROOT"
"$SV2V" -DSYNTHESIS --top=mm_core rtl/core/*.sv > "$TMP/mm_core.v"
echo "| N | 8x8 multipliers (\$mul_16) | RAM read ports (\$memrd) | MAX 10 10M50 limits |"
echo "|---|---|---|---|"
for n in 4 8 16; do
    "$BIN/yosys" -q -p "read_verilog $TMP/mm_core.v; chparam -set N $n mm_core; \
        hierarchy -top mm_core; synth -top mm_core -run :coarse; \
        tee -q -o $TMP/s.txt stat -width" >/dev/null 2>&1
    # totals are in the "design hierarchy" section at the end of the report
    mul=$(awk '/=== design hierarchy ===/ {h=1} h && /\$mul_16/ {print $1}' "$TMP/s.txt")
    mem=$(awk '/=== design hierarchy ===/ {h=1} h && /\$memrd/  {print $1}' "$TMP/s.txt")
    echo "| $n | $mul | $mem | 288 x 9-bit multipliers, 182 M9K |"
done
