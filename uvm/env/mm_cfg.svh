// mm_cfg.svh -- testbench configuration shared through uvm_config_db ("cfg").
class mm_cfg extends uvm_object;
    `uvm_object_utils(mm_cfg)
    int n = 4;
    int k_max = 64;
    virtual mm_bus_if vif;
    string cov_file = "";        // where mm_coverage writes its bin hits
    function new(string name = "mm_cfg");
        super.new(name);
    endfunction
endclass
