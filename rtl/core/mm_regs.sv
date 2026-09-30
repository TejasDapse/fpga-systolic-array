// mm_regs.sv
// Register-bus slave for mm_core: decodes the register map (PLAN.md §6),
// holds CTRL/STATUS/CFG and the performance counters.
//
// Bus (valid/ready, single clock):
//   A request is accepted on a clock edge where (bus_valid && bus_ready).
//   Writes take effect at that edge. Reads return bus_rdata with bus_rvalid
//   exactly 1 cycle after the accept. bus_ready is low only for the one cycle
//   in which a SOFT_RESET is being applied.
//
// Address map (byte addresses):
//   0x0000 CTRL           W   bit0 START (self-clearing), bit1 SOFT_RESET
//   0x0004 STATUS         R   bit0 BUSY, bit1 DONE (sticky, cleared by START)
//   0x0008 CFG_K          R/W K, 1 .. K_MAX (other values are ignored)
//   0x000C INFO           R   [7:0] N, [15:8] K_MAX, [31:16] VERSION
//   0x0010 PERF_TOTAL     R   cycles from START to DONE           (= K + 2N)
//   0x0014 PERF_COMPUTE   R   cycles with the array enabled       (= K + 2N - 1)
//   0x0018 PERF_FILLDRAIN R   enabled cycles with some PE idle
//   0x001C PERF_IDLE      R   cycles in IDLE since reset (saturating)
//   0x0020 PERF_MACS      R   useful MACs issued                  (= N*N*K)
//   0x1000 A_BUF          W   A[i][k] at 0x1000 + i*K_MAX + k   (N x K_MAX, row-major)
//   0x2000 B_BUF          W   B[k][j] at 0x2000 + k*N + j       (K_MAX x N, row-major)
//   0x3000 C_BUF          R   C[i][j] at 0x3000 + 4*(i*N + j)   (int32 words)
// A/B writes store bus_wdata[7:0] (one int8 per byte address) and are ignored
// while BUSY. Unmapped reads return 0. N and K_MAX must be powers of 2.

