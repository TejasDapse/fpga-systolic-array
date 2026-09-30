// test_models.cpp -- Days 31/32: run the shared vectors on the LT and CA SystemC models.
//
// Checks, per job: C == expected (NumPy / C++), perf counters == expected, and
// for the CA model the START->DONE time measured in clock cycles is within
// +-2 of the analytical model (Day 32 criterion; it should be exact).
//
//   make -C model/systemc test
#include <cstdio>
#include <systemc>

#include "bus_initiator.h"
#include "mm_ca.h"
#include "mm_lt.h"

using namespace sc_core;

struct Top : sc_module {
    sc_clock clk{"clk", 20, SC_NS};
    mm::MmLt lt;
    mm::MmCa ca;
    mm::BusInitiator lt_bus{"lt_bus"}, ca_bus{"ca_bus"};
    std::vector<mm::Job> jobs;
    int n, k_max, failures = 0, max_cycle_err = 0;

    Top(sc_module_name name, int n_, int k_max_, std::vector<mm::Job> jobs_)
        : sc_module(name), lt("lt", n_, k_max_), ca("ca", n_, k_max_),
          jobs(std::move(jobs_)), n(n_), k_max(k_max_) {
        lt_bus.socket.bind(lt.socket);
        ca_bus.socket.bind(ca.socket);
        ca.clk(clk);
        SC_THREAD(run_lt);
        SC_THREAD(run_ca);
    }

    void check(const char* model, size_t idx, const mm::Job& j,
               const std::vector<int32_t>& c, const mm::Perf& p) {
        if (c != j.c || !(p == j.perf)) {
            if (failures++ < 5)
                std::printf("%s: MISMATCH job %zu (N=%d K=%d) perf total %u/%u\n", model, idx,
                            j.n, j.k, p.total, j.perf.total);
        }
    }

    void run_lt() {                        // loosely timed: no clock, local time only
        std::vector<int32_t> c;
        mm::Perf p{};
        for (size_t i = 0; i < jobs.size(); ++i) {
            mm::run_job(lt_bus, n, k_max, jobs[i], c, p, [] {});
            check("LT", i, jobs[i], c, p);
        }
        wait(lt_bus.delay);                // sync once at the end (temporal decoupling)
        std::printf("LT: %zu jobs, simulated time %s\n", jobs.size(), sc_time_stamp().to_string().c_str());
    }

    void run_ca() {                        // clocked: drive mid-cycle like the RTL testbenches
        std::vector<int32_t> c;
        mm::Perf p{};
        auto tick = [this] { wait(clk.negedge_event()); };
        wait(clk.negedge_event());
        for (size_t i = 0; i < jobs.size(); ++i) {
            mm::run_job(ca_bus, n, k_max, jobs[i], c, p, tick);
            check("CA", i, jobs[i], c, p);
            // cycles measured independently of the counters: time a bare restart
            wait(clk.negedge_event());
            const sc_time t0 = sc_time_stamp();
            ca_bus.write(mm::reg::CTRL, mm::reg::CTRL_START);
            do { wait(clk.negedge_event()); } while (!(ca_bus.read(mm::reg::STATUS) & mm::reg::STATUS_DONE));
            // -1: START issued mid-cycle, seen at the next edge; DONE seen mid-cycle
            // -1: the DONE state itself is not counted in PERF_TOTAL
            const int measured = int((sc_time_stamp() - t0) / clk.period()) - 2;
            const int err = std::abs(measured - int(mm::predict_perf(n, jobs[i].k).total));
            max_cycle_err = std::max(max_cycle_err, err);
        }
        std::printf("CA: %zu jobs, max |measured - predicted| cycles = %d\n", jobs.size(), max_cycle_err);
        sc_stop();
    }
};

int sc_main(int argc, char** argv) {
    if (argc != 2) { std::puts("usage: test_models <vectors.hex>"); return 2; }
    std::vector<mm::Job> jobs = mm::read_vectors(argv[1]);
    const int n = jobs.at(0).n;
    std::printf("== %s (N=%d, %zu jobs)\n", argv[1], n, jobs.size());
    Top top("top", n, 64, std::move(jobs));
    sc_start();
    const bool ok = top.failures == 0 && top.max_cycle_err <= 2;
    std::printf("%d mismatches\n%s\n", top.failures, ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}
