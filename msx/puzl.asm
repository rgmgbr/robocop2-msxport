; Brainstorm, the bonus stage after level 1 (the Amiga's PUZL at $17100, which $8382 calls:
; docs/BRAINSTORM.md). Bank BANK_PUZL at A000h while it runs, FRONT at 8000h (front.asm
; front_bonus calls bs_stage); its graphics in the data banks from PUZL_GFX_BANK (tools/mkrom.py,
; tools/msxpuzl.py).
;
; The logic is PUZL's, routine by routine, in its order (docs/BRAINSTORM.md 2.3: the logic
; report's spec), one pass per 50 Hz tick on 50 and 60 Hz machines (its loop's PAL design rate).
; Its variables live in the mirror at their Amiga addresses (msx.inc pzv_...: $B00-$B21), so the
; trace harness compares them pass by pass with the original's (tools/openmsx_rc2.tcl
; rc2_pz_drive, tools/puzlcmp.py, tools/amigaemu.py puzl). Kept from the original as its traces
; show it (docs/BRAINSTORM.md 2.10): the column message_queue leaves in D0 in the pass that ends
; the fourth board (quirk 1); $B1A not cleared by a board's set-up (quirk 2); "TIMEOUT." queued on
; every pass of a time out (quirk 3); effect 6 asked for on every pass of a fade out (quirk 4); the
; palette pointer back to visit 1's at the end of every fade out (quirk 5).
;
; The display: every pass records what the original draws (pz_want, msx.inc), and the renderer
; (bs_show, bs_board, bs_feed, bs_hide) puts that on the screen. For now the play area stays
; black (bs_show clears it) and the renderer does nothing else. Silent for now: the effect each
; pass starts (pz_sfx) and the board's tune (pz_tune) are only recorded.

        include "puzl.inc"          ; the stage's places, sheet and VRAM coordinates (tools/msxpuzl.py)

