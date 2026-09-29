"""hex7seg: every input 0..F must produce the expected active-low pattern."""
import cocotb
from cocotb.triggers import Timer

from tb_utils import COMMON, SEG_PATTERNS, run_sim


@cocotb.test()
async def all_digits(dut):
    for digit in range(16):
        dut.hex.value = digit
        await Timer(1, "ns")
        expected = (~SEG_PATTERNS[digit]) & 0x7F
        got = int(dut.seg_n.value)
        assert got == expected, f"digit {digit:X}: got {got:#04x}, expected {expected:#04x}"


def test_hex7seg():
    run_sim("hex7seg", [COMMON / "hex7seg.sv"], "test_hex7seg")
