// pe.sv
// Processing Element for an output-stationary systolic array. See NOTES §12–§14.
//
// Every enabled cycle the PE:
//   - multiplies the operands arriving from the left (a) and from above (b),
//   - adds the product into its own accumulator (this PE owns one C[i][j]),
//   - passes a to the right and b downwards through registers.
//
// int8 x int8 -> int16 product; accumulated in int32 (K <= 2^17 can't overflow).
// `clear` zeroes the accumulator and the pass-through registers (start of a job).

module pe #(
    parameter int DW = 8,               // operand width
    parameter int AW = 32               // accumulator width
) (
    input  logic                 clk,
    input  logic                 rst_n,
    input  logic                 clear,
    input  logic                 en,
    input  logic signed [DW-1:0] a_in,  // from the left neighbour
    input  logic signed [DW-1:0] b_in,  // from the neighbour above
    output logic signed [DW-1:0] a_out, // to the right neighbour
    output logic signed [DW-1:0] b_out, // to the neighbour below
    output logic signed [AW-1:0] acc
);

    logic signed [2*DW-1:0] prod;
    assign prod = a_in * b_in;          // both operands signed -> signed multiply

    always_ff @(posedge clk) begin
        if (!rst_n || clear) begin
            a_out <= '0;
            b_out <= '0;
            acc   <= '0;
        end else if (en) begin
            a_out <= a_in;
            b_out <= b_in;
            acc   <= acc + AW'(prod);    // signed cast: sign-extends to AW bits
        end
    end

endmodule
