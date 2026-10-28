; Robocop 2 MSX - scroll engine prototype with the HUD split (play area 163 lines, HUD 45).
; MegaROM with a Konami SCC style mapper (MegaRAM compatible): 8 KiB banks switched by
; writes inside the page itself (9000h -> 8000h window, B000h -> A000h window).
; Banks 0-1 = code (4000h-7FFFh, fixed); data in the 8000h and A000h windows.
; Build with tools/mkrom.py (z80asm 1.8).

        include "banks.inc"
        include "sprites.inc"       ; the global sprite pool (tools/msxsprites.py --pool)
        include "hud_rt.inc"
        include "options.inc"       ; build options (tools/mkrom.py): FORCE_V9938, DEMO_ACTORS
        include "msx.inc"

        org 0x4000
        db "AB"
        dw init
        ds 12, 0
        db "ROM_KON5"               ; (4010h: the mapper's tag, Konami SCC: the MSX Pico+ firmware
                                    ;  starts the ROM with it as a sure detection)

init:   di
        ld sp,0xF380
        ld a,0xC9                   ; the BIOS's interrupt hooks: RET (a disk ROM started before
        ld (H_TIMI),a               ;  the game hooks H.TIMI to code at F365h, under this stack:
        ld (H_KEYI),a               ;  the BIOS's interrupts until IM 2 ran the stack's bytes)
        ld a,1                      ; bank 1 at 6000h again: a disk ROM started before the game
        ld (0x7000),a               ;  looks for RAM by writing 711Ch of every slot, which on
                                    ;  this mapper selects another bank there (the DDX 3.0: 127)
        if DIAG
        in a,(PPI_SLOT)
        ld (dg_a8b),a               ; (test build: A8h as the BIOS left it; the SCC probed
        ld hl,dg_log                ;  after each step of the start: sound.asm dg_probe)
        ld (dg_ptr),hl
        endif
        ld hl,2 + 3 * 256           ; the mapper's banks at power-on in the 8000h and A000h windows
        ld (act_8000),hl            ; (act_8000, act_a000: the interrupts put act_a000 back)
        call slot_page2             ; cartridge also in page 2 (8000h-BFFFh)
        ld a,2                      ; (and selected there, whatever wrote in the windows before)
        ld (BANK_8000),a
        inc a
        ld (BANK_A000),a
        ld hl,cold_init
        jp front_call               ; the rest of the start, the title, then level 1 (cold.asm: FRONT
                                    ;  code, the fixed area's room, docs/LEVEL2.md 3.2)

; A new game ($FFC4, $FFD8): level 1 from the disk's state again (the map without the last
; game's changes), score 0, two lives, SHARP; the display and the VDP's interrupts off meanwhile.
new_game:
        call dsp_off
ng_go:
        ld hl,ng_init               ; (cold.asm: AG cleared, two lives, SHARP, then lv_select with
        jr lv_gs                    ;  level 1's descriptor)

; A = the level (0: level 1): its start (level_init $871A), the display and the VDP's interrupts
; off: lv_select (cold.asm: the level's descriptor into lv_cur, its palette, its tiles and atlas
; into VRAM, the tile cache, the attributes, RoboCop and the camera, its logic bank), then its
; objects, the engines, the HUD and the display (docs/LEVEL2.md 3.1).
lv_go:  ld c,a
        ld hl,lv_select
lv_gs:  call front_call
        call logic_map
        call obj_start              ; the objects (the level's bank: lv_init)
        ld a,BANK_LC2
        call bank_8000
        call ao_start               ; the map objects and their first pass over the whole map
        call logic_map
        ld hl,engines_init
        call field_call             ; (field.asm)
        if DEMO_ACTORS
        call spr_demo_init
        endif
        ld hl,hud_init
        call front_call             ; (cold.asm)
        call logic_map
        if DEMO_HUD
        call demo_init
        endif
        call display_on
        if PZ_TEST
        ld a,(pz_first)
        or a
        jp nz,pz_test               ; (test build: Brainstorm once, before level 1's main loop)
        endif
        if LV_TEST
        ld a,(pz_first)
        or a
        jp nz,lv_test               ; (test build: level 2 once, instead of level 1's main loop)
        endif
mainloop:
        call wait_frame             ; feeds the VDP while waiting; returns right after the VBLANK
        call sprites_vblank         ; SAT of the list now on screen (still in the VBLANK)
        call key_scan               ; the keys the game reads as key codes (pause)
        call sec_tick               ; the timer's seconds (the Amiga's CIA-B interrupt)
        call hud_frame              ; HUD changes, long before the beam reaches the HUD
        call feed_vdp               ; (the scroll engine's next VDP command runs meanwhile)
        ld a,(g_tick)               ; did the game tick at the end of the last frame?
        or a
        jr z,ml_frame
        call do_update              ; scroll engine: state of the next frame, VDP work
        call cam_mark               ; (the view the objects are placed against)
        call pl_show                ; RoboCop's composition and place against the view shown
        call bob_flush              ; the BOBs of the tick as sprite objects
        if DEMO_ACTORS
        call demo_tick              ; the demo's objects
        endif
        call feed_vdp
        call sprites_moved          ; their positions go into the next SAT
        call sprites_tick           ; the budget for them, before their layout
        jr ml_spr
ml_frame:
        call do_update              ; (no tick: versions on their way may still go on screen)
        call cam_follow             ; (the view caught up without a tick: the objects follow it)
ml_spr: ld hl,fb_frame
        call field_call             ; the play-field BOBs (field.asm): what changed
        call sprites_frame          ; upload slice, SAT, R#5 for the list
        if DEMO_HUD
        call hud_demo               ; demo of the game's HUD events
        endif
        call do_publish             ; registers of the next frame for the VBLANK
        call cadence                ; g_tick: the game's ticks due (30 per second)
        ld a,(g_tick)               ; they run now, while the list waits for its VBLANK (the
        or a                        ; next frame shows their picture)
        jp z,mainloop
ml_tk:  ld a,(g_tn)
        dec a
        ld (bob_skip),a             ; (a tick before the frame's last one: its BOBs are not shown)
tick_start:
        call game_tick              ; the game's logic: RoboCop, the camera (the view)
        ld a,(g_event)
        or a
        jr nz,ml_tkd                ; (a death, the end: no more ticks this frame)
        ld hl,g_tn
        dec (hl)
        jr nz,ml_tk                 ; a late frame: the next tick at once
ml_tkd: ld hl,fl_pend
        ld b,5
ml_flc: ld (hl),0                   ; (held hit flashes: shown now or never)
        inc hl
        djnz ml_flc
        ld a,(jump_pend)            ; the cracked wall moved RoboCop and the camera (mapobj.asm
        or a                        ; act_10): the new view drawn at once
        jr z,ml_ev
        xor a
        ld (jump_pend),a
        ld hl,engines_jump
        call field_call
ml_ev:  ld a,(g_event)
        or a
        jp z,mainloop
        cp FE_RESTART
        jr z,ml_rst
        cp FE_OVER
        ld hl,front_over            ; game over: PIC9
        jr z,ml_fe
        ld hl,front_stats           ; the next level: its statistics ($85D8; a turbo R: the Z80
        call front_call             ;  again, front.asm), then load_level1's bonus stage
        ld hl,front_bonus           ;  (Brainstorm $8382, then the range $8420; level 2 later),
ml_fe:  call front_call             ;  then (for now) the title and a new game
        call title
        jp new_game
ml_rst: call level_restart
        xor a
        ld (g_tick),a               ; (no picture of the ticks before the restart)
        jp mainloop

        if PZ_TEST
; (Test build, tools/mkrom.py PZ_TEST=1 or 2) Once after the power-on, instead of level 1's main
; loop: the bonus stages as after level PZ_LEVEL ($8050; AG as ng_go cleared it: score 0, two
; lives, no continue) from the state front_stats leaves (a turbo R: the Z80 again), then the title
; and a new game as after a level. PZ_TEST=1: Brainstorm, then the shooting range (front_bonus);
; PZ_TEST=2: the range alone (front.asm front_rgtest).
pz_test:
        xor a
        ld (pz_first),a
        ld hl,PZ_LEVEL
        ld (AG + 0x8050),hl         ; (the level done: the stages' visit)
        ld hl,cpu_title
        call front_call             ; (cold.asm)
        if PZ_TEST = 2
        ld hl,front_rgtest
        else
        ld hl,front_bonus
        endif
        jr ml_fe
        endif

        if LV_TEST
; (Test build, tools/mkrom.py LV_TEST=2) Once after the power-on, instead of level 1's main loop:
; level 2 as the product starts it after the range, with LV_CARRY's score, lives, credits and
; rating (front.asm front_l2test: the carry, AG $8050 = 1, the screens between the range and the
; level), then lv_next; later games as the product's (pz_first: one shot).
lv_test:
        xor a
        ld (pz_first),a
        ld hl,front_l2test
        call front_call
        endif
; The next level (load_level1's tail $85B8-$85C4 and level_init $871A: AG $8050 its number, 1 for
; level 2): the display and the VDP's interrupts off (as a new game), then its start (lv_go).
lv_next:
        call dsp_off
        ld a,(AG + 0x8050)          ; (the word's low byte: the mirror keeps words little-endian)
        jp lv_go

; The CIA-B interrupt ($1015E, an alarm of 15625 lines: once a second) unless paused: the timer's
; seconds - 1 (BCD), at the bottom its minutes - 1 and seconds 59; below 0:00 time out ($804C,
; the timer stays at 0:00). Test builds with a script keep it still (the bench raises no CIA-B
; interrupt).
sec_tick:
        if INPUT_SCRIPT
        ret
        else
        ld a,(g_paused)
        or a
        ret nz
        ld a,(RG9SAV)
        and 2
        ld c,60
        jr z,stk_hz
        ld c,50
stk_hz: ld a,(wf_n)                 ; (the VBLANKs since the last frame)
        ld hl,sec_n
        add a,(hl)
        cp c
        jr nc,stk_sec
        ld (hl),a
        ret
stk_sec:
        sub c
        ld (hl),a
        ld hl,AG + (0x804B ^ 1)     ; seconds
        ld a,(hl)
        sub 1
        daa
        jp p,stk_s
        ld hl,AG + (0x804A ^ 1)     ; minutes
        ld a,(hl)
        sub 1
        daa
        jp m,stk_out
        ld (hl),a
        ld hl,AG + (0x804B ^ 1)
        ld a,0x59
stk_s:  ld (hl),a
        ret
stk_out:
        ld a,0xFF
        ld (AG + (0x804C ^ 1)),a
        ret
        endif

display_on:
        call split_cal              ; the HUD split's delay on this CPU (isr.asm; display off)
        ld a,R0_IE1_ON
        ld b,0
        call wrreg                  ; line interrupt on (R#19 comes with each frame)
        ld a,R1_ON
        ld b,1
        jp wrreg                    ; display and VBLANK interrupt on

; Brainstorm's end (msx/puzl.asm bs_stage), A = its result: the trace harness's breakpoint
; (tools/openmsx_rc2.tcl rc2_pz_drive), reached once, before anything changes the mirror.
pz_done:
        ret

; After a death with lives left (main_loop $82E4: level_init again, without reloading the
; level): the map keeps its changes and the lists their state (ao_start resets the object
; list's entries but type 58h's), RoboCop and the camera at the start, weapon 0; the display
; and the VDP's interrupts off meanwhile; the HUD as it is.
level_restart:
        call dsp_off
        ld hl,pl_init
        call front_call             ; (cold.asm)
        call logic_map
        call obj_start              ; (lv_fresh clear: the header's values only)
        ld a,BANK_LC2
        call bank_8000
        call ao_start
        call logic_map
        xor a
        call set_weapon             ; ($8844)
        ld hl,engines_init
        call field_call
        jp display_on

; The title (front end) before a new game (front.asm fr_title); test builds with a script start
; the game at once.
title:
        if INPUT_SCRIPT
        ret
        else
        ld hl,fr_title
        jp front_call
        endif

; The display and the VDP's interrupts off (a new game, a death's restart).
dsp_off:
        ld a,R0_IE1_OFF
        ld b,0
        call wrreg
        ld a,0x02                   ; display off, no VBLANK interrupt
        ld b,1
        jp wrreg

; HL = a routine of the play-field BOB module (BANK_FIELD at A000h around it; the bank that was
; there comes back). Keeps nothing but what the routine returns in BC, DE, HL.
field_call:
        ld a,(act_a000)
        push af
        ld a,BANK_FIELD
        call bank_a000
        call fc_hl
        pop af
        jp bank_a000
fc_hl:  jp (hl)

; HL = a routine of the front end (BANK_FRONT at 8000h around it).
front_call:
        ld a,BANK_FRONT
        call bank_8000
        jp (hl)

do_update:
        ld hl,(update_vec)
        jp (hl)

do_publish:
        ld hl,(pub_vec)
        call fc_hl
        ld hl,fb_tick               ; (field.asm: this picture's play-field copies may start now,
        inc (hl)                    ; the next one's items wait for it)
        ret

idle_work:
        ld a,(fb_busy)              ; the play-field BOBs (field.asm) first while they have work: a
        or a                        ; picture waits for them (isr.asm)
        jr z,iw_scr
        ld a,(fb_cq)                ; (their copy waiting, its picture published and uploaded:
        rra                         ; nothing else may take the VDP before the interrupts start it,
        jr nc,iw_fb                 ; or fb_wait in the blank)
        ld a,(fb_tick)
        ld hl,fb_cur + 11
        cp (hl)
        jr z,iw_scr
        ld a,(pk_state)
        dec a
        jr z,iw_scr
        ld a,(split_armed)
        or a
        ret nz
        call vdp_busy
        ret nz
        ld hl,fb_work
        jp field_call
iw_fb:  call vdp_busy
        ret nz
        ld hl,fb_work
        call field_call
iw_scr: ld hl,(idle_vec)
        jp (hl)                     ; the scroll engine's step (a command when the VDP is idle)

; Selects in page 2 the same slot (primary/secondary) as page 1.
slot_page2:
        call RSLREG
        rrca
        rrca
        and 3
        ld c,a
        ld b,0
        ld hl,EXPTBL
        add hl,bc
        ld a,(hl)
        and 0x80
        or c
        ld c,a                      ; C = E000 00PP
        ld hl,SLTTBL
        ld a,c
        and 3
        ld e,a
        ld d,0
        add hl,de
        ld a,(hl)
        and 0x0C                    ; secondary slot of page 1
        or c
        ld h,0x80
        jp ENASLT

        include "bank.asm"
        include "vdp.asm"
        include "isr.asm"
        include "tiles.asm"
        include "bob.asm"
        include "logic.asm"         ; the game logic's helpers
        include "at_fixed.inc"
        include "scroll9958.asm"
        include "scroll9938.asm"
        include "sprites.asm"
        include "hud.asm"
        include "player.asm"
        include "sound.asm"         ; the PSG and the OPLL (MSX-MUSIC / FM-PAC)
        include "player.inc"        ; RoboCop's logic tables (tools/player.py --inc)

; The shooting range's end (msx/frng.asm rg_stage leaves through it, the counts in the mirror) and
; its rating (front.asm front_range, ac_diff set, on both paths): the trace harness's breakpoints
; (tools/openmsx_rc2.tcl rc2_fr_drive), reached once each, before anything changes what they
; record. (After the code, before its tables: no routine moves.)
fr_done:
        ret
fr_rated:
        ret

        include "sprites_flash.inc" ; RoboCop's palette flashes (tools/msxsprites.py)
        include "grade.inc"         ; the fade's limits through the colour grade (tools/mkrom.py)
; (rowtab.inc, tools/mkrom.py: the map's rows, their banks relative to lv_mapb; the attributes'
; rows; view_offx)
rowtab:
        include "rowtab.inc"

code_end:
        ds 0x8000 - code_end, 0xFF  ; pads banks 0-1 (16 KiB)

; ----- the game logic, module 1: the enemies (BANK_LC1 at 8000h while the game ticks) -----
        org 0x8000
        include "objects.asm"
        include "shots.asm"         ; RoboCop's fire, shots and effects
        include "hits.asm"          ; RoboCop against bullets, enemies, pickups; the pickups
        include "at_c1.inc"         ; the original's tables (tools/amitab.py)
lc1_end:
        ds 0xA000 - lc1_end, 0xFF

; ----- the game logic, module 2: the map objects (BANK_LC2 at 8000h around its calls) -----
        org 0x8000
        include "mapobj.asm"
        include "at_c2.inc"
lc2_end:
        ds 0xA000 - lc2_end, 0xFF

; ----- the game logic of level 1 (BANK_L1 at A000h) -----
        org 0xA000
        include "level1.asm"
        include "at_l1.inc"
        include "cells_l1.inc"      ; the camera-cell masks of its spawn list and hazards (tools/cellmasks.py)
l1_end:
        ds 0xC000 - l1_end, 0xFF

; ----- the game logic, module 3: the special objects (BANK_LC3 at 8000h around its calls) -----
        org 0x8000
        include "special.asm"
        include "frame.asm"
        include "plmove.asm"        ; RoboCop's player_move (player.asm game_tick)
        include "at_c3.inc"
lc3_end:
        ds 0xA000 - lc3_end, 0xFF

; ----- the joystick script of test builds and the sound player (BANK_INPUT at A000h around
; their calls) -----
        org 0xA000
        include "input.inc"         ; (tools/mkrom.py JOY=..., TELE=...)
        include "sndplay.asm"
        include "sound.inc"         ; the streams (tools/msxsound.py)
input_end:
        ds 0xC000 - input_end, 0xFF

; ----- the front end: title, game over (BANK_FRONT at 8000h around its calls: front_call) -----
        org 0x8000
        include "front.asm"
        include "cold.asm"          ; init routines of the fixed code (cold.asm)
        include "split.asm"         ; the HUD split's code that runs from RAM (isr_init copies it)
        include "split8.asm"        ; the same on a turbo R's R800 (cold.asm cpu_set installs it)
        include "text.inc"          ; the text screens' font and the statistics (tools/msxtext.py)
        include "levels.inc"        ; the levels' descriptors, palettes and view_offy (tools/mkrom.py)
front_end:
        ds 0xA000 - front_end, 0xFF

; ----- the play-field BOBs and the scroll engines' set-up (BANK_FIELD at A000h around its calls:
; field_call) -----
        org 0xA000
        include "field.asm"
field_end:
        ds 0xC000 - field_end, 0xFF

; ----- the title music on the SCC / OPLL and RoboCop's speech (BANK_MUSIC at A000h around their
; calls: mus_call, snd_frame) -----
        org 0xA000
        include "music.asm"
        if DIAG
        include "diag.asm"          ; (test builds: what this machine showed the sound detection)
        endif
        if DIAG = 2
        include "lab.asm"           ; (test build: the VDP lab)
        endif
        include "music.inc"         ; the streams' banks, the SCC's waveforms, the OPLL's patch (tools/mkrom.py)
music_tab:
        ds (0x100 - (music_tab & 0xFF)) & 0xFF, 0xFF  ; (voice_tab: 256-byte aligned)
        include "voice.inc"         ; RoboCop's speech: its PSG tables (tools/msxvoice.py)
        ds (VOICE_RATE_T - 322) * 0x4000  ; (music.asm vm_cal aims at 322 T-states a sample: an
                                    ;  error here when tools/msxvoice.py's RATE_T changes)
        include "tune.inc"          ; the tunes after the title: Brainstorm's descriptor (tools/mkrom.py)
        include "tune.asm"          ;   and its player (after the title's code and tables: those keep
                                    ;   their places and bytes)
music_end:
        ds 0xC000 - music_end, 0xFF

; ----- Brainstorm, the bonus stage after level 1 (BANK_PUZL at A000h while it runs, FRONT at
; 8000h: front.asm front_bonus) -----
        org 0xA000
        include "puzl.asm"
puzl_end:
        ds 0xC000 - puzl_end, 0xFF

; ----- the shooting range, the second bonus stage after level 1 (BANK_FRNG at A000h while it
; runs, FRONT at 8000h: front.asm front_range) -----
        org 0xA000
        include "frng.asm"
frng_end:
        ds 0xC000 - frng_end, 0xFF

; ----- the game logic of level 2 (BANK_L2 at A000h while it is played, as BANK_L1 for level 1:
; lv_cur's lv_logic; docs/LEVEL2.md 3.2) -----
        org 0xA000
        include "level2.asm"
        include "at_l2.inc"
        include "cells_l2.inc"      ; the camera-cell masks of its spawn list and hazards (tools/cellmasks.py)
l2_end:
        ds 0xC000 - l2_end, 0xFF
