// mm_host.cpp -- C++ host test for the accelerator over UART (Phase 6, Day 45).
//
// Replays the shared vector file (model/vectors.py) on the board through the
// UART-to-bus bridge (PLAN.md §5/§6), compares C and the perf counters with the
// expected values, and writes the measured counters as CSV for the HW/SW
// performance correlation (tools/correlate.py).
//
//   make -C host
//   host/mm_host --port /dev/ttyUSB0 --vectors model/vectors/n4.hex --count 100
//                --csv docs/results/fpga_perf_n4.csv          (one command line)
// Without a board:  python3 host/fake_serial.py &   (prints a /dev/pts/N port)
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>

#include <chrono>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "../model/cpp/mm_ref.h"
#include "../model/systemc/mm_regmap.h"

namespace {

class Uart {
public:
    explicit Uart(const std::string& port) {
        fd_ = ::open(port.c_str(), O_RDWR | O_NOCTTY);
        if (fd_ < 0) throw std::runtime_error("cannot open " + port + ": " + std::strerror(errno));
        termios t{};
        tcgetattr(fd_, &t);
        cfmakeraw(&t);                                // 8N1, no echo, no flow control
        cfsetispeed(&t, B115200);
        cfsetospeed(&t, B115200);
        t.c_cflag |= CLOCAL | CREAD;
        t.c_cc[VMIN] = 0;
        t.c_cc[VTIME] = 20;                           // 2 s read timeout
        tcsetattr(fd_, TCSANOW, &t);
        tcflush(fd_, TCIOFLUSH);
    }
    ~Uart() { if (fd_ >= 0) ::close(fd_); }

    void send(const std::vector<uint8_t>& d) {
        for (size_t off = 0; off < d.size();) {
            ssize_t w = ::write(fd_, d.data() + off, d.size() - off);
            if (w < 0) throw std::runtime_error("write failed");
            off += size_t(w);
        }
    }
    std::vector<uint8_t> recv(size_t count) {
        std::vector<uint8_t> d(count);
        for (size_t got = 0; got < count;) {
            ssize_t r = ::read(fd_, d.data() + got, count - got);
            if (r <= 0)
                throw std::runtime_error("timeout: expected " + std::to_string(count) + " bytes, got " +
                                         std::to_string(got) + " (wiring? .sof loaded? try KEY0)");
            got += size_t(r);
        }
        return d;
    }

private:
    int fd_ = -1;
};

void put16(std::vector<uint8_t>& v, uint32_t x) { v.push_back(uint8_t(x)); v.push_back(uint8_t(x >> 8)); }
void put32(std::vector<uint8_t>& v, uint32_t x) { put16(v, x & 0xFFFF); put16(v, x >> 16); }
uint32_t get32(const uint8_t* p) { return p[0] | p[1] << 8 | p[2] << 16 | uint32_t(p[3]) << 24; }

// Register-level access through the bridge: W/R/B/D/P.
class Accelerator {
public:
    explicit Accelerator(Uart& u) : u_(u) {
        u_.send({'P'});
        auto r = u_.recv(3);
        if (r[0] != 'K') throw std::runtime_error("bad ping reply");
        n = r[1];
        k_max = r[2];
    }
    int n = 0, k_max = 0;

    void write(uint16_t addr, uint32_t data) {
        std::vector<uint8_t> c{'W'}; put16(c, addr); put32(c, data);
        expect_ok(c);
    }
    uint32_t read(uint16_t addr) {
        std::vector<uint8_t> c{'R'}; put16(c, addr);
        u_.send(c);
        return get32(u_.recv(4).data());
    }
    void write_block(uint16_t addr, const int8_t* data, size_t len) {
        std::vector<uint8_t> c{'B'}; put16(c, addr); put16(c, uint32_t(len));
        c.insert(c.end(), reinterpret_cast<const uint8_t*>(data), reinterpret_cast<const uint8_t*>(data) + len);
        expect_ok(c);
    }
    std::vector<uint8_t> read_block(uint16_t addr, size_t len) {
        std::vector<uint8_t> c{'D'}; put16(c, addr); put16(c, uint32_t(len));
        u_.send(c);
        return u_.recv(len);
    }

