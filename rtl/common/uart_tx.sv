// uart_tx.sv
// UART transmitter, 8N1 (8 data bits, no parity, 1 stop bit), LSB first.
// See NOTES §10.
//
// Handshake: a byte is accepted on a clock edge where (valid && ready).
// Hold `valid` high with `data` stable until you see `ready` -- then it's taken.
//
// Line format:  idle(1) | start(0) | d0 d1 ... d7 | stop(1) | idle(1)

module uart_tx #(
    parameter int CLK_HZ = 50_000_000,
    parameter int BAUD   = 115_200
) (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] data,
    input  logic       valid,
    output logic       ready,     // high when idle and able to accept a byte
    output logic       tx         // serial output line
);

    // Rounded clocks per bit: 50 MHz / 115200 = 434.03 -> 434
    localparam int CLKS_PER_BIT = (CLK_HZ + BAUD / 2) / BAUD;
    localparam int CW           = $clog2(CLKS_PER_BIT);

    typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;

    state_t      state;
    logic [CW-1:0] clk_cnt;       // counts clocks within one bit
    logic [2:0]  bit_idx;         // which data bit is being sent
    logic [7:0]  shreg;           // shift register holding the byte

    wire bit_done = (clk_cnt == CLKS_PER_BIT - 1);

    assign ready = (state == IDLE);

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state   <= IDLE;
            tx      <= 1'b1;
            clk_cnt <= '0;
            bit_idx <= '0;
            shreg   <= '0;
        end else begin
            case (state)
                IDLE: begin
                    tx <= 1'b1;
                    if (valid) begin
                        shreg   <= data;
                        tx      <= 1'b0;          // start bit
                        clk_cnt <= '0;
                        state   <= START;
                    end
                end

                START: begin
                    if (bit_done) begin
                        clk_cnt <= '0;
                        bit_idx <= '0;
                        tx      <= shreg[0];      // first data bit (LSB)
                        state   <= DATA;
                    end else begin
                        clk_cnt <= clk_cnt + 1'b1;
                    end
                end

                DATA: begin
                    if (bit_done) begin
                        clk_cnt <= '0;
                        if (bit_idx == 3'd7) begin
                            tx    <= 1'b1;        // stop bit
                            state <= STOP;
                        end else begin
                            bit_idx <= bit_idx + 1'b1;
                            shreg   <= shreg >> 1;
                            tx      <= shreg[1];  // next bit
                        end
                    end else begin
                        clk_cnt <= clk_cnt + 1'b1;
                    end
                end

                STOP: begin
                    if (bit_done) begin
                        clk_cnt <= '0;
                        state   <= IDLE;
                    end else begin
                        clk_cnt <= clk_cnt + 1'b1;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
