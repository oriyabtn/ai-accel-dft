# dft/Makefile - synthesize the core, insert scan, write a Verilog netlist
#   make N=4 CHAINS=4      ->  build/core_scan.v
N      ?= 4
CHAINS ?= 4
TOP     = systolic_core
BUILD   = build

all: $(BUILD)/core_scan.v

$(BUILD)/core.json: ../rtl/*.sv synth_core.ys
	mkdir -p $(BUILD)
	yosys -q -l $(BUILD)/synth.log -p "script synth_core.ys; chparam -set N $(N) $(TOP); \
	  synth -top $(TOP) -flatten; opt_clean -purge; write_json $@"

$(BUILD)/core_scan.json: $(BUILD)/core.json insert_scan.py
	python3 insert_scan.py $< $@ $(CHAINS) $(TOP)

$(BUILD)/core_scan.v: $(BUILD)/core_scan.json
	yosys -q -p "read_json $<; rename $(TOP) $(TOP)_scan; write_verilog -noattr $@"

clean:
	rm -rf $(BUILD)

.PHONY: all clean
