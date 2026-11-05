# test_systolic_core.py - the skew is now in hardware:
# every cycle we feed one whole column of A and one whole row of B.
import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly

AW = 8
ACCW = 32


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


async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.clear.value = 0
    dut.a_col.value = 0
    dut.b_row.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1


async def run(dut, A, B):
    """Feed column t of A and row t of B at cycle t. No skew here."""
    N = int(dut.N.value)
    K = A.shape[1]
    for t in range(K + 2 * (N - 1)):
        await FallingEdge(dut.clk)
        if t < K:
            dut.a_col.value = pack(A[:, t], AW)
            dut.b_row.value = pack(B[t, :], AW)
        else:
            dut.a_col.value = 0
            dut.b_row.value = 0
        dut.en.value = 1
        dut.clear.value = int(t == 0)
    await RisingEdge(dut.clk)
    await ReadOnly()
    return np.array(unpack(int(dut.c_out.value), N * N, ACCW)).reshape(N, N)


@cocotb.test()
async def test_identity(dut):
    N = int(dut.N.value)
    await reset(dut)
    A = np.arange(1, N * N + 1).reshape(N, N)
    C = await run(dut, A, np.eye(N, dtype=int))
    assert (C == A).all(), f"got\n{C}\nexpected\n{A}"


@cocotb.test()
async def test_random_back_to_back(dut):
    N = int(dut.N.value)
    await reset(dut)
    rng = np.random.default_rng()
    for K in (1, N, 3 * N):
        for _ in range(10):
            A = rng.integers(-128, 128, (N, K))
            B = rng.integers(-128, 128, (K, N))
            C = await run(dut, A, B)
            assert (C == A @ B).all(), f"K={K}: got\n{C}\nexpected\n{A @ B}"