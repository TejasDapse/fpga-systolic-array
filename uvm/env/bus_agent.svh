// bus_agent.svh -- driver, monitor and agent for the mm_core register bus.

typedef uvm_sequencer #(bus_item) bus_sequencer;

// Drives on falling edges: a request is presented mid-cycle and is accepted at
// the next rising edge on which bus_ready is high. Holds valid/addr/data stable
// until accepted (checked by SVA). Reads complete one cycle after the accept.
class bus_driver extends uvm_driver #(bus_item);
    `uvm_component_utils(bus_driver)
    virtual mm_bus_if vif;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        mm_cfg cfg;
        if (!uvm_config_db #(mm_cfg)::get(this, "", "cfg", cfg))
            `uvm_fatal("CFG", "no mm_cfg in config_db")
        vif = cfg.vif;
    endfunction

    task run_phase(uvm_phase phase);
        vif.bus_valid <= 1'b0;
        vif.bus_write <= 1'b0;
        vif.bus_addr  <= '0;
        vif.bus_wdata <= '0;
        vif.rst_n     <= 1'b0;
        forever begin
            seq_item_port.get_next_item(req);
            if (req.kind == bus_item::RESET) do_reset();
            else                             do_access(req);
            seq_item_port.item_done();
        end
    endtask

    task do_reset();
        @(negedge vif.clk);
        vif.bus_valid <= 1'b0;
        vif.rst_n     <= 1'b0;
        repeat (3) @(negedge vif.clk);
        vif.rst_n     <= 1'b1;
        @(negedge vif.clk);
    endtask

    task do_access(bus_item it);
        bit ready;
        @(negedge vif.clk);
        vif.bus_valid <= 1'b1;
        vif.bus_write <= it.write;
        vif.bus_addr  <= it.addr;
        vif.bus_wdata <= it.write ? it.data : $urandom;   // wdata is don't-care on reads
        do begin
            #1;                                            // let the drive settle
            ready = vif.bus_ready;
            @(negedge vif.clk);
        end while (!ready);
        vif.bus_valid <= 1'b0;
        if (!it.write) it.data = vif.bus_rdata;            // rvalid cycle (SVA checks it)
    endtask
endclass

// Publishes every accepted transaction, stamped with its accept edge, and a
// RESET item for each hard reset. Reads are published when rvalid arrives.
class bus_monitor extends uvm_monitor;
    `uvm_component_utils(bus_monitor)
    virtual mm_bus_if vif;
    uvm_analysis_port #(bus_item) ap;

    function new(string name, uvm_component parent);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
        mm_cfg cfg;
        if (!uvm_config_db #(mm_cfg)::get(this, "", "cfg", cfg))
            `uvm_fatal("CFG", "no mm_cfg in config_db")
        vif = cfg.vif;
    endfunction

    task run_phase(uvm_phase phase);
        longint unsigned edge_idx = 0;
        bus_item pending_rd;
        bit in_reset = 0;
        forever begin
            @(vif.mon_cb);
            edge_idx++;
            if (vif.mon_cb.rst_n !== 1'b1) begin
                if (!in_reset) begin
                    bus_item r = bus_item::type_id::create("reset");
                    r.kind  = bus_item::RESET;
                    r.cycle = edge_idx;
                    ap.write(r);
                end
                in_reset   = 1;
                pending_rd = null;
                continue;
            end
            in_reset = 0;
            if (pending_rd != null) begin                  // read accepted last edge
                pending_rd.data = vif.mon_cb.bus_rdata;
                ap.write(pending_rd);
                pending_rd = null;
            end
            if (vif.mon_cb.bus_valid && vif.mon_cb.bus_ready) begin
                bus_item t = bus_item::type_id::create("t");
                t.kind  = bus_item::BUS;
                t.write = vif.mon_cb.bus_write;
                t.addr  = vif.mon_cb.bus_addr;
                t.data  = vif.mon_cb.bus_wdata;
                t.cycle = edge_idx;
                if (t.write) ap.write(t);
                else         pending_rd = t;
            end
        end
    endtask
endclass

class bus_agent extends uvm_agent;
    `uvm_component_utils(bus_agent)
    bus_sequencer sqr;
    bus_driver    drv;
    bus_monitor   mon;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        sqr = bus_sequencer::type_id::create("sqr", this);
        drv = bus_driver::type_id::create("drv", this);
        mon = bus_monitor::type_id::create("mon", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction
endclass
