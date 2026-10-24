; The HUD split's timed path and split_cal's measures (isr.asm: the split's design, its entry
; and the parts with no deadline), run from RAM: their bytes here in BANK_FRONT, copied to SR_RAM
; (msx.inc) at the power-on by cold.asm isr_init and assembled for it (z80asm's org sets only
; the labels' addresses: the bytes stay here). Relative jumps inside, calls to the RAM
; addresses, jumps back to the fixed area for what has no deadline (sp_late, sp_r19). No
; cartridge read comes between a line match and the writes timed from it, so that a
; cartridge's wait states cannot move them (the MSX Pico+, isr.asm). Then hud_palette, which
; isr_init copies to SR_PAL.
;
; Every wait for a line match is its interrupt, never a poll of S#1 (2026-10-24): the user's
; MSX2 Hotbit, a real V9938 on Ademir Carchano's MSX2 kit, missed FH in 0-75 % of polls
; depending on their phase (the VDP lab, msx/lab.asm: the same counts again for the same
; timing, never a miss in openMSX or on the SX-2), most likely when a read of S#1 met FH's
; setting; the interrupt is taken whatever the CPU reads. While a wait lasts the interrupts
; are on in a loop of 14 T-state turns and IM2_JUMP's first two bytes are "pop hl / ret" (or
; "pop de / ret"): the match's interrupt drops the loop's address and returns to the waiter's
; caller, carry set, 49 T-states after the match on average (the turn under way, 0-14, the
; IM 2 response, 20, the two instructions, 22). FH then stays up until read: the split reads
; S#1 at its end (sp_r19), split_cal after its timed writes.
sr_rom:
        org SR_RAM
isr_split:
        xor a
        ld (split_armed),a
        ld b,SP_GAP
spg_lp: djnz spg_lp                 ; (no VDP write soon after isr's read of S#1: the Hotbit lost
                                    ;  R#19 writes made right after the read that acknowledged FH)
        ld a,(split_r19)
        out (c),a
        ld a,0x93
        out (c),a                   ; R#19: a match at the end of line V-2
        call sp_irq                 ; its interrupt
        jp nc,sp_late               ; (none within SP_TURNS turns: serviced too late, all at once)
        ld hl,split_list+1
        call sp_seq                 ; the blank, the sprites off, the page, scroll and colours
        ld a,(split_dly2)
        or a
        jr z,sp_d2x
        ld b,a
spd2_w: djnz spd2_w                 ; split_dly2 turns: the display-on mid-line V+4
sp_d2x:
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

; Waits for the interrupt of the match R#19 was just set for (IE1 on) -> C at it, 49 T-states
; after it on average; NC when no match came within SP_TURNS turns (a split serviced past line
; V-2: R#19 named a line gone, no match this frame). No read of S#1 here: a match that came
; between the R#19 write and the EI has left FH up, and its interrupt is taken at once (65-79
; T-states late, the writes still mid-line). IM2_JUMP stays "pop hl / ret" until sp_r19 puts its
; jump back. Uses A, B, HL; keeps C.
sp_irq: ld hl,0xC9E1
        ld (IM2_JUMP),hl            ; pop hl / ret
        ld b,SP_TURNS
        scf                         ; (the interrupt returns with carry set)
        ei
spi_lp: djnz spi_lp
        di
        ld hl,IM2_JP0
        ld (IM2_JUMP),hl            ; (none: the jump back)
        or a
        ret

; The split's timed writes from its match (sp_irq's return; split_cal's M runs them too, on
; cal_list with sp_v1 at R1_CAL and its delays at 0): split_dly turns, R#1 = (sp_v1): the blank
; mid-line V-1, split_dly1 turns (past the last pixel of line V-1), R#8 = sprites off, sp_regs
; on HL (lines V..V+4 are blank). Keeps C = VDP_CTRL.
sp_seq: ld a,(split_dly)
        or a
        jr z,sps_b
        ld b,a
