"""uart_bus_bridge (Day 18): every command against a Python bus slave.

Bytes are fed straight into rx_data/rx_valid (no UART), the slave stalls
bus_ready and delays bus_rvalid at random, and the TX FIFO is randomly "full".
"""
import random
import struct

import cocotb
from cocotb.queue import Queue
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, with_timeout

from tb_utils import TOP, run_sim, start_clock

TIMEOUT = 2000
INFO = 0x0000_4008 | (1 << 16)          # N = 8, K_MAX = 64, version 1


class Env:
    def __init__(self, dut):
        self.dut = dut
        self.mem = {0x000C: INFO}       # word address -> value
        self.writes = []                # (addr, data) in bus order
        self.txq = Queue()
        cocotb.start_soon(self._slave())
        cocotb.start_soon(self._tx_sink())

    async def _slave(self):
        d = self.dut
        pending = []                    # [cycles_left, data] for outstanding reads
        while True:
            ready = random.random() < 0.7
            d.bus_ready.value = int(ready)
            d.bus_rvalid.value = 0
            if pending and pending[0][0] == 0:
                d.bus_rvalid.value = 1
                d.bus_rdata.value = pending.pop(0)[1]
            for p in pending:
                p[0] -= 1
            await FallingEdge(d.clk)    # bridge outputs are stable mid-cycle...
            if ready and int(d.bus_valid.value):  # ...and are sampled at the next edge
                addr = int(d.bus_addr.value)
                if int(d.bus_write.value):
                    data = int(d.bus_wdata.value)
                    self.writes.append((addr, data))
                    self.mem[addr & ~3] = data
                else:
                    assert addr % 4 == 0, f"bridge issued unaligned read {addr:#x}"
                    pending.append([random.randint(0, 2), self.mem.get(addr, 0)])
            await RisingEdge(d.clk)

    async def _tx_sink(self):
        d = self.dut
        while True:
            d.tx_full.value = int(random.random() < 0.3)
            await FallingEdge(d.clk)
            if int(d.tx_push.value) and not int(d.tx_full.value):
                self.txq.put_nowait(int(d.tx_data.value))
            await RisingEdge(d.clk)

    async def send(self, data):
        d = self.dut
        for b in bytes(data):
            await FallingEdge(d.clk)
            d.rx_data.value = b
            d.rx_valid.value = 1
            await FallingEdge(d.clk)
            d.rx_valid.value = 0
            # a real UART byte takes 10 bit times (~4340 clocks); keep a
            # short but realistic gap so random bus stalls can't overrun the bridge
            await ClockCycles(d.clk, random.randint(16, 40))

    async def recv(self, count):
        return bytes([await with_timeout(self.txq.get(), 20_000, "ns") for _ in range(count)])


async def setup(dut):
    start_clock(dut.clk)
    dut.rx_valid.value = 0
    dut.rx_data.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    return Env(dut)


@cocotb.test()
async def every_command(dut):
    env = await setup(dut)

    await env.send(b"P")
    assert await env.recv(3) == bytes([ord("K"), 8, 64]), "ping"

    for _ in range(20):                                   # W / R round trips
        addr, data = random.randrange(0, 0x4000, 4), random.getrandbits(32)
        await env.send(b"W" + struct.pack("<HI", addr, data))
        assert await env.recv(1) == b"K"
        assert env.writes[-1] == (addr, data)
        await env.send(b"R" + struct.pack("<H", addr))
        assert struct.unpack("<I", await env.recv(4))[0] == data

    for length in (1, 3, 17, 64):                         # block write
        addr = random.randrange(0x1000, 0x1F00)
        payload = bytes(random.getrandbits(8) for _ in range(length))
        env.writes.clear()
        await env.send(b"B" + struct.pack("<HH", addr, length) + payload)
        assert await env.recv(1) == b"K"
        assert env.writes == [(addr + n, b) for n, b in enumerate(payload)]

    for addr, length in ((0x3000, 16), (0x3001, 7), (0x3003, 9), (0x3002, 1)):  # block read
        words = {a: random.getrandbits(32) for a in range(addr & ~3, addr + length + 4, 4)}
        env.mem.update(words)
        await env.send(b"D" + struct.pack("<HH", addr, length))
        want = b"".join(struct.pack("<I", words[a]) for a in sorted(words))
        off = addr - (addr & ~3)
        assert await env.recv(length) == want[off:off + length], f"block read {addr:#x}+{length}"

    await env.send(b"B" + struct.pack("<HH", 0x1000, 0))  # zero-length block write
    assert await env.recv(1) == b"K"
    await env.send(b"D" + struct.pack("<HH", 0x3000, 0))  # zero-length read: no reply
    await env.send(b"P")
    assert (await env.recv(3))[0] == ord("K")
    assert int(dut.err_cmd.value) == 0 and int(dut.err_timeout.value) == 0


@cocotb.test()
async def unknown_command_and_timeout(dut):
    env = await setup(dut)
    await env.send(b"x")
    assert await env.recv(1) == b"E"
    assert int(dut.err_cmd.value) == 1

    await env.send(b"W\x00\x10\x01")                      # host stops mid-command
    await ClockCycles(dut.clk, TIMEOUT + 50)
    assert int(dut.err_timeout.value) == 1
    await env.send(b"P")                                  # bridge accepts commands again
    assert (await env.recv(3))[0] == ord("K")


def test_uart_bus_bridge():
    run_sim("uart_bus_bridge", [TOP / "uart_bus_bridge.sv"], "test_uart_bus_bridge",
            parameters={"TIMEOUT_CLKS": TIMEOUT})
