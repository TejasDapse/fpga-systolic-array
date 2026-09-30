// mm_controller.sv
// Sequences one matrix multiply. See NOTES §8 (FSMs).
//
//   IDLE --start--> CLEAR --> COMPUTE (K cycles) --> DRAIN (2N-1 cycles) --> DONE --> IDLE
//
// Step counter t runs 0 .. K+2N-2 across COMPUTE and DRAIN:
//   COMPUTE, t < K : read column/row t of the A/B buffers (rd_en = 1, rd_addr = t).
//   DRAIN          : buffers idle, zeros are fed while the last wavefront drains.
//
// Timing of the last product (see mm_core.sv): the read issued at t = K-1
// reaches PE(N-1,N-1) at t = K-1 + 1 (RAM) + 2(N-1) (skew + hops) = K + 2N - 2,
// the final DRAIN step, so C is complete when DONE is entered.
//
// All PEs are busy at step t when every PE(i,j) has valid data, i.e. for
// 2N-1 <= t <= K (`all_active`, used by the fill/drain perf counter).

module mm_controller #(
    parameter int N     = 4,
    parameter int K_MAX = 64
) (
    input  logic                       clk,
    input  logic                       rst_n,
    input  logic                       start,     // 1-cycle pulse (ignored if busy)
    input  logic [$clog2(K_MAX+1)-1:0] k_len,     // 1 .. K_MAX, sampled at start
    output logic                       busy,
    output logic                       done,      // 1-cycle pulse, C is valid
    output logic                       clear,     // to array + skew buffers
    output logic                       array_en,  // COMPUTE or DRAIN
    output logic                       all_active,
    output logic                       rd_en,
    output logic [$clog2(K_MAX)-1:0]   rd_addr,
    output logic [2:0]                 state_o    // for the LEDs
);

    localparam int TW = $clog2(K_MAX + 2 * N);

    typedef enum logic [2:0] {IDLE, CLEAR, COMPUTE, DRAIN, DONE} state_t;

    state_t                     state;
    logic [TW-1:0]              t;
    logic [$clog2(K_MAX+1)-1:0] k_r;

    wire [TW-1:0] k_t    = TW'(k_r);
    wire [TW-1:0] last_t = k_t + TW'(2 * N - 2);

    assign busy       = (state != IDLE);
    assign done       = (state == DONE);
    assign clear      = (state == CLEAR);
    assign array_en   = (state == COMPUTE) || (state == DRAIN);
    assign all_active = array_en && (t >= TW'(2 * N - 1)) && (t <= k_t);
    assign rd_en      = (state == COMPUTE);
    assign rd_addr    = t[$clog2(K_MAX)-1:0];
    assign state_o    = state;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            t     <= '0;
            k_r   <= '0;
        end else begin
            case (state)
                IDLE: if (start) begin
                    k_r   <= k_len;
                    state <= CLEAR;
                end

                CLEAR: begin
                    t     <= '0;
                    state <= COMPUTE;
                end

                COMPUTE: begin
                    t <= t + 1'b1;
                    if (t == k_t - 1'b1) state <= DRAIN;
                end

                DRAIN: begin
                    if (t == last_t) state <= DONE;
                    else             t     <= t + 1'b1;
                end

                DONE: state <= IDLE;

                default: state <= IDLE;
            endcase
        end
    end

endmodule