    void run(const mm::Job& j, std::vector<int32_t>& c, mm::Perf& p) {
        write(mm::reg::CFG_K, uint32_t(j.k));
        for (int i = 0; i < n; ++i)                   // A rows are K_MAX apart
            write_block(mm::reg::a_addr(i, 0, k_max), &j.a[size_t(i * j.k)], size_t(j.k));
        write_block(mm::reg::B_BUF, j.b.data(), j.b.size());
        write(mm::reg::CTRL, mm::reg::CTRL_START);
        for (int polls = 0; !(read(mm::reg::STATUS) & mm::reg::STATUS_DONE); ++polls)
            if (polls > 1000) throw std::runtime_error("DONE never set");
        auto raw = read_block(mm::reg::C_BUF, size_t(4 * n * n));
        c.resize(size_t(n * n));
        for (int i = 0; i < n * n; ++i) c[size_t(i)] = int32_t(get32(&raw[size_t(4 * i)]));
        p = {read(mm::reg::PERF_TOTAL), read(mm::reg::PERF_COMPUTE),
             read(mm::reg::PERF_FILLDRAIN), read(mm::reg::PERF_MACS)};
    }

private:
    Uart& u_;
    void expect_ok(const std::vector<uint8_t>& cmd) {
        u_.send(cmd);
        if (u_.recv(1)[0] != 'K') throw std::runtime_error(std::string("command '") + char(cmd[0]) + "' not acknowledged");
    }
};

}  // namespace

int main(int argc, char** argv) {
    std::string port = "/dev/ttyUSB0", vectors, csv_path;
    size_t count = 100;
    for (int i = 1; i + 1 < argc; i += 2) {
        std::string a = argv[i];
        if (a == "--port") port = argv[i + 1];
        else if (a == "--vectors") vectors = argv[i + 1];
        else if (a == "--count") count = std::stoul(argv[i + 1]);
        else if (a == "--csv") csv_path = argv[i + 1];
        else { std::fprintf(stderr, "unknown option %s\n", a.c_str()); return 2; }
    }
    if (vectors.empty()) {
        std::puts("usage: mm_host --vectors <file.hex> [--port /dev/ttyUSB0] [--count 100] [--csv out.csv]");
        return 2;
    }
    try {
        Uart uart(port);
        Accelerator acc(uart);
        std::printf("port %s: N = %d, K_MAX = %d\n", port.c_str(), acc.n, acc.k_max);
        auto jobs = mm::read_vectors(vectors);
        std::ofstream csv;
        if (!csv_path.empty()) {
            csv.open(csv_path);
            csv << "job,N,K,total,compute,filldrain,macs,host_ms,c_match\n";
        }
        int fails = 0;
        size_t done = 0;
        for (size_t idx = 0; idx < jobs.size() && done < count; ++idx) {
            const mm::Job& j = jobs[idx];
            if (j.n != acc.n) continue;
            std::vector<int32_t> c;
            mm::Perf p{};
            auto t0 = std::chrono::steady_clock::now();
            acc.run(j, c, p);
            double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
            bool ok = c == j.c && p == j.perf;
            if (!ok && fails++ < 5)
                std::printf("FAIL job %zu (K=%d): C %s, total %u (expected %u)\n", idx, j.k,
                            c == j.c ? "ok" : "MISMATCH", p.total, j.perf.total);
            if (csv) csv << idx << ',' << j.n << ',' << j.k << ',' << p.total << ',' << p.compute << ','
                         << p.filldrain << ',' << p.macs << ',' << ms << ',' << (c == j.c) << '\n';
            ++done;
        }
        std::printf("%zu/%zu jobs correct (C and perf counters)\n", done - size_t(fails), done);
        std::puts(fails == 0 && done > 0 ? "PASS" : "FAIL");
        return fails == 0 && done > 0 ? 0 : 1;
    } catch (const std::exception& e) {
        std::printf("ERROR: %s\nFAIL\n", e.what());
        return 1;
    }
}
