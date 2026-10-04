// mm_scoreboard.svh -- predicts every register read from the monitored bus traffic.
//
// Independent of the sequences: it rebuilds the architectural state (CFG_K,
// A/B RAMs, job timing) from what was *accepted* on the bus, so any stimulus
// is checked. Expected C and perf counters come from the C++ model via DPI-C.
//
// Timing model (edge = rising-edge index of the accept, see bus_monitor):
//   START accepted at edge s (not busy)  ->  BUSY for accepts at s+1 .. s+K+2N+1
//   DONE visible from s+K+2N+2; C and counters final from then on.
// Reads while BUSY: STATUS is checked exactly, C and counters are skipped.

// Fixed-size arrays (N <= 16, K_MAX <= 64) map to plain C pointers; Verilator
// does not pass dynamic arrays to DPI open arrays yet.
localparam int MM_MAX_AB = 16 * 64, MM_MAX_C = 16 * 16;
typedef byte mm_ab_t[MM_MAX_AB];
typedef int  mm_c_t[MM_MAX_C];
import "DPI-C" function void mm_ref_dpi(input int n, input int k,
                                        input mm_ab_t a, input mm_ab_t b, output mm_c_t c);
import "DPI-C" function int unsigned mm_perf_dpi(input int n, input int k, input int which);

