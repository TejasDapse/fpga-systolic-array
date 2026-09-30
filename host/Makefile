# C++ host test (Phase 6, Day 45).   make   ->   host/mm_host
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra

mm_host: mm_host.cpp ../model/cpp/mm_ref.cpp ../model/cpp/mm_ref.h ../model/systemc/mm_regmap.h
	$(CXX) $(CXXFLAGS) -o $@ mm_host.cpp ../model/cpp/mm_ref.cpp

clean:
	rm -f mm_host

.PHONY: clean
