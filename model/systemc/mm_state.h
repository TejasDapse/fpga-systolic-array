// mm_state.h -- architectural state + register decode shared by the LT and CA models.
//
// Same semantics as rtl/core/mm_regs.sv: A/B writes store the low byte and are
// ignored while BUSY; out-of-range CFG_K is ignored; START is ignored while
// BUSY; unmapped reads return 0. Timing (when a job runs, what BUSY reads) is
// left to the model that owns this state.
#pragma once
#include <cstdint>
#include <vector>

#include "../cpp/mm_ref.h"
#include "mm_regmap.h"

namespace mm {

struct MmState {
    const int n, k_max;
    uint32_t cfg_k;
    bool busy = false, done = false;
    Perf perf{};
    uint32_t perf_idle = 0;
    std::vector<int8_t> a, b;          // N x K_MAX and K_MAX x N buffers (RTL layout)
    std::vector<int32_t> c;

    MmState(int n_, int k_max_)
        : n(n_), k_max(k_max_), cfg_k(uint32_t(k_max_)),
          a(size_t(n_ * k_max_)), b(size_t(k_max_ * n_)), c(size_t(n_ * n_)) {}

    // Soft reset: everything except the operand RAMs (they have no reset in RTL).
    void soft_reset() {
        cfg_k = uint32_t(k_max);
        busy = done = false;
        perf = {};
        perf_idle = 0;
        std::fill(c.begin(), c.end(), 0);
    }

    // Functional result of the job currently configured (A rows are K_MAX apart).
    void compute_c() {
        const int k = int(cfg_k);
        std::vector<int8_t> a_packed(size_t(n * k));
        for (int i = 0; i < n; ++i)
            for (int kk = 0; kk < k; ++kk) a_packed[size_t(i * k + kk)] = a[size_t(i * k_max + kk)];
        matmul_ref(n, k, a_packed.data(), b.data(), c.data());
    }

    enum class WriteEffect { NONE, START, SOFT_RESET };

    WriteEffect write(uint16_t addr, uint32_t data) {
        const int region = addr >> 12, off = addr & 0xFFF;
        if (region == 0) {
            if (addr == reg::CTRL) {
                if (data & reg::CTRL_SOFT_RESET) return WriteEffect::SOFT_RESET;
                if ((data & reg::CTRL_START) && !busy) return WriteEffect::START;
            } else if (addr == reg::CFG_K && data >= 1 && data <= uint32_t(k_max)) {
                cfg_k = data;
            }
        } else if (!busy && region == 1 && off < n * k_max) {
            a[size_t(off)] = int8_t(data & 0xFF);
        } else if (!busy && region == 2 && off < k_max * n) {
            b[size_t(off)] = int8_t(data & 0xFF);
        }
        return WriteEffect::NONE;
    }

    uint32_t read(uint16_t addr) const {
        const int region = addr >> 12, off = addr & 0xFFF;
        if (region == 3) return off < 4 * n * n ? uint32_t(c[size_t(off / 4)]) : 0;
        if (region != 0) return 0;
        switch (addr & ~3u) {
            case reg::STATUS:         return (done ? reg::STATUS_DONE : 0) | (busy ? reg::STATUS_BUSY : 0);
            case reg::CFG_K:          return cfg_k;
            case reg::INFO:           return uint32_t(reg::VERSION) << 16 | uint32_t(k_max) << 8 | uint32_t(n);
            case reg::PERF_TOTAL:     return perf.total;
            case reg::PERF_COMPUTE:   return perf.compute;
            case reg::PERF_FILLDRAIN: return perf.filldrain;
            case reg::PERF_IDLE:      return perf_idle;
            case reg::PERF_MACS:      return perf.macs;
            default:                  return 0;
        }
    }
};

}  // namespace mm
