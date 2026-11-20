module baseline_mean (
    input  logic        clk,
    input  logic        rst,
    input  logic        start,
    input  logic        sample_valid,
    output logic        sample_ready,
    input  logic [11:0] sample_in,
    output logic        result_valid,
    output logic [11:0] baseline_out
);

    typedef enum logic [1:0] {
        IDLE,
        ACQUIRE,
        DONE
    } state_t;

    state_t state;
    logic [17:0] accumulator;
    logic [5:0] sample_count;
    logic [17:0] extended_sample;
    logic [17:0] completed_sum;

    always_comb begin
        sample_ready = (state == ACQUIRE);
        result_valid = (state == DONE);
        extended_sample = {6'b000000, sample_in};
        completed_sum = accumulator + extended_sample;
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            state        <= IDLE;
            accumulator  <= 18'd0;
            sample_count <= 6'd0;
            baseline_out <= 12'd0;
        end else begin
            case (state)
                IDLE: begin
                    if (start) begin
                        accumulator  <= 18'd0;
                        sample_count <= 6'd0;
                        state        <= ACQUIRE;
                    end
                end

                ACQUIRE: begin
                    if (sample_valid) begin
                        if (sample_count == 6'd49) begin
                            baseline_out <= (completed_sum + 18'd25) / 18'd50;
                            accumulator  <= completed_sum;
                            sample_count <= 6'd50;
                            state        <= DONE;
                        end else begin
                            accumulator  <= completed_sum;
                            sample_count <= sample_count + 6'd1;
                        end
                    end
                end

                DONE: begin
                    state <= IDLE;
                end

                default: begin
                    state        <= IDLE;
                    accumulator  <= 18'd0;
                    sample_count <= 6'd0;
                end
            endcase
        end
    end

endmodule
