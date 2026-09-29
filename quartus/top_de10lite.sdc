# 50 MHz board clock -> 20 ns period
create_clock -name clk50 -period 20.000 [get_ports MAX10_CLK1_50]
derive_clock_uncertainty

# Buttons, switches, LEDs, HEX and UART are slow/asynchronous: don't time them.
set_false_path -from [get_ports {KEY[*] SW[*] UART_RXD}]
set_false_path -to   [get_ports {LEDR[*] HEX*[*] UART_TXD}]
