// mm_controller.sv
// Sequences one matrix multiply. See NOTES §8 (FSMs).
//
//   IDLE --start--> CLEAR --> COMPUTE (K + 2N - 1 cycles) --> DONE --> IDLE
//
// COMPUTE step t (t = 0 .. K+2N-2):
//   t < K : read column/row t of the A/B buffers (rd_en = 1, rd_addr = t).
//   later : buffers idle, zeros are fed while the last wavefront drains.
//
// Timing of the last product (see mm_core.sv): the read issued at t = K-1
// reaches PE(N-1,N-1) at step t = K-1 + 1 (RAM) + 2(N-1) (skew + hops)
// = K + 2N - 2, so C is complete when DONE is entered.
//
// `cycles` = number of clocks spent in CLEAR + COMPUTE = K + 2N. It is held
// until the next start so the host can read it.

module mm_controller #(
    parameter int N     = 4,
    parameter int K_MAX = 64
) (
    input  logic                     clk,
    input  logic                     rst_n,
    input  logic                     start,     // 1-cycle pulse (ignored if busy)
    input  logic [$clog2(K_MAX+1)-1:0] k_len,   // 1 .. K_MAX, sampled at start
    output logic                     busy,
    output logic                     done,      // 1-cycle pulse, C is valid
    output logic                     clear,     // to array + skew buffers
    output logic                     rd_en,
    output logic [$clog2(K_MAX)-1:0] rd_addr,
    output logic [31:0]              cycles,
    output logic [1:0]               state_o    // for the LEDs
);

    localparam int TW = $clog2(K_MAX + 2 * N);

    typedef enum logic [1:0] {IDLE, CLEAR, COMPUTE, DONE} state_t;

    state_t                     state;
    logic [TW-1:0]              t;
    logic [$clog2(K_MAX+1)-1:0] k_r;

    wire [TW-1:0] last_t = TW'(k_r) + TW'(2 * N - 2);

    assign busy    = (state != IDLE);
    assign done    = (state == DONE);
    assign clear   = (state == CLEAR);
    assign rd_en   = (state == COMPUTE) && (t < TW'(k_r));
    assign rd_addr = t[$clog2(K_MAX)-1:0];
    assign state_o = state;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state  <= IDLE;
            t      <= '0;
            k_r    <= '0;
            cycles <= '0;
        end else begin
            case (state)
                IDLE: if (start) begin
                    k_r    <= k_len;
                    cycles <= '0;
                    state  <= CLEAR;
                end

                CLEAR: begin
                    t      <= '0;
                    cycles <= cycles + 1'b1;
                    state  <= COMPUTE;
                end

                COMPUTE: begin
                    cycles <= cycles + 1'b1;
                    if (t == last_t) state <= DONE;
                    else             t     <= t + 1'b1;
                end

                DONE: state <= IDLE;

                default: state <= IDLE;
            endcase
        end
    end

endmodule
