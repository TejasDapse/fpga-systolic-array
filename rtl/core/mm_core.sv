// mm_core.sv
// Complete matrix-multiply engine: C (N x N) = A (N x K) * B (K x N),
// controlled entirely through a valid/ready register bus (map in mm_regs.sv).
//
//   register bus <-> mm_regs --write--> A banks (one RAM per row i,    address k) --\
//                      |  ^    port --> B banks (one RAM per column j, address k) ---+-> skew -> array
//                      |  |                                                            |
//                      |  +------------------ C readout <------------------------------/
//                      +--> mm_controller (start, CLEAR/COMPUTE/DRAIN/DONE, status) --> perf counters
//
// Banking: to feed the array we need all of A[.][k] and all of B[k][.] in the
// same cycle, so each row of A / column of B lives in its own narrow RAM and
// all banks are read in parallel at address k.

module mm_core #(
    parameter int          N       = 4,
    parameter int          K_MAX   = 64,
    parameter logic [15:0] VERSION = 16'h0001
) (
    input  logic        clk,
    input  logic        rst_n,
    // register bus
    input  logic        bus_valid,
    output logic        bus_ready,
    input  logic        bus_write,
    input  logic [15:0] bus_addr,
    input  logic [31:0] bus_wdata,
    output logic        bus_rvalid,
    output logic [31:0] bus_rdata,
    // board status
    output logic        busy,
    output logic        done,          // 1-cycle pulse
    output logic [2:0]  state,
    output logic [31:0] perf_compute
);

    localparam int KW = $clog2(K_MAX);
    localparam int KL = $clog2(K_MAX + 1);

    logic soft_reset;
    wire  core_rst_n = rst_n && !soft_reset;

    logic                   start, wr_en, wr_sel;
    logic [KL-1:0]          k_len;
    logic [$clog2(N)-1:0]   wr_lane;
    logic [KW-1:0]          wr_addr;
    logic [7:0]             wr_data;
    logic [$clog2(N*N)-1:0] c_idx;
    logic [31:0]            c_data;
    logic                   clear, array_en, all_active, rd_en;
    logic [KW-1:0]          rd_addr;

    mm_regs #(.N(N), .K_MAX(K_MAX), .VERSION(VERSION)) u_regs (
        .clk(clk), .rst_n(rst_n), .core_rst_n(core_rst_n),
        .bus_valid(bus_valid), .bus_ready(bus_ready), .bus_write(bus_write),
        .bus_addr(bus_addr), .bus_wdata(bus_wdata),
        .bus_rvalid(bus_rvalid), .bus_rdata(bus_rdata),
        .soft_reset(soft_reset), .start(start), .k_len(k_len),
        .wr_en(wr_en), .wr_sel(wr_sel), .wr_lane(wr_lane), .wr_addr(wr_addr),
        .wr_data(wr_data), .c_idx(c_idx), .c_data(c_data),
        .busy(busy), .done(done), .array_en(array_en), .all_active(all_active),
        .rd_en(rd_en), .perf_compute(perf_compute)
    );

    mm_controller #(.N(N), .K_MAX(K_MAX)) u_ctrl (
        .clk(clk), .rst_n(core_rst_n), .start(start), .k_len(k_len),
        .busy(busy), .done(done), .clear(clear), .array_en(array_en),
        .all_active(all_active), .rd_en(rd_en), .rd_addr(rd_addr), .state_o(state)
    );

    // ---------------- operand buffers ----------------
    wire [KW-1:0] addr = busy ? rd_addr : wr_addr;

    logic [N*8-1:0] a_col, b_row;    // A[.][k] and B[k][.] one cycle after the read

    for (genvar n = 0; n < N; n++) begin : g_bank
        wire sel_a = wr_en && !wr_sel && (wr_lane == n);
        wire sel_b = wr_en &&  wr_sel && (wr_lane == n);
        sram_sp #(.WIDTH(8), .DEPTH(K_MAX)) u_a (
            .clk(clk), .we(sel_a), .addr(addr), .wdata(wr_data), .rdata(a_col[n*8 +: 8]));
        sram_sp #(.WIDTH(8), .DEPTH(K_MAX)) u_b (
            .clk(clk), .we(sel_b), .addr(addr), .wdata(wr_data), .rdata(b_row[n*8 +: 8]));
    end

    // RAM data is valid one cycle after rd_en; feed zeros otherwise so the
    // accumulators stay put while the array fills and drains.
    logic rd_valid;
    always_ff @(posedge clk) begin
        if (!core_rst_n) rd_valid <= 1'b0;
        else             rd_valid <= rd_en;
    end

    wire [N*8-1:0] a_feed = rd_valid ? a_col : '0;
    wire [N*8-1:0] b_feed = rd_valid ? b_row : '0;

    // ---------------- skew + array ----------------
    logic [N*8-1:0] a_skew, b_skew;

    skew_buffer #(.N(N), .DW(8)) u_skew_a (
        .clk(clk), .rst_n(core_rst_n), .clear(clear), .din(a_feed), .dout(a_skew));
    skew_buffer #(.N(N), .DW(8)) u_skew_b (
        .clk(clk), .rst_n(core_rst_n), .clear(clear), .din(b_feed), .dout(b_skew));

    logic [N*N*32-1:0] c_out;

    systolic_array #(.N(N), .DW(8), .AW(32)) u_array (
        .clk(clk), .rst_n(core_rst_n), .clear(clear), .en(array_en),
        .a_in(a_skew), .b_in(b_skew), .c_out(c_out)
    );

    assign c_data = c_out[c_idx*32 +: 32];

endmodule
