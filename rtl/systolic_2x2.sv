// systolic_2x2.sv - 2x2 array of PEs
module systolic_2x2 (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               en,
  input  logic               clear,
  input  logic signed [7:0]  a_row0,
  input  logic signed [7:0]  a_row1,
  input  logic signed [7:0]  b_col0,
  input  logic signed [7:0]  b_col1,
  output logic signed [31:0] c00,
  output logic signed [31:0] c01,
  output logic signed [31:0] c10,
  output logic signed [31:0] c11
);

  // internal wires: A moving right
  logic signed [7:0] a_00_01;
  logic signed [7:0] a_10_11;

  // internal wires: B moving down
  logic signed [7:0] b_00_10;
  logic signed [7:0] b_01_11;

  pe u_pe00 (
    .clk   (clk),
    .rst_n (rst_n),
    .en    (en),
    .clear (clear),
    .a_in  (a_row0),
    .b_in  (b_col0),
    .a_out (a_00_01),
    .b_out (b_00_10),
    .acc   (c00)
  );

  pe u_pe01 (
    .clk   (clk),
    .rst_n (rst_n),
    .en    (en),
    .clear (clear),
    .a_in  (a_00_01),
    .b_in  (b_col1),
    .a_out (),
    .b_out (b_01_11),
    .acc   (c01)
  );

  pe u_pe10 (
    .clk   (clk),
    .rst_n (rst_n),
    .en    (en),
    .clear (clear),
    .a_in  (a_row1),
    .b_in  (b_00_10),
    .a_out (a_10_11),
    .b_out (),
    .acc   (c10)
  );

  pe u_pe11 (
    .clk   (clk),
    .rst_n (rst_n),
    .en    (en),
    .clear (clear),
    .a_in  (a_10_11),
    .b_in  (b_01_11),
    .a_out (),
    .b_out (),
    .acc   (c11)
  );

endmodule