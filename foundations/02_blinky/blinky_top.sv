// blinky_top.sv  --  Foundations Project 02
// Blinks LEDR[0] at 1 Hz and shows a binary counter on LEDR[9:1].
// Teaches: counters, clock ENABLE (tick) instead of a slow clock, reset.
//
// Expected on board:
//   LEDR[0] blinks (0.5 s on / 0.5 s off); LEDR[9:1] count up in binary.
//   Hold KEY0 -> reset (everything off).

module blinky_top #(
    parameter int CLK_HZ  = 50_000_000,
    parameter int TICK_HZ = 2                 // toggle twice per second = 1 Hz blink
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

    // Buttons are asynchronous and active-low -> synchronize, idle value 1.
    logic [1:0] key_s;
    sync_2ff #(.WIDTH(2), .INIT(1'b1)) u_key_sync (.clk(clk), .d(KEY), .q(key_s));

    logic rst_n;
    assign rst_n = key_s[0];                  // KEY0 pressed (0) = reset

    logic tick;
    tick_gen #(.DIV(CLK_HZ / TICK_HZ)) u_tick (.clk(clk), .rst_n(rst_n), .tick(tick));

    logic       blink;
    logic [8:0] count;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            blink <= 1'b0;
            count <= '0;
        end else if (tick) begin
            blink <= ~blink;
            count <= count + 1'b1;
        end
    end

    assign LEDR = {count, blink};

    assign {HEX5, HEX4, HEX3, HEX2, HEX1, HEX0} = {6{8'hFF}};
    assign UART_TXD = 1'b1;

endmodule
