SIM ?= icarus
TOPLEVEL_LANG = verilog

N ?= 4

VERILOG_SOURCES = $(PWD)/../../rtl/pe.sv $(PWD)/../../rtl/systolic_array.sv
COMPILE_ARGS += -g2012 -Psystolic_array.N=$(N)

COCOTB_TOPLEVEL = systolic_array
COCOTB_TEST_MODULES = test_systolic_array

include $(shell cocotb-config --makefiles)/Makefile.sim