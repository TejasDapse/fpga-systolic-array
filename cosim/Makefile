# Verilator + SystemC co-simulation (Phase 5).
#   make            N=4 and N=8, 1000 shared vectors each -> docs/results/cosim_n{4,8}.csv
#   make run N=8    one size
VERILATOR    ?= $(HOME)/miniconda3/envs/fpga/bin/verilator
SYSTEMC_HOME ?= $(HOME)/miniconda3/envs/fpga
export SYSTEMC_INCLUDE := $(SYSTEMC_HOME)/include
export SYSTEMC_LIBDIR  := $(SYSTEMC_HOME)/lib
N            ?= 4
ROOT         := ..
RTL          := $(addprefix $(ROOT)/rtl/core/,pe.sv systolic_array.sv skew_buffer.sv sram_sp.sv \
                  mm_controller.sv mm_regs.sv mm_core.sv)
BUILD        := build/n$(N)
RESULTS      := $(ROOT)/docs/results

all:
	$(MAKE) run N=4
	$(MAKE) run N=8

$(BUILD)/Vmm_core: cosim_main.cpp $(RTL) $(wildcard $(ROOT)/model/systemc/*.h) $(ROOT)/model/cpp/mm_ref.cpp
	@mkdir -p $(BUILD)
	$(VERILATOR) --sc --exe --build -j 0 -Wno-fatal -Wno-lint -Wno-style \
	    -GN=$(N) -GK_MAX=64 --top-module mm_core --Mdir $(BUILD) \
	    -CFLAGS "-std=c++17 -O2" -LDFLAGS "-Wl,-rpath,$(SYSTEMC_LIBDIR)" \
	    -MAKEFLAGS "CXX=/usr/bin/g++ LINK=/usr/bin/g++ AR=/usr/bin/ar" \
	    $(RTL) $(abspath cosim_main.cpp) $(abspath $(ROOT)/model/cpp/mm_ref.cpp)

$(ROOT)/model/vectors/n$(N).hex:
	python3 $(ROOT)/model/vectors.py --n $(N)

run: $(BUILD)/Vmm_core $(ROOT)/model/vectors/n$(N).hex
	@mkdir -p $(RESULTS)
	SC_COPYRIGHT_MESSAGE=DISABLE $(BUILD)/Vmm_core $(N) $(ROOT)/model/vectors/n$(N).hex $(RESULTS)/cosim_n$(N).csv

clean:
	rm -rf build

.PHONY: all run clean
