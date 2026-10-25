SIM ?= icarus
TOPLEVEL_LANG = verilog

VERILOG_SOURCES = $(PWD)/../rtl/pe.sv
COMPILE_ARGS += -g2012

COCOTB_TOPLEVEL = pe
COCOTB_TEST_MODULES = test_pe

include $(shell cocotb-config --makefiles)/Makefile.sim