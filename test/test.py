# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge
from cocotb_coverage.coverage import CoverPoint, coverage_db
import random

# uio_in bit assignments (see src/project.v)
LOAD = 1 << 0   # counter mode: load ui_in into the counter
WE = 1 << 6     # storage mode: write ui_in into mem[addr]
MODE = 1 << 7   # 0 = counter on uo_out, 1 = mem[addr] on uo_out
DEPTH = 40      # bytes of storage


@CoverPoint("top.counter_val",
            xf=lambda counter_val: counter_val,
            bins=list(range(256)))
def sample(counter_val):
    pass


@CoverPoint("top.mem_addr",
            xf=lambda addr: addr,
            bins=list(range(DEPTH)))
def sample_addr(addr):
    pass


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    dut._log.info("Test project behavior")

    for i in range(256):
        await FallingEdge(dut.clk)
        assert dut.uo_out.value == i

    dut.uio_in.value = LOAD

    for i in range(10000):
        loadval = random.randrange(0, 256)
        dut.ui_in.value = loadval
        sample(loadval)
        await FallingEdge(dut.clk)
        assert dut.uo_out.value == loadval

    coverage_db.report_coverage(dut._log.info, bins=True)
    coverage_db.export_to_yaml(filename="coverage.yml")


@cocotb.test()
async def test_storage(dut):
    """Fill all 40 bytes, read them back, and check the counter still works."""
    dut._log.info("Start storage test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)

    # After reset every byte reads as 0
    for a in range(DEPTH):
        dut.uio_in.value = MODE | a
        await FallingEdge(dut.clk)
        assert dut.uo_out.value == 0, f"mem[{a}] not cleared by reset"

    # Write a random byte to every address
    data = [random.randrange(0, 256) for _ in range(DEPTH)]
    for a, v in enumerate(data):
        dut.uio_in.value = MODE | WE | a
        dut.ui_in.value = v
        sample_addr(a)
        await FallingEdge(dut.clk)

    # Writes to out-of-range addresses (40..63) must be ignored
    for a in range(DEPTH, 64):
        dut.uio_in.value = MODE | WE | a
        dut.ui_in.value = 0xFF
        await FallingEdge(dut.clk)

    # Read everything back
    for a, v in enumerate(data):
        dut.uio_in.value = MODE | a
        await FallingEdge(dut.clk)
        assert dut.uo_out.value == v, f"mem[{a}] = {dut.uo_out.value}, expected {v}"

    # Out-of-range addresses read as 0
    for a in range(DEPTH, 64):
        dut.uio_in.value = MODE | a
        await FallingEdge(dut.clk)
        assert dut.uo_out.value == 0, f"addr {a} should read 0"

    # Back to counter mode: load still works and the count resumes
    dut.uio_in.value = LOAD
    dut.ui_in.value = 0x55
    await FallingEdge(dut.clk)
    assert dut.uo_out.value == 0x55
    dut.uio_in.value = 0
    await FallingEdge(dut.clk)
    assert dut.uo_out.value == 0x56

    # Storage contents survive counter-mode operation
    dut.uio_in.value = MODE | 7
    await FallingEdge(dut.clk)
    assert dut.uo_out.value == data[7]

    coverage_db.report_coverage(dut._log.info, bins=True)
    coverage_db.export_to_yaml(filename="coverage.yml")
