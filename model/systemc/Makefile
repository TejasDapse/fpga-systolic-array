# SystemC LT + CA models (Phase 5).   make test
# SystemC 3.0 comes from the conda env (conda install -c conda-forge systemc).
SYSTEMC_HOME ?= $(HOME)/miniconda3/envs/fpga
CXX          := /usr/bin/g++
CXXFLAGS     := -std=c++17 -O2 -Wall -Wno-unused-parameter -I$(SYSTEMC_HOME)/include
LDFLAGS      := -L$(SYSTEMC_HOME)/lib -lsystemc -Wl,-rpath,$(SYSTEMC_HOME)/lib
BUILD        := build
VECTORS      := ../vectors/n4.hex ../vectors/n8.hex
HDRS         := $(wildcard *.h) ../cpp/mm_ref.h

$(BUILD)/test_models: test_models.cpp ../cpp/mm_ref.cpp $(HDRS)
	@mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) -o $@ test_models.cpp ../cpp/mm_ref.cpp $(LDFLAGS)

$(VECTORS):
	python3 ../vectors.py

test: $(BUILD)/test_models $(VECTORS)
	@for v in $(VECTORS); do SC_COPYRIGHT_MESSAGE=DISABLE $(BUILD)/test_models $$v || exit 1; done

clean:
	rm -rf $(BUILD)

.PHONY: test clean
