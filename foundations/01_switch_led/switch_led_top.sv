// switch_led_top.sv  --  Foundations Project 01
// The simplest possible design: each slide switch drives its LED.
// Purpose: prove the whole tool flow works (pins, compile, program).
//
// Expected on board:
//   SW[i] up -> LEDR[i] on.   All HEX displays off.

module switch_led_top (
    input  logic       MAX10_CLK1_50,
    input  logic [1:0] KEY,
    input  logic [9:0] SW,
    output logic [9:0] LEDR,
    output logic [7:0] HEX0, HEX1, HEX2, HEX3, HEX4, HEX5,
    output logic       UART_TXD,
    input  logic       UART_RXD
);

    assign LEDR = SW;                  // pure combinational: wires only

    // Unused outputs must still be driven. HEX is active-low -> 1 = off.
    assign {HEX5, HEX4, HEX3, HEX2, HEX1, HEX0} = {6{8'hFF}};
    assign UART_TXD = 1'b1;            // UART line idles high

endmodule
