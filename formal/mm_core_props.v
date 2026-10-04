// mm_core_props.v -- formal properties for mm_core (SymbiYosys, open-source Yosys).
//
// Every bus input is unconstrained (any value, any cycle), so these hold for
// ANY master behaviour, not just the sequences the testbenches happen to drive.
// Same intent as the simulation SVA in uvm/tb/mm_sva.sv, written as immediate
// assertions because open-source Yosys does not parse concurrent SVA.
// Small parameters keep the state space tractable: N = 2, K_MAX = 4.
module mm_core_props (
    input wire        clk,
    input wire        rst_n,
    input wire        bus_valid,
    input wire        bus_write,
    input wire [15:0] bus_addr,
    input wire [31:0] bus_wdata
);
    wire        bus_ready, bus_rvalid, busy, done;
    wire [31:0] bus_rdata, perf_compute;
    wire [2:0]  state;

    mm_core #(.N(2), .K_MAX(4)) dut (
        .clk(clk), .rst_n(rst_n),
        .bus_valid(bus_valid), .bus_ready(bus_ready), .bus_write(bus_write),
        .bus_addr(bus_addr), .bus_wdata(bus_wdata),
        .bus_rvalid(bus_rvalid), .bus_rdata(bus_rdata),
        .busy(busy), .done(done), .state(state), .perf_compute(perf_compute)
    );

`ifdef FORMAL
    localparam [2:0] IDLE = 0, CLEAR = 1, COMPUTE = 2, DRAIN = 3, DONE = 4;

    reg past_valid = 1'b0;
    always @(posedge clk) past_valid <= 1'b1;

    // Start in reset; afterwards rst_n may do anything.
    always @(*) if (!past_valid) assume (!rst_n);

    wire rd_accept = bus_valid && bus_ready && !bus_write;

    // Combinational invariants (any cycle out of reset)
    always @(*) if (past_valid && rst_n) begin
        a_state_legal: assert (state <= DONE);
        a_busy:        assert (busy == (state != IDLE));
        a_done:        assert (done == (state == DONE));
    end

    // One-cycle properties (both cycles out of reset)
    always @(posedge clk) if (past_valid && $past(rst_n) && rst_n) begin
        a_rvalid_after_read: assert (!$past(rd_accept) || bus_rvalid);
        a_rvalid_only_after: assert (!bus_rvalid || $past(rd_accept));
        a_ready_one_cycle:   assert ($past(bus_ready) || bus_ready);
        a_done_pulse:        assert (!$past(done) || !done);
        a_done_then_idle:    assert ($past(state) != DONE || state == IDLE);
        // CLEAR -> COMPUTE; IDLE only if a soft reset aborted the job
        a_clear_then_run:    assert ($past(state) != CLEAR || state == COMPUTE || state == IDLE);
        a_compute_order:     assert ($past(state) != COMPUTE || state == COMPUTE || state == DRAIN
                                     || state == IDLE);
    end

    // Reachability: these must be hit (catches over-constrained / vacuous proofs)
    always @(posedge clk) if (past_valid && rst_n) begin
        c_done:      cover (done);
        c_read_busy: cover (rd_accept && busy);
    end
`endif
endmodule
