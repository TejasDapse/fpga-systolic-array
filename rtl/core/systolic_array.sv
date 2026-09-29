// systolic_array.sv
// N x N grid of PEs, output-stationary. See NOTES §13–§14.
//
//            b_in[0]  b_in[1] ... (column j enters at the top)
//               |        |
//   a_in[0] -> PE00 -> PE01 -> ...      a flows left -> right along a row
//   a_in[1] -> PE10 -> PE11 -> ...      b flows top  -> bottom along a column
//               |        |
//
// Inputs must already be skewed: row i / column j delayed by i / j cycles
// (skew_buffer.sv does that). A[i][k] and B[k][j] then meet in PE(i,j) at the
// same cycle. PE(i,j)'s accumulator is C[i][j].
//
// Ports are flat vectors (lane n = bits [n*W +: W]) to stay tool-friendly.

module systolic_array #(
    parameter int N  = 4,
    parameter int DW = 8,
    parameter int AW = 32
) (
    input  logic              clk,
    input  logic              rst_n,
    input  logic              clear,
    input  logic              en,
    input  logic [N*DW-1:0]   a_in,     // lane i = row i  (left edge)
    input  logic [N*DW-1:0]   b_in,     // lane j = column j (top edge)
    output logic [N*N*AW-1:0] c_out     // element (i,j) at [(i*N+j)*AW +: AW]
);

    // a_h[i][j] = a value entering PE(i,j) from the left (j = N: off the edge)
    // b_v[i][j] = b value entering PE(i,j) from above  (i = N: off the edge)
    logic [DW-1:0] a_h [N][N+1];
    logic [DW-1:0] b_v [N+1][N];

    for (genvar i = 0; i < N; i++) begin : g_edge
        assign a_h[i][0] = a_in[i*DW +: DW];
        assign b_v[0][i] = b_in[i*DW +: DW];
    end

    for (genvar i = 0; i < N; i++) begin : g_row
        for (genvar j = 0; j < N; j++) begin : g_col
            pe #(.DW(DW), .AW(AW)) u_pe (
                .clk(clk), .rst_n(rst_n), .clear(clear), .en(en),
                .a_in (a_h[i][j]),   .b_in (b_v[i][j]),
                .a_out(a_h[i][j+1]), .b_out(b_v[i+1][j]),
                .acc  (c_out[(i*N+j)*AW +: AW])
            );
        end
    end

endmodule
