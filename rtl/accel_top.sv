// accel_top.sv - controller + two memories + core.
// The host writes A (by columns) and B (by rows), pulses start, waits for done.
module accel_top #(
  parameter int N     = 4,
  parameter int AW    = 8,
  parameter int ACCW  = 32,
  parameter int KW    = 16,
  parameter int DEPTH = 64,                 // largest K the memories hold
  parameter int ADDRW = $clog2(DEPTH)
) (
  input  logic                clk,
  input  logic                rst_n,
  // control
  input  logic                start,
  input  logic [KW-1:0]       k_dim,
  output logic                busy,
  output logic                done,
  // host writes to memory A: one column of A per address
  input  logic                a_we,
  input  logic [ADDRW-1:0]    a_waddr,
  input  logic [N*AW-1:0]     a_wdata,
  // host writes to memory B: one row of B per address
  input  logic                b_we,
  input  logic [ADDRW-1:0]    b_waddr,
  input  logic [N*AW-1:0]     b_wdata,
  // result
  output logic [N*N*ACCW-1:0] c_out
);

  logic          en, clear, rd_valid, data_valid;
  logic [KW-1:0] rd_addr;
  logic [N*AW-1:0] a_rdata, b_rdata;
  logic [N*AW-1:0] a_col, b_row;

  controller #(.N(N), .KW(KW)) u_ctrl (
    .clk, .rst_n, .start, .k_dim,
    .busy, .done, .en, .clear, .rd_valid, .rd_addr, .data_valid
  );

  sram #(.DEPTH(DEPTH), .WIDTH(N*AW)) u_mem_a (
    .clk, .we(a_we), .waddr(a_waddr), .wdata(a_wdata),
    .re(rd_valid), .raddr(rd_addr[ADDRW-1:0]), .rdata(a_rdata)
  );

  sram #(.DEPTH(DEPTH), .WIDTH(N*AW)) u_mem_b (
    .clk, .we(b_we), .waddr(b_waddr), .wdata(b_wdata),
    .re(rd_valid), .raddr(rd_addr[ADDRW-1:0]), .rdata(b_rdata)
  );

  // when there is nothing to read, feed zeros
  assign a_col = data_valid ? a_rdata : '0;
  assign b_row = data_valid ? b_rdata : '0;

  systolic_core #(.N(N), .AW(AW), .ACCW(ACCW)) u_core (
    .clk, .rst_n, .en, .clear, .a_col, .b_row, .c_out
  );

endmodule
