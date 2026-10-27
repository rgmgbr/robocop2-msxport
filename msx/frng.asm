; The shooting range, the second bonus stage after level 1 (the Amiga's FRNG at $1EA00, which
; $8420 calls: docs/RANGE.md). Bank BANK_FRNG at A000h while it runs, FRONT at 8000h (front.asm
; front_range calls rg_stage); its graphics in the data banks from RANGE_GFX_BANK, its hit data from
; RANGE_HIT_BANK (tools/mkrom.py, tools/msxrange.py).
;
; The stage's entry and exit as FRNG's (docs/RANGE.md 3.1, step 6 of its section 5), with no
; targets and no display yet: FRNG's set-up (the sound stopped, weapon 0 and 25 shots on the panel,
; the mirror cleared, fr_code loaded, the visit's palette, the timer from 2:00, the crosshair's
; start, the delays idle, a fade in), then one pass per 50 Hz tick on 50 and 60 Hz machines (its
; PAL design rate: docs/RANGE.md 3.5) with the HUD, the timer and the joystick, and FRNG's end
; checks ($1EAA6): 130 passes after the ammo runs out ("NO AMMO."), at once when the timer runs out
; ("TIME OUT."). The play area stays black (front_range's intro left the palette black); the HUD
; shows below it as in the game. The logic (step 7), the display (steps 8-9) and the sound (step
; 11) come later.
;
; Its variables live in the mirror at their Amiga addresses (msx.inc frv_...: $B00-$BC5) and in
; fr_code (msx.inc: FRNG's code-area state), so that the trace harness compares them pass by pass
; with the original's (tools/openmsx_rc2.tcl rc2_fr_drive, tools/frngcmp.py, tools/amigaemu.py
; frng). Rules (Brainstorm's): FRONT at 8000h and BANK_FRNG at A000h while it runs; it calls fixed
; code and FRONT; data banks only at 8000h, through bank_8000, BANK_FRONT put back; hud_frame only
; through hud_keep.

        include "range.inc"         ; the stage's view, VRAM map, positions and layouts (tools/msxrange.py)

; (Build checks, no bytes: fr_code ends where the recent-blit list starts, and that list fits MP_B
; with its room (range.inc); an error here otherwise.)
        ds 0 - (fr_code + RG_FC_LEN - rg_blits) * (fr_code + RG_FC_LEN - rg_blits)
        ds 0 - (rg_blits + RG_BLITS_ROOM - 1) / (MP_B + 0x0300)
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
        jp fr_done                  ; ($1EAC4: the counts stay in $B04 and $B06)
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
        jp fr_done

; ($1EA40) The next 50 Hz tick: a VBLANK, at 60 Hz every sixth one skipped (front.asm fs_tick's
; rule and its fs_div). wf_n = the VBLANKs since the last pass, or since the timer's set-up
; (sec_tick counts real seconds with it).
rg_wait:
        ld a,(tick)
        ld b,a
rw_lp:  ld a,(tick)
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

; $1EA4A-$1EAA4: one pass, after its wait (tools/openmsx_rc2.tcl samples the mirror at fr_tick's
; call). For now: the fade's level, the counters and the joystick; no targets, no crosshair.
fr_frame:
        call rg_fade                ; $1F980
        ld hl,(frv_pass)
        inc hl
        ld (frv_pass),hl            ; ($1EA6E: $B00 + 1)
        ld hl,(frv_pass3)
        inc hl
        inc hl
        inc hl
        ld (frv_pass3),hl           ; ($1EA72: $B02 + 3)
        call joy_read               ; ($1EA92: $801C, $802E for the next pass's crosshair)
        ld hl,(tick_n)
        inc hl
        ld (tick_n),hl              ; (a JOY script goes on through the stage)
        ret

; $1F980: the fade's level ($BC1, 0-31): + 1 a pass while $BC0 is set, else - 1, nothing more at
; either end; at the end of a fade out the palette pointer goes back to visit 1's ($1F9A4). (The
; palette itself, COLOR01-31 limited by the level, comes with the display: step 8.)
rg_fade:
        ld hl,frv_fade
        ld a,(frv_fadein)
        or a
        jr z,rf_out
        ld a,(hl)
        cp 0x1F
        ret z
        inc (hl)
        ret
rf_out: ld a,(hl)
        or a
        ret z
        dec (hl)
        ret nz
        ld hl,rg_pal1
        ld (rg_pal),hl
        ret

; ----- data -----

rg_pal1:
        incbin "range_1_grade.pal"  ; visit 1's 16 colours ($1FBEA), through the colour grade (tools/mkrom.py)
rg_pal2:
        incbin "range_2_grade.pal"  ; visit 2's ($1FC2A)
        include "range_tab.inc"     ; FRNG's tables and fr_code's initial image (tools/msxrange.py)
