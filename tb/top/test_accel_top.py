# test_accel_top.py - the whole accelerator, with real memories.
# The testbench is now only the host: write A and B, start, wait, read C.
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


def read_c(dut):
    N = int(dut.N.value)
    return np.array(unpack(int(dut.c_out.value), N * N, ACCW)).reshape(N, N)


async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for sig in (dut.rst_n, dut.start, dut.k_dim,
                dut.a_we, dut.a_waddr, dut.a_wdata,
                dut.b_we, dut.b_waddr, dut.b_wdata):
        sig.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1


async def load(dut, A, B):
    """Write the columns of A and the rows of B into the two memories."""
    K = A.shape[1]
    for t in range(K):
        await FallingEdge(dut.clk)
        dut.a_we.value = 1
        dut.a_waddr.value = t
        dut.a_wdata.value = pack(A[:, t], AW)
        dut.b_we.value = 1
        dut.b_waddr.value = t
        dut.b_wdata.value = pack(B[t, :], AW)
    await FallingEdge(dut.clk)
    dut.a_we.value = 0
    dut.b_we.value = 0


async def compute(dut, K, junk_after=0):
    """Pulse start, count cycles until done, return (C, cycles)."""
    N = int(dut.N.value)
    await FallingEdge(dut.clk)
    dut.k_dim.value = K
    dut.start.value = 1
    await FallingEdge(dut.clk)
    dut.start.value = 0
    cycles = 1
    while True:
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.done.value):
            break
        cycles += 1
    C = read_c(dut)

    # junk on the write lines (we=0) must not change the result
    rng = np.random.default_rng()
    for _ in range(junk_after):
        await FallingEdge(dut.clk)
        dut.a_wdata.value = pack(rng.integers(-128, 128, N), AW)
        dut.b_wdata.value = pack(rng.integers(-128, 128, N), AW)
    if junk_after:
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert (read_c(dut) == C).all(), "result changed after done"
    return C, cycles


@cocotb.test()
async def test_identity(dut):
    N = int(dut.N.value)
    await reset(dut)
    A = np.arange(1, N * N + 1).reshape(N, N)
    await load(dut, A, np.eye(N, dtype=int))
    C, _ = await compute(dut, N)
    assert (C == A).all(), f"got\n{C}\nexpected\n{A}"


@cocotb.test()
async def test_cycle_count(dut):
    """One extra cycle now, for the memory: K + 2(N-1) + 1."""
    N = int(dut.N.value)
    await reset(dut)
    for K in (1, N, 3 * N):
        await load(dut, np.ones((N, K), dtype=int), np.ones((K, N), dtype=int))
        _, cycles = await compute(dut, K)
        assert cycles == K + 2 * (N - 1) + 1, f"K={K}: took {cycles} cycles"


@cocotb.test()
async def test_random_back_to_back(dut):
    N = int(dut.N.value)
    await reset(dut)
    rng = np.random.default_rng()
    for K in (1, N, 3 * N):
        for _ in range(10):
            A = rng.integers(-128, 128, (N, K))
            B = rng.integers(-128, 128, (K, N))
            await load(dut, A, B)
            C, _ = await compute(dut, K, junk_after=3)
            assert (C == A @ B).all(), f"K={K}: got\n{C}\nexpected\n{A @ B}"
