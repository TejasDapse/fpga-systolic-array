// test_mm_ref.cpp -- Day 29/30: C++ model == NumPy on the shared vectors,
// and the analytical perf model == the counters NumPy expects.
//
//   make -C model/cpp test            (vectors from model/vectors.py)
#include <cstdio>
#include <vector>

#include "mm_ref.h"

int main(int argc, char** argv) {
    int failures = 0, total = 0;
    for (int f = 1; f < argc; ++f) {
        for (const mm::Job& j : mm::read_vectors(argv[f])) {
            std::vector<int32_t> c(size_t(j.n * j.n));
            mm::matmul_ref(j.n, j.k, j.a.data(), j.b.data(), c.data());
            bool ok = (c == j.c) && (mm::predict_perf(j.n, j.k) == j.perf);
            if (!ok && failures++ < 5)
                std::printf("MISMATCH %s job %d (N=%d K=%d)\n", argv[f], total, j.n, j.k);
            ++total;
        }
    }
    std::printf("%d/%d vectors match (C and perf counters)\n", total - failures, total);
    std::puts(failures == 0 && total > 0 ? "PASS" : "FAIL");
    return failures == 0 && total > 0 ? 0 : 1;
}
