`timescale 1ns/1ps

module tb_baseline_mean;
    logic clk = 1'b0;
    logic rst = 1'b0;
    logic start = 1'b0;
    logic sample_valid = 1'b0;
    logic sample_ready;
    logic [11:0] sample_in = 12'd0;
    logic result_valid;
    logic [11:0] baseline_out;

    integer samples [0:49];
    integer input_fd;
    integer output_fd;
    integer scan_status;
    integer expected;
    integer index;
    integer blocks_checked = 0;
    reg [1023:0] vector_path;
    reg [1023:0] output_path;

    baseline_mean dut (
        .clk(clk),
        .rst(rst),
        .start(start),
        .sample_valid(sample_valid),
        .sample_ready(sample_ready),
        .sample_in(sample_in),
        .result_valid(result_valid),
        .baseline_out(baseline_out)
    );

    always #5 clk = ~clk;

    task automatic fail(input string message);
        begin
            $display("FAIL: %s", message);
            $fatal(1);
        end
    endtask

    task automatic apply_reset;
        begin
            @(negedge clk);
            rst = 1'b1;
            start = 1'b0;
            sample_valid = 1'b0;
            @(posedge clk);
            #1;
            if (sample_ready !== 1'b0 || result_valid !== 1'b0 ||
                baseline_out !== 12'd0)
                fail("reset no limpio la interfaz");
            @(negedge clk);
            rst = 1'b0;
        end
    endtask

    task automatic begin_transaction;
        begin
            @(negedge clk);
            start = 1'b1;
            sample_valid = 1'b1;
            sample_in = 12'd777;
            @(posedge clk);
            #1;
            if (sample_ready !== 1'b1)
                fail("start no inicio ACQUIRE");
            @(negedge clk);
            start = 1'b0;
            sample_valid = 1'b0;
        end
    endtask

    task automatic send_current_block(
        input integer expected_value,
        input integer stall_every,
        input integer inject_busy_start,
        input integer record_output
    );
        integer sent;
        integer held_result;
        begin
            begin_transaction();
            sent = 0;
            while (sent < 50) begin
                if (stall_every > 0 && sent > 0 && (sent % stall_every) == 0) begin
                    @(negedge clk);
                    sample_valid = 1'b0;
                    sample_in = 12'd4095;
                    @(posedge clk);
                    #1;
                    if (sample_ready !== 1'b1)
                        fail("una pausa abandono ACQUIRE");
                end

                @(negedge clk);
                sample_in = samples[sent][11:0];
                sample_valid = 1'b1;
                start = inject_busy_start && (sent == 10);
                if (sample_ready !== 1'b1)
                    fail("sample_ready bajo antes de 50 muestras");
                @(posedge clk);
                #1;
                sent = sent + 1;
                @(negedge clk);
                sample_valid = 1'b0;
                start = 1'b0;
            end

            if (result_valid !== 1'b1 || sample_ready !== 1'b0)
                fail("DONE no presento el protocolo esperado");
            if (baseline_out !== expected_value[11:0])
                fail("resultado numerico incorrecto");
            if (record_output)
                $fdisplay(output_fd, "%0d", baseline_out);
            held_result = baseline_out;

            @(posedge clk);
            #1;
            if (result_valid !== 1'b0 || sample_ready !== 1'b0)
                fail("result_valid no duro exactamente un ciclo");
            if (baseline_out !== held_result[11:0])
                fail("baseline_out no permanecio estable");
            @(negedge clk);
        end
    endtask

    task automatic test_reset_during_acquire;
        integer j;
        begin
            begin_transaction();
            for (j = 0; j < 7; j = j + 1) begin
                @(negedge clk);
                sample_valid = 1'b1;
                sample_in = 12'd1000;
                @(posedge clk);
            end
            @(negedge clk);
            sample_valid = 1'b0;
            rst = 1'b1;
            @(posedge clk);
            #1;
            if (sample_ready !== 1'b0 || result_valid !== 1'b0 ||
                baseline_out !== 12'd0)
                fail("reset durante ACQUIRE fallo");
            @(negedge clk);
            rst = 1'b0;
        end
    endtask

    task automatic test_reset_during_done;
        integer j;
        begin
            begin_transaction();
            for (j = 0; j < 50; j = j + 1) begin
                @(negedge clk);
                sample_valid = 1'b1;
                sample_in = 12'd321;
                @(posedge clk);
                @(negedge clk);
                sample_valid = 1'b0;
            end
            if (result_valid !== 1'b1 || baseline_out !== 12'd321)
                fail("precondicion de reset durante DONE fallo");
            rst = 1'b1;
            @(posedge clk);
            #1;
            if (result_valid !== 1'b0 || baseline_out !== 12'd0)
                fail("reset durante DONE fallo");
            @(negedge clk);
            rst = 1'b0;
        end
    endtask

    initial begin
        apply_reset();

        // Una muestra valida fuera de ACQUIRE debe rechazarse implicitamente.
        @(negedge clk);
        sample_valid = 1'b1;
        sample_in = 12'd4095;
        @(posedge clk);
        #1;
        if (sample_ready !== 1'b0 || baseline_out !== 12'd0)
            fail("se acepto una muestra en IDLE");
        @(negedge clk);
        sample_valid = 1'b0;

        for (index = 0; index < 50; index = index + 1)
            samples[index] = 0;
        send_current_block(0, 0, 0, 0);

        for (index = 0; index < 50; index = index + 1)
            samples[index] = 4095;
        send_current_block(4095, 7, 1, 0);

        for (index = 0; index < 50; index = index + 1)
            samples[index] = (index < 25) ? 1 : 0;
        send_current_block(1, 5, 0, 0);

        test_reset_during_acquire();
        test_reset_during_done();

        if ($value$plusargs("VECTORS=%s", vector_path) &&
            $value$plusargs("OUTPUT=%s", output_path)) begin
            input_fd = $fopen(vector_path, "r");
            output_fd = $fopen(output_path, "w");
            if (input_fd == 0 || output_fd == 0)
                fail("no se pudieron abrir los archivos de verificacion");

            scan_status = $fscanf(input_fd, "%d", expected);
            while (scan_status == 1) begin
                for (index = 0; index < 50; index = index + 1) begin
                    scan_status = $fscanf(input_fd, "%d", samples[index]);
                    if (scan_status != 1)
                        fail("archivo de vectores incompleto");
                end
                send_current_block(expected, 6, 1, 1);
                blocks_checked = blocks_checked + 1;
                scan_status = $fscanf(input_fd, "%d", expected);
            end
            $fclose(input_fd);
            $fclose(output_fd);
        end

        $display("PASS: protocolo y %0d bloques externos", blocks_checked);
        $finish;
    end

endmodule
