; The shooting range, the second bonus stage after level 1 (the Amiga's FRNG at $1EA00, which
; $8420 calls: docs/RANGE.md). Bank BANK_FRNG at A000h while it runs, FRONT at 8000h (front.asm
; front_range calls rg_stage); its graphics in the data banks from RANGE_GFX_BANK, its hit data from
; RANGE_HIT_BANK (tools/mkrom.py, tools/msxrange.py).
;
; The logic is FRNG's, routine by routine, in its order (docs/RANGE.md 2.3-2.7: the logic report's
; spec), one pass per 50 Hz tick on 50 and 60 Hz machines (its PAL design rate: docs/RANGE.md 3.5):
; FRNG's set-up (the sound stopped, weapon 0 and 25 shots on the panel, the mirror cleared, fr_code
; loaded, the visit's palette, the timer from 2:00, the crosshair's start, the delays idle, a fade
; in); then each pass the fade, the big target's erase, the hit effect's erase, the two target
; slots (the spawn, the pop-ups, the riser, the walkers) and the big target's draw, the effect's
; draw, the crosshair and the gun, the counters, the joystick for the next pass, the hits' delays;
; FRNG's end checks ($1EAA6): 130 passes after the ammo runs out ("NO AMMO."), at once when the
; timer runs out ("TIME OUT."). Kept from the original as its traces show it (docs/RANGE.md 2.11):
; the hit test's row below a BOB and its reads past the blit's own output (T1), position 6 locked
; (T2), the split targets' border from x & FFF0h, < for pop-ups and <= for walkers (T3), one + 25
; lost to a second armed hit within 10 passes (T4), a time out in the end sequence (T5) and its
; return without a fade out (T6), $BB6 counting every pass and the spawn's leftovers (T7), Y's
; lattice at the clamp (T8), both slots spawning script 1 (T9), a hit big target drawn once more
; and a pop-up's last call not scoring (T10).
;
; The hit test: $1EDBC's first blit writes the target's mask (less the scenery's priority plane for
; the pop-ups) into a buffer, and the CPU tests the bit under the crosshair. The port computes that
; one byte (docs/RANGE.md 3.4): every draw call keeps a short list of the recent blits (rg_bob),
; and a test reads the byte from the newest blit whose output covers it, out of range_hit.bin's
; masks and priority plane (rg_tmp), so that the tests that read past their own blit (T1) see what
; the earlier blits left there.
;
; The display (msx/frngview.asm, docs/RANGE.md 3.3): every pass records what the original draws
; (rg_want, msx.inc: range.inc's shown-state layout), and the renderer (rg_show at the entry, rg_feed
; between the passes, rg_hide at the exit) puts that on the screen, double-buffered on pages 0 and
; 1, the vertical lines as sprites, the HUD below as in the game; a camera over the 320-pixel street
; follows the crosshair (rg_cam).
;
; The sound (msx/tune.asm in BANK_MUSIC, ticked by the VBLANK interrupt 50 times a second:
; docs/RANGE.md 3.7): FRM's tune 1 starts in the set-up (tn_frm through mus_call) and plays its tick
; 0 after the first pass (tune.asm tn_hold: $B00 moved), 5,999 ticks, the stage's 2:00; the effects
; (2 the shot, 3 and 4 the hit sounds) go where FRNG asks for them, through snd_rfx ($1822C's rule
; at the next tick). The stage's end stops them (rg_end's snd_stop, right after the last pass: on
; the Amiga $8420 goes on from FRNG's rts to the result's text, whose $10768 silences the four
; channels with $FE14 within microseconds, so FRM's last tick is that pass's).
;
; Its variables live in the mirror at their Amiga addresses (msx.inc frv_...: $B00-$BC5) and in
; fr_code (msx.inc: FRNG's code-area state), so that the trace harness compares them pass by pass
; with the original's (tools/openmsx_rc2.tcl rc2_fr_drive, tools/frngcmp.py, tools/amigaemu.py
; frng). Rules (Brainstorm's): FRONT at 8000h and BANK_FRNG at A000h while it runs; it calls fixed
; code and FRONT; data banks only at 8000h, through bank_8000, BANK_FRONT put back; hud_frame only
; through hud_keep.

        include "range.inc"         ; the stage's view, VRAM map, positions and layouts (tools/msxrange.py)

RGB_LEN:    equ 9                   ; a recent blit's entry (rg_bob): its output's bytes 2 w' h (2), its
                                    ;   rows' 2 w', the mode's high byte (01h $100, 09h $9F0, 0Bh $B50),
                                    ;   the shift x & 15, the picture (RG_NONE: bytes 0), the mask's
                                    ;   row bytes wb, the priority plane's offset of its first word (2)

; (Build checks, no bytes: fr_code ends where the recent-blit list starts, and that list fits MP_B
; with its room (range.inc), in one 256-byte page (rg_btop holds its end's low byte); the wanted
; state fits its room (msx.inc); rg_popup writes a pop-up's record in RG_POP_...'s order; an error
; here otherwise.)
        ds 0 - (fr_code + RG_FC_LEN - rg_blits) * (fr_code + RG_FC_LEN - rg_blits)
        ds 0 - (rg_blits + RG_BLITS_ROOM - 1) / (MP_B + 0x0300)
        ds 0 - (RGB_LEN * RG_BLITS_MAX) / (RG_BLITS_ROOM + 1)
        ds 0 - ((rg_blits + RGB_LEN * RG_BLITS_MAX) / 256 - rg_blits / 256)
        ds 0 - RG_ST_LEN / (RGW_ROOM + 1)
        ds 0 - RG_POP_PLACE * RG_POP_PLACE - (RG_POP_PIC - 1) * (RG_POP_PIC - 1) - (RG_POP_X - 2) * (RG_POP_X - 2) - (RG_POP_Y - 4) * (RG_POP_Y - 4)
; (and front.asm front_range's result script, text.inc's txt_rg_res, fits fs_buf before fs_ptr: the
; check is here because text.inc comes after front.asm, and z80asm's ds takes no forward label)
        ds 0 - (fs_buf + TXT_RG_LEN) / (fs_ptr + 1)

; $1EA00: the stage -> its counts in the mirror (AM $B04 correct, $B06 dummy: $1EAC4's D1 and D0)
; and the time out in AG $804C. It leaves through fr_done (rc2.asm: the trace harness's end),
; FRONT at 8000h.
rg_stage:
        call snd_stop               ; ($20000: FRM's init; $FE14's stop all)
        ld hl,pf_pal
        ld bc,32
        xor a
        call fill                   ; ($FE14: the palette black)
        ld a,BANK_LC1
        call bank_8000
        xor a
        call set_weapon             ; ($1EA06: $8014 -> $FD30: $805C = 0, weapon 0's ammo, its icon)
        ld a,BANK_FRONT
        call bank_8000
        ld hl,0x0025
        ld (AG + 0x8030),hl         ; ($1EA0E: 25 shots, BCD)
        ld hl,AM_START
        ld bc,AM_END - AM_START
        xor a
        call fill                   ; ($1FB52: $FE14's clear_game_vars, $B00-$16EB; then $B00-$BC4)
        xor a
        ld (g_keys),a               ; (clear_game_vars: $802D, $802E, $804D)
        ld (g_joy),a
        ld (g_lock),a
        ld (g_paused),a             ; ($804E: FRNG never sets it; as Brainstorm leaves it)
        ld hl,rgt_frcode
        ld de,fr_code
        ld bc,RG_FC_LEN
        ldir                        ; (FRNG is decrunched again at every visit: its code-area state
                                    ;  from the file, position 6 locked)
        ld hl,0x01F4
        ld (rg_clip),hl             ; ($1EE42: the file's right clip)
        ld hl,0x09F0
        ld (rg_mode),hl             ; ($1EEC6: the file's first blit mode)
        ld hl,(AG + 0x8050)         ; the visit ($1FBBE: cmpi.w #2,$8050 / bmi): the palette only
        ld de,2
        or a
        sbc hl,de
        ld hl,rg_pal1
        jp m,rg_v1
        ld hl,rg_pal2
rg_v1:  ld (rg_pal),hl              ; ($1FBB4: $1F9B0 = $1FBEA, or $1FC2A from the second visit on)
        call rg_init                ; (the port's own: the hit test's list, the wanted state; before
                                    ;  the timer's set-up, which the first pass follows at once)
        call rg_show                ; (the stage's screen, the palette black: msx/frngview.asm)
        ld hl,tn_frm                ; ($1EA32: tune 1, msx/tune.asm; its stop all is the stop. Here,
        call mus_call               ;  before the timer's set-up, which the first pass follows at
                                    ;  once: tn_start waits for a VBLANK. Its tick 0 still comes
                                    ;  after the first pass: tn_hold, $B00 cleared above)
        ld a,0xFF
        ld (frv_fadein),a           ; ($1FBA6: $BC1 = 0 by the clear, $BC0 = FFh: a fade in)
        xor a
        ld (AG + (0x802C ^ 1)),a    ; ($1FBAE: clr.b $802C, the VBL's counter, which nothing reads here)
        ld hl,0x0200
        call rg_timer               ; ($1FBDC: setup_ciab_timer($0200), 2:00)
        xor a
        ld (AG + (0x804C ^ 1)),a    ; ($1EA1E: clr.b $804C)
        ld hl,0x0048
        ld (frv_cy),hl              ; ($1EA24: $B9E = $48)
        ld hl,0x00F0
        ld (frv_cx),hl              ; ($1EA2A: $B9A = $F0: the hit pixel at bitplane (129, 72))
        ld hl,0xFF00
        ld (frv_ddelay),hl          ; ($1EA38: st $BBE, st $BBC: the delays idle, words FF00h)
        ld (frv_cdelay),hl

; $1EA40: the pass loop, one pass per 50 Hz tick; the end checks after each pass.
rg_loop:
        call rg_wait                ; ($1EA40: the next pass)
        call hud_keep               ; ($8004, $8020: the panel's digits and messages; FRONT back)
        call sec_tick               ; ($1015E: the CIA-B's seconds; still in script builds)
fr_tick:
        call fr_frame               ; ($1EA4A-$1EAA4: the pass; the trace's sampling point)
        call rg_feed                ; (the renderer)
        ld hl,(frv_end)             ; $1EAA6: the end checks
        ld a,h
        or l
        jr z,rge_n
        inc hl
        ld (frv_end),hl             ; ($1EAAC: $B08 + 1)
        dec hl
        ld de,99
        or a
        sbc hl,de
        jp m,rg_loop                ; (the old $B08 below 99: cmpi.w #$63,D0 / bmi)
        xor a
        ld (frv_fadein),a           ; ($1EAB8: a fade out)
        ld a,(frv_fade)
        or a
        jr nz,rg_loop
        jr rg_end                   ; ($1EAC4: rts, the counts in $B04 and $B06)
rge_n:  ld hl,(AG + 0x8030)         ; ($1EACE: tst.w $8030)
        ld a,h
        or l
        jr nz,rge_t
        ld hl,frv_end
        inc (hl)                    ; ($1EAD6: $B08 + 1)
        ld a,HUD_MSG_1EB32
        call game_msg               ; ($1EADE: $8008, "NO AMMO.")
        jr rg_loop
rge_t:  ld a,(AG + (0x804C ^ 1))    ; ($1EAE8: tst.b $804C)
        or a
        jr z,rg_loop
        ld hl,frv_end
        inc (hl)                    ; ($1EAF2: $B08 + 1)
        ld a,HUD_MSG_1EB3B
        call game_msg               ; ($1EAFA: jmp $8008, "TIME OUT.": its rts leaves FRNG at once)
; FRNG's return, by either end: the sound stops at once ($8420 -> $10762 -> $10768's $FE14, before
; any other tick: here the VBLANK would tick the tune through rg_hide's waits and its page-2
; restore, about 13 ticks over the black screen), then the display as the result's screen expects
; it (rg_hide), the counts staying in $B04 and $B06.
rg_end: call snd_stop
        call rg_hide
        jp fr_done

; ($1EA40) The next 50 Hz tick: a VBLANK, at 60 Hz every sixth one skipped (front.asm fs_tick's
; rule and its fs_div). wf_n = the VBLANKs since the last pass, or since the timer's set-up
; (sec_tick counts real seconds with it).
rg_wait:
        ld a,(tick)
        ld b,a
rw_lp:  push bc
        call rg_feed                ; (the renderer's work meanwhile)
        pop bc
        ld a,(tick)
        cp b
        jr z,rw_lp
        ld a,(RG9SAV)
        and 2
        jr nz,rw_go                 ; (50 Hz)
        ld hl,fs_div
        inc (hl)
        ld a,(hl)
        cp 6
        jr c,rw_go
        ld (hl),0
        jr rg_wait                  ; (60 Hz: the sixth VBLANK skipped)
rw_go:  ld a,(tick)
        ld c,a
        ld hl,rg_last
        sub (hl)
        ld (wf_n),a
        ld (hl),c
        ret

; $F9DC setup_ciab_timer: HL = the time (H minutes, L seconds, BCD) -> $804A-$804B, no time out
; ($804C), the seconds counted from now (the CIA-B's TOD restarted: sec_n, rg_last).
rg_timer:
        ld (AG + 0x804A),hl         ; (the word $804A: the minutes in its high byte)
        xor a
        ld (AG + (0x804C ^ 1)),a
        ld (sec_n),a
        ld a,(tick)
        ld (rg_last),a
        ret

; The port's own state at the entry: the recent-blit list empty (the first blit's buffer then reads
; 0, as the bench's at FRNG's start), the wanted state with nothing drawn and the camera at its
; start (docs/RANGE.md 3.3; rg_cam moves it from the first pass on), and the pictures' tables
; (rgt_pics indices of every graphic the scripts draw: the renderer's pictures, the hit test's
; masks).
rg_init:
        ld a,rg_blits & 0xFF
        ld (rg_btop),a
        xor a
        ld (rg_blost),a
        ld hl,rg_want
        ld bc,RG_ST_LEN
        ld a,RG_NONE
        call fill
        ld a,RG_CAM_START
        ld (rg_want + RG_ST_S),a
        ld hl,0
        ld (rg_want + RG_ST_CROSS),hl
        ld (rg_want + RG_ST_CROSS + 2),hl
        ld hl,rgt_desc              ; by script: its pop-up's picture, the graphic at its descriptor's
        ld de,rg_spic               ;   +$E (a long, high word first: the low word at +16 in fr_code)
        ld b,RG_SCRIPTS
rgi_s:  push bc
        ld a,(hl)
        inc hl
        push hl
        ld h,(hl)
        ld l,a                      ; (the descriptor's offset in fr_code; FFFFh: not a pop-up)
        ld a,h
        and l
        inc a
        ld a,RG_NONE
        jr z,rgi_n
        ld bc,rgt_frcode + 16
        add hl,bc
        push de
        ld e,(hl)
        inc hl
        ld d,(hl)
        call rg_pic
        pop de
rgi_n:  ld (de),a
        inc de
        pop hl
        inc hl
        pop bc
        djnz rgi_s
        ld hl,rgt_rise_gfx          ; by frame, the riser's
        ld de,rg_rpic
        ld b,10
        call rgi_t
        ld hl,rgt_walk_gfx          ; by kind, the walker's
        ld de,rg_wpic
        ld b,16
        call rgi_t
        ld hl,rgt_fx_gfx            ; by frame, the dissolve's
        ld de,rg_fpic
        ld b,22
; HL = a table of B graphics (longs, the high word first) -> their pictures from DE on.
rgi_t:  inc hl
        inc hl
        ld a,(hl)
        inc hl
        push hl
        ld h,(hl)
        ld l,a
        push de
        push bc
        ex de,hl
        call rg_pic
        pop bc
        pop de
        ld (de),a
        inc de
        pop hl
        inc hl
        djnz rgi_t
        ret

; DE = a graphic's Amiga address's low word (unique among rgt_pics' keys) -> A = its picture (its
; rgt_pics index), RG_NONE when it has none. Uses BC, HL.
rg_pic:
        ld hl,rgt_pics + RG_PIC_KEY
        ld bc,RG_PIC_LEN
        xor a
rpc_l:  push af
        ld a,(hl)
        cp e
        jr nz,rpc_n
        inc hl
        ld a,(hl)
        dec hl
        cp d
        jr z,rpc_y
rpc_n:  add hl,bc
        pop af
        inc a
        cp RG_PICS
        jr c,rpc_l
        ld a,RG_NONE
        ret
rpc_y:  pop af
        ret

; ----- the pass -----

; $1EA4A-$1EAA4: one pass, after its wait (tools/openmsx_rc2.tcl samples the mirror at fr_tick's
; call), FRNG's routines in its order. The music ticks from the VBLANK (msx/tune.asm), so the
; divider $1EB30 is not kept; the panel ($8004, $8020) is hud_keep's, at the loop's start.
fr_frame:
        call rg_fade                ; $1F980
        call rg_bigerase            ; $1F44A
        call rg_fxerase             ; $1F808
                                    ; ($1EF6A: the random word $B0C, which nothing reads: left 0)
        call rg_targets             ; $1F0DA (and $1F3F6, the big target's draw)
        call rg_fxdraw              ; $1F83A
        call rg_cross               ; $1EB5C
        call rg_cam                 ; (the port's camera: the view follows the crosshair)
        ld hl,(frv_pass)
        inc hl
        ld (frv_pass),hl            ; ($1EA6E: $B00 + 1)
        ld hl,(frv_pass3)
        inc hl
        inc hl
        inc hl
        ld (frv_pass3),hl           ; ($1EA72: $B02 + 3)
        call joy_read               ; ($1EA92: $801C, $802E for the next pass's crosshair)
        call rg_delays              ; ($1EAA4: $1EB00)
        ld hl,(tick_n)
        inc hl
        ld (tick_n),hl              ; (a JOY script goes on through the stage)
        ret

; $1F980: the fade's level ($BC1, 0-31): + 1 a pass while $BC0 is set, else - 1, nothing more at
; either end; at the end of a fade out the palette pointer goes back to visit 1's ($1F9A4). Then
; pf_pal (COLOR01-31's, which the VBLANK loads for the play area) is the visit's graded palette with
; every component at most fade_cap[$BC1 >> 2] (msx/logic.asm pal_fade's rule, msx/puzl.asm bs_fade's).
rg_fade:
        ld hl,frv_fade
        ld a,(frv_fadein)
        or a
        jr z,rf_out
        ld a,(hl)
        cp 0x1F
        ret z
        inc (hl)
        jr rf_pal
rf_out: ld a,(hl)
        or a
        ret z
        dec (hl)
        jr nz,rf_pal
        ld hl,rg_pal1
        ld (rg_pal),hl
rf_pal: ld a,(frv_fade)
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
        ld hl,(rg_pal)
        ld de,pf_pal
rfp_lp: ld a,(hl)
        and 0x70
        cp b
        jr c,rfp_r
        ld a,b
rfp_r:  ld (de),a                   ; R
        ld a,(hl)
        and 7
        cp c
        jr c,rfp_b
        ld a,c
rfp_b:  ex de,hl
        or (hl)
        ld (hl),a                   ; R | B
        ex de,hl
        inc hl
        inc de
        ld a,(hl)
        cp c
        jr c,rfp_g
        ld a,c
rfp_g:  ld (de),a                   ; G
        inc hl
        inc de
        ld a,e
        cp (pf_pal + 32) & 0xFF
        jr nz,rfp_lp
        ret

; $1EB00: the hits' delays. $BBC (a correct hit's, 10 at the hit) - 1 while not negative: below 0,
; effect 3 and + 25 points, and nothing more this pass (a dummy's delay ending then waits a pass);
; then $BBE (a dummy hit's) the same way, below 0 effect 4. (tst.w / bmi, subq.w / bpl: the sign.)
rg_delays:
        ld hl,(frv_cdelay)
        bit 7,h
        jr nz,rdl_d                 ; ($1EB04: idle)
        dec hl
        ld (frv_cdelay),hl          ; ($1EB06: $BBC - 1)
        bit 7,h
        jr z,rdl_d
        ld a,3
        call snd_rfx                ; ($1EB0E: effect 3)
        ld de,0x0025
        jp add_score                ; ($1EB16: $800C, + 25)
rdl_d:  ld hl,(frv_ddelay)
        bit 7,h
        ret nz                      ; ($1EB20)
        dec hl
        ld (frv_ddelay),hl          ; ($1EB22: $BBE - 1)
        bit 7,h
        ret z
        ld a,4
        jp snd_rfx                  ; ($1EB2A: effect 4)

; FRNG's sound effects (jsr $20014: $2022C) -> msx/tune.asm: A = 2 the shot, 3 a correct hit, 4 a
; dummy hit, from the next tick on (tn_go: $1822C's rule there); of two requests before a tick the
; higher one, the one the Amiga lets sound (a shot and a due hit sound in one pass: the hit sound;
; the Amiga sounds the shot one tick first, docs/RANGE.md default 28). The ticks run again (fx_act:
; the tune may be over). puzl.asm snd_bfx's bytes (BANK_PUZL is not mapped here); RAM only, so no
; bank and no mirror byte: the traces are the silent stage's. Uses AF, HL (its callers, rg_cross
; and rg_delays, keep nothing in AF, BC, DE, HL across it; IX and IY stay).
snd_rfx:
        ld hl,tn_req
        cp (hl)
        ret c
        ld (hl),a
        ld a,2
        ld (fx_act),a
        ret

; $AC9A (through $8010): the ammo ($8030, BCD) minus one: LC1's shots.asm ammo_dec (LC1 is not
; mapped while the stage runs).
rg_ammo:
        ld hl,AG + 0x8030
        ld a,(hl)
        sub 1
        daa
        ld (hl),a
        inc hl
        ld a,(hl)
        sbc a,0
        daa
        ld (hl),a
        ret

; $1EB5C: the crosshair and the gun. The fire box ($1EB4A: n = 8 at a shot, - 1 a pass down to 0,
; then -1: none) around the crosshair before its move, for the renderer (the box and the restored
; rows are display); the shot (fire held with ammo left: the repeat count $1EB48 - 1, a shot below
; 0, then $18; fire up: its high byte FFh, so the next press shoots at once), which the next
; pass's draws test ($1EB46); the move by the previous pass's joystick byte, 4 a pass, right over
; left, down over up, clamped to $7C-$198 and $10-$9E (cmpi.w / bpl, bmi: the difference's sign;
; quirk T8). The crosshair at the pass's end goes to the wanted state.
rg_cross:
        ld hl,(fr_code + RG_FC_BOX)
        ld a,RG_NONE
        bit 7,h
        jr nz,rcr_b                 ; ($1EB98: bmi, no box)
        ld a,l                      ; (n: 8-0)
        dec hl
        ld (fr_code + RG_FC_BOX),hl ; ($1EB9C: $1EB4A - 1)
rcr_b:  ld (rg_want + RG_ST_BOX + RG_BOX_N),a
        ld hl,(frv_cx)
        inc hl
        inc hl
        inc hl
        inc hl
        ld a,l
        and 0xF0
        ld l,a
        ld (rg_want + RG_ST_BOX + RG_BOX_C),hl  ; (its centre: $1EBAC, (4 + $B9A) & FFF0h)
        ld hl,(frv_cy)
        ld (rg_want + RG_ST_BOX + RG_BOX_Y),hl  ; (its row, $B9E)
        xor a
        ld (fr_code + RG_FC_SHOT),a ; ($1EC7E: clr.b $1EB46)
        ld a,(g_joy)                ; ($1EC78: $802E)
        bit 4,a
        jr z,rcr_up                 ; ($1EC88: no fire)
        ld hl,(AG + 0x8030)
        ld a,h
        or l
        jr z,rcr_up                 ; ($1EC90: no ammo left)
        ld hl,(fr_code + RG_FC_REPEAT)
        dec hl
        ld (fr_code + RG_FC_REPEAT),hl  ; ($1EC92: $1EB48 - 1)
        bit 7,h
        jr z,rcr_mv                 ; ($1EC98: bpl, no shot yet)
        ld hl,0x0018
        ld (fr_code + RG_FC_REPEAT),hl  ; ($1EC9A)
        ld a,0xFF
        ld (fr_code + RG_FC_SHOT),a ; ($1ECA2: st $1EB46: the next pass's draws test the shot)
        ld l,8
        ld (fr_code + RG_FC_BOX),hl ; ($1ECA8: $1EB4A = 8)
        ld a,2
        call snd_rfx                ; ($1ECB4: effect 2, the shot)
        call rg_ammo                ; ($1ECBA: $8010, the ammo - 1)
        jr rcr_mv
rcr_up: ld a,0xFF
        ld (fr_code + RG_FC_REPEAT + 1),a  ; ($1ECC4: st $1EB48, its high byte)
rcr_mv: ld a,(g_joy)
        ld c,a
        ld de,4
        ld hl,(frv_cx)
        bit 3,c
        jr z,rcr_l
        add hl,de                   ; ($1ECD0: right, + 4)
        jr rcr_x
rcr_l:  bit 2,c
        jr z,rcr_x
        or a
        sbc hl,de                   ; ($1ECDC: left, - 4)
rcr_x:  ld de,0x7C
        call rg_lo                  ; ($1ECFE: cmpi.w #$7C / bpl)
        ld de,0x198
        call rg_hi                  ; ($1ED06: cmpi.w #$198 / bmi)
        ld (frv_cx),hl              ; ($1ED22)
        ld (rg_want + RG_ST_CROSS),hl
        ld de,4
        ld hl,(frv_cy)
        bit 1,c
        jr z,rcr_u
        add hl,de                   ; ($1ECE6: down, + 4)
        jr rcr_y
rcr_u:  bit 0,c
        jr z,rcr_y
        or a
        sbc hl,de                   ; ($1ECF2: up, - 4)
rcr_y:  ld de,0x10
        call rg_lo                  ; ($1ED10: cmpi.w #$10 / bpl)
        ld de,0x9E
        call rg_hi                  ; ($1ED18: cmpi.w #$9E / bmi)
        ld (frv_cy),hl              ; ($1ED26)
        ld (rg_want + RG_ST_CROSS + 2),hl
        ret

; The camera (docs/RANGE.md 3.3), once a pass after the crosshair's move: s = clamp(clamp(s, cx -
; RG_BAND_HI, cx - RG_BAND_LO), 0, RG_CAM_MAX), cx = $B9A - RG_LINE_DX (the line's x on the
; street): s moves only while the line is in the view's outer quarters, so the line stays in view
; (cx - s in 13-233). The renderer shows s from a page built at the multiple of 16 c with c - s in
; -7..8, R#18 the rest (frngview.asm). RG_ADJ=0 (docs/RANGE.md 6: R#18 always 0): s is a multiple
; of 16 that moves only when the line would leave cx - s in RG_ADJ_LO..RG_ADJ_HI (msxrange.py
; camera_steps).
        if RG_ADJ
RCM_LO:     equ RG_BAND_LO
RCM_HI:     equ RG_BAND_HI
        else
RCM_LO:     equ RG_ADJ_LO
RCM_HI:     equ RG_ADJ_HI
        endif
rg_cam: ld a,(rg_want + RG_ST_S)
        ld e,a
        ld d,0                      ; (DE = s)
        ld bc,-RG_LINE_DX - RCM_HI
        call rcm_b
        jp m,rcm_h                  ; (s above cx - HI)
        if RG_ADJ = 0
        ld bc,15
        add hl,bc                   ; (the next multiple of 16)
        endif
        call rcm_s                  ; s = cx - HI
rcm_h:  ld bc,-RG_LINE_DX - RCM_LO
        call rcm_b
        call m,rcm_s                ; (s above cx - LO: s = cx - LO)
        ld a,e
        bit 7,d
        jr z,rcm_0
        xor a                       ; (below 0)
rcm_0:  cp RG_CAM_MAX + 1
        jr c,rcm_w
        ld a,RG_CAM_MAX
rcm_w:  ld (rg_want + RG_ST_S),a
        ret
; BC = -(RG_LINE_DX + a band's bound) -> HL = cx - that bound, the sign flag HL - DE's
rcm_b:  ld hl,(frv_cx)
        add hl,bc
        or a
        sbc hl,de
        add hl,de                   ; (S kept: add hl,rr leaves it)
        ret
; DE = HL (RG_ADJ=0: its multiple of 16 at or below)
rcm_s:
        if RG_ADJ = 0
        ld a,l
        and 0xF0
        ld l,a
        endif
        ex de,hl
        ret

; HL = HL - DE < 0 (the 16-bit difference's sign, cmpi.w / bpl) ? DE : HL. Keeps BC, DE.
rg_lo:  push hl
        or a
        sbc hl,de
        pop hl
        ret p
        ld h,d
        ld l,e
        ret

; HL = HL - DE >= 0 (cmpi.w / bmi) ? DE : HL. Keeps BC, DE.
rg_hi:  push hl
        or a
        sbc hl,de
        pop hl
        ret m
        ld h,d
        ld l,e
        ret

; ----- the targets -----

; $1F0DA: the two slots (A3 = $B2E, then $B32: IY = the mirror's A3). An empty one (its script, byte
; (8,A3), 0) spawns script ($B00 & 3Fh) + 1, less 32 from 40 on (1-39), and calls nothing this pass;
; a running one calls its script's handler ($BB8 = the script's entry), whose D0 = -1 (A = FFh)
; frees the slot. Then $1F3F6, the big target's draw. A slot's pop-up in the wanted state is the
; one its handler drew this pass ($1F5F8), else none.
rg_targets:
        ld iy,frv_slot0
        ld hl,rg_want + RG_ST_POP
        call rtg_slot
        ld iy,frv_slot1
        ld hl,rg_want + RG_ST_POP + RG_POP_LEN
        call rtg_slot
        jp rg_bigdraw               ; ($1F10C)

rtg_slot:
        ld (hl),RG_NONE             ; (RG_POP_PLACE: none, unless its pop-up draws)
        ld (rg_wp),hl
        ld a,(iy + 9)               ; ($1F0E0: (8,A3), the script)
        or a
        jr z,rtg_new
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,0xEF88
        add hl,de
        ld (frv_entry + 2),hl       ; ($1F0EE: $BB8 = $1EF88 + 8 n, the script's entry)
        ld hl,0x0001
        ld (frv_entry),hl
        ld e,a
        ld d,0
        ld hl,rgt_kind
        add hl,de
        ld a,(hl)
        cp RG_K_POPUP
        jr nz,rtg_bg
        ld hl,rgt_desc              ; (its stub's lea: A0 = the descriptor, fr_code's copy)
        add hl,de
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld de,fr_code
        add hl,de
        push hl
        pop ix
        call rg_popup               ; ($1F0F4: $1F50C)
        jr rtg_d0
rtg_bg: cp RG_K_MOVE
        jr nz,rtg_rs
        call rg_move                ; ($1F32A)
        jr rtg_d0
rtg_rs: call rg_rise                ; ($1F14E)
rtg_d0: or a
        ret z                       ; ($1F0F8: D0 = 0, the slot runs on)
        xor a
        ld (iy + 8),a               ; ($1F0FC: clr.l (8,A3))
        ld (iy + 9),a
        ld (iy + 10),a
        ld (iy + 11),a
        ld (iy + 0),a               ; ($1F100: clr.l (A3))
        ld (iy + 1),a
        ld (iy + 2),a
        ld (iy + 3),a
        ret
; ($1F112) The spawn: the script, then (9,A3) = 10 and (10,A3) = 0, and the longs (-$20,A3),
; (-$18,A3), (-$10,A3), (-8,A3) and (A3) cleared. The original then puts its registers' leftovers in
; the first words of (-$20,A3) and (-8,A3) (D1, D0): 0 here ($B0E/$B12 are never read, $B26/$B2A
; only once the handler's first call set them).
rtg_new:
        ld a,(frv_pass)             ; ($1F114: $B00's low byte)
        and 0x3F
        inc a
        cp 0x28
        jr c,rgn_s                  ; ($1F11E: cmpi.w #$28 / bmi)
        sub 0x20
rgn_s:  ld (iy + 9),a               ; ($1F134: (8,A3))
        ld (iy + 8),10              ; ($1F13C: (9,A3))
        xor a
        ld (iy + 11),a              ; ($1F138: (10,A3))
        push iy
        pop hl
        ld de,-0x20
        add hl,de
        ld de,5
        ld b,5
rgn_z:  ld (hl),a                   ; ($1F124-$1F14A: the longs 8 bytes apart from (-$20,A3) to (A3))
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a
        add hl,de
        djnz rgn_z
        ret

; A = the running slot's script's hit effect (1-4): the word (4,$BB8), rgt_scripts + 8 n + 4.
rtg_type:
        ld a,(iy + 9)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,rgt_scripts + 4
        add hl,de
        ld a,(hl)
        ret

; $1F50C frng_h_popup: IX = the descriptor (fr_code's copy of $1F60E + 22 k, in the mirror's rule:
; its byte at +d at IX + (d ^ 1)), IY = the slot -> A = 0, or FFh (D0 = -1: the slot freed). The
; first call locks the position ($1F502 + its number) or is refused (taken: position 6 always,
; quirk T2); then the pop-up rises (slides when (B,A0) is set: the offset moves x) for (7,A0) calls
; by the speed (8,A0), holds (A,A0) calls and goes back as many as it rose; the last call frees the
; position and erases it without looking at a hit (quirk T10). A hit the previous pass's draw found
; ($12,A0) is scored first: armed when its column ($13,A0) is below the threshold ($14,A0) (cmp.w /
; bmi: quirk T3), with the script's hit effect, and the pop-up is erased. Otherwise it is drawn
; (mode $B50: its mask less the scenery's priority plane: only what the opening shows can be hit),
; and the draw's hit kept for the next pass.
rg_popup:
        ld a,(ix + 1)               ; ($1F50E: (A0), the position)
        xor 1
        ld e,a
        ld d,0
        ld hl,fr_code + RG_FC_LOCKS
        add hl,de
        ld (rg_lock),hl             ; ($1F510: A1 = $1F502 + the position)
        ld a,(iy + 2)               ; ($1F514: tst.b (3,A3), the first call's flag)
        or a
        jr nz,rpo_go
        ld (iy + 2),0xFF            ; ($1F51A)
        ld a,(hl)
        or a
        ld a,0xFF
        ret nz                      ; ($1F520: taken: $1F46E, D0 = -1)
        ld (hl),a                   ; ($1F524: st (A1))
        ld (ix + 0),a               ; ($1F526: st (1,A0): the phase, a rise)
        xor a
        ld (ix + 19),a              ; ($1F52A: clr.b ($12,A0))
        ld a,(ix + 2)
        ld (iy - 8),a
        ld a,(ix + 3)
        ld (iy - 7),a               ; ($1F52E: (-8,A3) = (2,A0))
        ld a,(ix + 6)
        ld (iy + 1),a               ; ($1F534: (A3) = (7,A0), the rise's calls)
rpo_go: ld l,(ix + 4)
        ld h,(ix + 5)
        ld e,(iy - 30)
        ld d,(iy - 29)
        add hl,de
        ex de,hl                    ; ($1F53C: D1 = (4,A0) + (-$1E,A3), the offset before this pass's)
        ld l,(ix + 2)
        ld h,(ix + 3)               ; ($1F538: D0 = (2,A0))
        ld a,(ix + 10)              ; ($1F544: tst.b (B,A0), a horizontal one)
        or a
        jr z,rpo_xy
        ex de,hl                    ; ($1F54A: exg D1,D0)
rpo_xy: ld (rg_px),hl
        ld (rg_py),de
        ld l,(ix + 8)
        ld h,(ix + 9)               ; (HL = (8,A0), the speed)
        ld c,(iy - 30)
        ld b,(iy - 29)              ; (BC = (-$1E,A3), the offset)
        ld a,(ix + 0)               ; ($1F550: the phase - 1, a byte)
        dec a
        jp p,rpo_h                  ; ($1F556: bpl)
        add hl,bc                   ; (rising, phase FFh or 0: the offset + the speed, $1F55C)
        ld (iy - 30),l
        ld (iy - 29),h
        dec (iy + 1)                ; ($1F560: subq.b #1,(A3))
        jr nz,rpo_hit
        ld (ix + 0),1               ; ($1F564: held next)
        ld a,(ix + 11)
        ld (iy + 1),a               ; ($1F56A: (A3) = (A,A0), the hold's calls)
        jr rpo_hit
rpo_h:  dec a
        jp p,rpo_l                  ; ($1F572)
        dec (iy + 1)                ; ($1F574: holding, phase 1)
        jr nz,rpo_hit
        ld (ix + 0),2               ; ($1F578: lowered next)
        ld a,(ix + 6)
        ld (iy + 1),a               ; ($1F57E: (A3) = (7,A0))
        jr rpo_hit
rpo_l:  dec a
        jp p,rpo_hit                ; ($1F586: phases 3-80h: nothing moves)
        ld a,c
        sub l
        ld (iy - 30),a
        ld a,b
        sbc a,h
        ld (iy - 29),a              ; ($1F58C: lowering, phase 2: the offset - the speed)
        dec (iy + 1)                ; ($1F590)
        jr nz,rpo_hit
        ld hl,(rg_lock)
        ld (hl),0                   ; ($1F594: clr.b (A1): the position free)
        jr rpo_er                   ; ($1F596: erased, the hit not looked at: quirk T10)
rpo_hit:
        ld a,(ix + 19)              ; ($1F598: tst.b ($12,A0))
        or a
        jr z,rpo_dr
        ld l,(ix + 18)
        ld h,0                      ; ($1F5A0: ($13,A0), the hit's column)
        ld e,(ix + 20)
        ld d,(ix + 21)
        or a
        sbc hl,de
        jp m,rpo_ok                 ; ($1F5A8: cmp.w ($14,A0) / bmi: armed)
        ld hl,(frv_dummy)
        inc hl
        ld (frv_dummy),hl           ; ($1F5AA: $B06 + 1)
        ld hl,10
        ld (frv_ddelay),hl          ; ($1F5AE: $BBE = 10)
        jr rpo_fx
rpo_ok: ld hl,(frv_correct)
        inc hl
        ld (frv_correct),hl         ; ($1F5B6: $B04 + 1)
        ld hl,10
        ld (frv_cdelay),hl          ; ($1F5BA: $BBC = 10)
rpo_fx: ld hl,(rg_lock)
        ld (hl),0                   ; ($1F5C0: clr.b (A1))
        call rtg_type               ; ($1F5C8: D5 = word (4,$BB8))
        ld hl,(rg_px)
        ld de,(rg_py)
        call rg_fxstart             ; ($1F5CC: $1F940)
rpo_er: ld hl,0x0100
        ld (rg_mode),hl             ; ($1F5D2: an erase)
        ld hl,(rg_px)
        ld de,(rg_py)
        ld c,(ix + 12)
        ld b,(ix + 13)              ; (D4 = ($C,A0))
        ld a,RG_NONE
        call rg_bob                 ; ($1F5DA)
        ld a,0xFF                   ; ($1F5DE: D0 = -1)
        ret
rpo_dr: ld hl,0x0B50
        ld (rg_mode),hl             ; ($1F5E6: the mask less the priority plane)
        ld hl,0x0258
        ld (rg_clip),hl             ; ($1F5EE)
        ld e,(iy + 9)
        ld d,0
        ld hl,rg_spic
        add hl,de
        ld a,(hl)                   ; (the script's picture)
        ld hl,(rg_wp)               ; (the wanted state: RG_POP_PLACE the position, RG_POP_PIC,
        ld c,(ix + 1)               ;  RG_POP_X D0, RG_POP_Y D1)
        ld (hl),c
        inc hl
        ld (hl),a
        inc hl
        ld de,(rg_px)
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld de,(rg_py)
        ld (hl),e
        inc hl
        ld (hl),d
        ld hl,(rg_px)
        ld c,(ix + 12)
        ld b,(ix + 13)
        call rg_bob                 ; ($1F5F8: (E,A0), the graphic: A its picture, DE D1)
        ld a,(frv_hit)
        ld (ix + 19),a              ; ($1F5FE: ($12,A0) = $B0B)
        ld a,(frv_hitx)
        ld (ix + 18),a              ; ($1F604: ($13,A0) = $BA3)
        xor a                       ; ($1F60A: D0 = 0)
        ret

; $1F14E frng_h_rise (scripts 23-25), IY = the slot -> A = 0 or FFh: the big target rising at x $82 +
; ($B00 & FFh) (its first call, unless a big target is out: $BA6); frames 0-3 two calls each, frame
; 4 54 calls (the hold (-6,A3) from $34 down below 0), 5-9 two calls each, then gone ($1F3E6). Each
; call sets up the draw $1F3F6 makes after the slots ($BA8, $BAE, $BB0, $BAA; the clip $1F4); a hit
; that draw found the previous pass ($BB2) is scored, always armed, with the hit effect at (x, $54)
; (the target drawn once more: quirk T10).
rg_rise:
        ld a,(iy + 1)               ; ($1F14E: tst.b (A3))
        or a
        jr nz,rri_go
        ld a,(frv_bigon)
        or a
        ld a,0xFF
        ret nz                      ; ($1F156: a big target out: D0 = -1)
        ld (frv_bigon),a            ; ($1F15A: st $BA6)
        ld (iy + 1),a               ; ($1F15E: st (A3))
        ld a,(frv_pass)             ; ($1F162: the byte $B01)
        ld l,a
        ld h,0
        ld de,0x82
        add hl,de
        ld (iy - 8),l
        ld (iy - 7),h               ; ($1F16A: (-8,A3), x)
        ld (iy - 6),0x34
        ld (iy - 5),0               ; ($1F16E: (-6,A3) = $34)
rri_go: ld l,(iy + 2)
        ld h,(iy + 3)
        srl h
        rr l                        ; ($1F178: the frame, (2,A3) >> 1)
        ld a,h
        or a
        jp nz,rg_bigend
        ld a,l
        cp 10
        jp nc,rg_bigend             ; ($1F17E: cmpi.w #$A / bpl: gone)
        ld c,a                      ; (C = the frame)
        cp 4
        jr nz,rri_n
        ld l,(iy - 6)
        ld h,(iy - 5)
        dec hl
        ld (iy - 6),l
        ld (iy - 5),h               ; ($1F188: frame 4 holds while (-6,A3) - 1 >= 0)
        bit 7,h
        jr z,rri_f                  ; ($1F18C: bpl)
rri_n:  ld l,(iy + 2)
        ld h,(iy + 3)
        inc hl
        ld (iy + 2),l
        ld (iy + 3),h               ; ($1F18E: (2,A3) + 1)
rri_f:  ld hl,0x01F4
        ld (fr_code + RG_FC_CLIP),hl  ; ($1F194: $1F46C = $1F4)
        ld b,0
        ld hl,rg_rpic
        add hl,bc
        ld a,(hl)
        ld (rg_bigpic),a            ; (its picture)
        ld hl,rgt_rise_size
        add hl,bc
        add hl,bc
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (frv_bigsz),de           ; ($1F19C: $BA8 = the frame's BLTSIZE)
        ld l,(iy - 8)
        ld h,(iy - 7)
        ld (frv_bigx),hl            ; ($1F1A6: $BAE = x)
        ld hl,rgt_rise_row
        add hl,bc
        add hl,bc
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (frv_bigy),de            ; ($1F1AA: $BB0 = its row)
        ld hl,rgt_rise_gfx
        add hl,bc
        add hl,bc
        add hl,bc
        add hl,bc
        ld de,frv_biggfx
        ld bc,4
        ldir                        ; ($1F1B2: $BAA = its graphic)
        ld a,(frv_bighit)           ; ($1F1B8: tst.b $BB2)
        or a
        ret z                       ; ($1F1BE: D0 = 0)
        ld hl,0x0100
        ld (rg_mode),hl             ; ($1F216: overwritten before any use)
        ld hl,(frv_correct)
        inc hl
        ld (frv_correct),hl         ; ($1F21E: $B04 + 1)
        ld hl,10
        ld (frv_cdelay),hl          ; ($1F222: $BBC = 10)
        call rtg_type
        ld l,(iy - 8)
        ld h,(iy - 7)
        ld de,0x64 - 8
        call rg_fxstart             ; ($1F236: the effect at (x, $5C - 8))
        xor a
        ld (frv_bighit),a           ; ($1F23C: clr.b $BB2)
        ld (frv_bigon),a            ; ($1F240: clr.b $BA6)
        dec a                       ; ($1F23A: D0 = -1)
        ret

; $1F32A frng_h_move (scripts 14-22), IY = the slot -> A = 0 or FFh: a big target sliding in from the
; right, of kind k = ($B00 & 1Eh) / 2 at its first call (unless a big target is out); x from $198,
; 1 px left a call for 63 calls, then right for 64, then gone; its draw set up for $1F3F6 from the
; kind's tables (its clip $1F46C: $1A0 or $1C0). A hit that draw found the previous pass is armed
; when the kind's threshold less its column ($BB4) is not negative (cmp.w / bmi: the dummy; quirk
; T3), with the hit effect at (x + 6, $68).
rg_move:
        ld a,(iy + 1)               ; ($1F32A: tst.b (A3))
        or a
        jr nz,rmv_go
        ld a,(frv_bigon)
        or a
        ld a,0xFF
        ret nz                      ; ($1F332)
        ld a,(frv_pass)
        and 0x1E
        ld l,a
        ld h,0
        ld (fr_code + RG_FC_KIND),hl  ; ($1F33C: $1F246 = $B00 & 1Eh, 2 k)
        ld a,0xFF
        ld (frv_bigon),a            ; ($1F342: st $BA6)
        ld (iy + 1),a               ; ($1F346: st (A3))
        ld (iy + 2),0xC0
        ld (iy + 3),0xFF            ; ($1F348: (2,A3) = -$40)
        ld (iy - 8),0x98
        ld (iy - 7),0x01            ; ($1F34E: (-8,A3) = $198)
rmv_go: ld l,(iy - 8)
        ld h,(iy - 7)
        inc hl                      ; ($1F354: x + 1)
        ld e,(iy + 2)
        ld d,(iy + 3)
        inc de                      ; ($1F358: the calls + 1)
        ld (iy + 2),e
        ld (iy + 3),d
        bit 7,d
        jr z,rmv_p                  ; ($1F360: bpl)
        dec hl
        dec hl                      ; ($1F362: on its way in: - 2, 1 px left in all)
rmv_p:  ld (iy - 8),l
        ld (iy - 7),h
        ld a,e
        cp 0x40
        jr nz,rmv_on
        ld a,d
        or a
        jp z,rg_bigend              ; ($1F36A: cmpi.w #$40 / beq: the 128th call, gone)
rmv_on: ld bc,(fr_code + RG_FC_KIND)  ; (BC = 2 k)
        push hl
        ld hl,rgt_walk_xoff
        add hl,bc
        ld e,(hl)
        inc hl
        ld d,(hl)
        pop hl
        add hl,de
        ld (frv_bigx),hl            ; ($1F378, $1F39A: $BAE = x + the kind's offset)
        ld hl,rgt_walk_size
        add hl,bc
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (frv_bigsz),de           ; ($1F37C: $BA8)
        ld hl,rgt_walk_row
        add hl,bc
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (frv_bigy),de            ; ($1F386: $BB0)
        ld hl,rgt_walk_clip
        add hl,bc
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (fr_code + RG_FC_CLIP),de  ; ($1F38A: $1F46C)
        ld a,c
        rrca
        ld e,a
        ld d,0
        ld hl,rg_wpic
        add hl,de
        ld a,(hl)
        ld (rg_bigpic),a            ; (its picture)
        ld hl,rgt_walk_gfx
        add hl,bc
        add hl,bc
        ld de,frv_biggfx
        ld bc,4
        ldir                        ; ($1F394: $BAA)
        ld a,(frv_bighit)           ; ($1F39E: tst.b $BB2)
        or a
        ret z                       ; ($1F3F2: D0 = 0)
        ld hl,rgt_walk_thr
        ld bc,(fr_code + RG_FC_KIND)
        add hl,bc
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld de,(frv_bigcol)
        or a
        sbc hl,de
        jp m,rmv_d                  ; ($1F3AE: cmp.w $BB4 / bmi: a dummy)
        ld hl,(frv_correct)
        inc hl
        ld (frv_correct),hl         ; ($1F3B0)
        ld hl,10
        ld (frv_cdelay),hl          ; ($1F3B4)
        jr rmv_fx
rmv_d:  ld hl,(frv_dummy)
        inc hl
        ld (frv_dummy),hl           ; ($1F3BC)
        ld hl,10
        ld (frv_ddelay),hl          ; ($1F3C0)
rmv_fx: ld hl,0x0100
        ld (rg_mode),hl             ; ($1F3C6)
        call rtg_type
        ld hl,(frv_bigx)
        ld de,6
        add hl,de
        ld de,0x70
        call rg_fxstart             ; ($1F3E2: the effect at (x + 6, $70 - 8))
; ($1F3E6) A big target gone: D0 = -1. (The rise's scoring path clears only the byte $BA6, here the
; word: $BA7 is never set.)
rg_bigend:
        ld hl,0
        ld (AM + 0x0BA6),hl         ; ($1F3E6: clr.w $BA6)
        xor a
        ld (frv_bighit),a           ; ($1F3EA: clr.b $BB2)
        dec a
        ret

; $1F3F6: the big target's draw for this pass ($BA8 set by its handler), with its clip and mode $9F0
; (the whole mask: it stands in front of everything); its hit kept for the handler's next call
; ($BB2, $BB5). The wanted state's big target: this draw, or none.
rg_bigdraw:
        xor a
        ld (frv_bighit),a           ; ($1F3F6: clr.b $BB2)
        ld bc,(frv_bigsz)
        ld a,b
        or c
        jr nz,rbd_go
        ld a,RG_NONE
        ld (rg_want + RG_ST_BIG + RG_BIG_PIC),a
        ret
rbd_go: ld hl,0x09F0
        ld (rg_mode),hl             ; ($1F40C)
        ld hl,(fr_code + RG_FC_CLIP)
        ld (rg_clip),hl             ; ($1F41E: the clip $1F46C)
        ld (rg_want + RG_ST_BIG + RG_BIG_CLIP),hl
        ld a,(rg_bigpic)
        ld (rg_want + RG_ST_BIG + RG_BIG_PIC),a
        ld hl,(frv_bigx)
        ld (rg_want + RG_ST_BIG + RG_BIG_X),hl
        ld de,(frv_bigy)
        ld (rg_want + RG_ST_BIG + RG_BIG_Y),de
        call rg_bob                 ; ($1F426)
        ld hl,0x01F4
        ld (rg_clip),hl             ; ($1F42A)
        ld a,(frv_hit)
        ld (frv_bighit),a           ; ($1F43C: $BB2 = $B0B)
        ld a,(frv_hitx)
        ld (frv_bigcol),a           ; ($1F442: $BB5 = $BA3)
        ret

; $1F44A: last pass's big target erased ($BA8 cleared), mode $100.
rg_bigerase:
        ld bc,(frv_bigsz)
        ld a,b
        or c
        ret z
        ld hl,0
        ld (frv_bigsz),hl           ; ($1F450: clr.w $BA8)
        ld hl,0x0100
        ld (rg_mode),hl             ; ($1F460)
        ld hl,(frv_bigx)
        ld de,(frv_bigy)
        ld a,RG_NONE
        jp rg_bob                   ; ($1F468)

; $1F940 frng_fx_start: A = the type (1-4), HL = x (D0), DE = y (D1) -> the hit effect from the
; type's first frame at (x, y - 8), its divider 3, unless one runs (one at a time).
rg_fxstart:
        ld c,a
        ld a,(frv_fxon)             ; ($1F948: tst.b $B3E)
        or a
        ret nz
        ld (frv_fxx),hl             ; ($1F960: $B56 = x)
        ex de,hl
        ld de,-8
        add hl,de
        ld (frv_fxy),hl             ; ($1F964: $B66 = y - 8)
        ld b,0
        ld hl,rgt_fx_first
        add hl,bc
        ld a,(hl)
        ld (frv_fxfrm),a            ; ($1F950: $B46 = the type's first frame)
        ld hl,rgt_fx_end
        add hl,bc
        ld a,(hl)
        ld (frv_fxend),a            ; ($1F958: $B4E = its end frame)
        ld a,1
        ld (frv_fxon),a             ; ($1F95C)
        ld a,3
        ld (frv_fxdiv),a            ; ($1F96A: $BB6 = 3)
        ret

; $1F808: the hit effect's frame of the last pass erased (mode $100, set even with no effect).
rg_fxerase:
        ld hl,0x0100
        ld (rg_mode),hl             ; ($1F808)
        ld a,(frv_fxon)
        or a
        ret z                       ; ($1F81C)
        ld a,(frv_fxfrm)
        add a,a
        ld e,a
        ld d,0
        ld hl,rgt_fx_size
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)                   ; ($1F830: D4 = the frame's BLTSIZE)
        ld hl,(frv_fxx)
        ld de,(frv_fxy)
        ld a,RG_NONE
        jp rg_bob                   ; ($1F834)

; $1F83A: the hit effect: $BB6 - 1 every pass; while an effect runs, the next frame each time it
; goes below 0 (then 3: the first frame shows 3 passes, the others 4), until the type's end frame
; ends it ($B3E = 0); else the frame drawn (mode $9F0; its mask is not stored: no used test reads
; a dissolve's bytes, docs/RANGE.md 3.4, so its blit counts as 0s). The wanted state's dissolve:
; this draw, or none.
rg_fxdraw:
        ld hl,0x09F0
        ld (rg_mode),hl             ; ($1F844)
        ld hl,frv_fxdiv
        dec (hl)                    ; ($1F854: subq.b #1,$BB6)
        ld a,(frv_fxon)
        or a
        jr z,rfd_off                ; ($1F85C)
        bit 7,(hl)
        jr z,rfd_f                  ; ($1F862: tst.b $BB6 / bpl)
        ld (hl),3
        ld hl,frv_fxfrm
        add a,(hl)
        ld (hl),a                   ; ($1F86A: $B46 + $B3E)
rfd_f:  ld a,(frv_fxend)
        ld b,a
        ld a,(frv_fxfrm)
        cp b
        jr z,rfd_off                ; ($1F878: its end)
        ld e,a
        ld d,0
        ld hl,rg_fpic
        add hl,de
        ld a,(hl)
        ld (rg_want + RG_ST_FX + RG_FX_PIC),a
        ld hl,rgt_fx_size
        add hl,de
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(frv_fxx)
        ld (rg_want + RG_ST_FX + RG_FX_X),hl
        ld de,(frv_fxy)
        ld (rg_want + RG_ST_FX + RG_FX_Y),de
        ld a,RG_NONE
        jp rg_bob                   ; ($1F88C)
rfd_off:
        xor a
        ld (frv_fxon),a             ; ($1F89C: clr.b $B3E)
        ld a,RG_NONE
        ld (rg_want + RG_ST_FX + RG_FX_PIC),a
        ret

; ----- the hit test (docs/RANGE.md 3.4) -----

; $1EDBC frng_draw_bob, as far as the logic sees it: HL = x (D0: bitplane x + 128), DE = y (D1: the
; row), BC = the BLTSIZE (D4: h << 6 | w words, the last for the shift), A = the picture whose mask
; the first blit reads (rgt_pics; RG_NONE when that blit's bytes are 0: an erase, mode $100, or a
; dissolve), rg_mode ($1EEC6), rg_clip ($1EE42) -> $B0B (FFh: the shot's pixel set in that blit's
; output; not tested with RG_NONE: no one reads an erase's or a dissolve's), $BA2-$BA5 (the pixel's
; column in the BOB's word-aligned box, its high byte FFh when outside; its row, rows 0 to h
; passing: quirk T1), the recent-blit list. The drawing itself is the renderer's. Keeps IX, IY.
rg_bob:
        ld (rgb_pic),a
        ld (rgb_x),hl
        ld (rgb_y),de
        ld (rgb_sz),bc
        ld a,0xFF
        ld (frv_hitx + 1),a         ; ($1EDC6: st $BA2, the column's high byte)
        xor a
        ld (frv_hit),a              ; ($1EDCA: clr.b $B0B)
        ld a,l
        and 0xF0
        ld e,a
        ld d,h
        ld hl,(frv_cx)
        ld bc,17
        add hl,bc
        or a
        sbc hl,de                   ; ($1EDE2: D7 = (x & 15) + $B9A + 17 - x)
        jp m,rgb_ro                 ; (bmi: left of the box)
        ex de,hl
        ld a,(rgb_sz)
        and 0x1F
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        dec hl                      ; ($1EDE6: D6 = ((D4 & 1Fh) - 1) * 16 + 15)
        or a
        sbc hl,de
        jp m,rgb_ro                 ; ($1EDEC: cmp.w / bmi: right of it)
        ld (frv_hitx),de            ; ($1EDEE: $BA2 = D7)
rgb_ro: ld hl,(rgb_sz)
        xor a
        add hl,hl
        rla
        add hl,hl
        rla
        ld l,h
        ld h,a
        ld (rgb_h),hl               ; ($1EDFE: h = D4 >> 6)
        ex de,hl
        ld hl,(frv_cy)
        ld bc,(rgb_y)
        or a
        sbc hl,bc
        ld (frv_hitrow),hl          ; ($1EE0C: $BA4 = $B9E - y)
        jp p,rgb_r1
        ld a,0xFF
        ld (frv_hitx + 1),a         ; ($1EE12: above the box)
rgb_r1: ex de,hl
        or a
        sbc hl,de
        jp p,rgb_cl                 ; ($1EE18: h - $BA4, cmp.w / bpl: rows 0 to h pass)
        ld a,0xFF
        ld (frv_hitx + 1),a         ; ($1EE1A: below it)
rgb_cl: ld a,(rgb_sz)
        and 0x3F
        dec a
        add a,a
        ld (rgb_wb),a               ; ($1EDFA: wb = 2 ((D4 & 3Fh) - 1), the mask's row bytes)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,(rgb_x)
        add hl,de
        ld de,(rg_clip)
        or a
        sbc hl,de                   ; ($1EE40: 8 wb + x - the clip)
        ld bc,(rgb_sz)
        jp m,rgb_w                  ; ($1EE44: bmi, nothing past the clip)
        ld a,4
rgb_k:  srl h
        rr l
        dec a
        jr nz,rgb_k                 ; ($1EE58: k = that >> 4, the whole words dropped)
        ld a,c
        sub l
        ld c,a
        ld a,b
        sbc a,h
        ld b,a                      ; ($1EE5A: D4 - k)
        add hl,hl
        ld a,(rgb_wb)
        add a,2
        ld e,a
        ld d,0
        or a
        sbc hl,de
        ret p                       ; ($1EE64: dmod = $26 - wb + 2 k reaching $28: no blit, no test)
rgb_w:  ld a,c
        and 0x3F
        add a,a
        ld (rgb_row),a              ; (the first blit's rows: 2 w' bytes, w' = D4 & 3Fh)
        ld de,(rgb_h)
        call rg_mul
        ex de,hl                    ; (DE = its output's bytes, 2 w' h)
        ld a,(rg_btop)              ; the list: the newest entries whose output is no larger go (this
rgb_dp: cp rg_blits & 0xFF          ;   one covers them); its sizes fall from the oldest to the newest
        jr z,rgb_ps
        sub RGB_LEN
        ld l,a
        ld h,rg_blits >> 8
        ld a,e
        sub (hl)
        inc hl
        ld a,d
        sbc a,(hl)
        ld a,l
        dec a
        jr nc,rgb_dp                ; (no larger: dropped)
        add a,RGB_LEN               ; (larger: kept, this one after it)
rgb_ps: cp (rg_blits + RGB_LEN * RG_BLITS_MAX) & 0xFF
        call z,rgb_full
        ld l,a
        ld h,rg_blits >> 8
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld a,(rgb_row)
        ld (hl),a
        inc hl
        ld a,(rg_mode + 1)
        ld (hl),a
        inc hl
        ld a,(rgb_x)
        and 15
        ld (hl),a
        inc hl
        ld a,(rgb_pic)
        ld (hl),a
        inc hl
        ld a,(rgb_wb)
        ld (hl),a
        inc hl
        push hl
        ld hl,(rgb_y)               ; (the priority plane's offset of its first word: $1EE30's 40 y,
        ld d,h                      ;  then $1EE84's (x & FFF0h) / 8 - 16)
        ld e,l
        add hl,hl
        add hl,hl
        add hl,de
        add hl,hl
        add hl,hl
        add hl,hl
        ex de,hl
        ld hl,(rgb_x)
        ld a,l
        and 0xF0
        ld l,a
        srl h
        rr l
        srl h
        rr l
        srl h
        rr l
        add hl,de
        ld de,-16
        add hl,de
        ex de,hl
        pop hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld a,l
        ld (rg_btop),a
        ld a,(rgb_pic)              ; (an erase's or a dissolve's own test: skipped, nothing reads its
        cp RG_NONE                  ;  $B0B: only $1F5FE and $1F43C read it, right after their own draw)
        ret z
        ld a,(fr_code + RG_FC_SHOT) ; ($1EEE8: tst.b $1EB46, a shot in the previous pass)
        or a
        ret z
        ld a,(frv_hitx + 1)         ; ($1EEF0: $BA2 / bmi: outside the box)
        or a
        ret m
        ld a,(rgb_row)
        ld de,(frv_hitrow)
        call rg_mul                 ; ($1EF00: 2 w' x $BA4, mulu's low word)
        ex de,hl
        ld hl,(frv_hitx)
        srl h
        rr l
        srl h
        rr l
        srl h
        rr l
        add hl,de                   ; ($1EF06: + ($BA2 >> 3), a word add: the byte i)
        call rg_tmp                 ; (the byte at $7FC50 + i)
        ld c,a
        ld a,(frv_hitx)
        and 7
        jr z,rgb_bt
        ld b,a
rgb_sh: sla c
        djnz rgb_sh
rgb_bt: bit 7,c                     ; ($1EF12: its bit 7 - ($BA2 & 7))
        ret z
        ld a,0xFF
        ld (frv_hit),a              ; ($1EF18: st $B0B)
        ret

; (The list full: RG_BLITS_MAX entries of strictly falling sizes, more than tools/msxrange.py found
; possible. The oldest goes, and the loss is counted in rg_blost.) -> A = the free entry's low byte.
; Keeps DE.
rgb_full:
        push de
        ld hl,rg_blits + RGB_LEN
        ld de,rg_blits
        ld bc,RGB_LEN * (RG_BLITS_MAX - 1)
        ldir
        pop de
        ld hl,rg_blost
        inc (hl)
        jr nz,rgf_n
        dec (hl)
rgf_n:  ld a,(rg_blits + RGB_LEN * (RG_BLITS_MAX - 1)) & 0xFF
        ret

; HL = i -> A = the byte at $7FC50 + i as the blits so far left it: from the newest recent blit
; whose output covers it, else 0 (the buffer as the bench starts it). In its row r = i / 2 w', at
; byte c = i mod 2 w': ((the mask's bytes c - 2, c - 1, c of row r) >> the shift)'s low byte, the
; bytes outside the row's first w' - 1 words 0 (the word before the first, and the last: ALWM 0),
; less (mode $B50) the priority plane's byte at the blit's first word + 40 r + c. range_hit.bin
; through the 8000h window: the masks in RANGE_HIT_BANK + 1, the plane in RANGE_HIT_BANK; BANK_FRONT
; back. Keeps IX, IY.
rg_tmp:
        ex de,hl
        ld a,(rg_btop)
rtm_lp: cp rg_blits & 0xFF
        jr z,rtm_0
        sub RGB_LEN
        ld l,a
        ld h,rg_blits >> 8
        ld a,e
        sub (hl)
        inc hl
        ld a,d
        sbc a,(hl)
        ld a,l
        dec a
        jr nc,rtm_lp                ; (i past its output: an older one)
        jr rtm_e
rtm_z:  pop ix
rtm_0:  xor a
        ret
rtm_e:  dec hl
        push ix
        push hl
        pop ix                      ; (IX = the entry)
        ex de,hl
        ld c,(ix + 2)
        call rg_div                 ; (HL = r, A = c)
        ld (rgb_c),a
        ld a,(ix + 5)
        cp RG_NONE
        jr z,rtm_z                  ; (an erase or a dissolve: 0)
        push hl
        ld a,(ix + 6)
        ex de,hl
        call rg_mul                 ; (r x wb)
        ex de,hl
        ld a,(ix + 5)
        ld l,a
        ld h,0
        ld c,l
        ld b,h
        add hl,hl
        add hl,bc
        add hl,hl
        add hl,hl
        ld bc,rgt_pics + RG_PIC_MASK
        add hl,bc
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a                      ; (the mask's offset in range_hit.bin: 2000h-3FFFh)
        add hl,de
        ld a,(rgb_c)
        ld e,a
        ld d,0
        add hl,de
        ld de,0x8000 - 0x2000 - 2
        add hl,de                   ; (the row's byte c - 2 in the 8000h window)
        ld a,RANGE_HIT_BANK + 1
        call bank_8000
        ld a,(rgb_c)
        sub 2
        ld c,a                      ; (C = the byte's place in the row, from c - 2)
        ld a,(ix + 2)
        sub 2
        ld b,a                      ; (B = 2 w' - 2: the last word's first byte)
        ld de,rgb_win
rtm_g:  xor a
        bit 7,c
        jr nz,rtm_s                 ; (before the row: 0)
        ld a,c
        cp b
        ld a,0
        jr nc,rtm_s                 ; (the last word: 0)
        ld a,(hl)
rtm_s:  ld (de),a
        inc hl
        inc c
        inc de
        ld a,e
        cp (rgb_win + 3) & 0xFF
        jr nz,rtm_g
        pop hl                      ; (r)
        ld a,(ix + 3)
        cp 0x0B
        ld a,0
        jr nz,rtm_p                 ; (mode $9F0: the mask alone)
        ld d,h
        ld e,l
        add hl,hl
        add hl,hl
        add hl,de
        add hl,hl
        add hl,hl
        add hl,hl                   ; (40 r)
        ld e,(ix + 7)
        ld d,(ix + 8)
        add hl,de
        ld a,(rgb_c)
        ld e,a
        ld d,0
        add hl,de
        ld de,0x8000
        add hl,de
        ld a,RANGE_HIT_BANK
        call bank_8000
        ld a,(hl)                   ; (the priority plane's byte: 1 where the scenery hides)
rtm_p:  ld (rgb_pr),a
        ld a,BANK_FRONT
        call bank_8000
        ld b,(ix + 4)               ; (the shift)
        ld hl,(rgb_win)             ; (L = the byte c - 2, H = c - 1,
        ld a,(rgb_win + 2)          ;  A = c)
        inc b
        jr rtm_n
rtm_r:  srl l
        rr h
        rra
rtm_n:  djnz rtm_r
        ld c,a
        ld a,(rgb_pr)
        cpl
        and c
        pop ix
        ret

; HL = HL / C, A = the remainder (C 1-127). Uses B.
rg_div:
        xor a
        ld b,16
rgv_l:  add hl,hl
        rla
        cp c
        jr c,rgv_n
        sub c
        inc l
rgv_n:  djnz rgv_l
        ret

; HL = A x DE, its low 16 bits (mulu's low word). Uses A, B.
rg_mul:
        ld hl,0
        ld b,8
rml_l:  add hl,hl
        add a,a
        jr nc,rml_n
        add hl,de
rml_n:  djnz rml_l
        ret

        include "frngview.asm"      ; the display: rg_show, rg_feed, rg_hide

; ----- data -----

rg_pal1:
        incbin "range_1_grade.pal"  ; visit 1's 16 colours ($1FBEA), through the colour grade (tools/mkrom.py)
rg_pal2:
        incbin "range_2_grade.pal"  ; visit 2's ($1FC2A)
        include "range_tab.inc"     ; FRNG's tables and fr_code's initial image (tools/msxrange.py)
