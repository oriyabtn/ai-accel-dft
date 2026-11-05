# test_systolic_2x2.py - checks the 2x2 array against NumPy
import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly

N = 2              # array size
K = 2              # shared dimension of A and B
CYCLES = K + 2 * (N - 1)


def a_input(A, i, t):
    """The number entering row i of the array at cycle t."""
    k = t - i
    if 0 <= k < K:
        return int(A[i][k])
    return 0


def b_input(B, j, t):
    """The number entering column j of the array at cycle t."""
    k = t - j
    if 0 <= k < K:
        return int(B[k][j])
    return 0

async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for sig in (dut.rst_n, dut.en, dut.clear,
                dut.a_row0, dut.a_row1, dut.b_col0, dut.b_col1):
        sig.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1


async def run(dut, A, B):
    """Feed A and B with the skew, then read the four results."""
    for t in range(CYCLES):
        await FallingEdge(dut.clk)
        dut.a_row0.value = a_input(A, 0, t)
        dut.a_row1.value = a_input(A, 1, t)
        dut.b_col0.value = b_input(B, 0, t)
        dut.b_col1.value = b_input(B, 1, t)
        dut.en.value = 1
        dut.clear.value = int(t == 0)
    await RisingEdge(dut.clk)
    await ReadOnly()
    return np.array([
        [dut.c00.value.to_signed(), dut.c01.value.to_signed()],
        [dut.c10.value.to_signed(), dut.c11.value.to_signed()],
    ])


@cocotb.test()
async def test_example(dut):
    """The example from the stepper page."""
    await reset(dut)
    A = np.array([[1, 2], [3, 4]])
    B = np.array([[5, 6], [7, 8]])
    C = await run(dut, A, B)
    assert (C == A @ B).all(), f"got\n{C}\nexpected\n{A @ B}"


@cocotb.test()
async def test_random_back_to_back(dut):
    """50 random pairs, one after another, without reset."""
    await reset(dut)
    rng = np.random.default_rng()
    for _ in range(50):
        A = rng.integers(-128, 128, (N, K))
        B = rng.integers(-128, 128, (K, N))
        C = await run(dut, A, B)
        assert (C == A @ B).all(), f"got\n{C}\nexpected\n{A @ B}"