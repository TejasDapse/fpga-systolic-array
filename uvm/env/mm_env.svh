// mm_env.svh -- agent + scoreboard + coverage.
class mm_env extends uvm_env;
    `uvm_component_utils(mm_env)
    bus_agent     agent;
    mm_scoreboard sb;
    mm_coverage   cov;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        agent = bus_agent::type_id::create("agent", this);
        sb    = mm_scoreboard::type_id::create("sb", this);
        cov   = mm_coverage::type_id::create("cov", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        agent.mon.ap.connect(sb.analysis_export);
        sb.cov = cov;
    endfunction
endclass
