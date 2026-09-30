#!/usr/bin/env bash
# Compile a Quartus project from the command line, print resources + timing,
# and optionally program the DE10-Lite.
#
#   tools/build.sh                         # list projects
#   tools/build.sh 04_uart_echo            # compile only
#   tools/build.sh 04_uart_echo --program  # compile + program over USB-Blaster
#   tools/build.sh all                     # compile every foundations project
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

list_projects() {
    find "$ROOT/foundations" "$ROOT/quartus" -name '*.qpf' 2>/dev/null \
        | sed "s|$ROOT/||; s|/quartus/[^/]*\.qpf$||; s|^quartus/.*|quartus|" | sort -u
}

if [ $# -lt 1 ]; then
    echo "usage: tools/build.sh <project|all> [--program]"
    echo "projects:"; list_projects | sed 's/^/  /'
    exit 1
fi

command -v quartus_sh >/dev/null || {
    echo "quartus_sh not in PATH. Add: export PATH=\$HOME/intelFPGA_lite/<ver>/quartus/bin:\$PATH"
    exit 1
}

build_one() {
    local name="$1" program="$2" dir
    if   [ -d "$ROOT/foundations/$name/quartus" ]; then dir="$ROOT/foundations/$name/quartus"
    elif [ -d "$ROOT/$name/quartus" ];             then dir="$ROOT/$name/quartus"
    elif [ -d "$ROOT/$name" ] && ls "$ROOT/$name"/*.qpf >/dev/null 2>&1; then dir="$ROOT/$name"
    else echo "No Quartus project for '$name'"; list_projects; exit 1
    fi

    local qpf top out
    qpf=$(ls "$dir"/*.qpf | head -1)
    top=$(basename "$qpf" .qpf)
    out="$dir/output_files"

    echo "================ $name ($top) ================"
    (cd "$dir" && quartus_sh --flow compile "$top" > "$dir/build.log" 2>&1) || {
        echo "COMPILE FAILED -- errors:"; grep -E "^Error" "$dir/build.log" | head -20
        echo "full log: $dir/build.log"; exit 1
    }

    echo "-- resources"
    grep -E "Total logic elements|Total registers|Total pins|Total memory bits|Embedded Multiplier" \
        "$out/$top.fit.summary" | sed 's/^/   /'

    echo "-- timing (slow 85C model)"
    grep -A6 "Fmax Summary" "$out/$top.sta.rpt" | grep "MHz" | head -3 | sed 's/^/   /' || true
    if grep -E "^Slack" "$out/$top.sta.summary" | grep -q -- "-"; then
        echo "   !! NEGATIVE SLACK -- timing FAILED. See $out/$top.sta.rpt"
    else
        echo "   all slacks >= 0 (timing met)"
    fi

    if [ "$program" = "yes" ]; then
        echo "-- programming"
        jtagconfig | head -3
        quartus_pgm -m jtag -o "p;$out/$top.sof"
    fi
    echo
}

PROGRAM=no
[ "${2:-}" = "--program" ] && PROGRAM=yes

if [ "$1" = "all" ]; then
    for p in $(ls "$ROOT/foundations" | grep -E '^[0-9]{2}_'); do build_one "$p" no; done
else
    build_one "$1" "$PROGRAM"
fi
