// perf_table.cpp -- Day 30: analytical performance predictions as CSV.
//   ./perf_table > ../../docs/results/perf_model.csv
#include <cstdio>

#include "mm_ref.h"

int main() {
    const double clk_hz = 50e6;
    std::puts("N,K,total,compute,filldrain,macs,utilization,gops_at_50MHz");
    for (int n : {4, 8, 16}) {
        for (int k = 1; k <= 64; ++k) {
            mm::Perf p = mm::predict_perf(n, k);
            double util = double(p.macs) / double(n * n * p.compute);
            double gops = 2.0 * p.macs / (p.total / clk_hz) / 1e9;
            std::printf("%d,%d,%u,%u,%u,%u,%.4f,%.3f\n", n, k, p.total, p.compute,
                        p.filldrain, p.macs, util, gops);
        }
    }
    return 0;
}
