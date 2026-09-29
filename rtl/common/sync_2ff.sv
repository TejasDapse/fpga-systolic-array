// sync_2ff.sv
// Two flip-flop synchronizer for asynchronous inputs (buttons, UART RX pin).
// Protects the design from metastability (NOTES §7).
//
// INIT sets the power-up value of both stages; use 1 for signals that idle
// high (UART RX line, active-low push buttons).

module sync_2ff #(
    parameter int WIDTH = 1,
    parameter bit INIT  = 1'b0
) (
    input  logic             clk,
    input  logic [WIDTH-1:0] d,     // asynchronous input
    output logic [WIDTH-1:0] q      // synchronized output (2-cycle delay)
);

    logic [WIDTH-1:0] stage1 = {WIDTH{INIT}};
    logic [WIDTH-1:0] stage2 = {WIDTH{INIT}};

    always_ff @(posedge clk) begin
        stage1 <= d;
        stage2 <= stage1;
    end

    assign q = stage2;

endmodule
