# Formal verification with SymbiYosys (open-source Yosys + z3).
#   make            convert RTL with sv2v, run prove (k-induction) + cover
FPGA_ENV ?= $(HOME)/miniconda3/envs/fpga
SV2V     ?= $(HOME)/tools/sv2v/sv2v-Linux/sv2v
export PATH := $(FPGA_ENV)/bin:$(PATH)
RTL      := $(addprefix ../rtl/core/,pe.sv systolic_array.sv skew_buffer.sv sram_sp.sv \
              mm_controller.sv mm_regs.sv mm_core.sv)

all: build/mm_core.v
	sby -f mm_core.sby

build/mm_core.v: $(RTL)
	@mkdir -p build
	$(SV2V) -DSYNTHESIS --top=mm_core $(RTL) > $@

clean:
	rm -rf build mm_core_prove mm_core_cover mm_core_bmc

.PHONY: all clean
