// uart_bus_bridge.sv
// Turns UART command bytes into register-bus transactions (PLAN.md §5).
// All multi-byte fields are little-endian.
//
//   'W' addr(2) data(4)        -> 'K'          write one word
//   'R' addr(2)                -> data(4)      read one word
//   'B' addr(2) len(2) bytes   -> 'K'          block write: byte n -> bus write
//                                              of {24'b0, byte} at addr + n
//   'D' addr(2) len(2)         -> len bytes    block read: byte n = byte
//                                              (addr+n)%4 of the word at (addr+n) & ~3
//   'P'                        -> 'K' N K_MAX  ping (reads the INFO register)
//   anything else              -> 'E'          and sets the sticky err_cmd flag
//
// Responses go into a TX FIFO (tx_push only when !tx_full).
// Payload bytes are handled one at a time: each one must be accepted by the
// bus before the next byte arrives (trivially true: a UART byte takes ~4340
// clocks at 115200 baud, a bus write a few clocks).
// If the host stops mid-command for TIMEOUT_CLKS, the bridge abandons the
// command and waits for a new one (so a crashed host script can't wedge it).

module uart_bus_bridge #(
    parameter int TIMEOUT_CLKS = 5_000_000,     // 100 ms at 50 MHz
    parameter logic [15:0] INFO_ADDR = 16'h000C
) (
    input  logic        clk,
    input  logic        rst_n,
    // from UART RX
    input  logic [7:0]  rx_data,
    input  logic        rx_valid,
    // to TX FIFO
    output logic [7:0]  tx_data,
    output logic        tx_push,
    input  logic        tx_full,
    // register bus master
    output logic        bus_valid,
    input  logic        bus_ready,
    output logic        bus_write,
    output logic [15:0] bus_addr,
    output logic [31:0] bus_wdata,
    input  logic        bus_rvalid,
    input  logic [31:0] bus_rdata,
    // status
    output logic        err_cmd,       // sticky: unknown command
    output logic        err_timeout    // sticky: host stalled mid-command
);

    localparam int TW = $clog2(TIMEOUT_CLKS + 1);

    typedef enum logic [2:0] {
        S_CMD,      // wait for a command byte
        S_ARGS,     // collect addr / data / len bytes
        S_BLK_W,    // block write: wait for the next payload byte
        S_WREQ,     // bus write request outstanding
        S_RREQ,     // bus read request outstanding
        S_RWAIT,    // waiting for read data
        S_SEND      // pushing response bytes into the TX FIFO
    } state_t;

    state_t      state;
    logic [7:0]  cmd;
    logic [47:0] args;                  // [15:0] addr, [31:16] len, [47:16] data
    logic [2:0]  arg_cnt, arg_need;
    logic [15:0] cnt;                   // block progress
    logic [31:0] send_buf;
    logic [2:0]  send_left;

    wire [15:0] addr = args[15:0];
    wire [15:0] len  = args[31:16];
    wire [15:0] cur  = addr + cnt;      // current block address

    assign tx_data = send_buf[7:0];
    assign tx_push = (state == S_SEND) && !tx_full;

    // ---------------- stall timeout ----------------
    logic [TW-1:0] idle_cnt;
    wire waiting_for_host = (state == S_ARGS) || (state == S_BLK_W);
    wire timed_out        = waiting_for_host && (idle_cnt == TW'(TIMEOUT_CLKS));

    always_ff @(posedge clk) begin
        if (!rst_n || !waiting_for_host || rx_valid) idle_cnt <= '0;
        else if (!timed_out)                         idle_cnt <= idle_cnt + 1'b1;
    end

    // ---------------- main FSM ----------------
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state       <= S_CMD;
            cmd         <= '0;
            args        <= '0;
            arg_cnt     <= '0;
            arg_need    <= '0;
            cnt         <= '0;
            send_buf    <= '0;
            send_left   <= '0;
            bus_valid   <= 1'b0;
            bus_write   <= 1'b0;
            bus_addr    <= '0;
            bus_wdata   <= '0;
            err_cmd     <= 1'b0;
            err_timeout <= 1'b0;
        end else if (timed_out) begin
            err_timeout <= 1'b1;
            state       <= S_CMD;
        end else begin
            case (state)
                S_CMD: if (rx_valid) begin
                    cmd     <= rx_data;
                    args    <= '0;
                    arg_cnt <= '0;
                    cnt     <= '0;
                    case (rx_data)
                        "W":      begin arg_need <= 3'd6; state <= S_ARGS; end
                        "R":      begin arg_need <= 3'd2; state <= S_ARGS; end
                        "B", "D": begin arg_need <= 3'd4; state <= S_ARGS; end
                        "P": begin
                            bus_valid <= 1'b1;
                            bus_write <= 1'b0;
                            bus_addr  <= INFO_ADDR;
                            state     <= S_RREQ;
                        end
                        default: begin
                            err_cmd   <= 1'b1;
                            send_buf  <= 32'("E");
                            send_left <= 3'd1;
                            state     <= S_SEND;
                        end
                    endcase
                end

                S_ARGS: if (rx_valid) begin
                    args[8*arg_cnt +: 8] <= rx_data;
                    arg_cnt              <= arg_cnt + 1'b1;
                    // Last argument byte: act on it now (rx_data is its value).
                    if (arg_cnt == arg_need - 1'b1) begin
                        case (cmd)
                            "W": begin                   // data = bytes 2..5
                                bus_valid <= 1'b1;
                                bus_write <= 1'b1;
                                bus_addr  <= addr;
                                bus_wdata <= {rx_data, args[39:16]};
                                state     <= S_WREQ;
                            end
                            "R": begin                   // addr = bytes 0..1
                                bus_valid <= 1'b1;
                                bus_write <= 1'b0;
                                bus_addr  <= {rx_data, args[7:0]};
                                state     <= S_RREQ;
                            end
                            "B": begin                   // len = bytes 2..3
                                if ({rx_data, args[23:16]} == 0) begin
                                    send_buf  <= 32'("K");
                                    send_left <= 3'd1;
                                    state     <= S_SEND;
                                end else begin
                                    state <= S_BLK_W;
                                end
                            end
                            "D": begin
                                if ({rx_data, args[23:16]} == 0) begin
                                    state <= S_CMD;
                                end else begin
                                    bus_valid <= 1'b1;
                                    bus_write <= 1'b0;
                                    bus_addr  <= {addr[15:2], 2'b00};
                                    state     <= S_RREQ;
                                end
                            end
                            default: state <= S_CMD;
                        endcase
                    end
                end

                S_BLK_W: if (rx_valid) begin
                    bus_valid <= 1'b1;
                    bus_write <= 1'b1;
                    bus_addr  <= cur;
                    bus_wdata <= {24'b0, rx_data};
                    state     <= S_WREQ;
                end

                S_WREQ: if (bus_ready) begin
                    bus_valid <= 1'b0;
                    if (cmd == "B" && cnt != len - 1'b1) begin
                        cnt   <= cnt + 1'b1;
                        state <= S_BLK_W;
                    end else begin
                        send_buf  <= 32'("K");
                        send_left <= 3'd1;
                        state     <= S_SEND;
                    end
                end

                S_RREQ: if (bus_ready) begin
                    bus_valid <= 1'b0;
                    state     <= S_RWAIT;
                end

                S_RWAIT: if (bus_rvalid) begin
                    state <= S_SEND;
                    case (cmd)
                        "P": begin
                            send_buf  <= {8'b0, bus_rdata[15:8], bus_rdata[7:0], 8'("K")};
                            send_left <= 3'd3;
                        end
                        "D": begin
                            send_buf  <= bus_rdata >> (8 * cur[1:0]);
                            send_left <= 3'd1;
                        end
                        default: begin
                            send_buf  <= bus_rdata;
                            send_left <= 3'd4;
                        end
                    endcase
                end

                S_SEND: if (!tx_full) begin
                    send_buf  <= send_buf >> 8;
                    send_left <= send_left - 1'b1;
                    if (send_left == 3'd1) begin
                        if (cmd == "D" && cnt != len - 1'b1) begin
                            // next byte of the block: read the word holding cur + 1
                            cnt       <= cnt + 1'b1;
                            bus_valid <= 1'b1;
                            bus_write <= 1'b0;
                            bus_addr  <= (cur + 1'b1) & 16'hFFFC;
                            state     <= S_RREQ;
                        end else begin
                            state <= S_CMD;
                        end
                    end
                end

                default: state <= S_CMD;
            endcase
        end
    end

endmodule
