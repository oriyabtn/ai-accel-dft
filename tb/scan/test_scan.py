# test_scan.py - checks the core after scan insertion.
#
# 1. functional: with scan_en = 0 the chip must still multiply correctly
# 2. chain:      bits shifted in must come out of each chain unchanged
# 3. capture:    load all flops by scan, run ONE normal cycle, unload,
#                and check that the captured values are right
import json
import os

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly

N = int(os.environ.get("N", 4))
CHAINS = int(os.environ.get("CHAINS", 4))
AW = 8
ACCW = 32
MAP = os.path.join(os.path.dirname(__file__), "../../dft/build/core_scan.map.json")


def pack(values, width):
    bus = 0
    for idx, v in enumerate(values):
        bus |= (int(v) & ((1 << width) - 1)) << (idx * width)
    return bus


def unpack(bus, count, width):
    out = []
    for idx in range(count):
        v = (bus >> (idx * width)) & ((1 << width) - 1)
        if v >= 1 << (width - 1):
            v -= 1 << width
        out.append(v)
    return out


def chains():
    with open(MAP) as f:
        return json.load(f)["chains"]


async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for sig in (dut.rst_n, dut.en, dut.clear, dut.a_col, dut.b_row,
                dut.scan_en, dut.scan_in):
        sig.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1


async def shift(dut, bits_in):
    """Shift one bit per chain per cycle. bits_in[c] is the list for chain c.
    Returns what came out of each chain, in the same order."""
    length = len(bits_in[0])
    out = [[] for _ in range(CHAINS)]
    for t in range(length):
        await FallingEdge(dut.clk)
        dut.scan_en.value = 1
        dut.scan_in.value = sum(int(bits_in[c][t]) << c for c in range(CHAINS))
        await ReadOnly()
        so = int(dut.scan_out.value)
        for c in range(CHAINS):
            out[c].append((so >> c) & 1)
    return out


# ---------------------------------------------------------------- functional
async def run(dut, A, B):
    K = A.shape[1]
    for t in range(K + 2 * (N - 1)):
        await FallingEdge(dut.clk)
        dut.scan_en.value = 0
        dut.a_col.value = pack(A[:, t], AW) if t < K else 0
        dut.b_row.value = pack(B[t, :], AW) if t < K else 0
        dut.en.value = 1
        dut.clear.value = int(t == 0)
    await RisingEdge(dut.clk)
    await ReadOnly()
    return np.array(unpack(int(dut.c_out.value), N * N, ACCW)).reshape(N, N)


@cocotb.test()
async def test_functional(dut):
    """scan_en = 0: the netlist must still be a correct matrix multiplier."""
    await reset(dut)
    A = np.arange(1, N * N + 1).reshape(N, N)
    C = await run(dut, A, np.eye(N, dtype=int))
    assert (C == A).all(), f"identity: got\n{C}"
    rng = np.random.default_rng()
    for K in (1, N, 3 * N):
        for _ in range(5):
            A = rng.integers(-128, 128, (N, K))
            B = rng.integers(-128, 128, (K, N))
            C = await run(dut, A, B)
            assert (C == A @ B).all(), f"K={K}: got\n{C}\nexpected\n{A @ B}"


# ---------------------------------------------------------------- chain test
@cocotb.test()
async def test_chain_integrity(dut):
    """Shift a random pattern in, then shift it out: it must come back unchanged.
    This is the first test every DFT engineer runs on a new scan design."""
    await reset(dut)
    lengths = [len(c) for c in chains()]
    length = max(lengths)
    rng = np.random.default_rng()
    pattern = [[int(b) for b in rng.integers(0, 2, length)] for _ in range(CHAINS)]
    await shift(dut, pattern)
    zeros = [[0] * length for _ in range(CHAINS)]
    out = await shift(dut, zeros)
    for c in range(CHAINS):
        # a chain of length L keeps the last L bits shifted in,
        # and gives them back in the same order
        skip = length - lengths[c]
        expected = pattern[c][skip:]
        assert out[c][:lengths[c]] == expected, f"chain {c} is broken"


# ---------------------------------------------------------------- capture test
@cocotb.test()
async def test_load_capture_unload(dut):
    """Load every flop with 0 by scan, apply a = 7, b = -5 to PE(0,0) for one
    normal cycle with clear = 1, then unload. PE(0,0) must now hold 7 * -5."""
    await reset(dut)
    cmap = chains()
    length = max(len(c) for c in cmap)
    zeros = [[0] * length for _ in range(CHAINS)]

    await shift(dut, zeros)                       # load: all flops = 0

    await FallingEdge(dut.clk)                    # capture: one normal cycle
    dut.scan_en.value = 0
    dut.en.value = 1
    dut.clear.value = 1
    dut.a_col.value = pack([7] + [0] * (N - 1), AW)
    dut.b_row.value = pack([-5] + [0] * (N - 1), AW)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.en.value = 0
    dut.clear.value = 0

    out = await shift(dut, zeros)                 # unload

    # the bit that comes out at time t sat at position (length - 1 - t)
    state = {}
    for c in range(CHAINS):
        for t, bit in enumerate(out[c]):
            pos = len(cmap[c]) - 1 - t
            if pos >= 0:
                for name in cmap[c][pos]:
                    state[name] = bit

    acc00 = sum(state[f"c_out[{i}]"] << i for i in range(ACCW))
    if acc00 >= 1 << (ACCW - 1):
        acc00 -= 1 << ACCW
    assert acc00 == -35, f"PE(0,0) captured {acc00}, expected -35"

    others = [state[f"c_out[{i}]"] for i in range(ACCW, N * N * ACCW)]
    assert not any(others), "another PE captured something non-zero"
