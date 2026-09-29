// hex7seg.sv
// Converts a 4-bit value (0-F) into 7-segment drive signals.
//
// DE10-Lite HEX displays are ACTIVE-LOW: 0 turns a segment ON.
// Bit order of seg_n: {g, f, e, d, c, b, a}
//
//        a
//      -----
//   f |     | b
//     |  g  |
//      -----
//   e |     | c
//     |     |
//      -----
//        d

module hex7seg (
    input  logic [3:0] hex,
    output logic [6:0] seg_n
);

    always_comb begin
        // Patterns written active-high (1 = on) for readability, then inverted.
        case (hex)
            4'h0: seg_n = ~7'h3F;
            4'h1: seg_n = ~7'h06;
            4'h2: seg_n = ~7'h5B;
            4'h3: seg_n = ~7'h4F;
            4'h4: seg_n = ~7'h66;
            4'h5: seg_n = ~7'h6D;
            4'h6: seg_n = ~7'h7D;
            4'h7: seg_n = ~7'h07;
            4'h8: seg_n = ~7'h7F;
            4'h9: seg_n = ~7'h6F;
            4'hA: seg_n = ~7'h77;
            4'hB: seg_n = ~7'h7C;   // lower-case b
            4'hC: seg_n = ~7'h39;
            4'hD: seg_n = ~7'h5E;   // lower-case d
            4'hE: seg_n = ~7'h79;
            4'hF: seg_n = ~7'h71;
            default: seg_n = 7'h7F; // all off
        endcase
    end

endmodule
