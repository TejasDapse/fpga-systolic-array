# Phase 1 — Hardware Bring-up Results

Machine: <Ubuntu version> · Quartus: <version> · Date: <YYYY-MM-DD>

## Pin check vs Terasic System Builder
- [ ] All pins match `tools/gen_quartus.py`  (list any corrections here)

## Compile results (from `tools/build.sh all`)

| Design | Logic elements | Registers | Memory bits | Fmax (MHz) | Worst slack (ns) | Timing met? |
|---|---|---|---|---|---|---|
| 01_switch_led | | | | n/a (no clock) | | |
| 02_blinky | | | | | | |
| 03_hex_counter | | | | | | |
| 04_uart_echo | | | | | | |

## Board checks

| Design | Works as expected? | Notes |
|---|---|---|
| 01_switch_led | | |
| 02_blinky | | |
| 03_hex_counter | | |
| 04_uart_echo (screen) | | |
| 04_uart_echo (`uart_echo_test.py --count 10000`) | | bytes / errors / B/s |
