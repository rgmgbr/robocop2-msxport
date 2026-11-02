; Level 1's briefing (tools/mkrom.py L1BRIEF=1), in the front end's second bank (BANK_FRONT2 at A000h,
; FRONT at 8000h: front2_call; after ending.asm, nothing there moves): the screens' code and the script
; (fe_text reads it in place, as et_keep reads the ending's: hud_keep leaves the A000h window alone).
; The level-1 restart's part, rs_init, is photo.asm's (FRONT: level_restart's front_call).

        if L1BRIEF

; A new game (cold.asm ng_init, after the globals: the score 0, two lives): load_level0 $82EC's level-1
; briefing ($11108 through the curtain entry $1079A) and PIC1 ($FE14, show_picture D0 = 0), then level
; 1's start as before. A new game's HUD under the briefing (hud_init: the panel as the level starts).
; Builds with a script skip it as they skip the title, and so does a test build's first start (no title).
l1_new:
        if INPUT_SCRIPT
        ret
        else
        if PZ_TEST + LV_TEST + END_TEST
        ld a,(pz_first)
        or a
        ret nz
        endif
        call hud_init
        jr l1_show
        endif

; The briefing from the display off (the title's end, a restart): the play area black and page 0
; unscrolled first, the display on; the curtain's 16 frames ($1079A clears the shown screen 16 px from
; both sides a frame: black here), the text (fe_text: 485 calls, fire from tick 50, silent, the HUD
; below), then PIC1 (PHOTOS) and the front end's end (front_done).
l1_show:
        ld hl,pf_pal
        ld bc,32
        xor a
        call fill
        ld hl,fs_clear
        call vdp_cmd                ; (the display off: the title's or the level's bytes there)
        call fs_list
        call fb_prep                ; (a turbo R: its pause off, the display on; g_tick 0)
        ld a,(cpu_tr)
        or a
        call z,display_on
        ld b,16
l1s_c:  push bc
        call fs_tick
        pop bc
        djnz l1s_c
        ld hl,txt_l1_brief
        call fe_text
        if PHOTOS
        xor a
        call pho_end                 ; PIC1
        else
        call front_done
        endif
        jp cpu_title                ; (a turbo R: its pause on again, the Z80, the display off; as
                                    ;  front_bonus' end before a level)

        include "brief1.inc"        ; txt_l1_brief (tools/msxtext.py)
        endif
