// mm_ca.h -- cycle-approximate SystemC model of mm_core (Phase 5, Day 32).
//
// A clocked SC_THREAD runs the same FSM as rtl/core/mm_controller.sv
//   IDLE -> CLEAR -> COMPUTE (K) -> DRAIN (2N-1) -> DONE -> IDLE
// and updates the perf counters every cycle with the same conditions as
// rtl/core/mm_regs.sv. The datapath is not modelled cycle by cycle: C is
// computed functionally when the FSM reaches DONE.
//
// Register access (b_transport) models the RTL bus: a transaction issued
// between clock edges takes effect at the next rising edge, which is where
// the RTL samples bus_valid. Reads return the state after the previous edge.
#pragma once
#include <algorithm>
#include <cstring>
#include <systemc>
#include <tlm>
#include <tlm_utils/simple_target_socket.h>

#include "mm_state.h"

namespace mm {

SC_MODULE(MmCa) {
    sc_core::sc_in<bool> clk;
    tlm_utils::simple_target_socket<MmCa> socket;

    enum class State { IDLE, CLEAR, COMPUTE, DRAIN, DONE };

    MmCa(sc_core::sc_module_name name, int n, int k_max)
        : sc_module(name), clk("clk"), socket("socket"), st_(n, k_max) {
        socket.register_b_transport(this, &MmCa::b_transport);
        SC_THREAD(run);
        sensitive << clk.pos();
    }

    const MmState& state() const { return st_; }
    State fsm() const { return state_; }

private:
    MmState st_;
    State state_ = State::IDLE;
    int t_ = 0, k_r_ = 0;
    bool start_pending_ = false, reset_pending_ = false;

    void run() {
        for (;;) {
            wait();                                   // rising edge
            if (reset_pending_) {                     // CTRL.SOFT_RESET
                reset_pending_ = start_pending_ = false;
                st_.soft_reset();
                state_ = State::IDLE;
                continue;
            }
            const int n = st_.n;
            const bool array_en = state_ == State::COMPUTE || state_ == State::DRAIN;
            const bool all_active = array_en && t_ >= 2 * n - 1 && t_ <= k_r_;
            const bool start = start_pending_;
            start_pending_ = false;

            // perf counters (mm_regs.sv): sampled with the state before this edge
            if (state_ == State::IDLE && st_.perf_idle != 0xFFFFFFFFu) ++st_.perf_idle;
            if (start) {
                st_.perf = {};
                st_.done = false;
            } else {
                if (st_.busy && state_ != State::DONE) ++st_.perf.total;
                if (array_en) ++st_.perf.compute;
                if (array_en && !all_active) ++st_.perf.filldrain;
                if (state_ == State::COMPUTE) st_.perf.macs += uint32_t(n * n);
            }

            // FSM (mm_controller.sv)
            switch (state_) {
                case State::IDLE:
                    if (start) { k_r_ = int(st_.cfg_k); state_ = State::CLEAR; }
                    break;
                case State::CLEAR:   t_ = 0; state_ = State::COMPUTE; break;
                case State::COMPUTE: if (t_ == k_r_ - 1) state_ = State::DRAIN; ++t_; break;
                case State::DRAIN:
                    if (t_ == k_r_ + 2 * n - 2) {
                        st_.compute_c();
                        state_ = State::DONE;
                    } else {
                        ++t_;
                    }
                    break;
                case State::DONE:
                    st_.done = true;
                    state_ = State::IDLE;
                    break;
            }
            st_.busy = state_ != State::IDLE;
        }
    }

    void b_transport(tlm::tlm_generic_payload& trans, sc_core::sc_time& delay) {
        if (delay != sc_core::SC_ZERO_TIME) {         // sync: this model is clocked
            wait(delay);
            delay = sc_core::SC_ZERO_TIME;
        }
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
                case MmState::WriteEffect::START:      start_pending_ = true; break;
                case MmState::WriteEffect::SOFT_RESET: reset_pending_ = true; break;
                case MmState::WriteEffect::NONE:       break;
            }
        } else if (trans.is_read()) {
            word = st_.read(addr);
            std::memcpy(trans.get_data_ptr(), &word, 4);
        }
        trans.set_response_status(tlm::TLM_OK_RESPONSE);
    }
};

}  // namespace mm
