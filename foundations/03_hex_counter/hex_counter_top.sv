// hex_counter_top.sv  --  Foundations Project 03
// A 24-bit hex counter on HEX5..HEX0, counting at 10 Hz.
// KEY1 toggles RUN / PAUSE through a 2-state FSM.
// Teaches: 7-segment decoding, button edge detection, a simple FSM.
//
// Expected on board:
//   HEX displays count up in hex (000000, 000001, ... 00000F, 000010 ...).
//   Press KEY1 -> pause (LEDR[0] off). Press again -> run (LEDR[0] on).
//   Hold KEY0 -> reset to 000000.

module hex_counter_top #(
    parameter int CLK_HZ  = 50_000_000,
    parameter int TICK_HZ = 10
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

    // ---- Edge detect on KEY1: one-cycle pulse at the moment it is pressed ----
    logic key1_prev;
    logic key1_press;
    always_ff @(posedge clk) key1_prev <= key_s[1];
    assign key1_press = key1_prev & ~key_s[1];     // was 1 (released), now 0 (pressed)

    // ---- RUN / PAUSE state machine (Moore) ----
    typedef enum logic {PAUSED = 1'b0, RUNNING = 1'b1} state_t;
    state_t state;

    always_ff @(posedge clk) begin
        if (!rst_n)
            state <= RUNNING;
        else if (key1_press) begin
            if (state == RUNNING) state <= PAUSED;
            else                  state <= RUNNING;
        end
    end

    // ---- Counter ----
    logic tick;
    tick_gen #(.DIV(CLK_HZ / TICK_HZ)) u_tick (.clk(clk), .rst_n(rst_n), .tick(tick));

    logic [23:0] count;
    always_ff @(posedge clk) begin
        if (!rst_n)
            count <= '0;
        else if (tick && state == RUNNING)
            count <= count + 1'b1;
    end

    // ---- Display: one hex7seg per digit (generate loop) ----
    logic [5:0][6:0] seg;               // packed: 6 digits x 7 segments
    for (genvar d = 0; d < 6; d++) begin : g_digit
        hex7seg u_hex (.hex(count[4*d +: 4]), .seg_n(seg[d]));
    end

    // Bit 7 is the decimal point (active-low, 1 = off).
    assign HEX0 = {1'b1, seg[0]};
    assign HEX1 = {1'b1, seg[1]};
    assign HEX2 = {1'b1, seg[2]};
    assign HEX3 = {1'b1, seg[3]};
    assign HEX4 = {1'b1, seg[4]};
    assign HEX5 = {1'b1, seg[5]};

    assign LEDR     = {9'b0, (state == RUNNING)};
    assign UART_TXD = 1'b1;

endmodule
