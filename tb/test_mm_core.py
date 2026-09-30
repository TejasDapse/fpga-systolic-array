"""mm_core through its register bus (Day 17): results, perf counters, corner cases.

The same register map is used by the UART bridge, host.py and (later) UVM / SystemC.
"""
import os
from pathlib import Path

import cocotb
import numpy as np
import pytest
from cocotb.triggers import ClockCycles, FallingEdge

from tb_utils import CORE, run_sim, start_clock, to_signed
from model.golden_model import edge_cases, expected_perf, matmul_int32, random_int8
from model import regmap as rm
from model.vectors import make_jobs, read_vectors, write_vectors

K_MAX = 64
N_RANDOM = int(os.environ.get("MM_RANDOM", "200"))    # random jobs per N
N_VECTORS = int(os.environ.get("MM_VECTORS", "100"))  # shared-vector jobs per N
VECTOR_DIR = Path(__file__).resolve().parent.parent / "model" / "vectors"


class Bus:
    """Valid/ready bus master. Drives on falling edges, samples mid-cycle."""

    def __init__(self, dut):
        self.dut = dut
        dut.bus_valid.value = 0
        dut.bus_write.value = 0
        dut.bus_addr.value = 0
        dut.bus_wdata.value = 0

    async def _request(self, write, addr, data=0):
        d = self.dut
        d.bus_valid.value = 1
        d.bus_write.value = int(write)
        d.bus_addr.value = addr
        d.bus_wdata.value = data & 0xFFFFFFFF
        while True:
            ready = int(d.bus_ready.value)
            await FallingEdge(d.clk)
            if ready:
                break
        d.bus_valid.value = 0

    async def write(self, addr, data):
        await self._request(True, addr, data)

    async def read(self, addr):
        await self._request(False, addr)
        assert int(self.dut.bus_rvalid.value), "rvalid must follow a read by 1 cycle"
        return int(self.dut.bus_rdata.value)


async def load(bus, n, a, b):
    k = a.shape[1]
    await bus.write(rm.CFG_K, k)
    for i in range(n):
        for kk in range(k):
            await bus.write(rm.a_addr(i, kk, K_MAX), int(a[i, kk]) & 0xFF)
    for kk in range(k):
        for j in range(n):
            await bus.write(rm.b_addr(kk, j, n), int(b[kk, j]) & 0xFF)


async def wait_done_and_read(bus, n):
    for _ in range(K_MAX + 4 * n + 20):
        if await bus.read(rm.STATUS) & rm.STATUS_DONE:
            break
    else:
        raise AssertionError("DONE never set")
    c = np.array([[to_signed(await bus.read(rm.c_addr(i, j, n)), 32) for j in range(n)]
                  for i in range(n)])
    perf = {name: await bus.read(addr) for name, addr in rm.PERF.items()}
    return c, perf


async def run_job(bus, n):
    await bus.write(rm.CTRL, rm.CTRL_START)
    return await wait_done_and_read(bus, n)


def check(name, n, a, b, c, perf):
    want = matmul_int32(a, b)
    assert np.array_equal(c, want), f"{name}:\n got\n{c}\n want\n{want}"
    for key, value in expected_perf(n, a.shape[1]).items():
        assert perf[key] == value, f"{name}: {key} = {perf[key]}, expected {value}"


async def setup(dut):
    start_clock(dut.clk)
    bus = Bus(dut)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    return bus, 2 ** len(dut.u_regs.wr_lane)            # N is a power of 2


@cocotb.test()
async def reset_values_and_info(dut):
    bus, n = await setup(dut)
    info = await bus.read(rm.INFO)
    assert info & 0xFF == n and (info >> 8) & 0xFF == K_MAX and info >> 16 == 1
    assert await bus.read(rm.CFG_K) == K_MAX
    assert await bus.read(rm.STATUS) == 0
    for bad in (0, K_MAX + 1, 0xFFFFFFFF):              # out-of-range K is ignored
        await bus.write(rm.CFG_K, bad)
        assert await bus.read(rm.CFG_K) == K_MAX
    assert await bus.read(0x0100) == 0, "unmapped read returns 0"
    idle1 = await bus.read(rm.PERF["PERF_IDLE"])
    idle2 = await bus.read(rm.PERF["PERF_IDLE"])
    assert idle2 > idle1 > 0, "PERF_IDLE counts while idle"


