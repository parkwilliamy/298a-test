/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_example (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // Pin map
  //   uio_in[7]    mode : 0 = counter (original design), 1 = 40-byte storage
  //   uio_in[0]    load : counter mode, load ui_in into the counter
  //   uio_in[5:0]  addr : storage mode, byte address 0..39
  //   uio_in[6]    we   : storage mode, write ui_in into mem[addr]
  //   ui_in[7:0]   data : counter load value / byte to store
  //   uo_out[7:0]  counter (mode 0) or mem[addr] (mode 1)

  wire mode = uio_in[7];
  wire load = ~mode & uio_in[0];

  // --- 8-bit counter with synchronous load (original design) ---
  reg [7:0] counter;

  always @ (posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      counter <= 0;
    end else begin
      if (load) counter <= ui_in;
      else counter <= counter+1;
    end
  end

  // --- 40-byte storage: area-cost experiment for GF180 ---
  // 40 x 8-bit register file = 320 flip-flops built from standard cells (the
  // Tiny Tapeout GF180 flow has no SRAM macros). Every byte is written from
  // ui_in and read out on uo_out, so synthesis has to keep all of it. A wide
  // counter whose upper bits never reach an output pin is deleted by Yosys as
  // dead logic, which is why widening `counter` to 320 bits did not show the
  // real cost.
  localparam DEPTH = 10;

  wire       we      = mode & uio_in[5];
  wire [3:0] addr    = uio_in[3:0];
  wire       addr_ok = (addr < DEPTH);

  reg [7:0] mem [0:DEPTH-1];
  integer i;

  always @ (posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (i = 0; i < DEPTH; i = i + 1) mem[i] <= 8'h00;
    end else if (we && addr_ok) begin
      mem[addr] <= ui_in;
    end
  end

  wire [7:0] rdata   = addr_ok ? mem[addr] : 8'h00;
  wire [7:0] out_val = mode ? rdata : counter;

  // All output pins must be assigned. If not used, assign to 0.
  assign uo_out  = ena ? out_val : 8'bz;
  assign uio_out = 0;
  assign uio_oe  = 0;

endmodule
