// mm_regmap.h -- register map shared by the SystemC models, co-sim and UVM DPI glue.
// Mirrors rtl/core/mm_regs.sv and model/regmap.py (PLAN.md §6).
#pragma once
#include <cstdint>

namespace mm::reg {
constexpr uint16_t CTRL = 0x0000, STATUS = 0x0004, CFG_K = 0x0008, INFO = 0x000C;
constexpr uint16_t PERF_TOTAL = 0x0010, PERF_COMPUTE = 0x0014, PERF_FILLDRAIN = 0x0018,
                   PERF_IDLE = 0x001C, PERF_MACS = 0x0020;
constexpr uint16_t A_BUF = 0x1000, B_BUF = 0x2000, C_BUF = 0x3000;
constexpr uint32_t CTRL_START = 1u << 0, CTRL_SOFT_RESET = 1u << 1;
constexpr uint32_t STATUS_BUSY = 1u << 0, STATUS_DONE = 1u << 1;
constexpr uint16_t VERSION = 0x0001;

inline uint16_t a_addr(int i, int k, int k_max) { return uint16_t(A_BUF + i * k_max + k); }
inline uint16_t b_addr(int k, int j, int n)     { return uint16_t(B_BUF + k * n + j); }
inline uint16_t c_addr(int i, int j, int n)     { return uint16_t(C_BUF + 4 * (i * n + j)); }
}  // namespace mm::reg