@cocotb.test()
async def random_and_edge_jobs(dut):
    bus, n = await setup(dut)
    rng = np.random.default_rng(n)
    cases = []
    for k in (1, 2 * n - 2, 2 * n - 1, K_MAX):          # around the fill/drain boundary
        cases += [(f"{name}_k{k}", ab) for name, ab in edge_cases(n, k).items()]
    for r in range(N_RANDOM):
        k = int(rng.integers(1, K_MAX + 1))
        cases.append((f"random{r}_k{k}", (random_int8((n, k), rng), random_int8((k, n), rng))))
    for name, (a, b) in cases:
        await load(bus, n, a, b)
        c, perf = await run_job(bus, n)
        check(name, n, a, b, c, perf)
    dut._log.info("N=%d: %d jobs passed through the bus", n, len(cases))


@cocotb.test()
async def back_to_back_and_busy_protection(dut):
    bus, n = await setup(dut)
    rng = np.random.default_rng(7)
    a, b = random_int8((n, K_MAX), rng), random_int8((K_MAX, n), rng)
    await load(bus, n, a, b)
    await bus.write(rm.CTRL, rm.CTRL_START)
    assert await bus.read(rm.STATUS) & rm.STATUS_BUSY
    # While busy: a second START, a new K and buffer writes must all be ignored.
    await bus.write(rm.CTRL, rm.CTRL_START)
    await bus.write(rm.a_addr(0, 0, K_MAX), 0x55)
    await bus.write(rm.b_addr(0, 0, n), 0x55)
    c, perf = await wait_done_and_read(bus, n)
    check("busy_protection", n, a, b, c, perf)
    # Run again without reloading: same buffers, same answer (DONE clears on START).
    c, perf = await run_job(bus, n)
    check("back_to_back", n, a, b, c, perf)


@cocotb.test()
async def soft_reset_mid_compute(dut):
    bus, n = await setup(dut)
    rng = np.random.default_rng(3)
    a, b = random_int8((n, K_MAX), rng), random_int8((K_MAX, n), rng)
    await load(bus, n, a, b)
    await bus.write(rm.CTRL, rm.CTRL_START)
    await ClockCycles(dut.clk, 10)
    await FallingEdge(dut.clk)                          # bus is driven on falling edges
    await bus.write(rm.CTRL, rm.CTRL_SOFT_RESET)
    assert await bus.read(rm.STATUS) == 0, "soft reset returns to IDLE"
    assert await bus.read(rm.PERF["PERF_TOTAL"]) == 0
    assert await bus.read(rm.CFG_K) == K_MAX, "soft reset restores CFG_K"
    assert await bus.read(rm.c_addr(0, 0, n)) == 0, "soft reset clears C"
    # Buffers survive a soft reset (RAM has no reset), so a fresh job still works.
    c, perf = await run_job(bus, n)
    check("after_soft_reset", n, a, b, c, perf)


@cocotb.test()
async def shared_vectors(dut):
    """Same vector file as the C++ / SystemC models (model/vectors.py)."""
    bus, n = await setup(dut)
    path = VECTOR_DIR / f"n{n}.hex"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_vectors(path, make_jobs(n, 1000, seed=2026 + n))
    for idx, job in enumerate(read_vectors(path)):
        if idx == N_VECTORS:
            break
        await load(bus, n, job["a"], job["b"])
        c, perf = await run_job(bus, n)
        assert np.array_equal(c, job["c"]), f"vector {idx}: C mismatch"
        for key, value in job["perf"].items():
            assert perf[key] == value, f"vector {idx}: {key} = {perf[key]}, expected {value}"


@pytest.mark.parametrize("n", [4, 8])
def test_mm_core(n):
    run_sim("mm_core",
            [CORE / f for f in ["pe.sv", "systolic_array.sv", "skew_buffer.sv", "sram_sp.sv",
                                "mm_controller.sv", "mm_regs.sv", "mm_core.sv"]],
            "test_mm_core", parameters={"N": n, "K_MAX": K_MAX}, build_name=f"mm_core_n{n}")
