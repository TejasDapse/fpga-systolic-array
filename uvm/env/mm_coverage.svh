// mm_coverage.svh -- functional coverage model (vplan: docs/vplan.md).
//
// Note: Verilator 5.052 parses covergroups but does not implement coverpoints yet,
// so the model is written as explicit bins: same structure as a covergroup
//   cp_k      : K = 1 | 2..2N-2 | 2N-1 (fill/drain boundary) | 2N..K_MAX-1 | K_MAX
//   cp_kind   : operand pattern classified from the data actually loaded
//   cp_values : corner values -128 / 0 / 127 present in a job
//   x_k_kind  : cross cp_k x cp_kind
//   scenario  : protocol / control corner cases, hit by the scoreboard
// Bin hits go to cfg.cov_file so regressions can merge them (uvm/regress.py).
class mm_coverage extends uvm_component;
    `uvm_component_utils(mm_coverage)

    static const string K_BINS[5]    = '{"k_1", "k_below_2n_1", "k_eq_2n_1", "k_mid", "k_max"};
    static const string KIND_BINS[6] = '{"random", "zeros", "all_min", "all_max", "min_max", "identity"};
    static const string VAL_BINS[3]  = '{"has_min", "has_zero", "has_max"};
    static const string SCEN_BINS[11] = '{
        "back_to_back", "start_while_busy", "buffer_write_while_busy", "cfg_k_invalid",
        "soft_reset_while_busy", "hard_reset_while_busy", "status_saw_busy",
        "c_read_while_busy", "perf_read_while_busy", "buffer_write_out_of_range",
        "c_read_out_of_range"};

    mm_cfg cfg;
    int unsigned hits[string];          // every bin, pre-created with 0

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        if (!uvm_config_db #(mm_cfg)::get(this, "", "cfg", cfg))
            `uvm_fatal("CFG", "no mm_cfg in config_db")
        foreach (K_BINS[i])    hits[{"cp_k.", K_BINS[i]}] = 0;
        foreach (KIND_BINS[i]) hits[{"cp_kind.", KIND_BINS[i]}] = 0;
        foreach (VAL_BINS[i])  hits[{"cp_values.", VAL_BINS[i]}] = 0;
        foreach (K_BINS[i])
            foreach (KIND_BINS[j]) hits[{"x_k_kind.", K_BINS[i], "__", KIND_BINS[j]}] = 0;
        foreach (SCEN_BINS[i]) hits[{"scenario.", SCEN_BINS[i]}] = 0;
    endfunction

    function void hit(string scenario);
        string key = {"scenario.", scenario};
        if (!hits.exists(key)) `uvm_fatal("COV", {"unknown scenario bin ", scenario})
        hits[key]++;
    endfunction

    function string k_bin(int k);
        int n = cfg.n;
        if (k == 1)             return K_BINS[0];
        if (k == cfg.k_max)     return K_BINS[4];
        if (k < 2 * n - 1)      return K_BINS[1];
        if (k == 2 * n - 1)     return K_BINS[2];
        return K_BINS[3];
    endfunction

    // Classify from the loaded data, not from what the sequence intended.
    function string kind_bin(int k, input byte a[], input byte b[]);
        bit a0 = 1, b0 = 1, amin = 1, bmin = 1, amax = 1, bmax = 1, bmax_only = 1, ident = 1;
        foreach (a[x]) begin
            a0 &= (a[x] == 0);  amin &= (a[x] == -128);  amax &= (a[x] == 127);
            ident &= (a[x] == ((x / k == x % k) ? 1 : 0));
        end
        foreach (b[x]) begin
            b0 &= (b[x] == 0);  bmin &= (b[x] == -128);  bmax &= (b[x] == 127);
        end
        if (a0 && b0)     return "zeros";
        if (amin && bmin) return "all_min";
        if (amax && bmax) return "all_max";
        if (amin && bmax) return "min_max";
        if (ident)        return "identity";
        return "random";
    endfunction

    function void sample_job(int k, input byte a[], input byte b[], bit back_to_back);
        string kb = k_bin(k), kd = kind_bin(k, a, b);
        bit has_min = 0, has_zero = 0, has_max = 0;
        foreach (a[x]) begin has_min |= a[x] == -128; has_zero |= a[x] == 0; has_max |= a[x] == 127; end
        foreach (b[x]) begin has_min |= b[x] == -128; has_zero |= b[x] == 0; has_max |= b[x] == 127; end
        hits[{"cp_k.", kb}]++;
        hits[{"cp_kind.", kd}]++;
        hits[{"x_k_kind.", kb, "__", kd}]++;
        if (has_min)  hits["cp_values.has_min"]++;
        if (has_zero) hits["cp_values.has_zero"]++;
        if (has_max)  hits["cp_values.has_max"]++;
        if (back_to_back) hit("back_to_back");
    endfunction

    function real percent(string prefix, output int covered, output int total);
        covered = 0;  total = 0;
        foreach (hits[key])
            if (prefix == "" || key.substr(0, prefix.len() - 1) == prefix) begin
                total++;
                if (hits[key] > 0) covered++;
            end
        return total ? 100.0 * covered / total : 0.0;
    endfunction

    function void report_phase(uvm_phase phase);
        string groups[5] = '{"cp_k.", "cp_kind.", "cp_values.", "x_k_kind.", "scenario."};
        string msg = "\n  coverage group      covered/total\n";
        int c, t, fd;
        foreach (groups[g]) begin
            real p = percent(groups[g], c, t);
            msg = {msg, $sformatf("  %-18s %4d/%-4d %6.1f%%\n", groups[g], c, t, p)};
        end
        begin
            real p = percent("", c, t);
            msg = {msg, $sformatf("  %-18s %4d/%-4d %6.1f%%", "TOTAL", c, t, p)};
        end
        foreach (hits[key]) if (hits[key] == 0) msg = {msg, "\n    not hit: ", key};
        `uvm_info("COV", msg, UVM_LOW)
        if (cfg.cov_file != "") begin
            fd = $fopen(cfg.cov_file, "w");
            foreach (hits[key]) $fwrite(fd, "%s %0d\n", key, hits[key]);
            $fclose(fd);
        end
    endfunction
endclass
