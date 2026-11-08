// pe.sv -- my processing element (Lab 3)
module pe #(
    parameter int DW = 8,     // operand width
    parameter int AW = 32     // accumulator width
) (
    input  logic                 clk,
    input  logic                 rst_n,   // synchronous reset, active low
    input  logic                 clear,   // start of a new job
    input  logic                 en,      // do one multiply-add this cycle
    input  logic signed [DW-1:0] a_in,
    input  logic signed [DW-1:0] b_in,
    output logic signed [DW-1:0] a_out,
    output logic signed [DW-1:0] b_out,
    output logic signed [AW-1:0] acc
);
    // TODO 1: declare the product. How many bits does DW x DW need? Make it signed.
    // TODO 2: compute it with one 'assign'.
    // TODO 3: one always_ff @(posedge clk) block:
    //   - if (!rst_n || clear): acc, a_out, b_out all become 0
    //   - else if (en): acc becomes acc + product (sign-extended to AW bits);
    //                   a_out takes a_in; b_out takes b_in
    //   - otherwise: write nothing (the registers hold)
    // Use <= for every register.
endmodule
