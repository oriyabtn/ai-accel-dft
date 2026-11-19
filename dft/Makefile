# dft/Makefile
#   make N=4 CHAINS=4            synthesize the core, insert scan -> build/core_scan.v
#   make faultsim PATTERNS=1024  stuck-at fault simulation of one PE
#   make atpg PATTERNS=1024      random patterns + SAT-based ATPG for the rest
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

# fault simulation of one PE with random patterns:  make faultsim PATTERNS=1024
PATTERNS ?= 1024
SEED     ?= 1

$(BUILD)/pe.json: ../rtl/pe.sv
	mkdir -p $(BUILD)
	yosys -q -l $(BUILD)/pe_synth.log -p "read_verilog -sv ../rtl/pe.sv; \
	  synth -top pe -flatten; opt_clean -purge; write_json $@"

faultsim: $(BUILD)/pe.json fault_sim.py
	python3 fault_sim.py $< pe $(PATTERNS) $(SEED)

# random patterns, then SAT-based ATPG for what is left:  make atpg PATTERNS=1024
atpg: $(BUILD)/pe.json atpg.py fault_sim.py
	python3 atpg.py $< pe $(PATTERNS) $(SEED)

clean:
	rm -rf $(BUILD)

.PHONY: all clean faultsim atpg
