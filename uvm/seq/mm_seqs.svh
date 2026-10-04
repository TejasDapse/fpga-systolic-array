// mm_seqs.svh -- sequence library. Sequences only create stimulus; every read
// they issue is checked by the scoreboard (which predicts it independently).

class mm_base_seq extends uvm_sequence #(bus_item);
    `uvm_object_utils(mm_base_seq)
    mm_cfg cfg;

    function new(string name = "mm_base_seq");
        super.new(name);
    endfunction

    task pre_body();
        if (!uvm_config_db #(mm_cfg)::get(m_sequencer, "", "cfg", cfg))
            `uvm_fatal("CFG", "no mm_cfg in config_db")
    endtask

    task wr(bit [15:0] addr, bit [31:0] data);
        bus_item it = bus_item::type_id::create("wr");
        start_item(it);
        it.kind = bus_item::BUS;  it.write = 1;  it.addr = addr;  it.data = data;
        finish_item(it);
    endtask

    task rd(bit [15:0] addr, output bit [31:0] data);
        bus_item it = bus_item::type_id::create("rd");
        start_item(it);
        it.kind = bus_item::BUS;  it.write = 0;  it.addr = addr;
        finish_item(it);
        data = it.data;
    endtask

    task hard_reset();
        bus_item it = bus_item::type_id::create("rst");
        start_item(it);
        it.kind = bus_item::RESET;
        finish_item(it);
    endtask

    // pin_k / pin_kind: the caller adds its own inline constraint on k / kind,
    // so switch off the matching distribution (a dist is a hard constraint).
    function mm_job new_job(bit pin_k = 0, bit pin_kind = 0);
        mm_job j = mm_job::type_id::create("job");
        j.n = cfg.n;
        j.k_max = cfg.k_max;
        if (pin_k)    j.c_k_dist.constraint_mode(0);
        if (pin_kind) j.c_kind_dist.constraint_mode(0);
        return j;
    endfunction

    task load(mm_job j);
        wr(`MM_CFG_K, j.k);
        for (int i = 0; i < cfg.n; i++)
            for (int kk = 0; kk < j.k; kk++)
                wr(`MM_A_BUF + i * cfg.k_max + kk, j.a[i * j.k + kk]);
        foreach (j.b[x]) wr(`MM_B_BUF + x, j.b[x]);
    endtask

    task wait_done(int max_polls = 1000);
        bit [31:0] s;
        repeat (max_polls) begin
            rd(`MM_STATUS, s);
            if (s[1]) return;
        end
        `uvm_error("SEQ", "DONE never set")
    endtask

    task read_results();
        bit [31:0] d;
        for (int i = 0; i < cfg.n * cfg.n; i++) rd(`MM_C_BUF + 4 * i, d);
        for (int r = `MM_PERF_TOTAL; r <= `MM_PERF_MACS; r += 4) rd(r[15:0], d);
    endtask

    task run_job(mm_job j, bit do_load = 1);
        if (do_load) load(j);
        wr(`MM_CTRL, 1);
        wait_done();
        read_results();
    endtask
endclass

// N random jobs (constrained K and operand patterns).
class mm_random_seq extends mm_base_seq;
    `uvm_object_utils(mm_random_seq)
    int unsigned jobs = 50;
    function new(string name = "mm_random_seq");
        super.new(name);
    endfunction
    task body();
        repeat (jobs) begin
            mm_job j = new_job();
            if (!j.randomize()) `uvm_fatal("RAND", "mm_job randomize failed")
            run_job(j);
        end
    endtask
endclass

// Every operand pattern at every K class (identity, zeros, all -128, all 127,
// -128 x 127, random) x (K = 1, 2N-2, 2N-1, mid, K_MAX).
class mm_edge_values_seq extends mm_base_seq;
    `uvm_object_utils(mm_edge_values_seq)
    function new(string name = "mm_edge_values_seq");
        super.new(name);
    endfunction
    task body();
        int ks[5] = '{1, 2 * cfg.n - 2, 2 * cfg.n - 1, cfg.k_max / 2, cfg.k_max};
        for (int kd = 0; kd <= int'(mm_job::IDENTITY); kd++)
            foreach (ks[i]) begin
                mm_job         j = new_job(.pin_k(1), .pin_kind(1));
                int unsigned   want_k = ks[i];
                mm_job::kind_e want_kind = mm_job::kind_e'(kd);
                if (!j.randomize() with { k == want_k; kind == want_kind; })
                    `uvm_fatal("RAND", "mm_job randomize failed")
                run_job(j);
            end
    endtask
endclass

// Re-run without reloading, and START immediately after DONE.
class mm_back_to_back_seq extends mm_base_seq;
    `uvm_object_utils(mm_back_to_back_seq)
    function new(string name = "mm_back_to_back_seq");
        super.new(name);
    endfunction
    task body();
        repeat (5) begin
            mm_job j = new_job();
            if (!j.randomize()) `uvm_fatal("RAND", "mm_job randomize failed")
            run_job(j);
            run_job(j, 0);                   // same buffers again
            wr(`MM_CTRL, 1);                 // START right after the previous DONE ...
            wr(`MM_CTRL, 1);                 // ... and once more while busy (ignored)
            wait_done();
            read_results();
        end
    endtask
endclass

// While a job runs: START again, write A/B, change CFG_K, read C and counters.
class mm_busy_seq extends mm_base_seq;
    `uvm_object_utils(mm_busy_seq)
    function new(string name = "mm_busy_seq");
        super.new(name);
    endfunction
    task body();
        bit [31:0] d;
        repeat (5) begin
            mm_job j = new_job(.pin_k(1));
            if (!j.randomize() with { k >= 16; }) `uvm_fatal("RAND", "mm_job randomize failed")
            load(j);
            wr(`MM_CTRL, 1);
            wr(`MM_CTRL, 1);                            // ignored
            wr(`MM_A_BUF, 8'h55);                       // ignored
            wr(`MM_B_BUF + 1, 8'h66);                   // ignored
            rd(`MM_C_BUF, d);                           // partial sums: not checked
            rd(`MM_PERF_TOTAL, d);                      // running: not checked
            rd(`MM_STATUS, d);
            wr(`MM_CFG_K, j.k == 1 ? 2 : j.k - 1);      // CFG_K is not busy-protected
            wait_done();
            read_results();                             // must equal the original job
            wr(`MM_CFG_K, j.k);
            run_job(j, 0);                              // rerun without reload: the writes
        end                                             // made while busy must not show up
    endtask
endclass

// Reset in the middle of a job, at a random point of CLEAR/COMPUTE/DRAIN,
// then check reset values and that the next job is correct.
class mm_reset_seq extends mm_base_seq;
    `uvm_object_utils(mm_reset_seq)
    bit use_hard_reset = 0;
    function new(string name = "mm_reset_seq");
        super.new(name);
    endfunction
    task body();
        bit [31:0] d;
        repeat (8) begin
            mm_job j = new_job(.pin_k(1));
            if (!j.randomize() with { k >= 8; }) `uvm_fatal("RAND", "mm_job randomize failed")
            load(j);
            wr(`MM_CTRL, 1);
            repeat ($urandom_range(0, j.k / 2)) rd(`MM_STATUS, d);
            if (use_hard_reset) hard_reset();
            else                wr(`MM_CTRL, 2);
            rd(`MM_STATUS, d);
            rd(`MM_CFG_K, d);
            read_results();                             // C and counters are zero
            run_job(j);                                 // reload (CFG_K was reset) + rerun
        end
    endtask
endclass

// Register-map corners: INFO, bad K values, unmapped / aliased / out-of-range.
class mm_reg_access_seq extends mm_base_seq;
    `uvm_object_utils(mm_reg_access_seq)
    function new(string name = "mm_reg_access_seq");
        super.new(name);
    endfunction
    task body();
        bit [31:0] d;
        bit [31:0] bad_k[4] = '{0, cfg.k_max + 1, 255, 32'hFFFF_FFFF};
        bit [15:0] unmapped[7] = '{16'h0024, 16'h0040, 16'h00FC,       // register page holes
                                   16'h1000, 16'h2000,                 // A/B are write-only
                                   16'h4000, 16'hF000};                // no region
        rd(`MM_INFO, d);
        rd(`MM_CFG_K, d);
        foreach (bad_k[i]) begin
            wr(`MM_CFG_K, bad_k[i]);                    // ignored
            rd(`MM_CFG_K, d);
        end
        wr(`MM_CFG_K, 3);
        rd(`MM_CFG_K, d);
        foreach (unmapped[i]) rd(unmapped[i], d);
        rd(`MM_C_BUF + 4 * cfg.n * cfg.n, d);           // just past C
        rd(16'h0104, d);                                // aliases STATUS
        wr(`MM_A_BUF + cfg.n * cfg.k_max, 8'h11);       // row N: out of range
        wr(`MM_B_BUF + cfg.k_max * cfg.n, 8'h22);       // row K_MAX: out of range
        wr(16'h4000, 32'h1234_5678);                    // unmapped region
        // top of the 4 KB windows (address bits 10/11; all out of range)
        wr(16'h1FFF, 8'h33);  wr(16'h1C00, 8'h33);  wr(16'h1400, 8'h33);
        wr(16'h2FFF, 8'h44);  wr(16'h2C00, 8'h44);  wr(16'h2800, 8'h44);
        rd(16'h3FFC, d);  rd(16'h3C00, d);
        rd(16'h0C08, d);                                // register page alias of CFG_K
        rd(`MM_PERF_IDLE, d);
        rd(`MM_PERF_IDLE, d);
    endtask
endclass

// Everything, for coverage closure in the regression.
class mm_all_seq extends mm_base_seq;
    `uvm_object_utils(mm_all_seq)
    int unsigned jobs = 50;
    function new(string name = "mm_all_seq");
        super.new(name);
    endfunction
    task body();
        mm_reg_access_seq   s_reg  = mm_reg_access_seq::type_id::create("s_reg");
        mm_edge_values_seq  s_edge = mm_edge_values_seq::type_id::create("s_edge");
        mm_back_to_back_seq s_b2b  = mm_back_to_back_seq::type_id::create("s_b2b");
        mm_busy_seq         s_busy = mm_busy_seq::type_id::create("s_busy");
        mm_reset_seq        s_soft = mm_reset_seq::type_id::create("s_soft");
        mm_reset_seq        s_hard = mm_reset_seq::type_id::create("s_hard");
        mm_random_seq       s_rand = mm_random_seq::type_id::create("s_rand");
        s_hard.use_hard_reset = 1;
        s_rand.jobs = jobs;
        s_reg.start(m_sequencer);
        s_edge.start(m_sequencer);
        s_b2b.start(m_sequencer);
        s_busy.start(m_sequencer);
        s_soft.start(m_sequencer);
        s_hard.start(m_sequencer);
        s_rand.start(m_sequencer);
    endtask
endclass
