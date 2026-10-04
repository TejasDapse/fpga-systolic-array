// cosim_main.cpp -- Phase 5, Days 33/34: RTL (Verilator -> SystemC) vs SystemC CA model.
//
// The verilated mm_core and the cycle-approximate model share one clock and
// receive the same job sequence (shared vector file). Per job we compare
//   * C:              RTL == CA model == expected (NumPy / C++)
//   * perf counters:  RTL == CA model == analytical model
//   * START->DONE:    cycles measured at the pins, independent of the counters
// and write one CSV row. Any functional mismatch fails the run.
//
//   make -C cosim N=8            (see Makefile)
#include <cstdio>
#include <fstream>
#include <systemc>

#include "Vmm_core.h"
#include "../model/systemc/bus_initiator.h"
#include "../model/systemc/mm_ca.h"

using namespace sc_core;

// Pin-level bus master for the RTL: drive on the falling edge, sample mid-cycle
// (same discipline as the cocotb Bus class in tb/test_mm_core.py).
struct RtlBus {
    sc_clock& clk;
    sc_signal<bool>& valid; sc_signal<bool>& ready; sc_signal<bool>& write_en;
    sc_signal<uint32_t>& addr; sc_signal<uint32_t>& wdata;
    sc_signal<bool>& rvalid; sc_signal<uint32_t>& rdata;

    void request(bool wr, uint16_t a, uint32_t d) {
        valid.write(true); write_en.write(wr); addr.write(a); wdata.write(d);
        for (;;) {
            wait(SC_ZERO_TIME);                       // let the drive settle
            const bool rdy = ready.read();
            wait(clk.negedge_event());
            if (rdy) break;
        }
        valid.write(false);
    }
    void write(uint16_t a, uint32_t d) { request(true, a, d); }
    uint32_t read(uint16_t a) {
        request(false, a, 0);
        if (!rvalid.read()) throw std::runtime_error("RTL: rvalid missing after read");
        return rdata.read();
    }
};

