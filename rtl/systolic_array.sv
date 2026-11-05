// systolic_array.sv - NxN array of PEs, output-stationary
module systolic_array #(
  parameter int N    = 4,    // array size
  parameter int AW   = 8,    // input width
  parameter int ACCW = 32    // accumulator width
) (
  input  logic                 clk,
  input  logic                 rst_n,
  input  logic                 en,
  input  logic                 clear,
  input  logic [N*AW-1:0]      a_in,    // row i   = a_in[i*AW +: AW]
  input  logic [N*AW-1:0]      b_in,    // col j   = b_in[j*AW +: AW]
  output logic [N*N*ACCW-1:0]  c_out    // C[i][j] = c_out[(i*N+j)*ACCW +: ACCW]
);

  // a_wire[i][j] is the A value entering PE(i,j) from the left.
  // Column N catches the a_out of the last PE in each row (unused).
  logic signed [AW-1:0] a_wire [N][N+1];

  // b_wire[i][j] is the B value entering PE(i,j) from above.
  // Row N catches the b_out of the last PE in each column (unused).
  logic signed [AW-1:0] b_wire [N+1][N];

  genvar i, j;
  generate
    for (i = 0; i < N; i++) begin : g_row
      for (j = 0; j < N; j++) begin : g_col

        // first column: A comes from outside
        if (j == 0) begin : g_a_edge
          assign a_wire[i][0] = a_in[i*AW +: AW];
        end

        // first row: B comes from outside
        if (i == 0) begin : g_b_edge
          assign b_wire[0][j] = b_in[j*AW +: AW];
        end

        pe #(.AW(AW), .ACCW(ACCW)) u_pe (
          .clk   (clk),
          .rst_n (rst_n),
          .en    (en),
          .clear (clear),
          .a_in  (a_wire[i][j]),
          .b_in  (b_wire[i][j]),
          .a_out (a_wire[i][j+1]),   // to the PE on the right
          .b_out (b_wire[i+1][j]),   // to the PE below
          .acc   (c_out[(i*N+j)*ACCW +: ACCW])
        );

      end
    end
  endgenerate

endmodule