// sram.sv - simple dual-port memory with a synchronous read.
// rdata shows the word at raddr one clock cycle AFTER the request.
module sram #(
  parameter int DEPTH = 64,
  parameter int WIDTH = 32,
  parameter int ADDRW = $clog2(DEPTH)
) (
  input  logic             clk,
  // write port (from the host)
  input  logic             we,
  input  logic [ADDRW-1:0] waddr,
  input  logic [WIDTH-1:0] wdata,
  // read port (from the controller)
  input  logic             re,
  input  logic [ADDRW-1:0] raddr,
  output logic [WIDTH-1:0] rdata
);

  logic [WIDTH-1:0] mem [DEPTH];

  always_ff @(posedge clk) begin
    if (we) mem[waddr] <= wdata;
    if (re) rdata <= mem[raddr];
  end

endmodule