module mm_regs #(
    parameter int          N       = 4,
    parameter int          K_MAX   = 64,
    parameter logic [15:0] VERSION = 16'h0001
) (
    input  logic                       clk,
    input  logic                       rst_n,        // board reset
    input  logic                       core_rst_n,   // board reset AND NOT soft reset
    // register bus
    input  logic                       bus_valid,
    output logic                       bus_ready,
    input  logic                       bus_write,
    input  logic [15:0]                bus_addr,
    input  logic [31:0]                bus_wdata,
    output logic                       bus_rvalid,
    output logic [31:0]                bus_rdata,
    // control to the datapath
    output logic                       soft_reset,   // 1-cycle pulse
    output logic                       start,        // 1-cycle pulse
    output logic [$clog2(K_MAX+1)-1:0] k_len,
    output logic                       wr_en,
    output logic                       wr_sel,       // 0 = A, 1 = B
    output logic [$clog2(N)-1:0]       wr_lane,
    output logic [$clog2(K_MAX)-1:0]   wr_addr,
    output logic [7:0]                 wr_data,
    output logic [$clog2(N*N)-1:0]     c_idx,
    input  logic [31:0]                c_data,
    // status from the controller
    input  logic                       busy,
    input  logic                       done,
    input  logic                       array_en,
    input  logic                       all_active,
    input  logic                       rd_en,
    // for the board display
    output logic [31:0]                perf_compute
);

    localparam int LW = $clog2(N);
    localparam int KW = $clog2(K_MAX);
    localparam int KL = $clog2(K_MAX + 1);

    // ---------------- address decode ----------------
    wire        accept  = bus_valid && bus_ready;
    wire        do_wr   = accept &&  bus_write;
    wire        do_rd   = accept && !bus_write;
    wire [3:0]  region  = bus_addr[15:12];
    wire [11:0] offset  = bus_addr[11:0];
    wire        is_reg  = (region == 4'h0);
    wire [5:0]  reg_sel = offset[7:2];          // word index within the register page

    // A: offset = i*K_MAX + k        B: offset = k*N + j
    wire [11:0] a_row = offset >> KW;
    wire [11:0] b_row = offset >> LW;
    wire        a_hit = (region == 4'h1) && (a_row < 12'(N));
    wire        b_hit = (region == 4'h2) && (b_row < 12'(K_MAX));

    assign wr_en   = do_wr && !busy && (a_hit || b_hit);
    assign wr_sel  = (region == 4'h2);
    assign wr_lane = wr_sel ? offset[LW-1:0] : a_row[LW-1:0];
    assign wr_addr = wr_sel ? b_row[KW-1:0]  : offset[KW-1:0];
    assign wr_data = bus_wdata[7:0];
    assign c_idx   = offset[2 +: $clog2(N*N)];

    // ---------------- CTRL / STATUS / CFG ----------------
    wire ctrl_wr = do_wr && is_reg && (reg_sel == 6'd0);
    wire cfg_wr  = do_wr && is_reg && (reg_sel == 6'd2);

    assign start     = ctrl_wr && bus_wdata[0] && !busy;
    assign bus_ready = !soft_reset;

    always_ff @(posedge clk) begin               // survives its own soft reset
        if (!rst_n) soft_reset <= 1'b0;
        else        soft_reset <= ctrl_wr && bus_wdata[1];
    end

    logic done_flag;
    always_ff @(posedge clk) begin
        if (!core_rst_n) begin
            done_flag <= 1'b0;
            k_len     <= KL'(K_MAX);
        end else begin
            if (start)     done_flag <= 1'b0;
            else if (done) done_flag <= 1'b1;
            if (cfg_wr && bus_wdata >= 1 && bus_wdata <= K_MAX)
                k_len <= KL'(bus_wdata);
        end
    end

    // ---------------- performance counters ----------------
    logic [31:0] perf_total, perf_filldrain, perf_idle, perf_macs;

    always_ff @(posedge clk) begin
        if (!core_rst_n) begin
            perf_total     <= '0;
            perf_compute   <= '0;
            perf_filldrain <= '0;
            perf_idle      <= '0;
            perf_macs      <= '0;
        end else begin
            if (!busy && perf_idle != '1) perf_idle <= perf_idle + 1'b1;
            if (start) begin
                perf_total     <= '0;
                perf_compute   <= '0;
                perf_filldrain <= '0;
                perf_macs      <= '0;
            end else begin
                if (busy && !done)            perf_total     <= perf_total + 1'b1;
                if (array_en)                 perf_compute   <= perf_compute + 1'b1;
                if (array_en && !all_active)  perf_filldrain <= perf_filldrain + 1'b1;
                if (rd_en)                    perf_macs      <= perf_macs + 32'(N * N);
            end
        end
    end

    // ---------------- read data (1-cycle latency) ----------------
    logic [31:0] reg_rdata;
    always_comb begin
        case (reg_sel)
            6'd1:    reg_rdata = {30'b0, done_flag, busy};
            6'd2:    reg_rdata = 32'(k_len);
            6'd3:    reg_rdata = {VERSION, 8'(K_MAX), 8'(N)};
            6'd4:    reg_rdata = perf_total;
            6'd5:    reg_rdata = perf_compute;
            6'd6:    reg_rdata = perf_filldrain;
            6'd7:    reg_rdata = perf_idle;
            6'd8:    reg_rdata = perf_macs;
            default: reg_rdata = '0;
        endcase
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            bus_rvalid <= 1'b0;
            bus_rdata  <= '0;
        end else begin
            bus_rvalid <= do_rd;
            if (do_rd)
                bus_rdata <= is_reg              ? reg_rdata :
                             (region == 4'h3 && offset < 12'(4 * N * N)) ? c_data : '0;
        end
    end

endmodule
