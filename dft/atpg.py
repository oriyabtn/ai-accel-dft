#!/usr/bin/env python3
"""atpg.py - test generation for the faults random patterns did not catch.

1. Run random patterns with the fault simulator (fault_sim.py).
2. For every fault still undetected, ask a SAT solver one question:
     "Is there an input pattern for which the good circuit and the circuit
      with this fault give a different output?"
   - If yes, the solver returns that pattern: a test for the fault.
   - If no, it is a proof: no test exists, the fault is untestable (redundant).
3. Check every pattern the solver found with the fault simulator.

This is how modern ATPG tools handle hard faults: the same two steps you did
by hand (activate the fault, propagate it to an output), as a logic puzzle
for a solver.

Usage: atpg.py netlist.json top_module [random_patterns] [seed]
"""
import random
import sys

from pysat.solvers import Minisat22

import fault_sim as fs


class Cnf:
    """Turns gates into clauses (the standard Tseitin encoding)."""

    def __init__(self):
        self.clauses = []
        self.nvars = 0

    def var(self):
        self.nvars += 1
        return self.nvars

    def add(self, *cl):
        self.clauses.append(list(cl))

    def gate(self, typ, y, a, b, s=None):
        add = self.add
        if typ == "$_NOT_":     add(-y, -a); add(y, a)
        elif typ == "$_BUF_":   add(-y, a); add(y, -a)
        elif typ == "$_AND_":   add(-y, a); add(-y, b); add(y, -a, -b)
        elif typ == "$_NAND_":  add(y, a); add(y, b); add(-y, -a, -b)
        elif typ == "$_OR_":    add(y, -a); add(y, -b); add(-y, a, b)
        elif typ == "$_NOR_":   add(-y, -a); add(-y, -b); add(y, a, b)
        elif typ == "$_ANDNOT_": add(-y, a); add(-y, -b); add(y, -a, b)      # a & ~b
        elif typ == "$_ORNOT_": add(y, -a); add(y, b); add(-y, a, -b)        # a | ~b
        elif typ in ("$_XOR_", "$_XNOR_"):
            if typ == "$_XNOR_":
                y = -y
            add(-y, a, b); add(-y, -a, -b); add(y, -a, b); add(y, a, -b)
        elif typ == "$_MUX_":                                                # s ? b : a
            add(-y, s, a); add(y, s, -a); add(-y, -s, b); add(y, -s, -b)
        else:
            sys.exit(f"unsupported gate {typ}")


def find_test(inputs, flops, gates, outputs, fault):
    """Return {input net: 0/1} that detects the fault, or None if none exists."""
    fnet, fval = fault
    cnf = Cnf()
    sources = inputs + [f["Q"] for f in flops]
    good, bad = {}, {}

    const1 = cnf.var()
    cnf.add(const1)

    def lit(table, n):
        if n == "1":
            return const1
        if n == "0":
            return -const1
        return table[n]

    for n in sources:                       # the two circuits share their inputs
        good[n] = bad[n] = cnf.var()
    if fnet in bad:                          # fault on an input: give the bad copy its own variable
        bad[fnet] = cnf.var()

    for typ, c in gates:
        for table in (good, bad):
            y = cnf.var()
            table[c["Y"]] = y
            if table is bad and c["Y"] == fnet:
                continue                     # the faulty net is not driven by its gate
            cnf.gate(typ, y, lit(table, c.get("A", "0")), lit(table, c.get("B", "0")),
                     lit(table, c["S"]) if "S" in c else None)
    cnf.add(bad[fnet] if fval else -bad[fnet])

    def observed(table):
        obs = [lit(table, o) for o in outputs]
        for f in flops:                      # captured value: E ? D : Q
            y = cnf.var()
            cnf.gate("$_MUX_", y, lit(table, f["Q"]), lit(table, f["D"]), lit(table, f["E"]))
            obs.append(y)
        return obs

    diffs = []
    for g, b in zip(observed(good), observed(bad)):
        d = cnf.var()
        cnf.gate("$_XOR_", d, g, b)
        diffs.append(d)
    cnf.add(*diffs)                          # at least one output must differ

    with Minisat22(bootstrap_with=cnf.clauses) as solver:
        if not solver.solve():
            return None
        model = set(solver.get_model())
    return {n: int(good[n] in model) for n in sources}


def main():
    path, top = sys.argv[1], sys.argv[2]
    patterns = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    rng = random.Random(seed)
    mask = (1 << patterns) - 1

    inputs, flops, gates, outputs, names = fs.build(fs.load(path, top))
    sources = inputs + [f["Q"] for f in flops]
    nets = sorted(set(sources) | {c["Y"] for _, c in gates})
    faults = [(n, v) for n in nets for v in (0, 1)]

    # step 1: random patterns
    stim = {n: rng.getrandbits(patterns) for n in sources}
    good = fs.simulate(inputs, flops, gates, outputs, stim, mask)
    missed = []
    for fault in faults:
        bad = fs.simulate(inputs, flops, gates, outputs, stim, mask, fault)
        if all(g == b for g, b in zip(good, bad)):
            missed.append(fault)
    print(f"{top}: {len(faults)} faults, {patterns} random patterns "
          f"leave {len(missed)} undetected\n")

    # step 2: the solver, one fault at a time
    new_tests, untestable = [], []
    for fault in missed:
        label = f"{names.get(fault[0], fault[0])} stuck at {fault[1]}"
        test = find_test(inputs, flops, gates, outputs, fault)
        if test is None:
            untestable.append(fault)
            print(f"  {label}: UNTESTABLE (proven: no pattern can detect it)")
            continue
        # step 3: check the pattern with the fault simulator
        one = {n: test[n] for n in sources}
        g = fs.simulate(inputs, flops, gates, outputs, one, 1)
        b = fs.simulate(inputs, flops, gates, outputs, one, 1, fault)
        ok = any(x != y for x, y in zip(g, b))
        new_tests.append(test)
        print(f"  {label}: test found, checked by simulation: {'yes' if ok else 'NO'}")

    detected = len(faults) - len(missed) + len(new_tests)
    testable = len(faults) - len(untestable)
    print(f"\nrandom patterns: {patterns},  extra patterns from ATPG: {len(new_tests)}")
    print(f"fault coverage: {detected}/{len(faults)} = {100 * detected / len(faults):.2f}%")
    print(f"test coverage:  {detected}/{testable} = {100 * detected / testable:.2f}%  "
          f"(untestable faults left out)")


if __name__ == "__main__":
    main()
