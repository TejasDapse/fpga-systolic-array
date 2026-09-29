"""Foundations 01: LEDR must mirror SW."""
import random

import cocotb
from cocotb.triggers import Timer

from tb_utils import ROOT, run_sim


@cocotb.test()
async def leds_follow_switches(dut):
    for value in [0, 0x3FF, 0x155, 0x2AA] + [random.randrange(1024) for _ in range(20)]:
        dut.SW.value = value
        await Timer(1, "ns")
        assert int(dut.LEDR.value) == value
    assert int(dut.UART_TXD.value) == 1


def test_01_switch_led():
    run_sim("switch_led_top", [ROOT / "foundations/01_switch_led/switch_led_top.sv"],
            "test_top_01_switch_led")
