// mm_core.sv
// Complete matrix-multiply engine: C (N x N) = A (N x K) * B (K x N).
//
//   write port --> A banks (one RAM per row i,    address k) --\
//              --> B banks (one RAM per column j, address k) ---+-> skew -> array -> C
//                                 mm_controller (start/done, cycle count) --/
//
// Banking: to feed the array we need all of A[.][k] and all of B[k][.] in the
// same cycle, so each row of A / column of B lives in its own narrow RAM and
// all banks are read in parallel at address k.
//
// Result readout: rd_data = C[rd_idx / N][rd_idx % N] (combinational mux).

module mm_core #(
    parameter int N     = 4,
    parameter int K_MAX = 64
) (
    input  logic                         clk,
    input  logic                         rst_n,
    // matrix load (ignored while busy)
    input  logic                         wr_en,
    input  logic                         wr_sel,    // 0 = A, 1 = B
    input  logic [$clog2(N)-1:0]         wr_lane,   // A: row i,  B: column j
    input  logic [$clog2(K_MAX)-1:0]     wr_addr,   // k
    input  logic [7:0]                   wr_data,
    // control
    input  logic [$clog2(K_MAX+1)-1:0]   k_len,
    input  logic                         start,
    output logic                         busy,
    output logic                         done,
    output logic [31:0]                  cycles,
    output logic [1:0]                   state,
    // result readout
    input  logic [$clog2(N*N)-1:0]       rd_idx,
    output logic [31:0]                  rd_data
);

    localparam int KW = $clog2(K_MAX);

    logic          clear, rd_en;
    logic [KW-1:0] rd_addr;

    mm_controller #(.N(N), .K_MAX(K_MAX)) u_ctrl (
        .clk(clk), .rst_n(rst_n), .start(start), .k_len(k_len),
        .busy(busy), .done(done), .clear(clear),
        .rd_en(rd_en), .rd_addr(rd_addr), .cycles(cycles), .state_o(state)
    );

    // ---------------- operand buffers ----------------
    wire [KW-1:0] addr = busy ? rd_addr : wr_addr;
    wire          we   = wr_en && !busy;

    wire  [N*8-1:0] a_col, b_row;    // A[.][k] and B[k][.] one cycle after the read

    for (genvar n = 0; n < N; n++) begin : g_bank
        wire sel_a = we && !wr_sel && (wr_lane == n);
        wire sel_b = we &&  wr_sel && (wr_lane == n);
        sram_sp #(.WIDTH(8), .DEPTH(K_MAX)) u_a (
            .clk(clk), .we(sel_a), .addr(addr), .wdata(wr_data), .rdata(a_col[n*8 +: 8]));
        sram_sp #(.WIDTH(8), .DEPTH(K_MAX)) u_b (
            .clk(clk), .we(sel_b), .addr(addr), .wdata(wr_data), .rdata(b_row[n*8 +: 8]));
    end

    // RAM data is valid one cycle after rd_en; feed zeros otherwise so the
    // accumulators stay put while the array fills and drains.
    logic rd_valid;
    always_ff @(posedge clk) begin
        if (!rst_n) rd_valid <= 1'b0;
        else        rd_valid <= rd_en;
    end

    wire [N*8-1:0] a_feed = rd_valid ? a_col : '0;
    wire [N*8-1:0] b_feed = rd_valid ? b_row : '0;

    // ---------------- skew + array ----------------
    logic [N*8-1:0] a_skew, b_skew;

    skew_buffer #(.N(N), .DW(8)) u_skew_a (
        .clk(clk), .rst_n(rst_n), .clear(clear), .din(a_feed), .dout(a_skew));
    skew_buffer #(.N(N), .DW(8)) u_skew_b (
        .clk(clk), .rst_n(rst_n), .clear(clear), .din(b_feed), .dout(b_skew));

    logic [N*N*32-1:0] c_out;

    systolic_array #(.N(N), .DW(8), .AW(32)) u_array (
        .clk(clk), .rst_n(rst_n), .clear(clear), .en(1'b1),
        .a_in(a_skew), .b_in(b_skew), .c_out(c_out)
    );

    assign rd_data = c_out[rd_idx*32 +: 32];

endmodule
