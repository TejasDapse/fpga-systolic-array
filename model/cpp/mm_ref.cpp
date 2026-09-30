// mm_ref.cpp -- see mm_ref.h
#include "mm_ref.h"

#include <algorithm>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace mm {

void matmul_ref(int n, int k, const int8_t* a, const int8_t* b, int32_t* c) {
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            uint32_t acc = 0;                               // unsigned: defined wrap-around
            for (int kk = 0; kk < k; ++kk) {
                int16_t prod = int16_t(a[i * k + kk]) * int16_t(b[kk * n + j]);
                acc += uint32_t(int32_t(prod));             // sign-extend, then add mod 2^32
            }
            c[i * n + j] = int32_t(acc);
        }
    }
}

Perf predict_perf(int n, int k) {
    const uint32_t compute = uint32_t(k + 2 * n - 1);
    const uint32_t all_busy = uint32_t(std::max(0, k - 2 * n + 2));
    return {compute + 1, compute, compute - all_busy, uint32_t(n * n * k)};
}

std::vector<Job> read_vectors(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open " + path);
    std::vector<Job> jobs;
    std::string line, tag;
    auto next = [&](const char* want) {
        while (std::getline(in, line) && line.empty()) {}
        std::istringstream ss(line);
        ss >> tag;
        if (tag != want) throw std::runtime_error(path + ": expected '" + want + "', got: " + line);
        return ss;
    };
    while (in >> std::ws, !in.eof()) {
        Job j;
        auto hdr = next("job");
        hdr >> std::hex >> j.n >> j.k;
        auto read_all = [&](const char* tag_name, auto& vec, size_t count) {
            auto ss = next(tag_name);
            uint32_t v;
            for (size_t i = 0; i < count && (ss >> std::hex >> v); ++i)
                vec.push_back(static_cast<typename std::decay_t<decltype(vec)>::value_type>(v));
            if (vec.size() != count) throw std::runtime_error(path + ": short '" + tag_name + "' line");
        };
        read_all("a", j.a, size_t(j.n * j.k));
        read_all("b", j.b, size_t(j.k * j.n));
        read_all("c", j.c, size_t(j.n * j.n));
        auto p = next("p");
        p >> std::hex >> j.perf.total >> j.perf.compute >> j.perf.filldrain >> j.perf.macs;
        jobs.push_back(std::move(j));
    }
    return jobs;
}

}  // namespace mm
