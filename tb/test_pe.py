# test_pe.py - checks that one PE multiplies and accumulates correctly
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly


async def reset(dut):
    """Start the clock and hold reset for two cycles."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.clear.value = 0
    dut.a_in.value = 0
    dut.b_in.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1


async def step(dut, a, b, clear):
    """Drive one pair of numbers and wait one clock cycle."""
    await FallingEdge(dut.clk)
    dut.a_in.value = a
    dut.b_in.value = b
    dut.en.value = 1
    dut.clear.value = int(clear)
    await RisingEdge(dut.clk)
    await ReadOnly()


@cocotb.test()
async def test_corner_cases(dut):
    """Extreme values where sign and width bugs show up."""
    await reset(dut)
    cases = [(-128, -128), (127, -128), (-128, 127), (127, 127), (0, -128), (-1, -1)]
    for a, b in cases:
        await step(dut, a, b, clear=True)
        got = dut.acc.value.to_signed()
        assert got == a * b, f"{a} * {b}: got {got}, expected {a * b}"


@cocotb.test()
async def test_random_accumulate(dut):
    """1000 random pairs, starting a new sum every 50 cycles."""
    await reset(dut)
    expected = 0
    for i in range(1000):
        a = random.randint(-128, 127)
        b = random.randint(-128, 127)
        clear = (i % 50 == 0)
        expected = a * b if clear else expected + a * b
        await step(dut, a, b, clear)
        got = dut.acc.value.to_signed()
        assert got == expected, f"cycle {i}: got {got}, expected {expected}"


@cocotb.test()
async def test_pass_through(dut):
    """Inputs must appear on the outputs one cycle later."""
    await reset(dut)
    await step(dut, 42, -7, clear=True)
    assert dut.a_out.value.to_signed() == 42
    assert dut.b_out.value.to_signed() == -7