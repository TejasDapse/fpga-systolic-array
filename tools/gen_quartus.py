#!/usr/bin/env python3
"""Generate Quartus project files (.qpf, .qsf, .sdc) for every DE10-Lite project.

All designs share the same top-level port list, so the pin table lives here
once. Run from anywhere:   python3 tools/gen_quartus.py

IMPORTANT: pin numbers below are from the DE10-Lite User Manual. Before the
first compile, cross-check them against the .qsf that Terasic's
"DE10-Lite System Builder" generates (see foundations/README.md, step 3).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEVICE = "10M50DAF484C7G"

# ---------------------------------------------------------------- pin table
PINS = {
    "MAX10_CLK1_50": "P11",
    "KEY[0]": "B8", "KEY[1]": "A7",
}
PINS.update({f"SW[{i}]": p for i, p in enumerate(
    ["C10", "C11", "D12", "C12", "A12", "B12", "A13", "A14", "B14", "F15"])})
PINS.update({f"LEDR[{i}]": p for i, p in enumerate(
    ["A8", "A9", "A10", "B10", "D13", "C13", "E14", "D14", "A11", "B11"])})
HEX_PINS = {
    0: ["C14", "E15", "C15", "C16", "E16", "D17", "C17", "D15"],
    1: ["C18", "D18", "E18", "B16", "A17", "A18", "B17", "A16"],
    2: ["B20", "A20", "B19", "A21", "B21", "C22", "B22", "A19"],
    3: ["F21", "E22", "E21", "C19", "C20", "D19", "E17", "D22"],
    4: ["F18", "E20", "E19", "J18", "H19", "F19", "F20", "F17"],
    5: ["J20", "K20", "L18", "N18", "M20", "N19", "N20", "L19"],
}
for n, pins in HEX_PINS.items():
    PINS.update({f"HEX{n}[{i}]": p for i, p in enumerate(pins)})
# UART on the 2x20 GPIO header: GPIO[0] = header pin 1, GPIO[1] = header pin 2
PINS["UART_TXD"] = "V10"   # GPIO[0]  FPGA -> adapter RXD
PINS["UART_RXD"] = "W10"   # GPIO[1]  adapter TXD -> FPGA

# ---------------------------------------------------------------- projects
# name: (top entity, [RTL files relative to the repo root], {top-level parameters})
COMMON = "rtl/common"
CORE = "rtl/core"
UART_FILES = [f"{COMMON}/{f}" for f in ["sync_2ff.sv", "tick_gen.sv", "hex7seg.sv",
                                         "uart_rx.sv", "uart_tx.sv", "fifo_sync.sv"]]
PROJECTS = {
    "foundations/01_switch_led": ("switch_led_top", [
        "foundations/01_switch_led/switch_led_top.sv"]),
    "foundations/02_blinky": ("blinky_top", [
        f"{COMMON}/sync_2ff.sv", f"{COMMON}/tick_gen.sv",
        "foundations/02_blinky/blinky_top.sv"]),
    "foundations/03_hex_counter": ("hex_counter_top", [
        f"{COMMON}/sync_2ff.sv", f"{COMMON}/tick_gen.sv", f"{COMMON}/hex7seg.sv",
        "foundations/03_hex_counter/hex_counter_top.sv"]),
    "foundations/04_uart_echo": ("uart_echo_top", [
        f"{COMMON}/sync_2ff.sv", f"{COMMON}/tick_gen.sv", f"{COMMON}/hex7seg.sv",
        f"{COMMON}/uart_rx.sv", f"{COMMON}/uart_tx.sv", f"{COMMON}/fifo_sync.sv",
        "foundations/04_uart_echo/uart_echo_top.sv"]),
    # The accelerator. Change N here (4 = bring-up, 8 = final) and re-run this script.
    ".": ("top_de10lite", UART_FILES + [
        f"{CORE}/{f}" for f in ["pe.sv", "systolic_array.sv", "skew_buffer.sv",
                                "sram_sp.sv", "mm_controller.sv", "mm_core.sv"]] + [
        "rtl/top/cmd_parser.sv", "rtl/top/top_de10lite.sv"], {"N": 4, "K_MAX": 64}),
}

SDC = """\
# 50 MHz board clock -> 20 ns period
create_clock -name clk50 -period 20.000 [get_ports MAX10_CLK1_50]
derive_clock_uncertainty

# Buttons, switches, LEDs, HEX and UART are slow/asynchronous: don't time them.
set_false_path -from [get_ports {KEY[*] SW[*] UART_RXD}]
set_false_path -to   [get_ports {LEDR[*] HEX*[*] UART_TXD}]
"""


def qsf_text(top: str, rtl_files: list[str], qdir: Path, params: dict) -> str:
    lines = [
        f'set_global_assignment -name FAMILY "MAX 10"',
        f"set_global_assignment -name DEVICE {DEVICE}",
        f"set_global_assignment -name TOP_LEVEL_ENTITY {top}",
        "set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files",
        "set_global_assignment -name NUM_PARALLEL_PROCESSORS ALL",
        "set_global_assignment -name VERILOG_INPUT_VERSION SYSTEMVERILOG_2005",
        f"set_global_assignment -name SDC_FILE {top}.sdc",
        "",
        "# ---- source files ----",
    ]
    for f in rtl_files:
        rel = Path("../" * len(qdir.relative_to(ROOT).parts)) / f
        lines.append(f"set_global_assignment -name SYSTEMVERILOG_FILE {rel.as_posix()}")
    if params:
        lines += ["", "# ---- top-level parameters ----"]
        lines += [f"set_parameter -name {k} {v}" for k, v in params.items()]
    lines += ["", "# ---- pins (all 3.3-V LVTTL) ----"]
    for port, pin in PINS.items():
        lines.append(f"set_location_assignment PIN_{pin} -to {port}")
        lines.append(f'set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to {port}')
    return "\n".join(lines) + "\n"


def main() -> None:
    for proj, (top, files, *params) in PROJECTS.items():
        qdir = ROOT / proj / "quartus"
        qdir.mkdir(parents=True, exist_ok=True)
        (qdir / f"{top}.qpf").write_text(f'PROJECT_REVISION = "{top}"\n')
        (qdir / f"{top}.qsf").write_text(qsf_text(top, files, qdir, params[0] if params else {}))
        (qdir / f"{top}.sdc").write_text(SDC)
        print(f"wrote {qdir.relative_to(ROOT)}/{top}.{{qpf,qsf,sdc}}")


if __name__ == "__main__":
    main()