; (Build checks, no bytes: msx.inc's wanted state keeps puzl.inc's shown-state layout up to the
; cells, and the visit's boards fit MP_B: an error here otherwise.)
        ds 0 - (pw_led - pz_want - PZ_ST_LED) * (pw_led - pz_want - PZ_ST_LED)
        ds 0 - (pw_timer - pz_want - PZ_ST_TIMER) * (pw_timer - pz_want - PZ_ST_TIMER)
        ds 0 - (pw_button - pz_want - PZ_ST_BUTTON) * (pw_button - pz_want - PZ_ST_BUTTON)
        ds 0 - (pw_light - pz_want - PZ_ST_LIGHT) * (pw_light - pz_want - PZ_ST_LIGHT)
        ds 0 - (pw_bar - pz_want - PZ_ST_BAR) * (pw_bar - pz_want - PZ_ST_BAR)
        ds 0 - (pw_tvk - pz_want - PZ_ST_CELL) * (pw_tvk - pz_want - PZ_ST_CELL)
        ds 0 - (pz_want + PW_LEN - 1 - pw_cimg) * (pz_want + PW_LEN - 1 - pw_cimg)
        ds 0 - (pz_boards + PZ_RECS_LEN_V1 - 1) / (MP_B + 0x0500)
        ds 0 - (pz_boards + PZ_RECS_LEN_V2 - 1) / (MP_B + 0x0500)

; $17100: the stage -> A = its result ($17100's D0): 0 solved, 1 failed, 2 out of time. It
; leaves through pz_done (rc2.asm: the trace harness's end) with A = the result, FRONT at 8000h.
bs_stage:
        call snd_stop               ; ($18000; $17D1A: $FE14's stop all)
        ld hl,pf_pal
        ld bc,32
        xor a
        call fill                   ; ($FE14: the palette black)
        ld hl,AM_START
        ld bc,AM_END - AM_START
        xor a
        call fill                   ; ($FE14 clear_game_vars: $B00-$16EB; $17D1A: $B00-$B21)
        xor a
        ld (g_keys),a               ; (clear_game_vars: $802D, $802E, $804D)
        ld (g_joy),a
        ld (g_lock),a
        ld hl,(AG + 0x8050)         ; the visit: the level done ($17156: cmpi.w #2,$8050 / bmi)
        ld de,2
        or a
        sbc hl,de
        ld hl,pzt_recs + PZ_RECS_V1 ; visit 1: the boards from $17448 (the immediate at $173D4) up
        ld bc,PZ_RECS_LEN_V1        ;   to $1775F,
        ld de,PZ_GFX_TV1            ;   Murphy's face (the immediate at $1729A)
        jp m,bs_v1
        ld hl,pzt_recs + PZ_RECS_V2 ; visit 2 (after level 2 on): the boards from $175C0,
        ld bc,PZ_RECS_LEN_V2
        ld de,PZ_GFX_TV2            ;   Ellen's face
bs_v1:  ld (pz_tv),de
        ld de,pz_boards
        ldir                        ; the boards in RAM (the original loads PUZL again each time)
        ld hl,pz_pal1
        ld (pz_pal),hl              ; (the immediate at $17B20; visit 2's own palette: milestone 3)
        call bs_show                ; the stage's screen, the palette black
        ld a,0xFF
        ld (pzv_fadein),a           ; ($17D1A: $B19 = 0, $B20 = FFh: a fade in)
        ld hl,0x0059
        call bs_timer               ; ($1710E: setup_timer($59), replaced by board 0's)
        xor a
        ld (g_paused),a             ; ($804E: no pause)
        ld hl,0xFFFE
        ld (pzv_board2),hl          ; ($1717E: $B0A = -2)

; $17184: the next board, or the end once the fourth is done.
bs_next:
        ld hl,(pzv_board2)
        inc hl
        inc hl                      ; D0 = $B0A + 2
        push hl
        ld de,9
        or a
        sbc hl,de
        pop hl
        ld a,0                      ; (the fourth board done: solved)
        jp p,bs_exit                ; (cmpi.w #9,D0 / bmi)
        srl h
        rr l                        ; (lsr.w #1: the board)
        ld a,l
        call bs_setup               ; $173D2
bs_loop:
        call bs_wait                ; ($171BA: the next pass)
        call hud_keep               ; ($8004, $8020: the panel's digits and messages; FRONT back)
        call sec_tick               ; ($1015E: the CIA-B's seconds; still in script builds)
pz_tick:
        call pz_frame               ; ($171C2-$1722F: the pass; the trace's sampling point)
        call bs_feed                ; (the renderer)
        ld hl,(pzv_endc)            ; $17230: the end checks
        ld a,h
        or l
        jr z,bse_n
        ld de,99
        or a
        sbc hl,de
        jp m,bs_loop                ; (the end sequence below 99: cmpi.w #$63,$B1A / bmi)
bse_n:  ld a,(pzv_done)
        ld hl,pzv_failed
        or (hl)
        jr z,bse_t
        ld a,6                      ; ($17264: solved or stuck: a fade out, effect 6 every pass)
        ld (pzv_sfx),a
        xor a
        ld (pzv_fadein),a
        ld a,(pzv_fade)
        or a
        jr nz,bs_loop
        ld a,(pzv_done)
        or a
        jr nz,bs_next               ; (solved: the next board)
        inc a                       ; (stuck: MEMORY MALFUNCTION)
        jr bs_exit
bse_t:  ld a,(AG + (0x804C ^ 1))
        or a
        jr z,bs_loop                ; (no time out)
        xor a
        ld (pzv_fadein),a           ; ($17254: a fade out)
        ld a,(pzv_fade)
        or a
        jr nz,bs_loop
        ld a,2                      ; (OUT OF TIME)
bs_exit:
        push af
        call bs_hide                ; (the display as the result's screen expects it)
        pop af
        jp pz_done                  ; (rc2.asm: a ret; nothing after it changes the mirror)

; ($171BA) The next 50 Hz tick: a VBLANK, at 60 Hz every sixth one skipped (front.asm fs_tick's
; rule and its fs_div), the renderer's work meanwhile. wf_n = the VBLANKs since the last pass, or
; since the timer's set-up (sec_tick counts real seconds with it).
bs_wait:
        ld a,(tick)
        ld b,a
bw_lp:  push bc
        call bs_feed
        pop bc
        ld a,(tick)
        cp b
        jr z,bw_lp
        ld a,(RG9SAV)
        and 2
        jr nz,bw_go                 ; (50 Hz)
        ld hl,fs_div
        inc (hl)
        ld a,(hl)
        cp 6
        jr c,bw_go
        ld (hl),0
        jr bs_wait                  ; (60 Hz: the sixth VBLANK skipped)
bw_go:  ld a,(tick)
        ld c,a
        ld hl,pz_last
        sub (hl)
        ld (wf_n),a
        ld (hl),c
        ret

; $F9DC setup_ciab_timer: HL = the time (H minutes, L seconds, BCD) -> $804A-$804B, no time out
; ($804C), the seconds counted from now (the CIA-B's TOD restarted: sec_n, pz_last).
bs_timer:
        ld (AG + 0x804A),hl         ; (the word $804A: the minutes in its high byte)
        xor a
        ld (AG + (0x804C ^ 1)),a
        ld (sec_n),a
        ld a,(tick)
        ld (pz_last),a
        ret

; $173D2: A = the board (0-3): its record's header (the cursor, the red chips, the timer, the
; tune), its 88 cells drawn (+ 10h taken off), a fade in. $B1A, $B16, $B1E and $B19 stay as
; they are (quirk 2).
bs_setup:
        ld c,a
        or a
        jr z,bsu_0
        ld a,5
        ld (pzv_sfx),a              ; (the new board's effect: not for the first)
bsu_0:  ld l,c
        ld h,0
        add hl,hl
        ld (pzv_board2),hl          ; $B0A = 2 x the board
        ld hl,pz_boards             ; (the immediate at $173D4)
        ld de,PZ_REC_LEN
        ld b,c
        inc b
        jr bsu_a
bsu_m:  add hl,de
bsu_a:  djnz bsu_m                  ; A4 = the board's record
        ld a,(hl)
        inc hl
        ld (pzv_col),a              ; $B0D (the high bytes stay 0)
        ld a,(hl)
        inc hl
        ld (pzv_row),a              ; $B0F
        ld a,(hl)
        inc hl
        ld (pzv_reds),a             ; $B11
        ld d,(hl)
        inc hl
        ld e,(hl)
        inc hl                      ; D0.w = the time, BCD MM SS
        ld a,(hl)
        inc hl
        ld (pz_tune),a              ; (the moveq's tune at $17440)
        push hl
        ex de,hl
        call bs_timer               ; ($8018)
        pop hl
        ld (pzv_cells + 2),hl       ; $B06 = A4: the cells (its high word stays 0)
        ld b,PZ_ROWS * PZ_COLS
bsu_c:  ld a,(hl)
        and 0x0F
        ld (hl),a
        inc hl
        djnz bsu_c
        call bs_board               ; (the 88 cells drawn: $1737A)
        ld a,0xFF
        ld (pzv_fadein),a           ; $B20 = FFh
        xor a
        ld (pzv_done),a             ; $B17 = 0
        ret                         ; (stop all, the tune: $18004, $18010)

; $171C2-$1722F: one pass, after its wait (tools/openmsx_rc2.tcl samples the mirror at pz_tick's
; call): the cursor's image, the fade, what the TV, the LED row and the timer show, the step,
; the counters, the decor, the joystick for the next pass's step.
pz_frame:
        ld a,(pzv_frame)
        and 0x1E
        ld e,a
        ld d,0
        ld hl,pzt_curofs
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld (pzv_curimg + 2),hl      ; $B12 = $17DE8 + word[$17194 + ($B00 & $1E)]
        call bs_fade                ; $17AF0
        call bs_tv                  ; $17298
        call bs_led                 ; $17944
        call bs_tmr                 ; $1797C
        call bs_step                ; $17760
        ld hl,(pzv_frame3)
        inc hl
        inc hl
        inc hl
        ld (pzv_frame3),hl          ; ($171F6: $B02 + 3)
        ld hl,(pzv_frame)
        inc hl
        ld (pzv_frame),hl           ; ($171FA: $B00 + 1)
        call bs_decor               ; $179FC
        call joy_read               ; ($801C: $802E for the next pass's step)
        ld hl,(tick_n)
        inc hl
        ld (tick_n),hl              ; (a JOY script goes on through the stage)
        ld a,(pzv_col)              ; the cursor the copper interrupt shows next ($17B5A: $B12,
        ld (pw_ccol),a              ;   $B0C, $B0E)
        ld a,(pzv_row)
        ld (pw_crow),a
        ld hl,(pzv_curimg + 2)
        add hl,hl
        add hl,hl
        ld a,h
        ld (pw_cimg),a              ; (the offset / 40h)
        ret

; $17AF0: the fade ($B19, 0-31: + 1 a pass while $B20 is set, else - 1; nothing more at either
; end), then pf_pal = the stage's palette with every component at most the step's cap (logic.asm
; pal_fade's rule: fade_cap[$B19 >> 2], the colour grade's limits of $B19 >> 1 & 1Eh; the
; VBLANK loads colours 1-15). At the end of a fade out the palette pointer goes back to visit 1's
; ($17B14: quirk 5).
bs_fade:
        ld a,(pzv_fadein)
        or a
        ld a,(pzv_fade)
        jr z,bfd_out
        cp 0x1F
        ret z
        inc a
        jr bfd_set
bfd_out:
        or a
        ret z
        dec a
        jr nz,bfd_set
        ld hl,pz_pal1
        ld (pz_pal),hl              ; (the immediate at $17B20 back to $17D6A)
bfd_set:
        ld (pzv_fade),a
        rrca
        rrca
        and 7
        ld e,a
        ld d,0
        ld hl,fade_cap
        add hl,de
        ld a,(hl)
        ld c,a                      ; the limit for B and G
        rlca
        rlca
        rlca
        rlca
        ld b,a                      ; the limit for R (bits 4-6)
        ld hl,(pz_pal)
        ld de,pf_pal
bfd_lp: ld a,(hl)
        and 0x70
        cp b
        jr c,bfd_r
        ld a,b
bfd_r:  ld (de),a                   ; R
        ld a,(hl)
        and 7
        cp c
        jr c,bfd_b
        ld a,c
bfd_b:  ex de,hl
        or (hl)
        ld (hl),a                   ; R | B
        ex de,hl
        inc hl
        inc de
        ld a,(hl)
        cp c
        jr c,bfd_g
        ld a,c
bfd_g:  ld (de),a                   ; G
        inc hl
        inc de
        ld a,e
        cp (pf_pal + 32) & 0xFF
        jr nz,bfd_lp
        ret

; $17298, what it draws: the face when ($B00 & the board's mask) = 0, else black, under the static
; frame ($B00 >> the board's shift) & 3; once the memory is restored the face alone (shift 0, mask
; 0). Counts the passes and those with the face, for the renderer's duty rule.
bs_tv:
        ld hl,(pzv_board2)
        ld de,pzt_masks
        add hl,de
        ld a,(pzv_frame)
        and (hl)
        ld c,PZ_TV_FACE
        jr z,btv_m
        ld c,PZ_TV_BLACK
btv_m:  ld de,pzt_shifts - pzt_masks
        add hl,de
        ld a,(hl)
        or a
        ld b,a
        ld a,PZ_TV_CLEAN
        jr z,btv_set
        ld a,(pzv_frame)
btv_sh: rrca
        djnz btv_sh
        and 3
        add a,c
btv_set:
        ld (pz_want),a
        ld hl,pw_tvk
        inc (hl)
        jr z,btv_x
        ld a,c
        cp PZ_TV_FACE
        ret nz
        inc hl
        inc (hl)                    ; (pw_tvf)
        ret
btv_x:  dec (hl)                    ; (both stay at FFh passes)
        ret

; $17944, what it draws: the LED position v = word[$179B6 + 2 ($B00 & 15)] gets the digit
; word[$179B6 + ($B02 & $1E)], when v is at least the board's threshold (word[$17972 + $B0A]).
bs_led:
        ld a,(pzv_frame)
        and 15
        add a,a
        ld e,a
        ld d,0
        ld hl,pzt_ledval
        add hl,de
        ld c,(hl)                   ; v, 0-8
        ld hl,(pzv_board2)
        ld de,pzt_ledthr
        add hl,de
        ld a,c
        sub (hl)
        ret c                       ; (v - the threshold < 0: bmi)
        ld a,(pzv_frame3)
        and 0x1E
        ld e,a
        ld d,0
        ld hl,pzt_ledval
        add hl,de
        ld a,(hl)                   ; the digit
        ld hl,pw_led
        ld e,c
        add hl,de
        ld (hl),a
        ret

; $1797C, what it draws: the timer's digits $804A & 15, $804B >> 4, $804B & 15.
bs_tmr:
        ld a,(AG + (0x804A ^ 1))
        and 15
        ld (pw_timer),a
        ld a,(AG + (0x804B ^ 1))
        ld c,a
        rrca
        rrca
        rrca
        rrca
        and 15
        ld (pw_timer + 1),a
        ld a,c
        and 15
        ld (pw_timer + 2),a
        ret

; $179FC, what it draws (after the counters' steps): the button's image ($B00 >> 3) & 1; the
; scanning light's image ($B00 >> 1) & 1 on row word[$17ADE + 2 (($B00 >> 3) & 7)] (rows 0 1 2
; 3 3 2 1 0); the board bar's image ($B02 >> 3) & 1 on row word[$17ADE + $B0A] (the board's, 3
; after the last).
bs_decor:
        ld a,(pzv_frame)
        ld c,a
        rrca
        rrca
        rrca
        and 1
        ld (pw_button),a
        ld a,c
        rrca
        rrca
        and 0x0E
        ld e,a
        ld d,0
        ld hl,pzt_rows
        add hl,de
        ld e,(hl)                   ; the light's row
        ld a,c
        rrca
        and 1
        ld hl,pw_light
        add hl,de
        ld (hl),a
        ld hl,(pzv_board2)
        ld de,pzt_rows
        add hl,de
        ld e,(hl)                   ; the bar's row
        ld d,0
        ld a,(pzv_frame3)
        rrca
        rrca
        rrca
        and 1
        ld hl,pw_bar
        add hl,de
        ld (hl),a
        ret

; $17760: the game. A time out starts the end ("TIMEOUT.", on every pass while $804C is set:
; quirk 3); an end sequence only counts ($B1A, the cursor hidden). Else: the effect asked for; the
; cursor's cell (a red chip: + 100, effect 3, one less; burnt: + 10h); the fourth board's end
; ("MEMORY RESTORED."); a move on a change of the joystick byte ($802E against $B1E, fire
; included: the lowest direction bit; refused past the edge, onto an IC or a burnt cell); with no
; move tried, the stuck test ("MALFUNCTION." with red chips left).
bs_step:
        xor a
        ld (pz_sfx),a
        ld a,(AG + (0x804C ^ 1))
        or a
        jr z,bst_e
        ld a,HUD_MSG_17738
        call game_msg               ; ($8008: "TIMEOUT.")
        ld hl,(pzv_endc)
        inc hl
        ld (pzv_endc),hl
bst_e:  ld hl,(pzv_endc)
        ld a,h
        or l
        jr z,bst_go
        inc hl
        ld (pzv_endc),hl            ; (the end sequence: $B1A + 1,
        ld hl,0x0200
        ld (pzv_curimg + 2),hl      ;  $B12 = $17FE8: no cursor)
        ret
bst_go: ld a,(pzv_sfx)
        or a
        jr z,bst_c
        ld (pz_sfx),a               ; ($18014: the effect asked for)
        xor a
        ld (pzv_sfx),a
bst_c:  ld a,(pzv_col)
        ld e,a                      ; D0 = $B0C
        ld a,(pzv_row)
        ld d,a                      ; D1 = $B0E
        call bs_cell                ; $178E8: HL = the cursor's cell, A = its value
        or a
        jr nz,bst_b
        push de
        push hl
        ld de,0x0100
        call add_score              ; ($800C: a red chip destroyed, + 100)
        ld a,3
        ld (pzv_sfx),a
        ld hl,(pzv_reds)
        dec hl
        ld (pzv_reds),hl
        ld a,h
        or l
        ld a,0
        jr nz,bst_d
        dec a
bst_d:  ld (pzv_done),a             ; (seq: no red chip left)
        pop hl
        pop de
        xor a
bst_b:  or 0x10
        ld (hl),a                   ; (burnt, every pass; the renderer draws the board's cells)
        ld a,(pzv_done)
        or a
        jr z,bst_j
        ld hl,(pzv_board2)
        ld bc,6
        or a
        sbc hl,bc
        jr nz,bst_j
        ld hl,8
        ld (pzv_board2),hl          ; (the fourth board done)
        ld hl,(pzv_endc)
        inc hl
        ld (pzv_endc),hl
        ld a,(msg_wr)               ; (message_queue returns D0 = its write index & $C as it was:
        and 6                       ;  msg_wr counts in steps of 2)
        add a,a
        push af
        ld a,HUD_MSG_1774E
        call game_msg               ; ($8008: "MEMORY RESTORED.")
        pop af
        ld e,a                      ; (quirk 1: a move this pass starts from that column)
        ld a,(pzv_row)
        ld d,a
bst_j:  ld a,(g_joy)
        ld hl,pzv_prevjoy
        cp (hl)
        jr z,bst_s                  ; (no change: no move)
        ld (hl),a                   ; $B1E = $802E
        rrca
        jr c,bst_up
        rrca
        jr c,bst_dn
        rrca
        jr c,bst_lt
        rrca
        jr nc,bst_s                 ; (a change without a direction)
        ld a,e                      ; right
        cp 10
        ret z
        inc e
        jr bst_h
bst_lt: ld a,e
        or a
        ret z
        dec e
bst_h:  call bs_blk
        ret nz
        ld l,e
        ld h,0
        ld (pzv_col),hl             ; $B0C = D0
        jr bst_m
bst_up: ld a,d
        or a
        ret z
        dec d
        jr bst_v
bst_dn: ld a,d
        cp 7
        ret z
        inc d
bst_v:  call bs_blk
        ret nz
        ld l,d
        ld h,0
        ld (pzv_row),hl             ; $B0E = D1
bst_m:  ld a,4
        ld (pzv_sfx),a              ; (the move's effect, the next pass)
        ret
bst_s:  call bs_stuck               ; $178A4
        ret nz
        ld a,(pzv_done)
        or a
        ret nz
        ld a,HUD_MSG_17741
        call game_msg               ; ($8008: "MALFUNCTION.")
        ld hl,(pzv_endc)
        inc hl
        ld (pzv_endc),hl
        ld a,0xFF
        ld (pzv_failed),a
        ret

; $178E8: E = D0 (a column), D = D1 (a row) -> HL = its cell, $B06 + 11 D1 + D0 (no bounds
; check: quirk 1's columns reach 3 bytes past the 88 cells), A = the cell. Keeps DE.
bs_cell:
        ld a,d
        add a,a
        add a,a
        add a,d
        add a,a
        add a,d                     ; 11 D1
        add a,e
        ld hl,(pzv_cells + 2)
        add a,l
        ld l,a
        jr nc,bcl_n
        inc h
bcl_n:  ld a,(hl)
        ret

; ($178E8's test) E, D = a cell -> NZ (A = FFh) when blocked: burnt ((signed byte)(the cell -
; 10h) >= 0: cmpi.b #$10 / bpl) or an IC (1); Z (A = 0) when free. Keeps DE.
bs_blk: call bs_cell
        cp 0x10
        jp p,bbk_y
        cp 1
        jr z,bbk_y
        xor a
        ret
bbk_y:  ld a,0xFF
        or a
        ret

; $178A4: E, D = the cursor -> Z when it is stuck: no neighbour inside the board free (left,
; right, up, down). Keeps DE.
bs_stuck:
        ld a,e
        or a
        jr z,bsk_r
        dec e
        call bs_blk
        inc e
        or a
        jr z,bsk_f
bsk_r:  ld a,e
        cp 10
        jr z,bsk_u
        inc e
        call bs_blk
        dec e
        or a
        jr z,bsk_f
bsk_u:  ld a,d
        or a
        jr z,bsk_d
        dec d
        call bs_blk
        inc d
        or a
        jr z,bsk_f
bsk_d:  ld a,d
        cp 7
        jr z,bsk_y
        inc d
        call bs_blk
        dec d
        or a
        jr z,bsk_f
bsk_y:  xor a                       ; (stuck)
        ret
bsk_f:  inc a                       ; (a free neighbour)
        ret

; ----- the display -----

; The stage's screen at its entry, the palette black: for now page 0's play area black (the
; intro's text gone: front.asm fs_clear; done before the fade in starts); nothing drawn yet in
; the wanted state.
bs_show:
        ld hl,fs_clear
        call vdp_cmd
        call vdp_wait
        ld hl,pz_want
        ld bc,PW_LEN
        ld a,PZ_ST_NONE
        call fill
        xor a
        ld (pw_tvk),a
        ld (pw_tvf),a
        ret

; A board's set-up ($173D2, the palette black): its 88 cells into both pages (the renderer).
bs_board:
        ret

; The renderer's state machine: called while bs_wait waits and after each pass.
bs_feed:
        ret

; The stage's end: the VDP idle, the display as the result's screen expects it.
bs_hide:
        jp vdp_wait

; ----- data -----

pz_pal1:
        incbin "puzl_1_grade.pal"   ; the stage's 16 colours, through the colour grade (tools/mkrom.py)
pz_cursor:
        incbin "puzl_cursor.spr"    ; the cursor's 9 sprite patterns (tools/msxpuzl.py)
        include "puzl_tab.inc"      ; PUZL's boards, messages and tables (tools/msxpuzl.py)
