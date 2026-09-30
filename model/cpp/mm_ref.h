// mm_ref.h -- bit-accurate C++ reference model of the accelerator (Phase 5, NOTES §21).
//
// Bit-accurate means: same types and same overflow behaviour as the RTL.
//   int8 x int8 -> int16 product, summed into an int32 accumulator that WRAPS
//   (two's complement), exactly like `acc <= acc + prod` in rtl/core/pe.sv.
//
// Also holds the analytical performance model: what every perf counter in
// rtl/core/mm_regs.sv must read after one job.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace mm {

// C[i][j] = sum_k A[i][k] * B[k][j]; all matrices row-major.
void matmul_ref(int n, int k, const int8_t* a, const int8_t* b, int32_t* c);

struct Perf {
    uint32_t total;       // PERF_TOTAL     START -> DONE
    uint32_t compute;     // PERF_COMPUTE   array enabled (COMPUTE + DRAIN)
    uint32_t filldrain;   // PERF_FILLDRAIN enabled cycles with some PE idle
    uint32_t macs;        // PERF_MACS      useful MACs
    bool operator==(const Perf& o) const {
        return total == o.total && compute == o.compute &&
               filldrain == o.filldrain && macs == o.macs;
    }
};

// Analytical model: 1 CLEAR + K COMPUTE + (2N-1) DRAIN; all PEs busy for
// array steps 2N-1 .. K.
Perf predict_perf(int n, int k);

// One job from a shared vector file (model/vectors.py format).
struct Job {
    int n = 0, k = 0;
    std::vector<int8_t>  a, b;
    std::vector<int32_t> c;      // expected
    Perf perf{};                 // expected
};

std::vector<Job> read_vectors(const std::string& path);

}  // namespace mm