sps_w:  djnz sps_w
sps_b:  ld a,(sp_v1)
        out (c),a
        ld a,0x81
        out (c),a                   ; R#1: display off from line V
        ld a,(split_dly1)
        or a
        jr z,sps_s
        ld b,a
sps_v:  djnz sps_v
sps_s:  ld a,R8_SPR_OFF
        out (c),a
        ld a,0x88
        out (c),a                   ; sprites off (the display is)
        ; (falls into sp_regs)

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

; split_cal's and vm_cal's waits (R#15 = 1, IE1 on, no other interrupt enabled): R#19 = A, FH
; acknowledged after the write (an FH the old R#19 latched meanwhile cannot count), then up to
; SC_WRAPS x 256 turns (0: 256 x 256, 15 frames at 3.58 MHz, 5 at 10.74) for the match's
; interrupt -> C at it (FH left up: sc_ack before the next wait), NC when none came (IM2_JUMP
; left "pop hl / ret": the caller puts its jump back). Uses A, B, E, HL; keeps C.
sc_sync:
        out (c),a
        ld a,0x93
        out (c),a
        in a,(c)
        ld hl,0xC9E1
        ld (IM2_JUMP),hl            ; pop hl / ret
        ld e,SC_WRAPS
        ld b,0
        scf
        ei
scs_lp: djnz scs_lp
        dec e
        jr nz,scs_lp
        di
        or a
        ret

; FH acknowledged, SC_GAP turns (the Hotbit lost R#19 writes made right after that read), R#19
; = A. Keeps C.
sc_ack: in b,(c)                    ; (A kept: the line)
        ld b,SC_GAP
sck_w:  djnz sck_w
        out (c),a
        ld a,0x93
        out (c),a
        ret

; Counts turns of 14 T-states until the interrupt of the match R#19 was set for (IM2_JUMP: "pop
; de / ret") -> C, H = the 256-turn wraps (each 26 T-states more, net), B = 256 - the turns of
; the last; DE = the PC the interrupt left (scn_inc: a wrap ended, H not counting it yet; isr.asm
; sc_turns adds it). NC after 64 wraps. FH is left up. Uses A, B, DE, HL; keeps C.
sc_cnt: ld hl,0xC9D1
        ld (IM2_JUMP),hl            ; pop de / ret
        ld hl,0
        ld b,l
        scf
        ei
scn_lp: djnz scn_lp
scn_inc:
        inc h
        ld a,h
        cp 64
        jr nz,scn_lp
        di
        or a
        ret

; split_cal's M run (isr.asm): the match of line CAL_LINE + 40 (sc_sync), sp_seq on cal_list from
; it as isr_split runs sp_seq from its own match (the same return, jump and call, all in RAM: no
; cartridge read between the match and the count), R#19 for 8 lines on (sc_ack), then the turns
; left to that match (sc_cnt) -> as sc_cnt; NC when a match did not come.
sc_mrun:
        ld a,CAL_LINE + 40
        call sc_sync                ; the match of line CAL_LINE + 40
        jp nc,scm_x                 ; (as isr_split's jp nc,sp_late)
        ld hl,cal_list              ; (as its ld hl,split_list+1)
        call sp_seq
        ld a,CAL_LINE + 48
        call sc_ack                 ; R#19 for 8 lines on
        call sc_cnt                 ; M: the turns left to its match
scm_x:  ret
sr_end:
        org sr_rom + sr_end - SR_RAM
SR_LEN:     equ sr_end - SR_RAM     ; (msx.inc: SR_RAM's room, SR_ROOM)
        if SR_LEN > SR_ROOM
sr_too_long:                        ; (an error: the block outgrew its room)
sr_too_long:
        endif


hud_palette:                        ; (the HUD's colours 1-15, as the split writes them from their
        incbin "hud_split.pal"      ;  RAM copy SR_PAL: cold.asm isr_init, tools/mkrom.py)
