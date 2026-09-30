// mm_pkg.sv -- UVM environment for mm_core (Phase 6). See docs/vplan.md.
`include "uvm_macros.svh"

// register map (PLAN.md §6, rtl/core/mm_regs.sv)
`define MM_CTRL        16'h0000
`define MM_STATUS      16'h0004
`define MM_CFG_K       16'h0008
`define MM_INFO        16'h000C
`define MM_PERF_TOTAL  16'h0010
`define MM_PERF_IDLE   16'h001C
`define MM_PERF_MACS   16'h0020
`define MM_A_BUF       16'h1000
`define MM_B_BUF       16'h2000
`define MM_C_BUF       16'h3000

package mm_pkg;
    import uvm_pkg::*;
    `include "mm_cfg.svh"
    `include "bus_item.svh"
    `include "mm_job.svh"
    `include "bus_agent.svh"
    `include "mm_coverage.svh"
    `include "mm_scoreboard.svh"
    `include "mm_env.svh"
    `include "mm_seqs.svh"
    `include "mm_tests.svh"
endpackage
