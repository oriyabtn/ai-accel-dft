SIM ?= icarus
TOPLEVEL_LANG = verilog

N ?= 4

VERILOG_SOURCES = $(PWD)/../../rtl/pe.sv \
                  $(PWD)/../../rtl/systolic_array.sv \
                  $(PWD)/../../rtl/skew_buffer.sv \
                  $(PWD)/../../rtl/systolic_core.sv
COMPILE_ARGS += -g2012 -Psystolic_core.N=$(N)

COCOTB_TOPLEVEL = systolic_core
COCOTB_TEST_MODULES = test_systolic_core

include $(shell cocotb-config --makefiles)/Makefile.sim