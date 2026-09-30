// tb_top.sv -- UVM testbench top: clock, interface, DUT, assertions, run_test.
//   +TEST=<uvm test name>  (default mm_random_test)   +JOBS=<n>   +COVFILE=<path>
`include "uvm_macros.svh"

module tb_top;
    import uvm_pkg::*;
    import mm_pkg::*;

    parameter int N     = 4;
    parameter int K_MAX = 64;

    logic clk = 0;
    always #10 clk = ~clk;                          // 50 MHz

    mm_bus_if bif (clk);

    mm_core #(.N(N), .K_MAX(K_MAX)) dut (
        .clk(clk), .rst_n(bif.rst_n),
        .bus_valid(bif.bus_valid), .bus_ready(bif.bus_ready), .bus_write(bif.bus_write),
        .bus_addr(bif.bus_addr), .bus_wdata(bif.bus_wdata),
        .bus_rvalid(bif.bus_rvalid), .bus_rdata(bif.bus_rdata),
        .busy(bif.busy), .done(bif.done), .state(bif.state), .perf_compute(bif.perf_compute)
    );

    mm_sva #(.N(N)) sva (
        .clk(clk), .rst_n(bif.rst_n), .soft_reset(dut.u_regs.soft_reset),
        .bus_valid(bif.bus_valid), .bus_ready(bif.bus_ready), .bus_write(bif.bus_write),
        .bus_rvalid(bif.bus_rvalid), .bus_addr(bif.bus_addr), .bus_wdata(bif.bus_wdata),
        .busy(bif.busy), .done(bif.done), .state(bif.state)
    );

    initial begin
        mm_cfg cfg = new("cfg");
        string test;
        cfg.n = N;
        cfg.k_max = K_MAX;
        cfg.vif = bif;
        void'($value$plusargs("COVFILE=%s", cfg.cov_file));
        uvm_config_db #(mm_cfg)::set(null, "*", "cfg", cfg);
        if (!$value$plusargs("TEST=%s", test)) test = "mm_random_test";
        run_test(test);                             // UVM_NO_DPI: no +UVM_TESTNAME
    end
endmodule
