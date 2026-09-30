# UVM testbench on Verilator (Phase 6).
#   make build N=4                    compile (UVM takes ~2 min)
#   make run N=4 TEST=mm_random_test SEED=1 JOBS=200
#   python3 regress.py                full regression + coverage merge -> docs/results/
# Needs: Verilator >= 5.03x, z3 (constraint solver) in PATH, UVM source (uvm-core).
VERILATOR ?= $(HOME)/miniconda3/envs/fpga/bin/verilator
UVM_HOME  ?= $(HOME)/tools/uvm-core/src
SOLVER_PATH ?= $(HOME)/miniconda3/envs/fpga/bin
N         ?= 4
TEST      ?= mm_random_test
SEED      ?= 1
JOBS      ?= 200
ROOT      := ..
BUILD     := build/n$(N)
RTL       := $(addprefix $(ROOT)/rtl/core/,pe.sv systolic_array.sv skew_buffer.sv sram_sp.sv \
               mm_controller.sv mm_regs.sv mm_core.sv)
TB        := tb/mm_bus_if.sv env/mm_pkg.sv tb/mm_sva.sv tb/tb_top.sv
DEPS      := $(RTL) $(TB) $(wildcard env/*.svh seq/*.svh tests/*.svh) dpi/mm_dpi.cpp $(ROOT)/model/cpp/mm_ref.cpp

build: $(BUILD)/Vtb_top

$(BUILD)/Vtb_top: $(DEPS)
	@mkdir -p $(BUILD)
	$(VERILATOR) --binary --timing --assert -j 0 -Wno-fatal -Wno-lint -Wno-style \
	    +define+UVM_NO_DPI +incdir+$(UVM_HOME) +incdir+env +incdir+seq +incdir+tests \
	    -GN=$(N) -GK_MAX=64 --top-module tb_top --Mdir $(BUILD) -o Vtb_top \
	    -CFLAGS "-std=c++17 -O1 -I$(abspath $(ROOT)/model/cpp)" \
	    -MAKEFLAGS "CXX=/usr/bin/g++ LINK=/usr/bin/g++ AR=/usr/bin/ar" \
	    $(UVM_HOME)/uvm_pkg.sv $(RTL) $(TB) $(abspath dpi/mm_dpi.cpp) $(abspath $(ROOT)/model/cpp/mm_ref.cpp)

run: build
	PATH=$(SOLVER_PATH):$$PATH $(BUILD)/Vtb_top +TEST=$(TEST) +JOBS=$(JOBS) \
	    +verilator+seed+$(SEED) +COVFILE=$(BUILD)/cov_$(TEST)_$(SEED).txt

clean:
	rm -rf build

.PHONY: build run clean
