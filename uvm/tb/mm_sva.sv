// mm_sva.sv -- assertions on the bus handshake and the controller FSM.
// Bound into tb_top next to the DUT; any failure is a test failure.
module mm_sva #(parameter int N = 4) (
    input logic       clk, rst_n,
    input logic       soft_reset,          // dut.u_regs.soft_reset (aborts a job)
    input logic       bus_valid, bus_ready, bus_write, bus_rvalid,
    input logic [15:0] bus_addr,
    input logic [31:0] bus_wdata,
    input logic       busy, done,
    input logic [2:0] state
);
    localparam logic [2:0] IDLE = 0, CLEAR = 1, COMPUTE = 2, DRAIN = 3, DONE = 4;

    default clocking @(posedge clk); endclocking
    default disable iff (!rst_n);

    wire rd_accept = bus_valid && bus_ready && !bus_write;

    // bus protocol (slave side)
    a_rvalid_after_read:  assert property (rd_accept |=> bus_rvalid);
    a_rvalid_only_after:  assert property (bus_rvalid |-> $past(rd_accept));
    a_ready_low_one_cyc:  assert property (!bus_ready |=> bus_ready);
    // bus protocol (master side): hold a request until it is accepted
    a_master_holds:       assert property (bus_valid && !bus_ready |=>
                                           bus_valid && $stable(bus_addr) && $stable(bus_write));

    // controller FSM -- a soft reset legally aborts any sequence, so these are
    // also disabled while it is applied (found by the regression: soft reset in DRAIN)
    a_state_legal:        assert property (state <= DONE);
    a_clear_then_compute: assert property (disable iff (!rst_n || soft_reset)
                                           state == CLEAR |=> state == COMPUTE);
    a_done_then_idle:     assert property (state == DONE |=> state == IDLE);
    a_done_pulse:         assert property (done |=> !done);
    a_done_is_state:      assert property (done == (state == DONE));
    a_busy_is_not_idle:   assert property (busy == (state != IDLE));
    a_drain_length:       assert property (disable iff (!rst_n || soft_reset)
                                           $rose(state == DRAIN) |->
                                           (state == DRAIN) [*2*N-1] ##1 state == DONE);

    // coverage of the interesting protocol events
    c_ready_low:          cover property (bus_valid && !bus_ready);
    c_back_to_back_rd:    cover property (rd_accept ##1 rd_accept);
endmodule
