"""Foundations 04: every byte sent to UART_RXD comes back on UART_TXD.

Simulated at 32 clocks per bit (CLK_HZ = 3.2 MHz, BAUD = 100 kHz).
"""
import random

import cocotb

from tb_utils import COMMON, ROOT, board_reset, read_displays, run_sim, uart_recv, uart_send

CLK_HZ, BAUD = 3_200_000, 100_000
CPB = CLK_HZ // BAUD


@cocotb.test()
async def echoes_back_to_back_bytes(dut):
    await board_reset(dut)
    clk = dut.MAX10_CLK1_50
    data = [0x00, 0xFF, 0x0D, 0x0A] + [random.randrange(256) for _ in range(28)]
    echoed = []

    async def reader():                               # plays the PC's receiver
        for _ in data:
            echoed.append(await uart_recv(dut.UART_TXD, clk, CPB))

    rd = cocotb.start_soon(reader())
    for b in data:                                    # PC sends with no gaps
        await uart_send(dut.UART_RXD, clk, CPB, b)
    await rd

    assert echoed == data, f"sent {data}\n got {echoed}"
    shown = read_displays(dut)
    assert shown & 0xFF == data[-1], "HEX1:HEX0 should show the last byte"
    assert shown >> 8 == len(data), "HEX5..HEX2 should show the byte count"
    assert int(dut.LEDR.value) & 0b11 == 0, "no framing/overflow errors expected"


def test_04_uart_echo():
    run_sim("uart_echo_top",
            [COMMON / f for f in ["sync_2ff.sv", "tick_gen.sv", "hex7seg.sv",
                                  "uart_rx.sv", "uart_tx.sv", "fifo_sync.sv"]]
            + [ROOT / "foundations/04_uart_echo/uart_echo_top.sv"],
            "test_top_04_uart_echo", parameters={"CLK_HZ": CLK_HZ, "BAUD": BAUD})
