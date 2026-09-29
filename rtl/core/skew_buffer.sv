// skew_buffer.sv
// Delays lane n by n cycles: a triangular set of shift registers. See NOTES §14.
//
//   lane 0: in ------------------------> out      (0 registers)
//   lane 1: in -> [R] -----------------> out      (1 register)
//   lane 2: in -> [R] -> [R] ----------> out      (2 registers)
//   ...
//
// Turns "column k of A all at once" into the diagonal wavefront the array needs.

module skew_buffer #(
    parameter int N  = 4,
    parameter int DW = 8
) (
    input  logic            clk,
    input  logic            rst_n,
    input  logic            clear,
    input  logic [N*DW-1:0] din,
    output logic [N*DW-1:0] dout
);

    assign dout[0 +: DW] = din[0 +: DW];

    for (genvar n = 1; n < N; n++) begin : g_lane
        logic [DW-1:0] sr [n];          // sr[0] = newest, sr[n-1] = oldest

        always_ff @(posedge clk) begin
            if (!rst_n || clear) begin
                for (int s = 0; s < n; s++) sr[s] <= '0;
            end else begin
                sr[0] <= din[n*DW +: DW];
                for (int s = 1; s < n; s++) sr[s] <= sr[s-1];
            end
        end

        assign dout[n*DW +: DW] = sr[n-1];
    end

endmodule
