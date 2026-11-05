// systolic_core.sv - skew buffers in front of the NxN array
module systolic_core #(
  parameter int N    = 4,
  parameter int AW   = 8,
  parameter int ACCW = 32
) (
  input  logic                clk,
  input  logic                rst_n,
  input  logic                en,
  input  logic                clear,
  input  logic [N*AW-1:0]     a_col,   // one column of A, all rows together
  input  logic [N*AW-1:0]     b_row,   // one row of B, all columns together
  output logic [N*N*ACCW-1:0] c_out
);

  logic [N*AW-1:0] a_skewed;
  logic [N*AW-1:0] b_skewed;

  skew_buffer #(.N(N), .W(AW)) u_skew_a (
    .clk(clk), .rst_n(rst_n), .en(en), .in(a_col), .out(a_skewed)
  );

  skew_buffer #(.N(N), .W(AW)) u_skew_b (
    .clk(clk), .rst_n(rst_n), .en(en), .in(b_row), .out(b_skewed)
  );

  systolic_array #(.N(N), .AW(AW), .ACCW(ACCW)) u_array (
    .clk   (clk),
    .rst_n (rst_n),
    .en    (en),
    .clear (clear),
    .a_in  (a_skewed),
    .b_in  (b_skewed),
    .c_out (c_out)
  );

endmodule