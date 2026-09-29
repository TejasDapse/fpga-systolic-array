// sram_sp.sv
// Single-port RAM written in the template Quartus infers as block RAM (M9K).
// See NOTES §9.
//
// Read latency = 1 cycle: `rdata` shows mem[addr] from the PREVIOUS clock edge.
// (Block RAM has registered address inputs, so it can't be read combinationally.)

module sram_sp #(
    parameter int WIDTH = 8,
    parameter int DEPTH = 64
) (
    input  logic                     clk,
    input  logic                     we,
    input  logic [$clog2(DEPTH)-1:0] addr,
    input  logic [WIDTH-1:0]         wdata,
    output logic [WIDTH-1:0]         rdata
);

    logic [WIDTH-1:0] mem [0:DEPTH-1];

    always_ff @(posedge clk) begin
        if (we) mem[addr] <= wdata;
        rdata <= mem[addr];
    end

endmodule
