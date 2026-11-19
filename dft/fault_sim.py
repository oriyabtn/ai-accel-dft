#!/usr/bin/env python3
"""fault_sim.py - stuck-at fault simulator for a full-scan gate-level netlist.

Full scan means every flip-flop can be loaded and read by the tester, so the
circuit is tested as pure combinational logic:
  inputs  = primary inputs  + every flip-flop output Q (loaded by scan)
  outputs = primary outputs + every flip-flop next value (captured, unloaded by scan)

Fault list: every signal (net bit) stuck at 0 and stuck at 1.
Not included: clock and reset, which are tested separately on real chips.

The patterns are random. All patterns are simulated at once ("bit-parallel"):
each signal is a Python integer whose bit k is its value in pattern k.

Usage: fault_sim.py netlist.json top_module [patterns] [seed]
"""
import json
import random
import sys

SKIP_INPUTS = {"clk", "rst_n"}


def load(path, top):
    with open(path) as f:
        mod = json.load(f)["modules"][top]
    return mod


def build(mod):
    """Return inputs, flops, gates in topological order, outputs, and readable names."""
    names = {}
    for net, info in sorted(mod["netnames"].items(), key=lambda x: x[1].get("hide_name", 0)):
        for i, b in enumerate(info["bits"]):
            if isinstance(b, int) and b not in names:
                names[b] = f"{net}[{i}]" if len(info["bits"]) > 1 else net

    inputs, outputs = [], []
    for port, info in mod["ports"].items():
        if info["direction"] == "input" and port not in SKIP_INPUTS:
            inputs += [b for b in info["bits"] if isinstance(b, int)]
        elif info["direction"] == "output":
            outputs += [b for b in info["bits"] if isinstance(b, int)]

    flops, gates = [], []
    for name, c in mod["cells"].items():
        conn = {p: v[0] for p, v in c["connections"].items()}
        if c["type"] == "$_DFFE_PN0P_":
            flops.append(conn)
        elif c["type"].startswith("$_D"):
            sys.exit(f"unsupported flip-flop type {c['type']}")
        else:
            gates.append((c["type"], conn))

    # topological order: a gate is ready when all its inputs are known
    known = set(inputs) | {f["Q"] for f in flops} | {"0", "1"}
    ordered, pending = [], gates
    while pending:
        nxt = []
        for g in pending:
            typ, conn = g
            ins = [v for p, v in conn.items() if p != "Y"]
            if all(v in known for v in ins):
                ordered.append(g)
                known.add(conn["Y"])
            else:
                nxt.append(g)
        if len(nxt) == len(pending):
            sys.exit("combinational loop found")
        pending = nxt
    return inputs, flops, ordered, outputs, names


def simulate(inputs, flops, gates, outputs, stim, mask, fault=None):
    """Simulate all patterns at once. fault = (net, 0 or 1) or None.
    Returns the list of observed values (outputs, then flop next states)."""
    v = {"0": 0, "1": mask}
    fnet, fval = fault if fault else (None, None)
    force = (mask if fval else 0)

    for net, val in stim.items():
        v[net] = force if net == fnet else val

    def get(n):
        return v[n]

    for typ, c in gates:
        a = get(c.get("A", "0"))
        b = get(c.get("B", "0"))
        if typ == "$_AND_":     y = a & b
        elif typ == "$_OR_":    y = a | b
        elif typ == "$_XOR_":   y = a ^ b
        elif typ == "$_NAND_":  y = ~(a & b) & mask
        elif typ == "$_NOR_":   y = ~(a | b) & mask
        elif typ == "$_XNOR_":  y = ~(a ^ b) & mask
        elif typ == "$_ANDNOT_": y = a & ~b & mask
        elif typ == "$_ORNOT_": y = (a | ~b) & mask
        elif typ == "$_NOT_":   y = ~a & mask
        elif typ == "$_BUF_":   y = a
        elif typ == "$_MUX_":
            s = get(c["S"])
            y = (a & ~s | b & s) & mask
        else:
            sys.exit(f"unsupported gate {typ}")
        v[c["Y"]] = force if c["Y"] == fnet else y

    observed = [get(o) for o in outputs]
    for f in flops:                       # what each flop captures: E ? D : Q
        e, d, q = get(f["E"]), get(f["D"]), get(f["Q"])
        observed.append((d & e | q & ~e) & mask)
    return observed


def main():
    path, top = sys.argv[1], sys.argv[2]
    patterns = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    rng = random.Random(seed)
    mask = (1 << patterns) - 1

    inputs, flops, gates, outputs, names = build(load(path, top))
    sources = inputs + [f["Q"] for f in flops]
    stim = {n: rng.getrandbits(patterns) for n in sources}

    nets = sorted(set(sources) | {c["Y"] for _, c in gates})
    faults = [(n, val) for n in nets for val in (0, 1)]
    good = simulate(inputs, flops, gates, outputs, stim, mask)

    first = {}                            # fault -> first pattern that detects it
    for fault in faults:
        bad = simulate(inputs, flops, gates, outputs, stim, mask, fault)
        diff = 0
        for g, b in zip(good, bad):
            diff |= g ^ b
        if diff:
            first[fault] = (diff & -diff).bit_length() - 1

    total = len(faults)
    print(f"{top}: {len(gates)} gates, {len(flops)} flip-flops, "
          f"{len(sources)} inputs (incl. scan), {total} faults\n")
    print(" patterns   detected   coverage")
    p = 1
    while p <= patterns:
        det = sum(1 for k in first.values() if k < p)
        print(f"{p:9d} {det:10d} {100 * det / total:9.2f}%")
        p *= 2

    missed = [f for f in faults if f not in first]
    print(f"\nnot detected after {patterns} patterns: {len(missed)}")
    for net, val in missed:
        print(f"  {names.get(net, net)} stuck at {val}")


if __name__ == "__main__":
    main()
