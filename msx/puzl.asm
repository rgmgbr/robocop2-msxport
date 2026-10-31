; Brainstorm, the bonus stage after level 1 (the Amiga's PUZL at $17100, which $8382 calls:
; docs/BRAINSTORM.md). Bank BANK_PUZL at A000h while it runs, FRONT at 8000h (front.asm
; front_bonus calls bs_stage); its graphics in the data banks from PUZL_GFX_BANK, and visit 2's
; TV pictures (Ellen's face) from PUZL_TV2_BANK (tools/mkrom.py, tools/msxpuzl.py --visits 1,2;
; docs/LEVEL2.md 3.9). Visit 2's own code is out of line (bs_v2, at the end), so that visit 1
; runs the code it ran before, instruction for instruction: its timing, pictures and VRAM as
; they were.
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
; (bs_show at the entry, bs_board at a set-up, bs_feed between the passes, bs_hide at the exit)
; puts that on the screen: the original's art 1:1 in the 256 x 162 play area, double-buffered on
; pages 0 and 1, the cursor as hardware sprites, the HUD below as in the game (docs/BRAINSTORM.md
; 3.3).
;
; The sound (msx/tune.asm, in BANK_MUSIC, ticked by the VBLANK interrupt: docs/BRAINSTORM.md 3.6):
; a board's set-up ends with PZM tune 1 from its start after the stop all ($1743A, $17442: tune.asm
; tn_pzm through mus_call), whose tick 0 waits for the next pass and plays with its request; the
; step sends the pass's pending request with snd_bfx where $17794 starts it (pz_sfx keeps it for
; the traces). Neither writes the mirror, so the traces are those of the silent stage.

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
        ld hl,pzt_recs + PZ_RECS_V2 ; visit 2 (after level 2 on): the boards from $175C0, then
        ld bc,PZ_RECS_LEN_V2        ;   its palette and Ellen's face (bs_v2: out of line, back
        jp bs_v2                    ;   at bs_vr)
bs_v1:  ld (pz_tv),de
        ld de,pz_boards
        ldir                        ; the boards in RAM (the original loads PUZL again each time)
        ld hl,pz_pal1
        ld (pz_pal),hl              ; (the immediate at $17B20)
        call bs_show                ; the stage's screen, the palette black
