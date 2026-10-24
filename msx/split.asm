; The HUD split's timed path and split_cal's measures (isr.asm: the split's design, its entry
; and the parts with no deadline), run from RAM: their bytes here in BANK_FRONT, copied to SR_RAM
; (msx.inc) at the power-on by cold.asm isr_init and assembled for it (z80asm's org sets only
; the labels' addresses: the bytes stay here). Relative jumps inside, calls to the RAM
; addresses, jumps back to the fixed area for what has no deadline (sp_late, sp_r19). No
; cartridge read comes between a line match and the writes timed from it, so that a
; cartridge's wait states cannot move them (the MSX Pico+, isr.asm). Then hud_palette, which
; isr_init copies to SR_PAL.
sr_rom:
        org SR_RAM
isr_split:
        ld a,(split_r19)
        ld l,a                      ; (HL is saved by the ISR)
        out (c),a
        ld a,0x93
        out (c),a                   ; R#19: a match at the end of line V-2
        xor a
        ld (split_armed),a
        call sp_fh                  ; FH of line V-2
        jp nc,sp_late               ; (serviced too late for its matches: the ROM's)
        ld a,l
        inc a
        out (c),a
        ld a,0x93
        out (c),a                   ; R#19: the end of line V-1, well ahead of its match (on the
                                    ;  ESE-VDP the write clears FH: none is up now)
        ld a,(split_dly)
        or a
        call nz,sp_wait
        ld a,R1_BLANK
        out (c),a
        ld a,0x81
        out (c),a                   ; display off from line V
        call sp_fh                  ; FH of line V-1
        ld a,R8_SPR_OFF
        out (c),a
        ld a,0x88
        out (c),a                   ; sprites off (the display is)
        ld hl,split_list+1
        call sp_regs                ; the HUD's page, scroll and palette (lines V..V+4 are blank)
        ld a,(split_dly2)
        or a
        call nz,sp_wait
        if SPLITDIAG
        ld a,(dg_step)
        inc a
        ld b,a
dg_dl:  djnz dg_dl                  ; SPLITDIAG: dg_step x 14 T-states more before the display-on
        endif
sp_on:  ld a,R1_ON
        out (c),a
        ld a,0x81
        out (c),a                   ; display on from line V+5: the HUD
        ld a,(hud_msk)
        or a
        jp z,sp_r19
        ld a,R25_HUD
        out (c),a
        ld a,0x99
        out (c),a                   ; V9958: no border mask in the HUD
        jp sp_r19                   ; (the ROM's: the rest has no deadline)

; Polls S#1 (R#15 = 1) for FH, the match R#19 was set for, SPLIT_POLLS times at most (the read
; acknowledges it) -> C when it came, NC when the bound ran out (its match was behind). Keeps C.
sp_fh:  ld b,SPLIT_POLLS
spf_lp: in a,(c)
        rrca
        ret c
        djnz spf_lp
        ret

; A (not 0) iterations of the split's timing loop (sp_wait: a poll of S#1 whose test never
; passes, bit 7 is the light pen's; split_cal counts the same loop): 41 T-states with the M1
; waits, a port read included, each.
sp_wait:
        ld b,a
spw_lp: in a,(c)
        rlca
        jr c,spw_x                  ; (never)
        djnz spw_lp
spw_x:  ret

; The HUD's registers (HL = the pairs of split_list: R#2 = page 3, V9938: R#18 = 0, R#23 =
; HUD_R23, V9958: R#26/R#27 = page 3 unscrolled; split_init) and the palette at sp_palp
; (SR_PAL, the RAM copy of hud_palette = gen/hud_split.pal: colours 1-15) with unrolled OUTIs.
; Keeps C = VDP_CTRL. (split_cal runs it on a list of R#16 writes and the play field's palette:
; the same timing.)
sp_regs:
        outi
        outi
        outi
        outi
        outi
        outi
        ld a,(split_list)
        cp 6
        jr z,sp_pal
        outi
        outi
sp_pal: ld a,1
        out (c),a
        ld a,0x90
        out (c),a                   ; R#16 = colour 1
        ld hl,(sp_palp)
        ld c,VDP_PAL
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        outi
        ld c,VDP_CTRL
        ret

; split_cal's measures, right after its count saw the FH of line CAL_LINE (R#15 = 1, R#23 = 0,
; C = VDP_CTRL): N, the iterations of sc_count's loop until that of line CAL_LINE + 32, then four
; times from a match sp_regs on cal_list and the play field's palette, R#23 = 0, R#19 for 8 lines
; on and the iterations left until that match -> NC when the match of line CAL_LINE + 32 did not
; come (no VDP); else HL = N, DE = M, the mean of the four (a match missed among them: the sum so
; far, 0 on the first).
sc_meas:
        ld a,CAL_LINE + 32
        call sc_r19
        call sc_count               ; N: the iterations of 32 lines
        ret nc
        push hl
        ld hl,pf_pal + 2
        ld (sp_palp),hl             ; (the play field's colours 1-15: what the VBLANK writes)
        ld de,0                     ; the sum of the four M
        ld a,CAL_LINE + 40
scm_lp: push de
        push af
        ld hl,cal_list
        call sp_regs                ; (from the match just seen)
        xor a
        out (c),a
        ld a,0x97
        out (c),a                   ; R#23 = 0 (cal_list leaves it; the HUD's list would not)
        pop af
        push af
        call sc_r19                 ; R#19: 8 lines on
        call sc_count               ; M: the iterations left of the 8 lines
        pop af
        pop de
        jr nc,scm_no                ; (its match missed: the slowest machine's value)
        add hl,de
        ex de,hl
        add a,8
        cp CAL_LINE + 40 + 4*8
        jr nz,scm_lp
        srl d
        rr e
        srl d
        rr e                        ; DE = the mean M
scm_no: pop hl                      ; HL = N
        scf
        ret

; A = a line: R#19 = it (R#23 is 0). Keeps C.
sc_r19: out (c),a
        ld a,0x93
        out (c),a
        ret

; Polls S#1 for FH with sp_wait's loop, 8192 times at most -> C and HL = the iterations until it
; came, NC when it did not (8192). Keeps C.
sc_count:
        ld b,0
        ld h,0
scc_lp: in a,(c)
        rrca
        jr c,scc_x
        djnz scc_lp
        inc h
        ld a,h
        cp 0x20
        jr nz,scc_lp
        ld l,0                      ; (8192: NC)
        ret
scc_x:  xor a
        sub b
        ld l,a                      ; HL = 256 * H + (256 - B) & 255
        scf
        ret
sr_end:
        org sr_rom + sr_end - SR_RAM
SR_LEN:     equ sr_end - SR_RAM     ; (msx.inc: SR_RAM's room, SR_ROOM)
        if SR_LEN > SR_ROOM
sr_too_long:                        ; (an error: the block outgrew its room)
sr_too_long:
        endif


hud_palette:                        ; (the HUD's colours 1-15, as the split writes them from their
        incbin "hud_split.pal"      ;  RAM copy SR_PAL: cold.asm isr_init, tools/mkrom.py)
