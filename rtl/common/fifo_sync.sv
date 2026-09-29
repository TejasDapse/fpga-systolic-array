// fifo_sync.sv
// Synchronous (single-clock) FIFO, first-word-fall-through:
// `rdata` always shows the oldest entry while `empty` is low.
//
// Full/empty detection uses pointers with one extra MSB:
//   empty: pointers identical
//   full : lower bits identical, MSBs differ (writer has lapped the reader)

module fifo_sync #(
    parameter int WIDTH = 8,
    parameter int DEPTH = 16          // must be a power of 2
) (
    input  logic             clk,
    input  logic             rst_n,
    // write side
    input  logic [WIDTH-1:0] wdata,
    input  logic             wr_en,   // ignored when full
    output logic             full,
    // read side
    output logic [WIDTH-1:0] rdata,
    input  logic             rd_en,   // ignored when empty
    output logic             empty
);

    localparam int AW = $clog2(DEPTH);

    logic [WIDTH-1:0] mem [0:DEPTH-1];
    logic [AW:0]      wptr, rptr;

    wire do_write = wr_en && !full;
    wire do_read  = rd_en && !empty;

    assign empty = (wptr == rptr);
    assign full  = (wptr[AW] != rptr[AW]) && (wptr[AW-1:0] == rptr[AW-1:0]);
    assign rdata = mem[rptr[AW-1:0]];

    // Storage has no reset (it doesn't need one, and this keeps it simple).
    always_ff @(posedge clk) begin
        if (do_write)
            mem[wptr[AW-1:0]] <= wdata;
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            wptr <= '0;
            rptr <= '0;
        end else begin
            if (do_write) wptr <= wptr + 1'b1;
            if (do_read)  rptr <= rptr + 1'b1;
        end
    end

endmodule