class mm_scoreboard extends uvm_subscriber #(bus_item);
    `uvm_component_utils(mm_scoreboard)

    mm_cfg       cfg;
    mm_coverage  cov;
    int          n, k_max, kw, lw;

    // architectural state
    int unsigned cfg_k;
    byte         a_mem[], b_mem[];
    bit          a_wr[], b_wr[];
    int          c_model[];
    bit          c_known;
    bit          job_started;
    longint      start_e, busy_to, done_from;
    int          job_k;
    int unsigned last_idle;
    bit          wrote_ab_since_start, had_job;

    int unsigned checks, jobs, skipped;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db #(mm_cfg)::get(this, "", "cfg", cfg))
            `uvm_fatal("CFG", "no mm_cfg in config_db")
        n = cfg.n;  k_max = cfg.k_max;
        if (n * k_max > MM_MAX_AB || n * n > MM_MAX_C)
            `uvm_fatal("CFG", $sformatf("N=%0d K_MAX=%0d exceeds the DPI array sizes", n, k_max))
        kw = $clog2(k_max);  lw = $clog2(n);
        a_mem = new[n * k_max];  a_wr = new[n * k_max];
        b_mem = new[k_max * n];  b_wr = new[k_max * n];
        c_model = new[n * n];
        reset_model();
    endfunction

    function void reset_model();
        cfg_k = k_max;
        job_started = 0;
        foreach (c_model[i]) c_model[i] = 0;          // array accumulators are reset
        c_known = 1;
        last_idle = 0;
        wrote_ab_since_start = 1;
        had_job = 0;
    endfunction

    function bit busy_at(longint e);
        return job_started && e > start_e && e <= busy_to;
    endfunction

    function bit done_at(longint e);
        return job_started && e >= done_from;
    endfunction

    function void check(string what, bit [31:0] got, bit [31:0] exp, bus_item t);
        checks++;
        if (got !== exp)
            `uvm_error("SB", $sformatf("%s: got %08h expected %08h  (%s)", what, got, exp,
                                       t.convert2string()))
    endfunction

    // ---------------------------------------------------------------- writes
    function void on_write(bus_item t);
        longint e = t.cycle;
        bit [3:0]  region = t.addr[15:12];
        bit [11:0] off = t.addr[11:0];
        if (region == 0) begin
            case (off[7:2])                             // register page aliases every 256 B
                6'd0: begin                             // CTRL
                    if (t.data[0]) begin
                        if (busy_at(e)) cov.hit("start_while_busy");
                        else            start_job(e);
                    end
                    if (t.data[1]) begin
                        if (busy_at(e)) cov.hit("soft_reset_while_busy");
                        reset_model();                  // takes effect at e+1 (no accept then)
                    end
                end
                6'd2: begin                             // CFG_K (accepted even while busy)
                    if (t.data >= 1 && t.data <= k_max) cfg_k = t.data;
                    else                                cov.hit("cfg_k_invalid");
                end
                default: ;
            endcase
        end else if (region == 1 || region == 2) begin
            bit is_b = (region == 2);
            bit hit  = is_b ? (off >> lw) < k_max : (off >> kw) < n;
            if (!hit) begin
                cov.hit("buffer_write_out_of_range");
            end else if (busy_at(e)) begin
                cov.hit("buffer_write_while_busy");
            end else if (is_b) begin
                b_mem[off] = t.data[7:0];  b_wr[off] = 1;  wrote_ab_since_start = 1;
            end else begin
                a_mem[off] = t.data[7:0];  a_wr[off] = 1;  wrote_ab_since_start = 1;
            end
        end
    endfunction

    function void start_job(longint e);
        byte    a_used[], b_used[];
        mm_ab_t a_dpi, b_dpi;
        mm_c_t  c_dpi;
        bit     all_written = 1;
        job_k = cfg_k;
        a_used = new[n * job_k];
        b_used = new[job_k * n];
        for (int i = 0; i < n; i++)
            for (int kk = 0; kk < job_k; kk++) begin
                a_used[i * job_k + kk] = a_mem[i * k_max + kk];
                all_written &= a_wr[i * k_max + kk];
            end
        foreach (b_used[x]) begin
            b_used[x] = b_mem[x];
            all_written &= b_wr[x];
        end
        foreach (a_used[x]) a_dpi[x] = a_used[x];
        foreach (b_used[x]) b_dpi[x] = b_used[x];
        mm_ref_dpi(n, job_k, a_dpi, b_dpi, c_dpi);
        foreach (c_model[x]) c_model[x] = c_dpi[x];
        c_known = all_written;
        if (!all_written) `uvm_warning("SB", "job uses unwritten A/B entries: C not checked")
        cov.sample_job(job_k, a_used, b_used, had_job && !wrote_ab_since_start);
        job_started = 1;
        start_e   = e;
        busy_to   = e + job_k + 2 * n + 1;
        done_from = e + job_k + 2 * n + 2;
        had_job = 1;
        wrote_ab_since_start = 0;
        jobs++;
    endfunction

    // ---------------------------------------------------------------- reads
    function void on_read(bus_item t);
        longint e = t.cycle;
        bit [3:0]  region = t.addr[15:12];
        bit [11:0] off = t.addr[11:0];
        bit busy = busy_at(e);
        if (region == 0) begin
            case (off[7:2])
                6'd1: begin
                    check("STATUS", t.data, {30'b0, done_at(e), busy}, t);
                    if (busy) cov.hit("status_saw_busy");
                end
                6'd2: check("CFG_K", t.data, cfg_k, t);
                6'd3: check("INFO", t.data, {16'h0001, 8'(k_max), 8'(n)}, t);
                6'd4, 6'd5, 6'd6, 6'd8: begin
                    int which = (off[7:2] == 6'd8) ? 3 : int'(off[7:2]) - 4;
                    if (busy) begin
                        skipped++;
                        cov.hit("perf_read_while_busy");
                    end else begin
                        check($sformatf("PERF[%0d]", which), t.data,
                              done_at(e) ? mm_perf_dpi(n, job_k, which) : 0, t);
                    end
                end
                6'd7: begin                             // PERF_IDLE: monotonic between resets
                    checks++;
                    if (t.data < last_idle)
                        `uvm_error("SB", $sformatf("PERF_IDLE went backwards: %0d -> %0d",
                                                   last_idle, t.data))
                    last_idle = t.data;
                end
                default: check("unmapped register", t.data, 0, t);
            endcase
        end else if (region == 3 && off < 4 * n * n) begin
            if (busy) begin
                skipped++;
                cov.hit("c_read_while_busy");
            end else if (c_known) begin
                check($sformatf("C[%0d]", off >> 2), t.data, c_model[off >> 2], t);
            end
        end else begin
            check("unmapped read", t.data, 0, t);
            if (region == 3) cov.hit("c_read_out_of_range");
        end
    endfunction

    function void write(bus_item t);
        if (t.kind == bus_item::RESET) begin
            if (busy_at(t.cycle)) cov.hit("hard_reset_while_busy");
            reset_model();
        end else if (t.write) begin
            on_write(t);
        end else begin
            on_read(t);
        end
    endfunction

    function void report_phase(uvm_phase phase);
        `uvm_info("SB", $sformatf("%0d checks, %0d jobs, %0d reads skipped while busy",
                                  checks, jobs, skipped), UVM_LOW)
        if (checks == 0) `uvm_error("SB", "scoreboard checked nothing")
    endfunction
endclass
