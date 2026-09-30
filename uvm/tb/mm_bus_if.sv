// mm_bus_if.sv -- register-bus interface between the UVM agent and mm_core.
// The driver drives on the falling edge (mid-cycle, race-free); the monitor
// samples through a clocking block at the rising edge (values just before it).
interface mm_bus_if (input logic clk);
    logic        rst_n;
    logic        bus_valid, bus_ready, bus_write, bus_rvalid;
    logic [15:0] bus_addr;
    logic [31:0] bus_wdata, bus_rdata;
    // status outputs, observed only
    logic        busy, done;
    logic [2:0]  state;
    logic [31:0] perf_compute;

    clocking mon_cb @(posedge clk);
        default input #1step;
        input rst_n, bus_valid, bus_ready, bus_write, bus_addr, bus_wdata, bus_rvalid, bus_rdata;
    endclocking
endinterface
