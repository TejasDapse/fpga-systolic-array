"""uart_tx: bytes sent through the valid/ready handshake appear correctly on the line.

Simulated at CLK_HZ = 3.2 MHz, BAUD = 100 kHz -> 32 clocks per bit (fast to simulate,
same logic as 50 MHz / 115200).
"""
import random

import cocotb
from cocotb.triggers import ClockCycles, RisingEdge

from tb_utils import COMMON, run_sim, start_clock, uart_recv

CLK_HZ, BAUD = 3_200_000, 100_000
CPB = CLK_HZ // BAUD


async def setup(dut):
    start_clock(dut.clk)
    dut.valid.value = 0
    dut.data.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def send_byte(dut, byte):
    """Hold valid until the DUT accepts (valid && ready at a clock edge)."""
    dut.data.value = byte
    dut.valid.value = 1
    while True:
        await RisingEdge(dut.clk)
        if int(dut.ready.value) == 1:      # ready was high at this edge -> accepted
            break
    dut.valid.value = 0


@cocotb.test()
async def idle_line_is_high(dut):
    await setup(dut)
    await ClockCycles(dut.clk, 3 * CPB)
    assert int(dut.tx.value) == 1
    assert int(dut.ready.value) == 1


@cocotb.test()
async def sends_random_bytes(dut):
    await setup(dut)
    data = [0x00, 0xFF, 0x55, 0xAA, 0x01, 0x80] + [random.randrange(256) for _ in range(30)]
    received = []

    async def monitor():
        for _ in data:
            received.append(await uart_recv(dut.tx, dut.clk, CPB))

    mon = cocotb.start_soon(monitor())
    for b in data:
        await send_byte(dut, b)
    await mon
    assert received == data, f"sent {data}\n got {received}"


@cocotb.test()
async def busy_while_sending(dut):
    await setup(dut)
    await send_byte(dut, 0x3C)
    await ClockCycles(dut.clk, 5 * CPB)          # middle of the frame
    assert int(dut.ready.value) == 0, "ready must be low while a frame is on the line"
    await ClockCycles(dut.clk, 6 * CPB)          # frame (10 bits) is over
    assert int(dut.ready.value) == 1


def test_uart_tx():
    run_sim("uart_tx", [COMMON / "uart_tx.sv"], "test_uart_tx",
            parameters={"CLK_HZ": CLK_HZ, "BAUD": BAUD})
