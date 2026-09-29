// tick_gen.sv
// Generates a one-cycle-wide pulse ("tick") every DIV clock cycles.
// Use the tick as a clock ENABLE -- never as a clock (NOTES §6).
//
// Example: DIV = 50_000_000 at 50 MHz -> one tick per second.

module tick_gen #(
    parameter int DIV = 50_000_000     // must be >= 2
) (
    input  logic clk,
    input  logic rst_n,                // synchronous, active-low
    output logic tick
);

    localparam int W = $clog2(DIV);

    logic [W-1:0] cnt;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            cnt  <= '0;
            tick <= 1'b0;
        end else if (cnt == DIV - 1) begin
            cnt  <= '0;
            tick <= 1'b1;
        end else begin
            cnt  <= cnt + 1'b1;
            tick <= 1'b0;
        end
    end

endmodule
