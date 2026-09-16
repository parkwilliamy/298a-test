# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ClockCycles, FallingEdge
from cocotb_coverage.coverage import CoverPoint, CoverCross, coverage_db
import random

@CoverPoint("top.counter_val",
            xf=lambda counter_val: counter_val,
            bins=list(range(256)))
def sample(counter_val):
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

    dut.uio_in.value = 1

    for i in range(10000):
        loadval = random.randrange(0,256)
        dut.ui_in.value = loadval
        sample(loadval)
        await FallingEdge(dut.clk)
        assert dut.uo_out.value == loadval

    coverage_db.report_coverage(dut._log.info, bins=True)
    coverage_db.export_to_yaml(filename="coverage.yml")

