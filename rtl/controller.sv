// controller.sv - runs one matrix multiply: start -> RUN for K+2(N-1) cycles -> done
module controller #(
  parameter int N  = 4,     // array size
  parameter int KW = 16     // width of K and of the cycle counter
) (
  input  logic          clk,
  input  logic          rst_n,
  input  logic          start,      // one-cycle pulse from the host
  input  logic [KW-1:0] k_dim,      // K, must be at least 1
  output logic          busy,
  output logic          done,       // stays high until the next start
  output logic          en,         // to the core: registers move only when 1
  output logic          clear,      // to the core: first cycle of a new run
  output logic          rd_valid,   // to the memories: 1 = read, 0 = give zeros
  output logic [KW-1:0] rd_addr     // to the memories: which drawer
);

  typedef enum logic {IDLE, RUN} state_t;
  state_t        state;
  logic [KW-1:0] cnt;      // cycle number inside RUN
  logic [KW-1:0] k_reg;    // K, captured at start
  logic [KW-1:0] last;     // number of the last cycle

  assign last = k_reg + KW'(2 * (N - 1)) - KW'(1);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state <= IDLE;
      cnt   <= '0;
      k_reg <= '0;
      done  <= 1'b0;
    end else begin
      case (state)
        IDLE: begin
          if (start) begin
            state <= RUN;
            cnt   <= '0;
            k_reg <= k_dim;
            done  <= 1'b0;
          end
        end
        RUN: begin
          if (cnt == last) begin
            state <= IDLE;
            done  <= 1'b1;
          end else begin
            cnt <= cnt + 1'b1;
          end
        end
      endcase
    end
  end

  assign busy     = (state == RUN);
  assign en       = (state == RUN);
  assign clear    = (state == RUN) && (cnt == '0);
  assign rd_valid = (state == RUN) && (cnt < k_reg);
  assign rd_addr  = cnt;

endmodule