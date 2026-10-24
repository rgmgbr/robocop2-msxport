; Test build (tools/mkrom.py DIAG=2; BANK_MUSIC at A000h, from diag.asm dg_main): the VDP lab.
; Written for the user's MSX2 Hotbit (a real V9938) with the MSX Pico+, on which the HUD split
; failed in all three of the cartridge's turbo modes while every openMSX machine was clean
; (2026-10-24). No game; the interrupts off (split_cal's EI meets a stub of the lab's own at
; IM2_JUMP). It measures again and again and shows, in hex (front.asm dg_show, dg_row):
;   0  the VDP (vdp_id: 0 V9938, 2 V9958), R#9 as the BIOS left it (bit 1: 50 Hz), the runs
;   1  the speech's calibration at the power-on (music.asm vm_cal): P (vc_p), vm_dly
;   2  the split's (isr.asm split_cal, run here): split_dly, split_dly2
;   4-7  the iterations of a poll loop between the line matches of lines 40 and 72 (32 lines),
;      the fewest and the most of 16 runs. LOOP: the split's loop (split_cal's sc_count: 41
;      T-states an iteration with the M1 waits and a port read), run from RAM, then from the
;      cartridge (5 opcode fetches and 2 operand reads an iteration there); a cartridge's wait
;      states a read = 41 x (RAM / ROM - 1) / 7. DATA: that loop with 4 data reads more (73
;      T-states) from RAM, reading RAM, then the cartridge; its wait states a data read = 73 x
;      (RAM / ROM - 1) / 4.
;   9-16  R#19 rewritten D iterations of the split's delay loop (D = 0-7, the columns) after the
;      match of line 100, for line 101 (the split's case: its R#19 for line V-1 goes out right
;      after the match of line V-2, about D = 0 here; up to 0.1.1 about 1.5 iterations later)
;      and, as a control, for line 102: how many of 16 tries saw that match (10h: all), the
;      probe run from RAM and from the cartridge. A VDP that took R#19 at the start of the line
;      would give 00 for line 101 at any D.
;   18  tries whose match of line 100 never came (none on any VDP)
;   19  the sum of the cartridge's A000h-AFFFh (this bank) read with nothing written between the
;      reads, and of 32 more passes with an OUT before each read (to the PSG's address port,
;      R#15 selected: the Pico+'s second core handles every write and answers the next read
;      later), how many of them gave another sum since the start (FFh at most; 32 passes a
;      run): a cartridge that answers a read too late gives wrong bytes (the Pico+'s risky mode
;      drops /WAIT; its normal mode may miss the Z80's sampling on a machine whose slot signals
;      come late). The sum expected is the ROM file's (tools: the bytes of bank BANK_MUSIC's
;      first 4 KiB).
; openMSX's C-BIOS_MSX2 (a V9938, a plain Z80 at 3.58 MHz, no cartridge waits): P 00AE, DLY 07,
; split 00 / 02; LOOP 00AD 00AE from RAM and from the cartridge, DATA 0060 0061 both; line 101
; 10 10 10 0F 00 00 00 00 from RAM, 10 10 10 0E 00 00 00 00 from the cartridge (the match at
; the line's right border, R#19 compared live: the write past it from D = 3 on); line 102 10
; everywhere; no match missing. Its FS-A1FX (a V9958 through the T9769B, whose VDP ports take
; cycles more): P 00A5, split 00 / 00, LOOP 00A5 00A6, DATA 005E 005F, line 101 10 10 10 06 00...
; The read test: the sum that build's ROM file gives (A15A for the first lab build), no pass bad.
LAB_RAM:    equ 0xD000              ; (the probes' copies: no game runs; the AM area)
LAB_V:      equ 0xD100              ; the lab's variables:
lab_run:    equ LAB_V               ;   the runs so far,
lab_nofh:   equ LAB_V + 1           ;   tries without their first match,
lab_cur:    equ LAB_V + 2           ;   2: the count just made,
lab_min:    equ LAB_V + 4           ;   2: the fewest so far,
lab_max:    equ LAB_V + 6           ;   2: the most,
lab_n:      equ LAB_V + 8           ;   4 x 4: LOOP RAM, LOOP ROM, DATA RAM, DATA ROM (fewest,
                                    ;   most),
lab_h:      equ LAB_V + 24          ;   4 x 8: the R#19 tries (line 101 RAM, ROM; line 102 RAM, ROM)
lab_sum:    equ LAB_V + 56          ;   2: the bank's sum read with no write between the reads,
lab_bad:    equ LAB_V + 58          ;   the passes with an OUT before each read that gave another
LAB_V_END:  equ LAB_V + 60
LAB_RDN:    equ 32                  ; (those passes a run)
LAB_L0:     equ 40                  ; (the loops' first line; split_cal's CAL_LINE)
LAB_L1:     equ 100
LAB_TRIES:  equ 16
LAB_POLLS:  equ 20                  ; (~3.6 lines at 3.58 MHz: the next frame's match is far)

lab_main:
        di
        ld hl,lab_isr
        ld (IM2_JUMP + 1),hl        ; (the interrupts only acknowledged from now on)
        ld hl,lab_cnt
        ld de,LAB_RAM
        ld bc,lab_end - lab_cnt
        ldir                        ; the probes into RAM
        ld hl,LAB_V
        ld de,LAB_V + 1
        ld bc,LAB_V_END - LAB_V - 1
        ld (hl),0
        ldir
        call lab_text
        ld hl,dg_show
        call front_call             ; (the screen: BANK_FRONT at 8000h from now on)
        ld hl,dgv_pal
        ld de,pf_pal
        ld bc,32
        ldir                        ; (split_cal writes pf_pal's colours 1-15: the screen's)
        ld a,(vdp_id)
        call split_init             ; (cal_list: isr.asm)
        call split_cal
        di                          ; (its EI)
lab_lp: call lab_meas
        call lab_text
        ld b,0
lab_rw: push bc
        ld hl,dg_row
        call front_call             ; (row B again)
        pop bc
        inc b
        ld a,b
        cp 24
        jr nz,lab_rw
        ld hl,lab_run
        inc (hl)
        jr lab_lp

; The measures (IE1 on so that FH stays up until read; R#23 = 0, R#15 = 1 meanwhile).
lab_meas:
        ld c,VDP_CTRL
        ld a,R0_IE1_ON
        out (c),a
        ld a,0x80
        out (c),a
        xor a
        out (c),a
        ld a,0x97
        out (c),a                   ; R#23 = 0
        ld a,1
        out (c),a
        ld a,0x8F
        out (c),a                   ; S#1
        ld ix,LAB_RAM
        ld hl,lab_n
        call lab_n16                ; LOOP RAM
        ld ix,lab_cnt
        ld hl,lab_n + 4
        call lab_n16                ; LOOP ROM
        ld ix,LAB_RAM + lab_dat - lab_cnt
        ld de,LAB_V_END             ; (reads RAM)
        ld hl,lab_n + 8
        call lab_n16                ; DATA RAM
        ld ix,LAB_RAM + lab_dat - lab_cnt
        ld de,lab_main              ; (reads the cartridge)
        ld hl,lab_n + 12
        call lab_n16                ; DATA ROM
        ld ix,LAB_RAM + lab_r19 - lab_cnt
        ld e,LAB_L1 + 1
        ld hl,lab_h
        call lab_r8                 ; line 101 from RAM
        ld ix,lab_r19
        ld e,LAB_L1 + 1
        ld hl,lab_h + 8
        call lab_r8                 ; line 101 from the cartridge
        ld ix,LAB_RAM + lab_r19 - lab_cnt
        ld e,LAB_L1 + 2
        ld hl,lab_h + 16
        call lab_r8                 ; line 102 from RAM
        ld ix,lab_r19
        ld e,LAB_L1 + 2
        ld hl,lab_h + 24
        call lab_r8                 ; line 102 from the cartridge
        call lab_rd                 ; the cartridge's bytes read after a write
        xor a
        out (c),a
        ld a,0x8F
        out (c),a                   ; R#15 = 0
        ld a,R0_IE1_OFF
        out (c),a
        ld a,0x80
        out (c),a                   ; IE1 off (dg_show's)
        ret

; IX = a counting probe (lab_cnt, lab_dat or a copy; DE: lab_dat's reads), HL = 4 bytes: the
; fewest and the most iterations of 16 runs from the match of line LAB_L0 to that of LAB_L0 + 32
; (split_cal's way: the first count only syncs). Keeps C, DE.
lab_n16:
        push hl
        ld hl,0xFFFF
        ld (lab_min),hl
        ld hl,0
        ld (lab_max),hl
        in a,(c)                    ; (an FH pending: acknowledged)
        ld b,16
ln_lp:  push bc
        ld a,LAB_L0
        call lab_wr19
        call lab_ix                 ; (the first match)
        jr nc,ln_nx
        ld a,LAB_L0 + 32
        call lab_wr19
        call lab_ix                 ; HL = the iterations of 32 lines
        jr nc,ln_nx
        ld (lab_cur),hl
        push de
        ld de,(lab_min)
        or a
        sbc hl,de
        jr nc,ln_m1
        ld hl,(lab_cur)
        ld (lab_min),hl
ln_m1:  ld hl,(lab_cur)
        ld de,(lab_max)
        or a
        sbc hl,de
        jr c,ln_m2
        ld hl,(lab_cur)
        ld (lab_max),hl
ln_m2:  pop de
ln_nx:  pop bc
        djnz ln_lp
        pop hl
        push de
        ld de,(lab_min)
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld de,(lab_max)
        ld (hl),e
        inc hl
        ld (hl),d
        pop de
        ret

; IX = lab_r19 or its copy, E = the line it rewrites R#19 for, HL = 8 bytes: per D = 0-7 how
; many of LAB_TRIES tries saw that match. Keeps C, E.
lab_r8: ld d,0
lr_d:   push hl
        ld b,LAB_TRIES
        ld l,0
lr_t:   push bc
        push hl
        call lab_ix
        pop hl
        jr nc,lr_m
        inc l
lr_m:   pop bc
        djnz lr_t
        ld a,l
        pop hl
        ld (hl),a
        inc hl
        inc d
        ld a,d
        cp 8
        jr nz,lr_d
        ret

; The cartridge's A000h-AFFFh summed with no write between the reads (lab_sum), then LAB_RDN
; times with an OUT before each read: lab_bad counts the passes whose sum differs. Keeps C.
lab_rd: call lab_sum0
        ld (lab_sum),hl
        ld b,LAB_RDN
lrd_lp: push bc
        call lab_sum1
        ld de,(lab_sum)
        or a
        sbc hl,de
        jr z,lrd_ok
        ld hl,lab_bad
        ld a,(hl)
        inc a
        jr z,lrd_ok                 ; (FFh at most)
        ld (hl),a
lrd_ok: pop bc
        djnz lrd_lp
        ret

; -> HL = the sum of A000h-AFFFh's bytes, read with nothing written meanwhile.
lab_sum0:
        ld hl,0
        ld de,0xA000
lsz_lp: ld a,(de)
        add a,l
        ld l,a
        jr nc,lsz_nc
        inc h
lsz_nc: inc e
        jr nz,lsz_lp
        inc d
        ld a,d
        cp 0xB0
        jr nz,lsz_lp
        ret

; -> HL = the same sum, each read right after an OUT to the PSG's address port (R#15 selected).
lab_sum1:
        ld hl,0
        ld de,0xA000
lso_lp: ld a,15
        out (PSG_ADDR),a
        ld a,(de)
        add a,l
        ld l,a
        jr nc,lso_nc
        inc h
lso_nc: inc e
        jr nz,lso_lp
        inc d
        ld a,d
        cp 0xB0
        jr nz,lso_lp
        ret

lab_ix: jp (ix)

; A = a line: R#19 = it. Keeps C.
lab_wr19:
        out (c),a
        ld a,0x93
        out (c),a
        ret

; The interrupt while split_cal's EI lasts: FH and VBLANK acknowledged, nothing else.
lab_isr:
        push af
        ld a,1
        out (VDP_CTRL),a
        ld a,0x8F
        out (VDP_CTRL),a
        in a,(VDP_CTRL)
        xor a
        out (VDP_CTRL),a
        ld a,0x8F
        out (VDP_CTRL),a
        in a,(VDP_CTRL)
        pop af
        ei
        reti

; ----- the probes: relative jumps only (they run here and as copies at LAB_RAM) -----

; Polls S#1 for FH with the split's loop (isr.asm sc_count), 8192 times at most -> C and HL =
; the iterations until it came, NC when it did not. Keeps C, DE.
lab_cnt:
        ld b,0
        ld h,0
lc_lp:  in a,(c)
        rrca
        jr c,lc_x
        djnz lc_lp
        inc h
        ld a,h
        cp 0x20
        jr nz,lc_lp
        ld l,0
        ret
lc_x:   xor a
        sub b
        ld l,a
        scf
        ret

; The same loop with 4 data reads at DE an iteration (73 T-states). Keeps C, DE.
lab_dat:
        ld b,0
        ld h,0
ld_lp:  ld a,(de)
        ld a,(de)
        ld a,(de)
        ld a,(de)
        in a,(c)
        rrca
        jr c,ld_x
        djnz ld_lp
        inc h
        ld a,h
        cp 0x20
        jr nz,ld_lp
        ld l,0
        ret
ld_x:   xor a
        sub b
        ld l,a
        scf
        ret

; D = a delay (iterations of the split's 41 T-state loop, isr.asm sp_wait), E = a line: R#19 =
; LAB_L1, its match, D iterations, R#19 = E -> C when the match of line E came within LAB_POLLS
; polls. Uses AF, B, HL; keeps C, DE.
lab_r19:
        ld a,LAB_L1
        out (c),a
        ld a,0x93
        out (c),a
        in a,(c)                    ; (an FH pending: acknowledged)
        ld b,0
        ld h,0x20
lr_w:   in a,(c)
        rrca
        jr c,lr_f
        djnz lr_w
        dec h
        jr nz,lr_w
        ld hl,lab_nofh
        inc (hl)                    ; (the match of LAB_L1 never came)
        or a
        ret
lr_f:   ld a,d
        or a
        jr z,lr_r
        ld b,a
lr_dl:  in a,(c)
        rlca
        jr c,lr_r                   ; (never: the light pen's bit)
        djnz lr_dl
lr_r:   ld a,e
        out (c),a
        ld a,0x93
        out (c),a                   ; R#19 = E
        ld b,LAB_POLLS
lr_p:   in a,(c)
        rrca
        ret c
        djnz lr_p
        ret
lab_end:

; The screen's text (dg_txt) from the measures.
lab_text:
        ld hl,dg_txt
        ld de,dg_txt + 1
        ld bc,32 * 24 - 1
        ld (hl),' '
        ldir
        ld bc,0x0000
        call dg_at
        ld hl,lbs_0
        call dg_str
        ld a,(vdp_id)
        call dg_hex
        ld hl,lbs_r9
        call dg_str
        ld a,(RG9SAV)
        call dg_hex
        ld hl,lbs_run
        call dg_str
        ld a,(lab_run)
        call dg_hex
        ld bc,0x0100
        call dg_at
        ld hl,lbs_sp
        call dg_str
        ld hl,(vc_p)
        call lab_hex16
        ld hl,lbs_dly
        call dg_str
        ld a,(vm_dly)
        call dg_hex
        ld bc,0x0200
        call dg_at
        ld hl,lbs_spl
        call dg_str
        ld a,(split_dly)
        call dg_hex
        ld hl,lbs_dly2
        call dg_str
        ld a,(split_dly2)
        call dg_hex
        ld de,lbs_n                 ; (the rows' labels in turn)
        ld hl,lab_n
        ld bc,4 * 256 + 4           ; (4 rows from row 4)
lt_n:   push bc
        push hl
        ld b,c
        ld c,0
        call dg_at                  ; (uses HL)
        ex de,hl
        call dg_str
        inc hl                      ; (past its 0)
        ex de,hl
        pop hl
        call lab_hw                 ; the fewest
        ld a,' '
        call dg_ch
        call lab_hw                 ; the most
        pop bc
        inc c
        djnz lt_n
        ld hl,lab_h
        ld bc,4 * 256 + 9           ; (4 pairs of rows from row 9)
lt_h:   push bc
        push hl
        ld b,c
        ld c,0
        call dg_at
        ex de,hl
        call dg_str
        inc hl
        ex de,hl
        pop hl
        pop bc
        push bc
        push hl
        ld b,c
        inc b
        ld c,0
        call dg_at                  ; (the next row: the values)
        pop hl
        ld b,8
lt_hv:  ld a,(hl)
        call dg_hex
        ld a,' '
        call dg_ch
        inc hl
        djnz lt_hv
        pop bc
        inc c
        inc c
        djnz lt_h
        ld bc,0x1200
        call dg_at
        ld hl,lbs_nofh
        call dg_str
        ld a,(lab_nofh)
        call dg_hex
        ld bc,0x1300
        call dg_at
        ld hl,lbs_sum
        call dg_str
        ld hl,(lab_sum)
        call lab_hex16
        ld hl,lbs_bad
        call dg_str
        ld a,(lab_bad)
        jp dg_hex

; HL = a word in memory: its 4 hex digits at the cursor; HL past it. Keeps BC, DE.
lab_hw: ld a,(hl)
        inc hl
        push af
        ld a,(hl)
        inc hl
        call dg_hex
        pop af
        jp dg_hex

; HL = a word: its 4 hex digits at the cursor. Keeps BC, DE.
lab_hex16:
        ld a,h
        call dg_hex
        ld a,l
        jp dg_hex

lbs_0:      db "VDP LAB  VDP ", 0
lbs_r9:     db "  R9 ", 0
lbs_run:    db "  RUN ", 0
lbs_sp:     db "SPEECH P ", 0
lbs_dly:    db "  DLY ", 0
lbs_spl:    db "SPLIT DLY ", 0
lbs_dly2:   db "  DLY2 ", 0
lbs_n:      db "LOOP RAM ", 0
            db "LOOP ROM ", 0
            db "DATA RAM ", 0
            db "DATA ROM ", 0
            db "R19 101 RAM  D 0-7", 0
            db "R19 101 ROM", 0
            db "R19 102 RAM", 0
            db "R19 102 ROM", 0
lbs_nofh:   db "NO MATCH 100: ", 0
lbs_sum:    db "READ SUM ", 0
lbs_bad:    db "  AFTER OUT BAD ", 0
