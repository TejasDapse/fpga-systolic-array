# Verilator + SystemC co-simulation (Phase 5).
#   make                    N = 4, 8, 16 (K_MAX = 64), 1000 shared vectors each
#                           -> docs/results/cosim_n{N}.csv
#   make run N=8 KMAX=128   one configuration (K_MAX != 64 -> cosim_n{N}_k{KMAX}.csv)
FPGA_ENV     ?= $(HOME)/miniconda3/envs/fpga
VERILATOR    ?= $(FPGA_ENV)/bin/verilator
SYSTEMC_HOME ?= $(FPGA_ENV)
export SYSTEMC_INCLUDE := $(SYSTEMC_HOME)/include
export SYSTEMC_LIBDIR  := $(SYSTEMC_HOME)/lib
N            ?= 4
KMAX         ?= 64
ROOT         := ..
RTL          := $(addprefix $(ROOT)/rtl/core/,pe.sv systolic_array.sv skew_buffer.sv sram_sp.sv \
                  mm_controller.sv mm_regs.sv mm_core.sv)
BUILD        := build/n$(N)_k$(KMAX)
SUFFIX       := $(if $(filter-out 64,$(KMAX)),_k$(KMAX))
CSV          := cosim_n$(N)$(SUFFIX).csv
VEC          := $(ROOT)/model/vectors/n$(N)$(SUFFIX).hex
RESULTS      := $(ROOT)/docs/results

all:
	$(MAKE) run N=4
	$(MAKE) run N=8
	$(MAKE) run N=16
	$(MAKE) run N=4 KMAX=16
	$(MAKE) run N=8 KMAX=128

$(BUILD)/Vmm_core: cosim_main.cpp $(RTL) $(wildcard $(ROOT)/model/systemc/*.h) $(ROOT)/model/cpp/mm_ref.cpp
	@mkdir -p $(BUILD)
	$(VERILATOR) --sc --exe --build -j 0 -Wno-fatal -Wno-lint -Wno-style \
	    -GN=$(N) -GK_MAX=$(KMAX) --top-module mm_core --Mdir $(BUILD) \
	    -CFLAGS "-std=c++17 -O2" -LDFLAGS "-Wl,-rpath,$(SYSTEMC_LIBDIR)" \
	    -MAKEFLAGS "CXX=/usr/bin/g++ LINK=/usr/bin/g++ AR=/usr/bin/ar" \
	    $(RTL) $(abspath cosim_main.cpp) $(abspath $(ROOT)/model/cpp/mm_ref.cpp)

$(VEC):
	python3 $(ROOT)/model/vectors.py --n $(N) --k-max $(KMAX)

run: $(BUILD)/Vmm_core $(VEC)
	@mkdir -p $(RESULTS)
	SC_COPYRIGHT_MESSAGE=DISABLE $(BUILD)/Vmm_core $(N) $(VEC) $(RESULTS)/$(CSV) $(KMAX)

clean:
	rm -rf build

.PHONY: all run clean
