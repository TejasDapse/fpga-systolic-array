// cmd_parser.sv
// Byte-level command protocol between the host and mm_core (PLAN.md §5).
//
//   'P'            -> 'K', N, K_MAX          ping / discover parameters
//   'S' k          -> 'K'  (or 'E' if k is 0 or > K_MAX)
//   'A' N*K bytes  -> 'K'  A, int8, row-major
//   'B' K*N bytes  -> 'K'  B, int8, row-major
//   'G'            -> 'D'  after the multiply has finished
//   'R'            -> N*N int32 (row-major, little-endian)
//   'C'            -> 4-byte cycle count (little-endian)
//   anything else  -> 'E'  and the sticky `err_cmd` flag is set
//
// Responses are pushed into a TX FIFO (tx_push only when !tx_full).
// If the host stops mid-command for TIMEOUT_CLKS, the parser gives up and
// returns to waiting for a command (so a crashed host script can't wedge it).

module cmd_parser #(
    parameter int N            = 4,
    parameter int K_MAX        = 64,
    parameter int TIMEOUT_CLKS = 5_000_000        // 100 ms at 50 MHz
) (
    input  logic                         clk,
    input  logic                         rst_n,
    // from UART RX
    input  logic [7:0]                   rx_data,
    input  logic                         rx_valid,
    // to TX FIFO
    output logic [7:0]                   tx_data,
    output logic                         tx_push,
    input  logic                         tx_full,
    // to mm_core
    output logic                         wr_en,
    output logic                         wr_sel,
    output logic [$clog2(N)-1:0]         wr_lane,
    output logic [$clog2(K_MAX)-1:0]     wr_addr,
    output logic [7:0]                   wr_data,
    output logic [$clog2(K_MAX+1)-1:0]   k_len,
    output logic                         start,
    input  logic                         done,
    input  logic [31:0]                  cycles,
    output logic [$clog2(N*N)-1:0]       rd_idx,
    input  logic [31:0]                  rd_data,
    // status
    output logic                         err_cmd,     // sticky: bad command / bad K
    output logic                         err_timeout  // sticky: host stalled mid-command
);

    localparam int LW = $clog2(N);
    localparam int KW = $clog2(K_MAX);
    localparam int KL = $clog2(K_MAX + 1);
    localparam int SW = $clog2(N * N * 4 + 1);   // send counter width
    localparam int TW = $clog2(TIMEOUT_CLKS + 1);

    typedef enum logic [2:0] {S_CMD, S_ARG_K, S_LOAD, S_RUN, S_SEND} state_t;
    typedef enum logic [1:0] {R_BYTE, R_PING, R_RESULT, R_CYCLES} resp_t;

    state_t        state;
    resp_t         resp;
    logic [7:0]    resp_byte;          // payload for R_BYTE
    logic [SW-1:0] send_cnt, send_last;

    // Load counters. A (N x K, row-major): outer = row i,  inner = k.
    //                B (K x N, row-major): outer = k,      inner = column j.
    logic          load_b;
    logic [KW-1:0] outer, inner;       // KW >= LW is assumed (K_MAX >= N)
    wire  [KW-1:0] inner_last = load_b ? KW'(N - 1) : KW'(k_len - 1'b1);
    wire  [KW-1:0] outer_last = load_b ? KW'(k_len - 1'b1) : KW'(N - 1);

    assign wr_sel  = load_b;
    assign wr_lane = load_b ? inner[LW-1:0] : outer[LW-1:0];
    assign wr_addr = load_b ? outer : inner;
    assign wr_data = rx_data;
    assign wr_en   = (state == S_LOAD) && rx_valid;

    // ---------------- response byte mux ----------------
    logic [31:0] word;
    assign rd_idx = send_cnt[2 +: $clog2(N*N)];   // 4 bytes per element
    assign word   = (resp == R_RESULT) ? rd_data : cycles;

    always_comb begin
        case (resp)
            R_PING:  tx_data = (send_cnt == 0) ? "K" :
                               (send_cnt == 1) ? 8'(N) : 8'(K_MAX);
            R_BYTE:  tx_data = resp_byte;
            default: tx_data = word[8*send_cnt[1:0] +: 8];
        endcase
    end
    assign tx_push = (state == S_SEND) && !tx_full;

    // ---------------- stall timeout ----------------
    logic [TW-1:0] idle_cnt;
    wire waiting_for_host = (state == S_ARG_K) || (state == S_LOAD);
    wire timed_out        = waiting_for_host && (idle_cnt == TW'(TIMEOUT_CLKS));

    always_ff @(posedge clk) begin
        if (!rst_n || !waiting_for_host || rx_valid) idle_cnt <= '0;
        else if (!timed_out)                         idle_cnt <= idle_cnt + 1'b1;
    end

    // ---------------- main FSM ----------------
    task automatic reply(input logic [7:0] b);
        resp      <= R_BYTE;
        resp_byte <= b;
        send_cnt  <= '0;
        send_last <= '0;
        state     <= S_SEND;
    endtask

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state       <= S_CMD;
            resp        <= R_BYTE;
            resp_byte   <= '0;
            send_cnt    <= '0;
            send_last   <= '0;
            load_b      <= 1'b0;
            outer       <= '0;
            inner       <= '0;
            k_len       <= KL'(K_MAX);
            start       <= 1'b0;
            err_cmd     <= 1'b0;
            err_timeout <= 1'b0;
        end else begin
            start <= 1'b0;

            if (timed_out) begin
                err_timeout <= 1'b1;
                state       <= S_CMD;
            end else case (state)
                S_CMD: if (rx_valid) begin
                    outer <= '0;
                    inner <= '0;
                    case (rx_data)
                        "P": begin
                            resp      <= R_PING;
                            send_cnt  <= '0;
                            send_last <= SW'(2);
                            state     <= S_SEND;
                        end
                        "S": state <= S_ARG_K;
                        "A": begin load_b <= 1'b0; state <= S_LOAD; end
                        "B": begin load_b <= 1'b1; state <= S_LOAD; end
                        "G": begin start  <= 1'b1; state <= S_RUN;  end
                        "R": begin
                            resp      <= R_RESULT;
                            send_cnt  <= '0;
                            send_last <= SW'(N * N * 4 - 1);
                            state     <= S_SEND;
                        end
                        "C": begin
                            resp      <= R_CYCLES;
                            send_cnt  <= '0;
                            send_last <= SW'(3);
                            state     <= S_SEND;
                        end
                        default: begin
                            err_cmd <= 1'b1;
                            reply("E");
                        end
                    endcase
                end

                S_ARG_K: if (rx_valid) begin
                    if (rx_data == 0 || rx_data > K_MAX) begin
                        err_cmd <= 1'b1;
                        reply("E");
                    end else begin
                        k_len <= KL'(rx_data);
                        reply("K");
                    end
                end

                S_LOAD: if (rx_valid) begin
                    if (inner == inner_last) begin
                        inner <= '0;
                        if (outer == outer_last) reply("K");
                        else                     outer <= outer + 1'b1;
                    end else begin
                        inner <= inner + 1'b1;
                    end
                end

                S_RUN: if (done) reply("D");

                S_SEND: if (!tx_full) begin
                    if (send_cnt == send_last) state    <= S_CMD;
                    else                       send_cnt <= send_cnt + 1'b1;
                end

                default: state <= S_CMD;
            endcase
        end
    end

endmodule
