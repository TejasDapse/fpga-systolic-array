// mm_lt.h -- loosely-timed TLM-2.0 model of mm_core (Phase 5, Day 31; NOTES §22–§23).
//
// One target socket, blocking transport (b_transport), same register map as the
// RTL. The generic payload maps 1:1 onto one bus transaction:
//   address = bus_addr, 4-byte data = bus_wdata / bus_rdata (little-endian).
//
// Loosely timed: a START computes C immediately (functional C++ model) and
// records when the hardware *would* finish, using the analytical cycle count.
// STATUS reads BUSY until simulated time (incl. the annotated delay) reaches
// that point. Every access annotates one bus cycle of delay.
#pragma once
#include <algorithm>
#include <cstring>
#include <systemc>
#include <tlm>
#include <tlm_utils/simple_target_socket.h>

#include "mm_state.h"

namespace mm {

SC_MODULE(MmLt) {
    tlm_utils::simple_target_socket<MmLt> socket;

    MmLt(sc_core::sc_module_name name, int n, int k_max,
         sc_core::sc_time clk_period = sc_core::sc_time(20, sc_core::SC_NS))
        : sc_module(name), socket("socket"), st_(n, k_max), period_(clk_period) {
        socket.register_b_transport(this, &MmLt::b_transport);
    }

    const MmState& state() const { return st_; }

private:
    MmState st_;
    sc_core::sc_time period_;
    sc_core::sc_time done_at_ = sc_core::SC_ZERO_TIME;
    sc_core::sc_time idle_since_ = sc_core::SC_ZERO_TIME;
    uint32_t idle_accum_ = 0;

    void update_status(const sc_core::sc_time& now) {
        if (st_.busy && now >= done_at_) {
            st_.busy = false;
            st_.done = true;
            idle_since_ = done_at_;
        }
        const uint64_t idle = st_.busy ? 0 : uint64_t((now - idle_since_) / period_);
        st_.perf_idle = uint32_t(std::min<uint64_t>(idle_accum_ + idle, 0xFFFFFFFFu));
    }

    void b_transport(tlm::tlm_generic_payload& trans, sc_core::sc_time& delay) {
        const sc_core::sc_time now = sc_core::sc_time_stamp() + delay;
        update_status(now);

        if (trans.get_data_length() != 4 || trans.get_byte_enable_ptr() ||
            trans.get_address() > 0xFFFF) {
            trans.set_response_status(tlm::TLM_GENERIC_ERROR_RESPONSE);
            return;
        }
        const auto addr = uint16_t(trans.get_address());
        uint32_t word = 0;
        if (trans.is_write()) {
            std::memcpy(&word, trans.get_data_ptr(), 4);
            switch (st_.write(addr, word)) {
                case MmState::WriteEffect::START:
                    idle_accum_ = st_.perf_idle;
                    st_.compute_c();
                    st_.perf = predict_perf(st_.n, int(st_.cfg_k));
                    st_.busy = true;
                    st_.done = false;
                    done_at_ = now + period_ * st_.perf.total;
                    break;
                case MmState::WriteEffect::SOFT_RESET:
                    st_.soft_reset();
                    idle_accum_ = 0;
                    idle_since_ = now;
                    break;
                case MmState::WriteEffect::NONE:
                    break;
            }
        } else if (trans.is_read()) {
            word = st_.read(addr);
            std::memcpy(trans.get_data_ptr(), &word, 4);
        }
        delay += period_;                               // one bus cycle
        trans.set_response_status(tlm::TLM_OK_RESPONSE);
    }
};

}  // namespace mm
