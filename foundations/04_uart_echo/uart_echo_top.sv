// uart_echo_top.sv  --  Foundations Project 04
// Every byte received on UART RX is sent straight back on UART TX.
// A small FIFO between RX and TX absorbs tiny baud-rate differences
// between the PC's adapter and the FPGA.
//
// Expected on board (115200 8N1):
//   Type in a terminal on the Mac -> characters echo back.
//   HEX1:HEX0 = last byte received (hex), HEX5..HEX2 = number of bytes received.
//   LEDR[0] = framing error seen (sticky), LEDR[1] = FIFO overflow (sticky),
//   LEDR[9] = heartbeat (1 Hz blink: "design is alive").
//   Hold KEY0 -> reset.
//
// Wiring: GPIO[0] (header pin 1) = UART_TXD -> adapter RXD
//         GPIO[1] (header pin 2) = UART_RXD <- adapter TXD
//         header pin 12 (GND)    -> adapter GND

module uart_echo_top #(
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

    // ---------------- RX -> FIFO -> TX ----------------
    logic [7:0] rx_data;
    logic       rx_valid, rx_frame_err;

    uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_rx (
        .clk(clk), .rst_n(rst_n), .rx(UART_RXD),
        .data(rx_data), .valid(rx_valid), .frame_err(rx_frame_err)
    );

    logic [7:0] fifo_rdata;
    logic       fifo_full, fifo_empty;
    logic       tx_ready;

    fifo_sync #(.WIDTH(8), .DEPTH(16)) u_fifo (
        .clk(clk), .rst_n(rst_n),
        .wdata(rx_data),    .wr_en(rx_valid),              .full(fifo_full),
        .rdata(fifo_rdata), .rd_en(tx_ready & ~fifo_empty), .empty(fifo_empty)
    );

    uart_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_tx (
        .clk(clk), .rst_n(rst_n),
        .data(fifo_rdata), .valid(~fifo_empty), .ready(tx_ready),
        .tx(UART_TXD)
    );

    // ---------------- Status / debug ----------------
    logic [7:0]  last_byte;
    logic [15:0] byte_count;
    logic        err_frame, err_overflow;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            last_byte    <= '0;
            byte_count   <= '0;
            err_frame    <= 1'b0;
            err_overflow <= 1'b0;
        end else begin
            if (rx_valid) begin
                last_byte  <= rx_data;
                byte_count <= byte_count + 1'b1;
            end
            if (rx_frame_err)          err_frame    <= 1'b1;
            if (rx_valid && fifo_full) err_overflow <= 1'b1;
        end
    end

    logic tick_2hz, heartbeat;
    tick_gen #(.DIV(CLK_HZ / 2)) u_hb (.clk(clk), .rst_n(rst_n), .tick(tick_2hz));
    always_ff @(posedge clk) begin
        if (!rst_n)        heartbeat <= 1'b0;
        else if (tick_2hz) heartbeat <= ~heartbeat;
    end

    logic [23:0] shown;
    assign shown = {byte_count, last_byte};

    logic [5:0][6:0] seg;               // packed: 6 digits x 7 segments
    for (genvar d = 0; d < 6; d++) begin : g_digit
        hex7seg u_hex (.hex(shown[4*d +: 4]), .seg_n(seg[d]));
    end

    assign HEX0 = {1'b1, seg[0]};
    assign HEX1 = {1'b1, seg[1]};
    assign HEX2 = {1'b1, seg[2]};
    assign HEX3 = {1'b1, seg[3]};
    assign HEX4 = {1'b1, seg[4]};
    assign HEX5 = {1'b1, seg[5]};

    assign LEDR = {heartbeat, 7'b0, err_overflow, err_frame};

endmodule
