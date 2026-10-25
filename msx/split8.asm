; The HUD split's timed path on a turbo R's R800 (docs/TURBO_R.md 4), with split_cal8's waits:
; installed at SR_RAM by cold.asm cpu_set in place of split.asm's block while the game runs on the
; R800 (the bytes here in BANK_FRONT; z80asm's org sets only the labels' addresses). There the
; turbo R's S1990 holds every access to the VDP's ports until 62 R800 cycles (186 VDP ticks)
; after the last one, so the Z80 block's 44 accesses from its blank to its display-on (8,184
; ticks) cannot fit five blank lines. On the R800 the play field shows lines 0-160 and six blank
; lines hold them (the user's choice, 2026-10-25): the interrupt comes a line earlier (V-6: the
; VBLANK's iv_list rewrites the list's R#19 while sl_off is 1), the match taken by its interrupt
; is line V-3's (split_r19), then one delay (split_dly, split_cal8's) and every write back to
; back, paced by the S1990 alone (the code between them a few cycles, under the ~52 its hold
; leaves free): the blank ~916 ticks after the match (from line 161), R#16, the sprites off (past
; line 160's last pixel), the page and the scroll, the border mask, colours 1-15, the display on
; (from line 167, the HUD's first): 46 accesses, 8,556 ticks after the blank. No write while the
; HUD is drawn. Every wait for a match is its interrupt (split.asm's way); the R800 block's own
; copies of split.asm's waits serve split_cal8.
sr8_rom:
        org SR_RAM
isr_split8:
        xor a
        ld (split_armed),a
        ld b,SP_GAP8
sp8_g:  djnz sp8_g                  ; (no VDP write soon after isr's read of S#1: SP_GAP's way)
        ld a,(split_r19)
        out (c),a
        ld a,0x93
        out (c),a                   ; R#19: a match at the end of line V-3
        call sp_irq8                ; its interrupt
        jr nc,sp8_t                 ; (none: counted, the writes at once, the HUD that much late)
        ld a,(split_dly)
        ld b,a
sp8_d:  djnz sp8_d                  ; split_dly turns (split_cal8: 1-255)
sp8_b:  ld a,R1_BLANK
        out (c),a
        ld a,0x81
        out (c),a                   ; display off from line 161
        ld a,1
        out (c),a
        ld a,0x90
        out (c),a                   ; R#16 = colour 1
        ld a,R8_SPR_OFF
        out (c),a
        ld a,0x88
        out (c),a                   ; sprites off (line 160 drawn)
        ld hl,split_list
        ld b,(hl)
        inc hl
        otir                        ; the HUD's page and scroll (split_init)
        ld a,(hud_msk)
        or a
        jr z,sp8_p
        ld a,R25_HUD
        out (c),a
        ld a,0x99
        out (c),a                   ; V9958: no border mask in the HUD
sp8_p:  ld hl,SR_PAL
        ld bc,30 * 256 + VDP_PAL
        otir                        ; the HUD's colours 1-15
        ld c,VDP_CTRL
        ld a,R1_ON
        out (c),a
        ld a,0x81
        out (c),a                   ; display on from line 167: the HUD
        jp sp_r19                   ; (the ROM's: the rest has no deadline)
sp8_t:  ld hl,sp8_cnt
        inc (hl)                    ; (for the tests: never in openMSX)
        jr sp8_b

; Waits for the interrupt of the match R#19 was just set for (IE1 on) -> C at it, ~20 cycles
; after it; NC after sp8_tmo turns (split_cal8: ~2.3 lines' worth; the longest wait is ~2 lines).
; IM2_JUMP stays "pop hl / ret" until sp_r19 puts its jump back. Uses A, B, HL; keeps C.
sp_irq8:
        ld hl,0xC9E1
        ld (IM2_JUMP),hl            ; pop hl / ret
        ld hl,(sp8_tmo)
        ld b,l
        inc h                       ; (H + 1 passes, the first of L turns)
        scf                         ; (the interrupt returns with carry set)
        ei
sp8_w:  djnz sp8_w
        dec h
        jr nz,sp8_w
        di
        ld hl,IM2_JP0
        ld (IM2_JUMP),hl            ; (none: the jump back)
        or a
        ret

; split.asm's sc_sync, sc_ack and sc_cnt for split_cal8 (the same contracts; SC_GAP8 turns in
; sc8_ack; scn8_inc: sc_cnt's scn_inc, sc_turns finds the block's own through scn_at).
sc8_sync:
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
sc8_s:  djnz sc8_s
        dec e
        jr nz,sc8_s
        di
        or a
        ret
sc8_ack:
        in b,(c)                    ; (A kept: the line)
        ld b,SC_GAP8
sc8_k:  djnz sc8_k
        out (c),a
        ld a,0x93
        out (c),a
        ret
sc8_cnt:
        ld hl,0xC9D1
        ld (IM2_JUMP),hl            ; pop de / ret
        ld hl,0
        ld b,l
        scf
        ei
sc8_n:  djnz sc8_n
scn8_inc:
        inc h
        ld a,h
        cp 64
        jr nz,sc8_n
        di
        or a
        ret
sr8_end:
        org sr8_rom + sr8_end - SR_RAM
SR8_LEN:    equ sr8_end - SR_RAM
        if SR8_LEN > SR_ROOM
sr8_too_long:                       ; (an error: the block outgrew SR_RAM's room)
sr8_too_long:
        endif
        if (sp8_g & 0xFF) >= 0xFE
sr8_page_g:                         ; (an error: a timed djnz at xxFEh/xxFFh costs the R800 a cycle
sr8_page_g:                         ;  or two more a turn: H2)
        endif
        if (sp8_d & 0xFF) >= 0xFE
sr8_page_d:
sr8_page_d:
        endif
        if (sp8_w & 0xFF) >= 0xFE
sr8_page_w:
sr8_page_w:
        endif
        if (sc8_n & 0xFF) >= 0xFE
sr8_page_n:
sr8_page_n:
        endif

; The R800's split delay (docs/TURBO_R.md 4.3): isr.asm split_cal on the R800, through front_call
; (BANK_FRONT at 8000h). As split_cal's N: R#1 = R1_CAL (no VBLANK interrupt), IE1 on, R#23 = 0,
; R#15 = 1, the least of CAL_TRIES counts from the match of line CAL_LINE to that of CAL_LINE +
; 32 with the R800 block's waits; then n = (N + SC8_K) / 32 the turns of a line (~133: 456 cycles
; a line, ~3.42 a turn with the refresh), split_dly = n x SC8_D / 256 (at least 1: the blank ~916
; ticks after the match less the path around the delay), sp8_tmo = n x 147 / 64 (2.3 lines).
; Any measure missing (no VDP): SPLIT_DLY8, SP_TMO8 (the FS-A1GT's in openMSX). Leaves R#15 = 0,
; IM2_JUMP as it found it, the display off, the interrupts on.
split_cal8:
        di
        ld hl,(IM2_JUMP)
        push hl
        ld c,VDP_CTRL
        ld a,R1_CAL
        out (c),a
        ld a,0x81
        out (c),a                   ; R#1: display off, no VBLANK interrupt
        ld a,R0_IE1_ON
        out (c),a
        ld a,0x80
        out (c),a                   ; IE1 on (the interrupts off but in the waits)
        xor a
        out (c),a
        ld a,0x97
        out (c),a                   ; R#23 = 0
        ld a,1
        out (c),a
        ld a,0x8F
        out (c),a                   ; S#1
        ld hl,0xFFFF
        ld (cal_n),hl
        ld b,CAL_TRIES
s8c_n:  push bc
        ld a,CAL_LINE
        call sc8_sync               ; the match of line CAL_LINE
        jr nc,s8c_x
        ld a,CAL_LINE + 32
        call sc8_ack                ; R#19 for 32 lines on
        call sc8_cnt                ; N: the turns to its match
        jr nc,s8c_x
        call sc_turns
        ld de,cal_n
        call sc_min
s8c_x:  pop bc
        djnz s8c_n
        ld hl,(cal_n)
        ld a,h
        and l
        inc a
        jr z,s8c_dflt               ; (no N: no VDP)
        ld de,SC8_K
        add hl,de                   ; n32: the turns of 32 lines
        ld (cal_n),hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld a,h                      ; n = n32 / 32 (below 256 up to ~1.9 times an R800)
        push af
        ld e,SC8_D
        call s8c_mul
        ld a,h                      ; n x SC8_D / 256
        or a
        jr nz,s8c_d
        inc a                       ; (at least one turn)
s8c_d:  ld (split_dly),a
        pop af                      ; (n)
        ld e,147
        call s8c_mul                ; n x 147 (below 37,500)
        ld b,6
s8c_sh: srl h
        rr l
        djnz s8c_sh                 ; / 64: 2.3 lines of turns
        jr s8c_tmo
s8c_dflt:
        ld a,SPLIT_DLY8
        ld (split_dly),a
        ld hl,SP_TMO8
s8c_tmo:
        ld (sp8_tmo),hl
s8c_end:
        ld c,VDP_CTRL
        in a,(c)                    ; (S#1: the last match acknowledged)
        xor a
        ld (split_armed),a          ; (no split before the VBLANK arms it)
        out (c),a
        ld a,0x8F
        out (c),a                   ; R#15 = 0
        pop hl
        ld (IM2_JUMP),hl            ; (its jump back)
        ei
        ret

; HL = A x E. Uses A, B, D.
s8c_mul:
        ld hl,0
        ld d,h
        ld b,8
s8m_l:  add hl,hl
        add a,a
        jr nc,s8m_n
        add hl,de
s8m_n:  djnz s8m_l
        ret
