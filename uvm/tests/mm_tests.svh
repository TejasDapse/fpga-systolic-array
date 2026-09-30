// mm_tests.svh -- tests: build the env, reset the DUT, run one sequence.
// Select with +TEST=<name> (tb_top); +JOBS=<n> sets the random job count.

class mm_base_test extends uvm_test;
    `uvm_component_utils(mm_base_test)
    mm_env env;
    mm_cfg cfg;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        if (!uvm_config_db #(mm_cfg)::get(this, "", "cfg", cfg))
            `uvm_fatal("CFG", "no mm_cfg in config_db")
        env = mm_env::type_id::create("env", this);
    endfunction

    virtual function mm_base_seq make_seq();
        return null;
    endfunction

    task run_phase(uvm_phase phase);
        mm_base_seq seq = make_seq();
        phase.raise_objection(this);
        begin                                           // initial hard reset
            bus_item it = bus_item::type_id::create("rst");
            it.kind = bus_item::RESET;
            env.agent.sqr.execute_item(it);
        end
        if (seq != null) seq.start(env.agent.sqr);
        phase.drop_objection(this);
    endtask

    function int unsigned jobs_arg(int unsigned dflt);
        int unsigned j;
        return $value$plusargs("JOBS=%d", j) ? j : dflt;
    endfunction

    function void report_phase(uvm_phase phase);
        uvm_report_server rs = uvm_report_server::get_server();
        int errs = rs.get_severity_count(UVM_ERROR) + rs.get_severity_count(UVM_FATAL);
        $display("\n*** %s: %s (N=%0d) ***\n", get_type_name(), errs == 0 ? "TEST PASSED" : "TEST FAILED", cfg.n);
    endfunction
endclass

class mm_random_test extends mm_base_test;
    `uvm_component_utils(mm_random_test)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function mm_base_seq make_seq();
        mm_random_seq s = mm_random_seq::type_id::create("s");
        s.jobs = jobs_arg(200);
        return s;
    endfunction
endclass

class mm_edge_values_test extends mm_base_test;
    `uvm_component_utils(mm_edge_values_test)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function mm_base_seq make_seq(); return mm_edge_values_seq::type_id::create("s"); endfunction
endclass

class mm_back_to_back_test extends mm_base_test;
    `uvm_component_utils(mm_back_to_back_test)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function mm_base_seq make_seq(); return mm_back_to_back_seq::type_id::create("s"); endfunction
endclass

class mm_start_while_busy_test extends mm_base_test;
    `uvm_component_utils(mm_start_while_busy_test)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function mm_base_seq make_seq(); return mm_busy_seq::type_id::create("s"); endfunction
endclass

class mm_soft_reset_test extends mm_base_test;
    `uvm_component_utils(mm_soft_reset_test)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function mm_base_seq make_seq(); return mm_reset_seq::type_id::create("s"); endfunction
endclass

class mm_hard_reset_test extends mm_base_test;
    `uvm_component_utils(mm_hard_reset_test)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function mm_base_seq make_seq();
        mm_reset_seq s = mm_reset_seq::type_id::create("s");
        s.use_hard_reset = 1;
        return s;
    endfunction
endclass

class mm_reg_access_test extends mm_base_test;
    `uvm_component_utils(mm_reg_access_test)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function mm_base_seq make_seq(); return mm_reg_access_seq::type_id::create("s"); endfunction
endclass

class mm_all_test extends mm_base_test;
    `uvm_component_utils(mm_all_test)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function mm_base_seq make_seq();
        mm_all_seq s = mm_all_seq::type_id::create("s");
        s.jobs = jobs_arg(50);
        return s;
    endfunction
endclass
