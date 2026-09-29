# Hardware Bring-up — Accelerator on the DE10-Lite

Everything below runs on one Ubuntu 22.04 machine (simulation, Quartus, programming, host script).
The design already passes full-system simulation (`tb/test_top_de10lite.py`, N = 4 and 8).

## 0. One-time setup

```bash
# Simulators + Python (no sudo needed; already done on this machine)
CONDA_NO_PLUGINS=true CONDA_SOLVER=classic conda create -y -n fpga -c conda-forge \
    --override-channels python=3.12 iverilog verilator
conda activate fpga
pip install -r requirements.txt

# Serial port access for host.py (log out and back in afterwards)
sudo usermod -aG dialout $USER

# USB-Blaster access without root
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="09fb", ATTR{idProduct}=="6010|6810", MODE="0666"' \
    | sudo tee /etc/udev/rules.d/51-usbblaster.rules
sudo udevadm control --reload && sudo udevadm trigger
```

**Quartus Prime Lite** (Intel blocks scripted downloads, so use a browser):
1. Intel FPGA Software Download Center → *Quartus Prime Lite Edition*, Linux.
   Download `QuartusLiteSetup-<ver>-linux.run` **and** the MAX 10 device file `max10-<ver>.qdz`
   into the same folder.
2. `chmod +x QuartusLiteSetup-*.run && ./QuartusLiteSetup-*.run` → install to `~/intelFPGA_lite/<ver>`
   (Questa is not needed; untick it to save space).
3. `echo 'export PATH=$HOME/intelFPGA_lite/<ver>/quartus/bin:$PATH' >> ~/.bashrc` and open a new shell.

## 1. Check the board is visible

```bash
lsusb | grep 09fb        # "Altera Blaster" -> board's USB-Blaster is connected
jtagconfig               # 1) USB-Blaster [1-x]   031050DD   10M50DA(.|ES)/10M50DC
ls /dev/ttyUSB*          # USB-UART adapter (CP2102 / FT232) -> /dev/ttyUSB0
```

If `jtagconfig` shows no cable: re-plug after the udev rule, or run `killall jtagd` and retry.

## 2. Wiring (same as foundations/04_uart_echo)

| DE10-Lite GPIO header | Adapter |
|---|---|
| pin 1 (GPIO[0], FPGA TX) | RXD |
| pin 2 (GPIO[1], FPGA RX) | TXD |
| pin 12 (GND) | GND |

Adapter jumper at **3.3 V**. Do not connect the adapter's VCC.

Tip: first program `foundations/04_uart_echo` and run `python host/uart_echo_test.py`
— 0 errors proves the wiring before debugging the accelerator.

## 3. Build and program (N = 4 first)

```bash
cd quartus
quartus_sh --flow compile top_de10lite
quartus_pgm -m jtag -o "p;output_files/top_de10lite.sof"
```

Check after compile (`output_files/top_de10lite.fit.summary` and `.sta.summary`):
- Timing: setup slack ≥ 0 for `clk50` (Slow 1200mV 85C model).
- Resources: embedded 9-bit multipliers ≈ N² (16 for N=4, 64 for N=8).

Copy both summaries into `docs/results/` (e.g. `fit_n4.summary`, `sta_n4.summary`).

On the board after programming: LEDR[9] blinks at 1 Hz, all other LEDs off, HEX shows 000000.

## 4. Run the tests

```bash
python host/host.py --tests 100             # N=4: expect "PASS"
```

After a run HEX5..HEX0 shows the last cycle count (K + 2N in hex) and LEDR[8] is on.

## 5. Scale to N = 8

1. In `tools/gen_quartus.py`, change `{"N": 4, ...}` to `{"N": 8, ...}` for the `"."` project.
2. `python3 tools/gen_quartus.py`, then recompile and reprogram as in step 3.
3. `python host/host.py --tests 1000` → PASS.
4. `python host/host.py --bench` → `docs/results/bench_n8.csv` + two plots.

## 6. If something fails

| Symptom | Likely cause / check |
|---|---|
| `timeout: expected 3 bytes, got 0` on ping | TX/RX not crossed, no GND, wrong port, .sof not loaded, KEY0 held |
| `Permission denied: /dev/ttyUSB0` | Not in `dialout` group yet (log out/in) — or `sudo chmod 666 /dev/ttyUSB0` for today |
| LEDR[5] on | UART framing errors → baud mismatch or noisy wiring |
| LEDR[6] on | FPGA received an unknown command / bad K (bytes got out of sync) |
| LEDR[7] on | Host stopped mid-command for > 100 ms; parser recovered by itself |
| Wrong C values but cycles OK | Run sim again with the same matrices; check `tb/test_mm_core.py` passes |
| Timing fails at N=8 | Register the multiplier output in `pe.sv` (2-stage PE); update the cycle formula |

Press KEY0 to reset the design at any time, then rerun `host.py`.
