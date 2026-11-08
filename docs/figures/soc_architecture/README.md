# SoC Architecture, Block by Block

13 figures that grow the 4×4 systolic array (`mm_core`) into a full system-on-chip, drawn in the same style as the core register placement figure. Every page is a TikZ figure; `soc_architecture.pdf` holds all of them in order, and `png/` has one image per page.

- `00_contents`: contents, how to read the figures, reading order
- `01_soc_overview`: the whole SoC and where `mm_core` fits
- `02_cpu_pipeline`: a 5-stage RV32I pipeline, register by register
- `03_caches_mmu`: cache tag / index / offset, MESI, TLB and page walk
- `04_gpu`: shader cores, warps, SIMT, latency hiding
- `05_npu`: a full NPU around a systolic array; requantization example
- `06_interconnect`: AXI channels, VALID / READY, APB, crossbar, NoC
- `07_memory`: DRAM controller, PHY, DRAM bank, timing, bandwidth
- `08_job_flow`: one AI job end to end, interrupts, DMA, cache coherence
- `09_clock_power`: PLL, clock gating, DVFS, power domains, reset, CDC
- `10_boot_security`: secure boot, TrustZone, crypto, JTAG, FPGA configuration
- `11_peripherals`: APB, UART, SPI, I2C, GPIO, timer, watchdog
- `12_mini_soc_de10lite`: plan for a RISC-V CPU + `mm_core` on one Avalon bus
- `13_floorplan_cheatsheet`: illustrative floorplan, cheat sheet, practice questions

Numbers about this project come from `rtl/core/*.sv` and `docs/results`. Numbers about real SoCs are marked *example* or *typical*; anything not built or measured is marked *estimate* or *plan*.

Rebuild (Ubuntu, needs `tectonic` and `poppler-utils`):

```bash
cd docs/figures/soc_architecture && ./build.sh
```

All figures share `soc_style.tex` (colours, flip-flop squares, waveform macros).
