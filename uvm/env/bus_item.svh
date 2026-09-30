// bus_item.svh -- one register-bus transaction (or a hard reset request).
//   driver : executes it; for reads it fills `data` with bus_rdata
//   monitor: publishes accepted transactions with the accept edge in `cycle`
class bus_item extends uvm_sequence_item;
    `uvm_object_utils(bus_item)
    typedef enum {BUS, RESET} kind_e;

    rand kind_e       kind;
    rand bit          write;
    rand bit [15:0]   addr;
    rand bit [31:0]   data;           // wdata for writes, rdata for reads
    longint unsigned  cycle;          // monitor: rising-edge index of the accept

    constraint c_kind { soft kind == BUS; }

    function new(string name = "bus_item");
        super.new(name);
    endfunction

    function string convert2string();
        if (kind == RESET) return $sformatf("@%0d RESET", cycle);
        return $sformatf("@%0d %s [%04h] %08h", cycle, write ? "WR" : "RD", addr, data);
    endfunction
endclass
