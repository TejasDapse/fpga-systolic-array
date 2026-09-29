// top_de10lite.sv  --  Systolic-array matrix-multiply accelerator on the DE10-Lite
//
//   UART_RXD -> uart_rx -> cmd_parser -> mm_core (buffers, skew, N x N array)
//   UART_TXD <- uart_tx <- TX FIFO <--/
//
// Board I/O:
//   KEY0          hold = reset
//   HEX5..HEX0    cycle count of the last multiply (hex)
//   LEDR[1:0]     controller state (0 idle, 1 clear, 2 compute, 3 done)
//   LEDR[2]       busy
//   LEDR[5]       UART framing error seen      (sticky)
//   LEDR[6]       bad command / bad K          (sticky)
//   LEDR[7]       host stalled mid-command     (sticky)
//   LEDR[8]       a multiply has completed since reset
//   LEDR[9]       heartbeat (1 Hz)
//
// Wiring: same as foundations/04_uart_echo (GPIO[0] = TX, GPIO[1] = RX, GND).

module top_de10lite #(
    parameter int N      = 4,
    parameter int K_MAX  = 64,
    parameter int CLK_HZ = 50_000_000,
    parameter int BAUD   = 115_200
) (
    input  logic       MAX10_CLK1_50,
    input  logic [1:0] KEY,
    input  logic [9:0] SW,
    output logic [9:0] LEDR,
    output logic [7:0] HEX0, HEX1, HEX2, HEX3, HEX4, HEX5,
    output logic       UART_TXD,
    input  logic       UART_RXD
);

    logic clk;
    assign clk = MAX10_CLK1_50;

    logic [1:0] key_s;
    sync_2ff #(.WIDTH(2), .INIT(1'b1)) u_key_sync (.clk(clk), .d(KEY), .q(key_s));

    logic rst_n;
    assign rst_n = key_s[0];

    // ---------------- UART ----------------
    logic [7:0] rx_data;
    logic       rx_valid, rx_frame_err;

    uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_rx (
        .clk(clk), .rst_n(rst_n), .rx(UART_RXD),
        .data(rx_data), .valid(rx_valid), .frame_err(rx_frame_err)
    );

    logic [7:0] txq_wdata, txq_rdata;
    logic       txq_push, txq_full, txq_empty, tx_ready;

    fifo_sync #(.WIDTH(8), .DEPTH(16)) u_txq (
        .clk(clk), .rst_n(rst_n),
        .wdata(txq_wdata), .wr_en(txq_push),               .full(txq_full),
        .rdata(txq_rdata), .rd_en(tx_ready & ~txq_empty),  .empty(txq_empty)
    );

    uart_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_tx (
        .clk(clk), .rst_n(rst_n),
        .data(txq_rdata), .valid(~txq_empty), .ready(tx_ready), .tx(UART_TXD)
    );

    // ---------------- parser + core ----------------
    logic                       wr_en, wr_sel, start, busy, done;
    logic [$clog2(N)-1:0]       wr_lane;
    logic [$clog2(K_MAX)-1:0]   wr_addr;
    logic [7:0]                 wr_data;
    logic [$clog2(K_MAX+1)-1:0] k_len;
    logic [31:0]                cycles, rd_data;
    logic [$clog2(N*N)-1:0]     rd_idx;
    logic [1:0]                 mm_state;
    logic                       err_cmd, err_timeout;

    cmd_parser #(.N(N), .K_MAX(K_MAX), .TIMEOUT_CLKS(CLK_HZ / 10)) u_parser (
        .clk(clk), .rst_n(rst_n),
        .rx_data(rx_data), .rx_valid(rx_valid),
        .tx_data(txq_wdata), .tx_push(txq_push), .tx_full(txq_full),
        .wr_en(wr_en), .wr_sel(wr_sel), .wr_lane(wr_lane), .wr_addr(wr_addr),
        .wr_data(wr_data), .k_len(k_len), .start(start), .done(done),
        .cycles(cycles), .rd_idx(rd_idx), .rd_data(rd_data),
        .err_cmd(err_cmd), .err_timeout(err_timeout)
    );

    mm_core #(.N(N), .K_MAX(K_MAX)) u_core (
        .clk(clk), .rst_n(rst_n),
        .wr_en(wr_en), .wr_sel(wr_sel), .wr_lane(wr_lane), .wr_addr(wr_addr),
        .wr_data(wr_data), .k_len(k_len), .start(start),
        .busy(busy), .done(done), .cycles(cycles), .state(mm_state),
        .rd_idx(rd_idx), .rd_data(rd_data)
    );

    // ---------------- status ----------------
    logic err_frame, ran_once;
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            err_frame <= 1'b0;
            ran_once  <= 1'b0;
        end else begin
            if (rx_frame_err) err_frame <= 1'b1;
            if (done)         ran_once  <= 1'b1;
        end
    end

    logic tick_2hz, heartbeat;
    tick_gen #(.DIV(CLK_HZ / 2)) u_hb (.clk(clk), .rst_n(rst_n), .tick(tick_2hz));
    always_ff @(posedge clk) begin
        if (!rst_n)        heartbeat <= 1'b0;
        else if (tick_2hz) heartbeat <= ~heartbeat;
    end

    logic [5:0][6:0] seg;
    for (genvar d = 0; d < 6; d++) begin : g_digit
        hex7seg u_hex (.hex(cycles[4*d +: 4]), .seg_n(seg[d]));
    end

    assign HEX0 = {1'b1, seg[0]};
    assign HEX1 = {1'b1, seg[1]};
    assign HEX2 = {1'b1, seg[2]};
    assign HEX3 = {1'b1, seg[3]};
    assign HEX4 = {1'b1, seg[4]};
    assign HEX5 = {1'b1, seg[5]};

    assign LEDR = {heartbeat, ran_once, err_timeout, err_cmd, err_frame,
                   2'b00, busy, mm_state};

endmodule
