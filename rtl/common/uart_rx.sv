// uart_rx.sv
// UART receiver, 8N1, LSB first. See NOTES §10.
//
// Method: after the falling edge of the start bit, wait HALF a bit period to
// reach the middle of the start bit, confirm it is still 0, then sample every
// full bit period -- i.e. always in the middle of each bit, where the signal
// is most stable.
//
// Outputs:
//   valid     - 1-cycle pulse when `data` holds a newly received byte
//   frame_err - 1-cycle pulse when the stop bit was 0 (byte discarded)

module uart_rx #(
    parameter int CLK_HZ = 50_000_000,
    parameter int BAUD   = 115_200
) (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       rx,          // asynchronous serial input (from pin)
    output logic [7:0] data,
    output logic       valid,
    output logic       frame_err
);

    localparam int CLKS_PER_BIT = (CLK_HZ + BAUD / 2) / BAUD;
    localparam int HALF_BIT     = CLKS_PER_BIT / 2;
    localparam int CW           = $clog2(CLKS_PER_BIT);

    typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;

    // The RX pin is asynchronous to our clock -> synchronize first.
    logic rx_s;
    sync_2ff #(.WIDTH(1), .INIT(1'b1)) u_sync (.clk(clk), .d(rx), .q(rx_s));

    state_t        state;
    logic [CW-1:0] clk_cnt;
    logic [2:0]    bit_idx;
    logic [7:0]    shreg;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state     <= IDLE;
            clk_cnt   <= '0;
            bit_idx   <= '0;
            shreg     <= '0;
            data      <= '0;
            valid     <= 1'b0;
            frame_err <= 1'b0;
        end else begin
            valid     <= 1'b0;   // default: pulses last one cycle
            frame_err <= 1'b0;

            case (state)
                IDLE: begin
                    clk_cnt <= '0;
                    if (rx_s == 1'b0)             // falling edge = start bit
                        state <= START;
                end

                START: begin
                    if (clk_cnt == HALF_BIT - 1) begin
                        clk_cnt <= '0;
                        bit_idx <= '0;
                        // Still low in the middle? Real start bit. Else a glitch.
                        if (rx_s == 1'b0) state <= DATA;
                        else              state <= IDLE;
                    end else begin
                        clk_cnt <= clk_cnt + 1'b1;
                    end
                end

                DATA: begin
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt <= '0;
                        shreg   <= {rx_s, shreg[7:1]};   // LSB arrives first
                        if (bit_idx == 3'd7)
                            state <= STOP;
                        else
                            bit_idx <= bit_idx + 1'b1;
                    end else begin
                        clk_cnt <= clk_cnt + 1'b1;
                    end
                end

                STOP: begin
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        // We are in the middle of the stop bit; return to IDLE
                        // now so we are ready early for the next start bit.
                        clk_cnt <= '0;
                        state   <= IDLE;
                        if (rx_s == 1'b1) begin
                            data  <= shreg;
                            valid <= 1'b1;
                        end else begin
                            frame_err <= 1'b1;
                        end
                    end else begin
                        clk_cnt <= clk_cnt + 1'b1;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
