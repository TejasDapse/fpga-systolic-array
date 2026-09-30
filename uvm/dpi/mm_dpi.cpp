// mm_dpi.cpp -- DPI-C glue: the UVM scoreboard calls the bit-accurate C++ model
// (model/cpp/mm_ref.cpp) instead of re-implementing it in SystemVerilog.
//
//   import "DPI-C" function void mm_ref_dpi(input int n, input int k,
//                                           input byte a[1024], input byte b[1024],
//                                           output int c[256]);
// Fixed-size unpacked arrays are passed as C pointers (IEEE 1800 Annex H).
//   import "DPI-C" function int unsigned mm_perf_dpi(input int n, input int k, input int which);
#include <cstdint>

#include "mm_ref.h"
#include "svdpi.h"

extern "C" void mm_ref_dpi(int n, int k, const char* a, const char* b, int* c) {
    mm::matmul_ref(n, k, reinterpret_cast<const int8_t*>(a), reinterpret_cast<const int8_t*>(b),
                   reinterpret_cast<int32_t*>(c));
}

// which: 0 total, 1 compute, 2 filldrain, 3 macs
extern "C" unsigned mm_perf_dpi(int n, int k, int which) {
    const mm::Perf p = mm::predict_perf(n, k);
    switch (which) {
        case 0: return p.total;
        case 1: return p.compute;
        case 2: return p.filldrain;
        default: return p.macs;
    }
}