bs_vr:  ld a,0xFF
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
bsu_t:  ld hl,tn_pzm                ; ($1743A stop all, $17442 the tune: pz_tune, 1 in every record:
        jp mus_call                 ;  PZM tune 1, msx/tune.asm; its tick 0 after the next pass)

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
        call snd_bfx                ; (from the next tick, $1822C's rule there)
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

; ($17794: jsr $18014) A = the pass's request ($B04: 3, 4, 5 or 6) to msx/tune.asm: that effect
; from its next tick on (tn_go: $1822C's rule there); of two requests before a tick the higher one,
; the one the Amiga lets sound. The ticks run again (fx_act: the tune may be over). RAM only, so
; it needs no bank. Uses AF, HL.
snd_bfx:
        ld hl,tn_req
        cp (hl)
        ret c
        ld (hl),a
        ld a,2
        ld (fx_act),a
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

; The play area is double-buffered (docs/BRAINSTORM.md 3.3): display page 0 with sprite set A,
; page 1 with set B, each published at a VBLANK by a register list (bs_list, as front.asm fs_list
; does), the HUD below through the split as in the game. Each page keeps the state it shows
; (rd_st0, rd_st1: puzl.inc's PZ_ST_ layout); a build brings the page not shown to the wanted
; state (pz_want, the board's cells) with one HMMM an element that differs, from the sheet (page
; 0 lines 162-217) or the TV pictures (page 2), then writes its set's SAT (the cursor) and
; publishes it; that page is then shown, and the next build goes to the other one. A page is
; never drawn while it shows (only a board's set-up draws both, with the palette black), so no
; block shows half drawn, and every change reaches each page once, at its next build. The VDP's
; commands go through vdp_cmd (cmd_lock; never cmdbuf, which the tile engine keeps); the VRAM
; streams set their address with vram_write and end with vram_done.

; The stage's screen at its entry (bs_stage), the play area black (pf_pal 0) with the intro's
; list on screen (page 0, sprites off): the screen and the sheet into page 0, page 0's play area
; copied to page 1, the visit's TV pictures into page 2, the cursor's patterns and both sets'
; colour rows (sprite 0 the cursor's colour, sprite 1 image 2's second colour), both SATs empty;
; nothing drawn yet in the wanted state nor in either page's.
RD_SAT_A:   equ SPR_COL_A + 0x200   ; the SATs of sprite sets A (page 0) and B (page 1)
RD_SAT_B:   equ SPR_COL_B + 0x200
bs_show:
        call vdp_wait
        ld hl,PZ_GFX_SCREEN
        call rd_at
        push hl
        ld e,0
        ld hl,0
        call vram_write             ; page 0 from its first line: the screen, then the sheet
        pop hl
        ld bc,PZ_GFX_PAGE0
        call rd_rom
        call vram_done
        ld hl,rd_cp01
        call vdp_cmd                ; page 0's play area to page 1
        ld hl,(pz_tv)
        call rd_at                  ; the visit's 9 TV pictures (TV_STATES order) into page 2:
bsw_tv: ld de,0                     ;   picture n at (80 (n % 3), 80 (n / 3)), a line at a time
        ld c,3
bsw_r:  push bc
        push de                     ; (a row of pictures)
        ld b,3
bsw_p:  push bc
        push de                     ; (a picture)
        ld b,PZ_TV_W
bsw_l:  push bc
        push de
        push hl
        ex de,hl
        ld e,PZ_TV_VRAM >> 16
        call vram_write
        pop hl
        ld b,PZ_TV_LINE
        call rd_line
        call vram_done
        pop de
        push hl
        ld hl,PZ_LINE_BYTES
        add hl,de
        ex de,hl                    ; (its next line)
        pop hl
        pop bc
        djnz bsw_l
        pop de
        push hl
        ld hl,PZ_TV_LINE
        add hl,de
        ex de,hl                    ; (the next picture of the row)
        pop hl
        pop bc
        djnz bsw_p
        pop de
        push hl
        ld hl,PZ_LINE_BYTES * PZ_TV_W
        add hl,de
        ex de,hl                    ; (the next row)
        pop hl
        pop bc
        dec c
        jr nz,bsw_r
        ld a,BANK_FRONT
        call bank_8000              ; (FRONT at 8000h again)
        ld e,SPR_PAT >> 16
        ld hl,SPR_PAT & 0xFFFF
        call vram_write             ; the cursor's patterns from slot 0 (sprites.asm's slots: the
        ld hl,pz_cursor             ;  level's start forgets them, cold.asm spr_init)
        ld de,PZ_CUR_PATS * 32
bsw_s:  ld a,(hl)
        out (VDP_DATA),a
        inc hl
        dec de
        ld a,d
        or e
        jr nz,bsw_s
        call vram_done
        ld hl,(AG + 0x8050)         ; the cursor's colours: the visit's (bs_stage's test)
        ld de,2
        or a
        sbc hl,de
        ld bc,PZ_CUR_COL_1 * 256 + PZ_CUR_COL2_1
        jp m,bsw_c
        ld bc,PZ_CUR_COL_2 * 256 + PZ_CUR_COL2_2
bsw_c:  ld hl,SPR_COL_A & 0xFFFF
        call rd_cols
        ld hl,SPR_COL_B & 0xFFFF
        call rd_cols
        ld hl,RD_SAT_A & 0xFFFF
        call rd_hide
        ld hl,RD_SAT_B & 0xFFFF
        call rd_hide
        ld hl,pz_want
        ld bc,PW_LEN
        ld a,PZ_ST_NONE
        call fill                   ; nothing drawn yet
        xor a
        ld (pw_tvk),a
        ld (pw_tvf),a
        ld hl,rd_st0
        ld bc,PZ_ST_LEN
        ld a,PZ_ST_NONE
        call fill
        ld hl,rd_st1
        ld bc,PZ_ST_LEN
        ld a,PZ_ST_NONE
        call fill                   ; both pages: the screen's own pixels
        ld hl,rd_cmd
        ld bc,15
        xor a
        call fill
        ld a,0xD0
        ld (rd_cmd + 14),a          ; (HMMM; the high bytes of SX, DX, NX and NY stay 0)
        xor a
        ld (rd_state),a
        ld (rd_shown),a             ; (the intro's list: page 0)
        ld (rd_acc),a
        ld (rd_face),a
        ld hl,(pzv_frame)
        ld (rd_fr),hl               ; (the first build after the first pass)
        dec a
        ld (rd_tvw),a
        ret

rd_cp01:
        dw 0, 0, 0, PZ_PAGE_B, 256, PZ_SCREEN_LINES    ; SX, SY, DX, DY, NX, NY
        db 0, 0, 0xD0                                   ; HMMM

; HL = an offset in puzl_gfx.bin -> its bank at 8000h (rd_bank), HL = its address there.
rd_at:  ld a,h
        rlca
        rlca
        rlca
        and 7
        add a,PUZL_GFX_BANK
rd_at1: ld (rd_bank),a
        call bank_8000
        ld a,h
        and 0x1F
        or 0x80
        ld h,a
        ret

; BC = bytes from HL (rd_bank at 8000h) to port 98h: rd_line's pieces of 128 at most.
rd_rom: ld a,b
        or c
        ret z
        ld a,b
        or a
        ld a,128
        jr nz,rr_n                  ; (256 or more left)
        ld a,c
        cp 128
        jr c,rr_n
        ld a,128
rr_n:   push bc
        push af
        ld b,a
        call rd_line
        pop af
        pop bc
        ld e,a
        ld a,c
        sub e
        ld c,a
        jr nc,rd_rom
        dec b
        jr rd_rom

; B = bytes (1-128) from HL (rd_bank at 8000h) to port 98h, the next bank from A000h on (no OTIR
; reads past 9FFFh: BANK_PUZL holds A000h) -> HL = the next byte's place (rd_bank). Changes D, E.
rd_line:
        ld a,h
        cp 0x9F
        jr c,rl_all                 ; (256 bytes or more to the window's end)
        ld a,l
        neg                         ; (those left: 256 - L)
        jr z,rl_all
        cp b
        jr nc,rl_all
        ld e,a
        ld a,b
        sub e
        ld d,a                      ; (the rest, from the next bank)
        ld b,e
        ld c,VDP_DATA
        otir
        call rl_nb
        ld b,d
rl_all: ld c,VDP_DATA
        otir
        ld a,h
        cp 0xA0
        ret nz
rl_nb:  ld a,(rd_bank)
        inc a
        ld (rd_bank),a
        call bank_8000
        ld hl,0x8000
        ret

; HL = a colour table's low 16 bits (page 3), B, C = the colours of sprites 0 and 1: their 16
; rows each.
rd_cols:
        ld e,SPR_COL_A >> 16
        call vram_write
        ld a,b
        call rdc_16
        ld a,c
        call rdc_16
        jp vram_done
rdc_16: ld e,16
rdc_lp: out (VDP_DATA),a
        dec e
        jr nz,rdc_lp
        ret

; HL = a SAT's low 16 bits (page 3): its first entry Y = 216, no sprite.
rd_hide:
        ld e,RD_SAT_A >> 16
        call vram_write
        ld a,216
        out (VDP_DATA),a
        jp vram_done

; A board's set-up ($173D2, the palette black: the fade out reached 0, or the entry): its 88 cells
; into both pages at once, the one on screen included (the fade in never shows the last board),
; and in both pages' states; the cursor at the board's start from the next picture on (the copper
; interrupt $17B5A reads $B0C and $B0E as the set-up left them). The passes wait meanwhile; a
; build goes on afterwards.
bs_board:
        ld a,(pzv_col)
        ld (pw_ccol),a
        ld a,(pzv_row)
        ld (pw_crow),a
        ld hl,(pzv_cells + 2)
        ld a,PZ_ST_CELL
bbd_lp: push hl
        push af
        ld e,a
        ld d,0
        ld a,(hl)
        and 0x1F
        ld c,a                      ; its tile
        ld hl,rd_st0
        add hl,de
        ld (hl),c
        ld hl,rd_st1
        add hl,de
        ld (hl),c
        ld a,e
        call rd_mk
        xor a
        call rd_go                  ; page 0
        ld a,1
        call rd_go                  ; page 1
        pop af
        pop hl
        inc hl
        inc a
        cp PZ_ST_LEN
        jr nz,bbd_lp
        ret

; A = a page: rd_cmd into it (vdp_cmd waits for the command before).
rd_go:  ld (rd_cmd + 7),a           ; (DY's high byte: the page)
        ld hl,rd_cmd
        jp vdp_cmd

; The renderer's state machine, called while bs_wait waits and after each pass; it never waits for
; the VDP. Idle: after a pass, with the VDP idle, a build of the page not shown starts (its TV
; picture by the duty rule). Building: with the VDP idle, one HMMM for the next element whose
; wanted state differs from the page's (that page's state updated); none left: the cursor into
; the page's sprite set, its list published. Published: once that list is on screen (app_seq),
; the page is the one shown; idle again.
bs_feed:
        ld a,(rd_state)
        dec a
        jr z,bf_bld
        dec a
        jr z,bf_pub
        ld hl,(pzv_frame)
        ld de,(rd_fr)
        or a
        sbc hl,de
        ret z                       ; (no pass since the last build: nothing new)
        call vdp_busy
        ret nz
        ld hl,(pzv_frame)
        ld (rd_fr),hl
        call rd_tvp
        ld a,(rd_shown)
        xor 1
        ld (rd_page),a
        xor a
        ld (rd_elem),a
        inc a
        ld (rd_state),a
bf_bld: call vdp_busy
        ret nz
        call rd_next
        jr c,bf_end
        ld (hl),c                   ; (the page shows it once this command ran)
        call rd_mk
        ld hl,rd_cmd
        jp vdp_cmd
bf_end: call rd_sat
        call bs_list
        ld a,2
        ld (rd_state),a
        ret
bf_pub: ld a,(app_seq)
        ld b,a
        ld a,(pub_seq)
        cp b
        ret nz                      ; (not on screen yet)
        ld a,(rd_page)
        ld (rd_shown),a
        xor a
        ld (rd_state),a
        ret

; The TV picture of a build (rd_tvw) from the passes since the last one (pw_tvk of them, pw_tvf
; with the face: taken here). The face shows when acc + f/k >= 1/2, then acc += f/k - shown (in
; 1/256: acc stays within -128..127), under the newest pass's static frame: board 2's face, every
; other pass, keeps its half duty when a picture covers two passes; with a picture a pass this is
; the original's sequence. Once the memory is restored, the face alone.
rd_tvp: ld a,(pz_want)
        cp PZ_ST_NONE
        ret z                       ; (no pass yet)
        ld d,a
        ld a,(pw_tvk)
        ld c,a
        ld a,(pw_tvf)
        ld h,a
        xor a
        ld (pw_tvk),a
        ld (pw_tvf),a
        ld a,d
        cp PZ_TV_CLEAN
        jr nc,rtp_s
        and 3
        ld d,a                      ; (the newest static frame)
        ld a,c
        or a
        jr z,rtp_f                  ; (no pass since the last build: its decision again)
        ld l,0                      ; HL = f x 256
        call rd_div                 ; HL = f x 256 / k
        ld a,(rd_acc)
        ld c,a
        rla
        sbc a,a
        ld b,a
        add hl,bc                   ; t = acc + f/k
        ld a,h
        or a
        jp m,rtp_n
        jr nz,rtp_y                 ; (256 or more)
        ld a,l
        cp 128
        jr c,rtp_n
rtp_y:  ld a,l
        ld (rd_acc),a               ; (t - 256)
        ld a,1
        jr rtp_d
rtp_n:  ld a,l
        ld (rd_acc),a               ; (t)
        xor a
rtp_d:  ld (rd_face),a
rtp_f:  ld a,(rd_face)
        or a
        ld a,PZ_TV_BLACK
        jr z,rtp_b
        ld a,PZ_TV_FACE
rtp_b:  add a,d
rtp_s:  ld (rd_tvw),a
        ret

; HL / C (C 1-255) -> HL. Changes A, B.
rd_div: xor a
        ld b,16
rdv_l:  add hl,hl
        rla
        jr c,rdv_s
        cp c
        jr c,rdv_n
rdv_s:  sub c
        inc l
rdv_n:  djnz rdv_l
        ret

; -> the build's next element whose wanted value (not FFh: never drawn) differs from the page's:
; NC, A = the element, C = its value, HL = its byte in the page's state (rd_elem past it); carry
; when none is left. Elements: the TV (rd_tvw), pz_want's LEDs, timer, button, lights and bars,
; then the board's 88 cells (their tiles).
rd_next:
        ld a,(rd_page)
        or a
        ld hl,rd_st0
        jr z,rn_p
        ld hl,rd_st1
rn_p:   ld a,(rd_elem)
        ld e,a
        ld d,0
        add hl,de                   ; HL = its byte in the page's state
        or a
        jr nz,rn_w
        ld a,(rd_tvw)
        ld c,a
        inc a
        jr z,rn_t                   ; (no TV picture yet)
        ld a,c
        cp (hl)
        jr nz,rn_hit
rn_t:   inc hl
        inc e
rn_w:   ld a,e
        cp PZ_ST_CELL
        jr nc,rn_c
        push hl
        ld hl,pz_want
        add hl,de
        ex de,hl                    ; DE = its wanted byte
        pop hl
        neg
        add a,PZ_ST_CELL
        ld b,a
rn_wl:  ld a,(de)
        ld c,a
        inc a
        jr z,rn_wn                  ; (never drawn)
        ld a,c
        cp (hl)
        jr nz,rn_hit
rn_wn:  inc de
        inc hl
        djnz rn_wl
        ld e,PZ_ST_CELL
rn_c:   ld a,e
        cp PZ_ST_LEN
        ccf
        ret c                       ; (none left)
        push hl
        ld hl,(pzv_cells + 2)
        ld d,0
        add hl,de
        ld de,0 - PZ_ST_CELL
        add hl,de
        ex de,hl                    ; DE = its cell
        pop hl
        neg
        add a,PZ_ST_LEN
        ld b,a
rn_cl:  ld a,(de)
        and 0x1F
        cp (hl)
        jr nz,rn_hc
        inc de
        inc hl
        djnz rn_cl
        scf
        ret
rn_hc:  ld c,a
rn_hit: ld a,(rd_page)
        or a
        ld a,l
        jr nz,rn_h1
        sub rd_st0 & 0xFF
        jr rn_h
rn_h1:  sub rd_st1 & 0xFF
rn_h:   ld e,a
        inc a
        ld (rd_elem),a
        ld a,e
        or a                        ; (NC)
        ret

; A = an element, C = its value -> rd_cmd: the HMMM that draws it into the page being built
; (rd_page: DY's high byte), from the TV pictures (page 2) or the sheet (page 0).
rd_mk:  ld b,0
        or a
        jr nz,rmk_l
        ld hl,rd_tvsrc              ; the TV: picture C
        add hl,bc
        add hl,bc
        add hl,bc
        ld a,(hl)
        ld (rd_cmd),a
        inc hl
        ld a,(hl)
        ld (rd_cmd + 2),a
        inc hl
        ld a,(hl)
        ld (rd_cmd + 3),a           ; (SY: page 2)
        ld a,PZ_TV_X
        ld e,PZ_TV_Y
        ld bc,PZ_TV_W * 256 + PZ_TV_W
        jp rmk_put
rmk_l:  cp PZ_ST_TIMER
        jr nc,rmk_t
        dec a                       ; an LED position: digit C
        add a,a
        add a,a
        add a,a
        add a,PZ_LED_X
        ld e,PZ_LED_Y
        jr rmk_dg
rmk_t:  cp PZ_ST_BUTTON
        jr nc,rmk_b
        sub PZ_ST_TIMER             ; a timer digit
        ld e,a
        ld d,0
        ld hl,rd_tmx
        add hl,de
        ld a,(hl)
        ld e,PZ_TIMER_Y
rmk_dg: ld d,a
        ld a,c
        add a,a
        add a,a
        add a,a
        add a,PZ_DIGIT_SX
        ld l,PZ_DIGIT_SY
        ld bc,PZ_DIGIT_W * 256 + PZ_DIGIT_H
        jr rmk_sh
rmk_b:  cp PZ_ST_LIGHT
        jr nc,rmk_lb
        ld a,c                      ; the button: image C
        rrca
        rrca
        rrca
        and 0x20
        add a,PZ_BUTTON_SX
        ld l,PZ_BUTTON_SY
        ld d,PZ_BUTTON_X
        ld e,PZ_BUTTON_Y
        ld bc,PZ_BUTTON_W * 256 + PZ_BUTTON_H
        jr rmk_sh
rmk_lb: cp PZ_ST_CELL
        jr nc,rmk_c
        cp PZ_ST_BAR
        jr nc,rmk_br
        sub PZ_ST_LIGHT             ; a light's row: image C
        add a,a
        add a,a
        add a,a
        add a,PZ_ROW_Y
        ld e,a
        ld a,c
        add a,a
        add a,a
        add a,a
        add a,PZ_LIGHT_SX
        ld l,PZ_LIGHT_SY
        ld d,PZ_LIGHT_X
        ld bc,PZ_LIGHT_W * 256 + PZ_LIGHT_H
        jr rmk_sh
rmk_br: sub PZ_ST_BAR               ; a bar's row: image C
        add a,a
        add a,a
        add a,a
        add a,PZ_ROW_Y
        ld e,a
        ld a,c
        add a,a
        add a,c
        add a,a
        add a,a
        add a,a
        add a,PZ_BAR_SX
        ld l,PZ_BAR_SY
        ld d,PZ_BAR_X
        ld bc,PZ_BAR_W * 256 + PZ_BAR_H
        jr rmk_sh
rmk_c:  sub PZ_ST_CELL              ; a cell: tile C
        ld e,PZ_CELL_Y
rmk_cr: cp PZ_COLS
        jr c,rmk_cc
        sub PZ_COLS
        ld d,a
        ld a,e
        add a,PZ_CELL_W
        ld e,a
        ld a,d
        jr rmk_cr
rmk_cc: add a,a
        add a,a
        add a,a
        add a,a
        add a,PZ_CELL_X
        ld d,a
        ld a,c
        and 0x10
        add a,PZ_CHIP_SY
        ld l,a
        ld a,c
        add a,a
        add a,a
        add a,a
        add a,a
        add a,PZ_CHIP_SX
        ld bc,PZ_CELL_W * 256 + PZ_CELL_W
; A = SX, L = SY (the sheet, page 0), D = DX, E = DY (in the page), B = NX, C = NY
rmk_sh: ld (rd_cmd),a
        ld a,l
        ld (rd_cmd + 2),a
        xor a
        ld (rd_cmd + 3),a
        ld a,d
; A = DX, E = DY (in the page), B = NX, C = NY
rmk_put:
        ld (rd_cmd + 4),a
        ld a,e
        ld (rd_cmd + 6),a
        ld a,(rd_page)
        ld (rd_cmd + 7),a
        ld a,b
        ld (rd_cmd + 8),a
        ld a,c
        ld (rd_cmd + 10),a
        ret

rd_tvsrc:                           ; per TV picture its place in page 2: SX, SY
        db PZ_TV0_SX
        dw PZ_TV0_SY
        db PZ_TV1_SX
        dw PZ_TV1_SY
        db PZ_TV2_SX
        dw PZ_TV2_SY
        db PZ_TV3_SX
        dw PZ_TV3_SY
        db PZ_TV4_SX
        dw PZ_TV4_SY
        db PZ_TV5_SX
        dw PZ_TV5_SY
        db PZ_TV6_SX
        dw PZ_TV6_SY
        db PZ_TV7_SX
        dw PZ_TV7_SY
        db PZ_TV8_SX
        dw PZ_TV8_SY
rd_tmx: db PZ_TMIN_X, PZ_TTEN_X, PZ_TUNIT_X     ; the timer digits' x

; The cursor into the SAT of the page's set ($17B5A's sprite 0 over cell ($B0C, $B0E)): sprite 0
; its image's colour-3 pixels, sprite 1 image 2's colour-2 pixels, then Y = 216; nothing (Y = 216
; first) in the end sequences ($B12 = $17FE8: the original's junk sprite is not shown).
rd_sat: ld a,(rd_page)
        or a
        ld hl,RD_SAT_A & 0xFFFF
        jr z,rs_a
        ld hl,RD_SAT_B & 0xFFFF
rs_a:   ld e,RD_SAT_A >> 16
        call vram_write
        ld a,(pw_cimg)
        cp 8
        jr nc,rs_end                ; (no cursor)
        ld e,a
        ld d,0
        ld hl,rd_cura
        add hl,de
        ld b,(hl)
        ld hl,rd_curb
        add hl,de
        ld c,(hl)                   ; (sprite 1's pattern, FFh: none)
        ld a,(pw_crow)
        and 15
        add a,a
        add a,a
        add a,a
        add a,a
        add a,PZ_SAT_Y
        ld d,a
        ld a,(pw_ccol)
        and 15
        add a,a
        add a,a
        add a,a
        add a,a
        add a,PZ_SAT_X
        ld e,a
        call rs_one
        ld b,c
        inc c
        call nz,rs_one
rs_end: ld a,216
        out (VDP_DATA),a
        jp vram_done
rs_one: ld a,d                      ; Y, X, 4 x the pattern, 0 (each nop keeps 18 T or more
        out (VDP_DATA),a            ;  between two VRAM writes, as sprites.asm's OUTIs: 17 T is
        ld a,e                      ;  too fast for the VDP with a 5.37 MHz Z80, the turbo of
        nop                         ;  some MSX2+ and FPGA machines)
        out (VDP_DATA),a
        ld a,b
        add a,a
        add a,a
        out (VDP_DATA),a
        xor a
        nop
        out (VDP_DATA),a
        ret

rd_cura:                            ; per cursor image sprite 0's pattern,
        db PZ_CURA_0, PZ_CURA_1, PZ_CURA_2, PZ_CURA_3, PZ_CURA_4, PZ_CURA_5, PZ_CURA_6, PZ_CURA_7
rd_curb:                            ;   sprite 1's (FFh: none)
        db PZ_CURB_0, PZ_CURB_1, PZ_CURB_2, PZ_CURB_3, PZ_CURB_4, PZ_CURB_5, PZ_CURB_6, PZ_CURB_7

; The register list of the page built (front.asm fs_list's, with the sprites on): its page and
; sprite set, unscrolled; the split shows the HUD as in the game.
bs_list:
        call next_list
        push hl
        inc hl
        ld (hl),14                  ; 7 registers (10 on the V9958)
        inc hl
        ex de,hl
        ld hl,rd_regs
        ld bc,8
        ldir
        ex de,hl
        ld a,(rd_page)
        or a
        ld bc,R2_PAGE0 * 256 + R5_SET_A
        jr z,bl_a
        ld bc,R2_PAGE1 * 256 + R5_SET_B
bl_a:   ld (hl),b
        inc hl
        ld (hl),0x82
        inc hl
        ld (hl),0
        inc hl
        ld (hl),0x92                ; R#18
        inc hl
        ld (hl),c
        inc hl
        ld (hl),0x85
        inc hl
        ld a,(vdp_id)
        cp 2
        jp nz,list_tail
        ex (sp),hl
        inc hl
        ld (hl),20
        dec hl
        ex (sp),hl
        ld b,3
        ld a,0x99
bl_58:  ld (hl),0                   ; V9958: R#25-R#27 = 0 (one page, unscrolled)
        inc hl
        ld (hl),a
        inc hl
        inc a
        djnz bl_58
        jp list_tail
rd_regs:
        db 0, 0x97                  ; R#23 first (isr.asm iv_list: the split's R#19 from it)
        db SPLIT_LINE, 0x93         ; R#19: the HUD's split
        db R1_ON, 0x81
        db R8_SPR_ON, 0x88

; The stage's end: the VDP idle and the last list published on screen (front.asm fe_text then
; shows page 0 with the sprites off); both SATs empty; page 2's tiles back (cold.asm
; tiles_upload, the same bytes vdp_setup wrote: the title uploads them again in the product,
; script builds have no title).
bs_hide:
        call vdp_wait
bh_w:   ld a,(app_seq)
        ld b,a
        ld a,(pub_seq)
        cp b
        jr nz,bh_w
        ld hl,RD_SAT_A & 0xFFFF
        call rd_hide
        ld hl,RD_SAT_B & 0xFFFF
        call rd_hide
        ld a,BANK_FRONT
        call bank_8000
        ld e,4
        jp tiles_upload

; ----- data -----

pz_pal1:
        incbin "puzl_1_grade.pal"   ; the stage's 16 colours, through the colour grade (tools/mkrom.py)
pz_cursor:
        incbin "puzl_cursor.spr"    ; the cursor's 9 sprite patterns (tools/msxpuzl.py)
        include "puzl_tab.inc"      ; PUZL's boards, messages and tables (tools/msxpuzl.py)

; ----- visit 2 (after level 2 on: AG $8050 >= 2), after everything visit 1 runs or reads, which
; so keeps its addresses -----

; bs_stage's visit 2 (HL, BC: its boards' source and length): the boards, visit 2's palette
; ($17DAA: the immediate at $17B20; bs_fade still puts visit 1's back at the end of every fade
; out: quirk 5) and the stage's screen with Ellen's face; then bs_stage's own course (bs_vr).
; (pz_tv is visit 1's only: bs_show2 takes Ellen's pictures from their blob.)
bs_v2:  ld de,pz_boards
        ldir                        ; the boards and what follows them up to $1775F
        ld hl,pz_pal2
        ld (pz_pal),hl
        call bs_show2
        jp bs_vr

; bs_show for visit 2: its head as bs_show's (the screen and the sheet into page 0, page 0's play
; area to page 1: keep the two equal), then Ellen's 9 TV pictures ($25160: the immediate at
; $1729A), puzl_tv2.bin from PUZL_TV2_BANK (tools/mkrom.py: a blob of their own after the ROM's
; last block, docs/LEVEL2.md 3.9), streamed by bs_show's own code from bsw_tv on, which then does
; the rest (the cursor's patterns and visit 2's colours, the SATs, the states) and returns.
bs_show2:
        call vdp_wait
        ld hl,PZ_GFX_SCREEN
        call rd_at
        push hl
        ld e,0
        ld hl,0
        call vram_write             ; page 0 from its first line: the screen, then the sheet
        pop hl
        ld bc,PZ_GFX_PAGE0
        call rd_rom
        call vram_done
        ld hl,rd_cp01
        call vdp_cmd                ; page 0's play area to page 1
        ld a,PUZL_TV2_BANK
        ld hl,PZ_GFX_TV2
        call rd_atb                 ; Ellen's pictures into page 2 (TV_STATES order), and the rest
        jp bsw_tv

; A = a blob's first bank, HL = an offset in it (8 banks at most) -> rd_at's for another blob
; than puzl_gfx.bin: its bank at 8000h (rd_bank), HL = its address there.
rd_atb: push bc
        ld b,a
        ld a,h
        rlca
        rlca
        rlca
        and 7
        add a,b
        pop bc
        jp rd_at1

pz_pal2:
        incbin "puzl_2_grade.pal"   ; visit 2's 16 colours (Ellen's face: its own two, provisional)
