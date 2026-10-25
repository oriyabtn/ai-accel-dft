// pe.sv - Processing Element: one multiply-accumulate unit
module pe #(
  parameter int AW   = 8,    // width of inputs (INT8)
  parameter int ACCW = 32    // width of accumulator
) (
  input  logic                   clk,
  input  logic                   rst_n,
  input  logic                   en,
  input  logic                   clear,
  input  logic signed [AW-1:0]   a_in,
  input  logic signed [AW-1:0]   b_in,
  output logic signed [AW-1:0]   a_out,
  output logic signed [AW-1:0]   b_out,
  output logic signed [ACCW-1:0] acc
);

  logic signed [ACCW-1:0] prod;
  assign prod = a_in * b_in;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      a_out <= '0;
      b_out <= '0;
      acc   <= '0;
    end else if (en) begin
      a_out <= a_in;
      b_out <= b_in;
      acc   <= clear ? prod : acc + prod;
    end
  end

endmodule