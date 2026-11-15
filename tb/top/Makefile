SIM ?= icarus
TOPLEVEL_LANG = verilog

N ?= 4

VERILOG_SOURCES = $(PWD)/../../rtl/pe.sv \
                  $(PWD)/../../rtl/systolic_array.sv \
                  $(PWD)/../../rtl/skew_buffer.sv \
                  $(PWD)/../../rtl/systolic_core.sv \
                  $(PWD)/../../rtl/sram.sv \
                  $(PWD)/../../rtl/controller.sv \
                  $(PWD)/../../rtl/accel_top.sv
COMPILE_ARGS += -g2012 -Paccel_top.N=$(N)

COCOTB_TOPLEVEL = accel_top
COCOTB_TEST_MODULES = test_accel_top

include $(shell cocotb-config --makefiles)/Makefile.sim