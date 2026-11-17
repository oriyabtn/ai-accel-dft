# tb/scan - tests the core AFTER scan insertion (gate-level netlist)
SIM ?= icarus
TOPLEVEL_LANG = verilog

N      ?= 4
CHAINS ?= 4
export N CHAINS

DFT = $(PWD)/../../dft
VERILOG_SOURCES = $(DFT)/build/core_scan.v

COCOTB_TOPLEVEL = systolic_core_scan
COCOTB_TEST_MODULES = test_scan

include $(shell cocotb-config --makefiles)/Makefile.sim

# build the scanned netlist first (and rebuild if N or CHAINS changed)
$(DFT)/build/core_scan.v: FORCE
	$(MAKE) -C $(DFT) N=$(N) CHAINS=$(CHAINS) --always-make
	rm -rf sim_build

FORCE:
