"""Shared helpers for all cocotb testbenches (NOTES §11).

- start_clock / reset helpers
- UART bit-level driver and monitor (to talk to the DUT's serial pins)
- 7-segment decoder (to read the HEX displays in simulation)
- run_sim(): build + run one testbench with the cocotb Python runner

Works with cocotb 1.9 and 2.x.
"""
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cocotb
from cocotb.triggers import ClockCycles, RisingEdge, Timer

TB_DIR = Path(__file__).resolve().parent
ROOT = TB_DIR.parent
RTL = ROOT / "rtl"
COMMON = RTL / "common"
CORE = RTL / "core"
TOP = RTL / "top"
sys.path.insert(0, str(ROOT))          # so tests can import model.golden_model


# --------------------------------------------------------------- clock/reset
async def _clock(sig, period_ns):
    half = period_ns // 2
    while True:
        sig.value = 0
        await Timer(half, "ns")
        sig.value = 1
        await Timer(half, "ns")


def start_clock(sig, period_ns=20):
    """Start a free-running clock on `sig` (default 20 ns = 50 MHz)."""
    return cocotb.start_soon(_clock(sig, period_ns))


# --------------------------------------------------------------- UART
async def uart_send(line, clk, cpb, byte, stop_bit=1):
    """Drive one 8N1 frame onto `line`, each bit lasting `cpb` clock cycles."""
    line.value = 0                                   # start bit
    await ClockCycles(clk, cpb)
    for i in range(8):                               # data, LSB first
        line.value = (byte >> i) & 1
        await ClockCycles(clk, cpb)
    line.value = stop_bit                            # stop bit
    await ClockCycles(clk, cpb)
    line.value = 1                                   # back to idle


async def uart_recv(line, clk, cpb, timeout_cycles=100_000):
    """Wait for a frame on `line` and return the decoded byte.

    Samples in the middle of every bit, exactly like a real receiver.
    """
    waited = 0
    while int(line.value) == 1:
        await RisingEdge(clk)
        waited += 1
        assert waited < timeout_cycles, "uart_recv: timed out waiting for start bit"
    await ClockCycles(clk, cpb // 2)
    assert int(line.value) == 0, "uart_recv: start bit glitch"
    value = 0
    for i in range(8):
        await ClockCycles(clk, cpb)
        value |= int(line.value) << i
    await ClockCycles(clk, cpb)
    assert int(line.value) == 1, "uart_recv: missing stop bit (framing error)"
    return value


def to_signed(value, bits):
    """Interpret the low `bits` bits of an integer as two's complement."""
    value = int(value) & ((1 << bits) - 1)
    return value - (1 << bits) if value >> (bits - 1) else value


# --------------------------------------------------------------- 7-segment
# Active-high patterns {g,f,e,d,c,b,a} for 0..F (same table as hex7seg.sv)
SEG_PATTERNS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07,
                0x7F, 0x6F, 0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71]
SEG_TO_DIGIT = {p: d for d, p in enumerate(SEG_PATTERNS)}


def decode_hex_display(hex_signal):
    """Read an 8-bit active-low HEX output and return the digit 0..15."""
    raw = int(hex_signal.value)
    assert raw & 0x80, "decimal point should be off (bit 7 = 1)"
    pattern = (~raw) & 0x7F
    assert pattern in SEG_TO_DIGIT, f"invalid 7-seg pattern {raw:#04x}"
    return SEG_TO_DIGIT[pattern]


def read_displays(dut, count=6):
    """Decode HEX(count-1)..HEX0 into one integer (HEX0 = least significant)."""
    value = 0
    for n in reversed(range(count)):
        value = (value << 4) | decode_hex_display(getattr(dut, f"HEX{n}"))
    return value


# --------------------------------------------------------------- runner
def _get_runner(sim):
    try:
        from cocotb_tools.runner import get_runner   # cocotb 2.x
    except ImportError:
        from cocotb.runner import get_runner         # cocotb 1.9
    return get_runner(sim)


def run_sim(toplevel, sources, test_module, parameters=None, build_name=None):
    """Compile `sources` with `toplevel` and run the cocotb tests in `test_module`.

    Environment variables:
      SIM=icarus|verilator   (default icarus)
      WAVES=1                dump waveforms into tb/sim_build/<build_name or toplevel>/
    """
    sim = os.environ.get("SIM", "icarus")
    waves = os.environ.get("WAVES", "0") == "1"
    build_dir = TB_DIR / "sim_build" / (build_name or toplevel)
    runner = _get_runner(sim)

    build_args = ["-g2012"] if sim == "icarus" else ["--timing", "-Wno-fatal"]
    runner.build(
        sources=[str(s) for s in sources],
        hdl_toplevel=toplevel,
        parameters=parameters or {},
        build_args=build_args,
        build_dir=build_dir,
        timescale=("1ns", "1ps"),
        waves=waves,
        always=True,
    )
    results_xml = build_dir / "results.xml"
    runner.test(
        hdl_toplevel=toplevel,
        test_module=test_module,
        build_dir=build_dir,
        test_dir=TB_DIR,
        results_xml=str(results_xml),
        waves=waves,
    )

    # Fail the pytest run if any cocotb test failed.
    failed = [tc.get("name") for tc in ET.parse(results_xml).iter("testcase")
              if tc.find("failure") is not None or tc.find("error") is not None]
    assert not failed, f"cocotb tests failed: {failed}"


# --------------------------------------------------------------- board helpers
async def board_reset(dut):
    """Board-level reset for DE10-Lite tops. Buttons are active-low (1 = released)."""
    clk = dut.MAX10_CLK1_50
    start_clock(clk)
    dut.SW.value = 0
    dut.UART_RXD.value = 1
    dut.KEY.value = 0b10                 # hold KEY0 -> reset
    await ClockCycles(clk, 5)
    dut.KEY.value = 0b11                 # release
    await ClockCycles(clk, 3)            # 2-FF synchronizer delay


async def press_key1(dut):
    dut.KEY.value = 0b01
    await ClockCycles(dut.MAX10_CLK1_50, 5)
    dut.KEY.value = 0b11
    await ClockCycles(dut.MAX10_CLK1_50, 5)
