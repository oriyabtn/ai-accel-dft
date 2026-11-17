#!/usr/bin/env python3
"""insert_scan.py - add scan chains to a gate-level netlist.

Reads a flat Yosys JSON netlist, and for every flip-flop:
  D  ->  scan_en ? previous_flop_Q : D      (a 2-input mux)
  E  ->  scan_en | E                         (shifting must work even when en=0)
The flip-flops are split into CHAINS chains of (almost) equal length.
New ports: scan_en, scan_in[CHAINS-1:0], scan_out[CHAINS-1:0].

It also writes out.map.json: for every chain, the flip-flops in shift order
(position 0 is next to scan_in), with the signal names each one drives.

Usage: insert_scan.py in.json out.json chains top_module
"""
import json
import sys

FLOP_TYPES = {"$_DFFE_PN0P_", "$_DFF_PN0_"}   # the two kinds Yosys gives us here


def main():
    src, dst, chains, top = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    design = json.load(open(src))
    mod = design["modules"][top]
    cells, ports, nets = mod["cells"], mod["ports"], mod["netnames"]

    # every net bit in Yosys JSON is an integer; find the largest one in use
    def bits_in(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from bits_in(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from bits_in(v)
        elif isinstance(obj, int):
            yield obj
    next_bit = max(bits_in(mod)) + 1

    def new_bit():
        nonlocal next_bit
        next_bit += 1
        return next_bit - 1

    # new ports
    scan_en = new_bit()
    scan_in = [new_bit() for _ in range(chains)]
    scan_out = [None] * chains
    ports["scan_en"] = {"direction": "input", "bits": [scan_en]}
    ports["scan_in"] = {"direction": "input", "bits": scan_in}
    nets["scan_en"] = {"hide_name": 0, "bits": [scan_en]}
    nets["scan_in"] = {"hide_name": 0, "bits": scan_in}

    # the flip-flops, in a fixed order (sorted by name) so the chains are reproducible
    flops = sorted(n for n, c in cells.items() if c["type"] in FLOP_TYPES)
    others = {c["type"] for c in cells.values() if c["type"].startswith("$_D")} - FLOP_TYPES
    if others:
        sys.exit(f"unsupported flip-flop types: {others}")

    per_chain = -(-len(flops) // chains)          # ceiling division
    order = []
    for k in range(chains):
        chain = flops[k * per_chain:(k + 1) * per_chain]
        prev = scan_in[k]
        for name in chain:
            c = cells[name]
            d_old = c["connections"]["D"][0]
            d_new = new_bit()
            cells[name + "$scan_mux"] = {
                "hide_name": 1, "type": "$_MUX_", "parameters": {}, "attributes": {},
                "port_directions": {"A": "input", "B": "input", "S": "input", "Y": "output"},
                "connections": {"A": [d_old], "B": [prev], "S": [scan_en], "Y": [d_new]},
            }
            c["connections"]["D"] = [d_new]
            if c["type"] == "$_DFFE_PN0P_":
                e_old = c["connections"]["E"][0]
                e_new = new_bit()
                cells[name + "$scan_en_or"] = {
                    "hide_name": 1, "type": "$_OR_", "parameters": {}, "attributes": {},
                    "port_directions": {"A": "input", "B": "input", "Y": "output"},
                    "connections": {"A": [e_old], "B": [scan_en], "Y": [e_new]},
                }
                c["connections"]["E"] = [e_new]
            prev = c["connections"]["Q"][0]
            order.append((k, name))
        scan_out[k] = prev
    ports["scan_out"] = {"direction": "output", "bits": scan_out}
    nets["scan_out"] = {"hide_name": 0, "bits": scan_out}

    json.dump(design, open(dst, "w"))

    # readable names for every flip-flop output, for the map file
    q_names = {}
    for net, info in nets.items():
        if info.get("hide_name"):
            continue
        for idx, bit in enumerate(info["bits"]):
            q_names.setdefault(bit, []).append(f"{net}[{idx}]")
    scan_map = [[] for _ in range(chains)]
    for k, name in order:
        q = cells[name]["connections"]["Q"][0]
        scan_map[k].append(sorted(q_names.get(q, [name])))
    json.dump({"chains": scan_map}, open(dst.replace(".json", ".map.json"), "w"), indent=1)
    lengths = [sum(1 for k, _ in order if k == i) for i in range(chains)]
    print(f"scan: {len(flops)} flip-flops in {chains} chains, lengths {lengths}")


if __name__ == "__main__":
    main()