SC_MODULE(Cosim) {
    sc_clock clk{"clk", 20, SC_NS};
    sc_signal<bool> rst_n{"rst_n"}, bus_valid{"bus_valid"}, bus_ready{"bus_ready"},
        bus_write{"bus_write"}, bus_rvalid{"bus_rvalid"}, busy{"busy"}, done{"done"};
    sc_signal<uint32_t> bus_addr{"bus_addr"}, bus_wdata{"bus_wdata"}, bus_rdata{"bus_rdata"},
        state{"state"}, perf_compute{"perf_compute"};

    Vmm_core rtl{"rtl"};
    mm::MmCa ca;
    mm::BusInitiator ca_bus{"ca_bus"};
    RtlBus rtl_bus{clk, bus_valid, bus_ready, bus_write, bus_addr, bus_wdata, bus_rvalid, bus_rdata};

    std::vector<mm::Job> jobs;
    int n, k_max;
    std::string csv_path;
    int func_mismatch = 0, perf_mismatch = 0, max_cycle_err = 0;

    Cosim(sc_module_name name, int n_, int k_max_, std::vector<mm::Job> jobs_, std::string csv)
        : sc_module(name), ca("ca", n_, k_max_), jobs(std::move(jobs_)), n(n_), k_max(k_max_),
          csv_path(std::move(csv)) {
        rtl.clk(clk); rtl.rst_n(rst_n);
        rtl.bus_valid(bus_valid); rtl.bus_ready(bus_ready); rtl.bus_write(bus_write);
        rtl.bus_addr(bus_addr); rtl.bus_wdata(bus_wdata);
        rtl.bus_rvalid(bus_rvalid); rtl.bus_rdata(bus_rdata);
        rtl.busy(busy); rtl.done(done); rtl.state(state); rtl.perf_compute(perf_compute);
        ca.clk(clk);
        ca_bus.socket.bind(ca.socket);
        SC_THREAD(run);
    }

    void run() {
        auto tick = [] {};                             // RtlBus already waits per access
        auto ca_tick = [this] { wait(clk.negedge_event()); };
        rst_n.write(false);
        wait(clk.negedge_event()); wait(clk.negedge_event()); wait(clk.negedge_event());
        rst_n.write(true);
        wait(clk.negedge_event());

        std::ofstream csv(csv_path);
        csv << "job,N,K,predicted_total,rtl_total,ca_total,rtl_compute,ca_compute,"
               "rtl_filldrain,ca_filldrain,rtl_macs,ca_macs,rtl_pin_cycles,cycle_error,c_match\n";
        std::vector<int32_t> c_rtl, c_ca;
        mm::Perf p_rtl{}, p_ca{};
        for (size_t i = 0; i < jobs.size(); ++i) {
            const mm::Job& j = jobs[i];
            mm::run_job(rtl_bus, n, k_max, j, c_rtl, p_rtl, tick);
            mm::run_job(ca_bus, n, k_max, j, c_ca, p_ca, ca_tick);

            // Pin-level timing of the RTL, independent of the counters: START is
            // driven at falling edge t0 and accepted at the rising edge t0 + T/2;
            // the `done` pulse (DONE state) is sampled at falling edges.
            const sc_time t0 = sc_time_stamp();
            rtl_bus.write(mm::reg::CTRL, mm::reg::CTRL_START);
            while (!done.read()) wait(clk.negedge_event());
            const int pin_cycles =
                int((sc_time_stamp() - t0 - clk.period() / 2 - clk.period() / 2) / clk.period());

            const mm::Perf pred = mm::predict_perf(n, j.k);
            const bool c_ok = c_rtl == j.c && c_ca == j.c;
            const bool perf_ok = p_rtl == pred && p_ca == pred;
            const int err = std::abs(pin_cycles - int(pred.total));
            func_mismatch += !c_ok;
            perf_mismatch += !perf_ok;
            max_cycle_err = std::max(max_cycle_err, err);
            if ((!c_ok || !perf_ok) && func_mismatch + perf_mismatch <= 5)
                std::printf("job %zu (K=%d): C %s; total/compute/filldrain/macs "
                            "rtl %u/%u/%u/%u ca %u/%u/%u/%u pred %u/%u/%u/%u\n",
                            i, j.k, c_ok ? "ok" : "MISMATCH",
                            p_rtl.total, p_rtl.compute, p_rtl.filldrain, p_rtl.macs,
                            p_ca.total, p_ca.compute, p_ca.filldrain, p_ca.macs,
                            pred.total, pred.compute, pred.filldrain, pred.macs);
            csv << i << ',' << n << ',' << j.k << ',' << pred.total << ',' << p_rtl.total << ','
                << p_ca.total << ',' << p_rtl.compute << ',' << p_ca.compute << ','
                << p_rtl.filldrain << ',' << p_ca.filldrain << ',' << p_rtl.macs << ','
                << p_ca.macs << ',' << pin_cycles << ',' << err << ',' << (c_ok ? 1 : 0) << '\n';
        }
        std::printf("N=%d: %zu jobs, C mismatches %d, perf mismatches %d, "
                    "max |pin cycles - predicted| = %d\n",
                    n, jobs.size(), func_mismatch, perf_mismatch, max_cycle_err);
        std::printf("wrote %s\n", csv_path.c_str());
        sc_stop();
    }
};

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 4) { std::puts("usage: cosim <N> <vectors.hex> <out.csv> [K_MAX=64]"); return 2; }
    const int n = std::atoi(argv[1]);
    const int k_max = argc > 4 ? std::atoi(argv[4]) : 64;
    std::vector<mm::Job> jobs;
    for (mm::Job& j : mm::read_vectors(argv[2]))          // vectors are made for K_MAX = 64
        if (j.k <= k_max) jobs.push_back(std::move(j));
    Cosim top("top", n, k_max, std::move(jobs), argv[3]);
    sc_start();
    const bool ok = top.func_mismatch == 0 && top.perf_mismatch == 0 && top.max_cycle_err == 0;
    std::puts(ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}
