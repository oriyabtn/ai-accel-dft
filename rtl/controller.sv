// controller.sv - runs one matrix multiply.
// The memories answer one cycle late, so en and clear are delayed
// by one cycle too: they reach the core together with the data.
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
  output logic          en,         // to the core, delayed one cycle
  output logic          clear,      // to the core, delayed one cycle
  output logic          rd_valid,   // to the memories: 1 = read this cycle
  output logic [KW-1:0] rd_addr,    // to the memories: which drawer
  output logic          data_valid  // rd_valid delayed one cycle: memory data is real
);

  typedef enum logic {IDLE, RUN} state_t;
  state_t        state;
  logic [KW-1:0] cnt;      // cycle number inside RUN
  logic [KW-1:0] k_reg;    // K, captured at start
  logic [KW-1:0] last;     // number of the last cycle

  // the run is one cycle longer than before, to wait for the memory
  assign last = k_reg + KW'(2 * (N - 1));

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

  // requests to the memory: same as before
  logic en_now, clear_now;
  assign en_now    = (state == RUN) && (cnt != last);
  assign clear_now = (state == RUN) && (cnt == '0);
  assign rd_valid  = (state == RUN) && (cnt < k_reg);
  assign rd_addr   = cnt;
  assign busy      = (state == RUN);

  // the fix: one flip-flop on each control signal
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      en         <= 1'b0;
      clear      <= 1'b0;
      data_valid <= 1'b0;
    end else begin
      en         <= en_now;
      clear      <= clear_now;
      data_valid <= rd_valid;
    end
  end

endmodule
