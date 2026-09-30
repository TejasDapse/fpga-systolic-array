// bus_initiator.h -- TLM-2.0 initiator helpers: one generic payload per bus transaction.
#pragma once
#include <cstring>
#include <stdexcept>
#include <string>
#include <systemc>
#include <tlm>
#include <tlm_utils/simple_initiator_socket.h>

#include "../cpp/mm_ref.h"
#include "mm_regmap.h"

namespace mm {

struct BusInitiator : sc_core::sc_module {
    tlm_utils::simple_initiator_socket<BusInitiator> socket;
    sc_core::sc_time delay = sc_core::SC_ZERO_TIME;   // LT: accumulated local time

    explicit BusInitiator(sc_core::sc_module_name name) : sc_module(name), socket("socket") {}

    uint32_t access(tlm::tlm_command cmd, uint16_t addr, uint32_t data = 0) {
        tlm::tlm_generic_payload trans;
        unsigned char buf[4];
        std::memcpy(buf, &data, 4);
        trans.set_command(cmd);
        trans.set_address(addr);
        trans.set_data_ptr(buf);
        trans.set_data_length(4);
        trans.set_streaming_width(4);
        trans.set_byte_enable_ptr(nullptr);
        trans.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
        socket->b_transport(trans, delay);
        if (trans.is_response_error())
            throw std::runtime_error("TLM error at address " + std::to_string(addr));
        std::memcpy(&data, buf, 4);
        return data;
    }
    void write(uint16_t addr, uint32_t data) { access(tlm::TLM_WRITE_COMMAND, addr, data); }
    uint32_t read(uint16_t addr) { return access(tlm::TLM_READ_COMMAND, addr); }

};

// Load one job, start it, wait for DONE, read C and the perf counters.
// Works with any bus exposing write(addr, data) / read(addr): the TLM
// initiator above, or the pin-level RTL driver in cosim/.
// `tick` is called between accesses (e.g. wait one clock for clocked models).
template <class Bus, class Tick>
void run_job(Bus& bus, int n, int k_max, const Job& j, std::vector<int32_t>& c, Perf& p,
             Tick tick) {
    bus.write(reg::CFG_K, uint32_t(j.k)); tick();
    for (int i = 0; i < n; ++i)
        for (int kk = 0; kk < j.k; ++kk) {
            bus.write(reg::a_addr(i, kk, k_max), uint8_t(j.a[size_t(i * j.k + kk)])); tick();
        }
    for (int kk = 0; kk < j.k; ++kk)
        for (int jj = 0; jj < n; ++jj) {
            bus.write(reg::b_addr(kk, jj, n), uint8_t(j.b[size_t(kk * n + jj)])); tick();
        }
    bus.write(reg::CTRL, reg::CTRL_START); tick();
    for (int polls = 0; !(bus.read(reg::STATUS) & reg::STATUS_DONE); ++polls) {
        if (polls > 100000) throw std::runtime_error("DONE never set");
        tick();
    }
    c.resize(size_t(n * n));
    for (int idx = 0; idx < n * n; ++idx) {
        c[size_t(idx)] = int32_t(bus.read(uint16_t(reg::C_BUF + 4 * idx))); tick();
    }
    p = {bus.read(reg::PERF_TOTAL), bus.read(reg::PERF_COMPUTE), bus.read(reg::PERF_FILLDRAIN),
         bus.read(reg::PERF_MACS)};
}

}  // namespace mm
