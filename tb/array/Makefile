SIM ?= icarus
TOPLEVEL_LANG = verilog

VERILOG_SOURCES = $(PWD)/../../rtl/pe.sv $(PWD)/../../rtl/systolic_2x2.sv
COMPILE_ARGS += -g2012

COCOTB_TOPLEVEL = systolic_2x2
COCOTB_TEST_MODULES = test_systolic_2x2

include $(shell cocotb-config --makefiles)/Makefile.sim