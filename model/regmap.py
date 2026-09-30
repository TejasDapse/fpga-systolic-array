"""Register map shared by the cocotb tests and host.py (mirrors rtl/core/mm_regs.sv)."""
CTRL, STATUS, CFG_K, INFO = 0x0000, 0x0004, 0x0008, 0x000C
PERF = {"PERF_TOTAL": 0x0010, "PERF_COMPUTE": 0x0014, "PERF_FILLDRAIN": 0x0018,
        "PERF_IDLE": 0x001C, "PERF_MACS": 0x0020}
A_BUF, B_BUF, C_BUF = 0x1000, 0x2000, 0x3000

CTRL_START, CTRL_SOFT_RESET = 1 << 0, 1 << 1
STATUS_BUSY, STATUS_DONE = 1 << 0, 1 << 1


def a_addr(i, k, k_max):
    return A_BUF + i * k_max + k


def b_addr(k, j, n):
    return B_BUF + k * n + j


def c_addr(i, j, n):
    return C_BUF + 4 * (i * n + j)
