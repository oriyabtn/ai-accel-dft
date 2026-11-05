# test_systolic_array.py - checks the NxN array against NumPy
import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly

AW = 8
ACCW = 32


def a_input(A, i, t):
    """The number entering row i of the array at cycle t."""
    k = t - i
    if 0 <= k < A.shape[1]:
        return int(A[i][k])
    return 0


def b_input(B, j, t):
    """The number entering column j of the array at cycle t."""
    k = t - j
    if 0 <= k < B.shape[0]:
        return int(B[k][j])
    return 0


def pack(values, width):
    """Pack a list of signed numbers into one wide bus, item 0 at the bottom."""
    bus = 0
    for idx, v in enumerate(values):
        bus |= (v & ((1 << width) - 1)) << (idx * width)
    return bus


def unpack(bus, count, width):
    """Split one wide bus into a list of signed numbers."""
    out = []
    for idx in range(count):
        v = (bus >> (idx * width)) & ((1 << width) - 1)
        if v >= 1 << (width - 1):
            v -= 1 << width
        out.append(v)
    return out


async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.clear.value = 0
    dut.a_in.value = 0
    dut.b_in.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1


async def run(dut, A, B):
    """Feed A and B with the skew, then read all N*N results."""
    N = int(dut.N.value)
    K = A.shape[1]
    for t in range(K + 2 * (N - 1)):
        await FallingEdge(dut.clk)
        dut.a_in.value = pack([a_input(A, i, t) for i in range(N)], AW)
        dut.b_in.value = pack([b_input(B, j, t) for j in range(N)], AW)
        dut.en.value = 1
        dut.clear.value = int(t == 0)
    await RisingEdge(dut.clk)
    await ReadOnly()
    flat = unpack(int(dut.c_out.value), N * N, ACCW)
    return np.array(flat).reshape(N, N)


@cocotb.test()
async def test_identity(dut):
    """A times the identity matrix must give A back."""
    N = int(dut.N.value)
    await reset(dut)
    A = np.arange(1, N * N + 1).reshape(N, N)
    C = await run(dut, A, np.eye(N, dtype=int))
    assert (C == A).all(), f"got\n{C}\nexpected\n{A}"


@cocotb.test()
async def test_random_back_to_back(dut):
    """Random matrices with several values of K, one after another."""
    N = int(dut.N.value)
    await reset(dut)
    rng = np.random.default_rng()
    for K in (1, N, 3 * N):
        for _ in range(10):
            A = rng.integers(-128, 128, (N, K))
            B = rng.integers(-128, 128, (K, N))
            C = await run(dut, A, B)
            assert (C == A @ B).all(), f"K={K}: got\n{C}\nexpected\n{A @ B}"