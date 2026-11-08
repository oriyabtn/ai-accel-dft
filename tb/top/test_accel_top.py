# test_accel_top.py - the controller now runs everything.
# The testbench only plays the role of the two memories.
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
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.k_dim.value = 0
    dut.a_col.value = 0
    dut.b_row.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1


async def run(dut, A, B, garbage_after=0):
    """Start the accelerator and act as memory until done.
    Returns the result and the number of cycles it took."""
    N = int(dut.N.value)
    K = A.shape[1]
    rng = np.random.default_rng()

    # one-cycle start pulse
    await FallingEdge(dut.clk)
    dut.k_dim.value = K
    dut.start.value = 1
    await FallingEdge(dut.clk)
    dut.start.value = 0

    cycles = 0
    while True:
        # act as memory: look at what the controller asks for
        if int(dut.rd_valid.value):
            addr = int(dut.rd_addr.value)
            dut.a_col.value = pack(A[:, addr], AW)
            dut.b_row.value = pack(B[addr, :], AW)
        else:
            dut.a_col.value = 0
            dut.b_row.value = 0
        cycles += 1
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.done.value):
            break
        await FallingEdge(dut.clk)

    C = read_c(dut)

    # after done: put random junk on the memory lines.
    # en must be 0, so the result must not change.
    for _ in range(garbage_after):
        await FallingEdge(dut.clk)
        dut.a_col.value = pack(rng.integers(-128, 128, N), AW)
        dut.b_row.value = pack(rng.integers(-128, 128, N), AW)
    if garbage_after:
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert (read_c(dut) == C).all(), "result changed after done"

    return C, cycles


@cocotb.test()
async def test_identity(dut):
    N = int(dut.N.value)
    await reset(dut)
    A = np.arange(1, N * N + 1).reshape(N, N)
    C, _ = await run(dut, A, np.eye(N, dtype=int))
    assert (C == A).all(), f"got\n{C}\nexpected\n{A}"


@cocotb.test()
async def test_cycle_count(dut):
    """done must rise after exactly K + 2(N-1) cycles."""
    N = int(dut.N.value)
    await reset(dut)
    for K in (1, N, 3 * N):
        A = np.ones((N, K), dtype=int)
        B = np.ones((K, N), dtype=int)
        _, cycles = await run(dut, A, B)
        assert cycles == K + 2 * (N - 1), f"K={K}: took {cycles} cycles"


@cocotb.test()
async def test_random_with_junk_after_done(dut):
    """Random matrices; junk on the inputs between runs must not matter."""
    N = int(dut.N.value)
    await reset(dut)
    rng = np.random.default_rng()
    for K in (1, N, 3 * N):
        for _ in range(10):
            A = rng.integers(-128, 128, (N, K))
            B = rng.integers(-128, 128, (K, N))
            C, _ = await run(dut, A, B, garbage_after=5)
            assert (C == A @ B).all(), f"K={K}: got\n{C}\nexpected\n{A @ B}"