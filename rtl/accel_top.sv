// accel_top.sv - controller + core. The memories are still outside (the testbench).
module accel_top #(
  parameter int N    = 4,
  parameter int AW   = 8,
  parameter int ACCW = 32,
  parameter int KW   = 16
) (
  input  logic                clk,
  input  logic                rst_n,
  input  logic                start,
  input  logic [KW-1:0]       k_dim,
  output logic                busy,
  output logic                done,
  output logic                rd_valid,
  output logic [KW-1:0]       rd_addr,
  input  logic [N*AW-1:0]     a_col,    // from memory A
  input  logic [N*AW-1:0]     b_row,    // from memory B
  output logic [N*N*ACCW-1:0] c_out
);

  logic en, clear;

  controller #(.N(N), .KW(KW)) u_ctrl (
    .clk, .rst_n, .start, .k_dim,
    .busy, .done, .en, .clear, .rd_valid, .rd_addr
  );

  systolic_core #(.N(N), .AW(AW), .ACCW(ACCW)) u_core (
    .clk, .rst_n, .en, .clear, .a_col, .b_row, .c_out
  );

endmodule