// mm_job.svh -- one matrix multiply: K, operand pattern, A (N x K) and B (K x N).
// Scalars are randomized under constraints (z3 solver in Verilator); the
// operand arrays are filled procedurally in post_randomize from `kind`.
class mm_job extends uvm_object;
    `uvm_object_utils(mm_job)
    typedef enum {RANDOM, ZEROS, ALL_MIN, ALL_MAX, MIN_MAX, IDENTITY} kind_e;

    int n = 4, k_max = 64;
    rand int unsigned k;
    rand kind_e       kind;
    byte              a[], b[];       // row-major, a[i*k + kk], b[kk*n + j]

    constraint c_k_legal { k inside {[1:k_max]}; }
    // Weight the fill/drain boundary (2N-1) and the extremes; see vplan.
    constraint c_k_dist {
        k dist { 1 := 5, [2 : 2*n - 2] :/ 15, 2*n - 1 := 5, [2*n : k_max - 1] :/ 55, k_max := 20 };
    }
    constraint c_kind_dist {
        kind dist { RANDOM := 60, ZEROS := 8, ALL_MIN := 8, ALL_MAX := 8, MIN_MAX := 8, IDENTITY := 8 };
    }

    function new(string name = "mm_job");
        super.new(name);
    endfunction

    function void post_randomize();
        a = new[n * k];
        b = new[k * n];
        foreach (a[x]) a[x] = pick(x / k == x % k);
        foreach (b[x]) b[x] = (kind == MIN_MAX) ? 8'sd127 : pick_b();
    endfunction

    local function byte pick(bit diag);
        case (kind)
            ZEROS:    return 0;
            ALL_MIN:  return -128;
            ALL_MAX:  return 127;
            MIN_MAX:  return -128;
            IDENTITY: return diag ? 1 : 0;
            default:  return byte'($urandom);
        endcase
    endfunction

    local function byte pick_b();
        case (kind)
            ZEROS:   return 0;
            ALL_MIN: return -128;
            ALL_MAX: return 127;
            default: return byte'($urandom);
        endcase
    endfunction

    function string convert2string();
        return $sformatf("job K=%0d kind=%s", k, kind.name());
    endfunction
endclass
