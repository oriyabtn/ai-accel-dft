// skew_buffer.sv - delays lane i by i clock cycles
module skew_buffer #(
  parameter int N = 4,    // number of lanes
  parameter int W = 8     // width of each lane
) (
  input  logic          clk,
  input  logic          rst_n,
  input  logic          en,
  input  logic [N*W-1:0] in,    // lane i = in[i*W +: W]
  output logic [N*W-1:0] out    // lane i, i cycles later
);

  genvar i;
  generate
    for (i = 0; i < N; i++) begin : g_lane

      if (i == 0) begin : g_direct
        // lane 0: no delay
        assign out[0 +: W] = in[0 +: W];

      end else begin : g_delay
        // lane i: a chain of i registers
        logic [W-1:0] sr [i];

        always_ff @(posedge clk or negedge rst_n) begin
          if (!rst_n) begin
            for (int k = 0; k < i; k++) sr[k] <= '0;
          end else if (en) begin
            sr[0] <= in[i*W +: W];
            for (int k = 1; k < i; k++) sr[k] <= sr[k-1];
          end
        end

        assign out[i*W +: W] = sr[i-1];
      end

    end
  endgenerate

endmodule