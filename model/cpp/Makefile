# C++ reference model (Phase 5).   make test   |   make perf_table
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
VECTORS  := ../vectors/n4.hex ../vectors/n8.hex ../vectors/n16.hex

all: test_mm_ref perf_table

test_mm_ref: test_mm_ref.cpp mm_ref.cpp mm_ref.h
	$(CXX) $(CXXFLAGS) -o $@ test_mm_ref.cpp mm_ref.cpp

perf_table: perf_table.cpp mm_ref.cpp mm_ref.h
	$(CXX) $(CXXFLAGS) -o $@ perf_table.cpp mm_ref.cpp

$(VECTORS):
	python3 ../vectors.py

test: test_mm_ref $(VECTORS)
	./test_mm_ref $(VECTORS)

clean:
	rm -f test_mm_ref perf_table

.PHONY: all test clean
