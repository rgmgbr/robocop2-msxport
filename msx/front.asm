; The front end (bank BANK_FRONT at 8000h while it runs; called from the fixed code through
; front_call): the pictures in SCREEN 8 - the title (TPIC, shown by game_boot $11A20) and the
; game over (PIC9, main_loop $82A8) - converted by tools/msxpic.py (256 x lines, the fixed
; G7 palette) and stored from their banks on (PIC_..._BANK, 32 lines per bank, read through
; the A000h window).
;
; While a picture shows, the VBLANK interrupt only counts frames and runs the sound (front_mode:
; no register list, no HUD split, no play-field palette).

PIC_TOP:    equ 106                 ; (the picture's centre line on the 212-line screen)

; ----- the title -----

; The title before a new game (rc2.asm title, through front_call; cold.asm cold_init at power-on):
; TPIC with its music (front_title), the front end's end (front_done), then the level's tiles 0-255
; again (cold.asm tiles_upload: the pictures' G7 overwrote the start of page 2). (Was rc2.asm's:
; the fixed area's room, docs/LEVEL2.md 3.2.)
fr_title:
        call front_title
        call front_done
        ld e,4
        jp tiles_upload

; TPIC while the music plays (the user's choices, 2026-10-25; the Amiga loops it until fire):
; - played to its end, the game starts (no loop);
; - fire pressed (after it was released): the music fades out (snd_fade), then RoboCop's speech
;   (YOUR MOVE, CREEP: tools/msxvoice.py's PCM on the PSG), then the game;
; - fire pressed while the speech plays in the music (the SCC / OPLL: its place at tick
;   VOICE_TICK, front_fire): the speech plays out, then the game.
front_title:
        ld a,PIC_TITLE_BANK
        ld b,PIC_TITLE_LINES
        call pic_show
        xor a
        ld (mus_end),a
        ld (vm_hit),a               ; (the last title's speech may have left it set)
        call snd_music              ; (TITM tune 1: $10884)
        call front_fire
        jp z,snd_stop               ; (the tune's end)
        ld a,(vm_hit)
        or a
        jp nz,snd_stop              ; (the speech in the music played out)
        call snd_fade
        ld a,(mus_mode)
        or a
        call z,snd_stop             ; (the PSG player's music; vm_alone stops the SCC's / OPLL's)
        ld hl,vm_alone              ; (music.asm)
        jp mus_call

; The title music fades out (front_title, fire pressed; the port's: the original cuts
; it): 3 dB more every FADE_TICKS ticks (music.asm mus_adv, sndplay.asm sq_frame: mus_att) down
; to silence, 1.2 s, or until the tune's end; front_title then stops it (snd_stop, or vm_alone
; for the SCC / OPLL). The interrupts on.
snd_fade:
        ld a,FADE_TICKS
        ld (mus_fade),a
sfd_lp: halt
        ld a,(mus_end)
        or a
        ret nz
        ld a,(mus_att)
        cp 15
        jr c,sfd_lp
        ret

; ----- the game over -----

; PIC9 with GAME OVER below it (tools/msxtext.py) for 30 seconds, or until fire is pressed once
; released (the fire held as RoboCop fell does not skip it); then the high-score entry when the score
; enters the table and the continue offer when a credit is left (frontx.asm fo_hsc: ending.asm
; hs_entry, front_cont), and the answer (fo_cont) also as the flags: NZ continues (rc2.asm ml_ov:
; lv_cont), Z the title. (The original: 128 VBLs, main_loop $82A8: show_picture D0 = 8; the user's
; choice: longer, and a way out.)
FO_TICKS:   equ 30 * 50             ; 50 Hz ticks (fs_tick: the same time at 60 Hz)
front_over:
        xor a
        ld (fo_cont),a              ; (first: a continue taken earlier in this power-on must not
                                    ;  leave it set for a game over without a credit)
        call snd_stop               ; (show_picture $11E06: $FE14)
        ld a,PIC_GAMEOVER_BANK
        ld b,PIC_GAMEOVER_LINES
        call pic_show
        ld hl,FO_TICKS
        ld c,0                      ; (fire not released yet)
fo_lp:  push hl
        push bc
        call fs_tick
        call ff_bits
        pop bc
        pop hl
        jr z,fo_rel
        dec c
        inc c
        jr nz,fov_x                 ; (pressed after a release)
        jr fo_n
fo_rel: ld c,1
fo_n:   dec hl
        ld a,h
        or l
        jr nz,fo_lp
fov_x:  ld a,0xFF                   ; ($82C4: high_score_entry $12082: its st.b $8032 first (the key
        ld (g_key),a                ;  byte: FFh, no key), which a continued game's frame_keys then
                                    ;  takes as handled ($8033))
        call fo_hsc                 ; (the rest of $12082, then $82CA's $11FD2 (front_cont); a turbo
                                    ;  R: the Z80 again, cold.asm cpu_title)
        ld a,(fo_cont)
        or a
        ret

; $11FD2 after the game over (docs/LEVEL2.md 3.7, default 6): a credit used, AG $805E - 1 (a word);
; still 0 or more: the game's display again and the offer, $11590 ("YOU HAVE A GAME CREDIT." /
; "PRESS FIRE TO CONTINUE.", 304 calls) through fe_text, silent ($11FDA's load_level_music only
; initialises MU1), and fo_cont set when the screen ended by fire or fire is held at its end ($82D0
; tests $802E right after $10768); below 0 its high byte cleared ($11FEE: 00FFh) and no offer
; ($11FE8 clears the joystick byte: the title). Level 1 never shows it: $805E is 0 there ($83FA,
; Brainstorm solved, is its only + 1, after level 1). After PIC9 (G7, the split and the line
; interrupt off): a turbo R on the Z80 as after front_stats (cpu_title), front_done's SCREEN 5,
; fb_prep, which measures the split and turns the display on on a turbo R, and display_on on the
; other machines (else no HUD split: lines 162-211 would show PIC9's bytes, fs_clear clears 162).
front_cont:
        ld hl,(AG + 0x805E)
        dec hl
        ld (AG + 0x805E),hl
        bit 7,h
        jr z,fc_on
fc_neg: xor a
        ld (AG + (0x805E ^ 1)),a    ; ($11FEE: clr.b $805E, the word's high byte)
        jp cpu_title
fc_on:  call cpu_title
        call front_done
        call fb_prep
        ld a,(cpu_tr)
        or a
        call z,display_on
fc_txt: ld hl,txt_cont              ; (frontx.asm fo_hsc comes here after an entry: the display on)
        call fe_text
        ld a,(fs_done)
        or a
        jr z,fc_yes                 ; (ended by fire)
        call ff_bits
        jr z,fc_x                   ; (no fire held at its end: the title)
fc_yes: ld a,1
        ld (fo_cont),a
fc_x:   jp cpu_title

; ----- the level's statistics -----

; show_level_stats ($85D8: script $1132F through $10762): the henchmen killed ($16C2), the nukes
; collected ($16C0) and the hostages rescued ($16BE) typed into the play area, one script
; element a tick (50 a second: at 60 Hz every sixth VBLANK is skipped), in the text screens'
; font and palette (tools/msxtext.py; column c at x 8c - 16, row r at line 67 + 8r); no cursor
; ($FE14 cleared $B00); the HUD stays below. It ends after the script's wait (362 ticks), or
; with fire from tick 50 on; then the play area goes black at once ($FE14).
front_stats:
        call snd_stop               ; ($10768: $FE14)
        ld hl,fb_init
        call field_call             ; (no play-field BOB holds a list now)
        ld hl,pf_pal
        ld bc,32
        xor a
        call fill                   ; black from the next VBLANK
        call fs_vbl
        ld hl,fs_clear
        call vdp_cmd                ; the play area of page 0 black
        call fs_list                ; page 0 unscrolled, no sprites
fs_on:  call fs_vbl
        ld a,(app_seq)
        ld b,a
        ld a,(pub_seq)
        cp b
        jr nz,fs_on                 ; (until that list is on screen)
        call vdp_wait
        ld hl,txt_pal
        ld de,pf_pal
        ld bc,32
        ldir                        ; ($109A8 at once)
        ld hl,txt_stats
        ld de,fs_buf
        ld bc,TXT_STATS_LEN
        ldir
        ld hl,(AM + 0x16C2)
        ld de,fs_buf + TXT_F1
        call fs_num
        ld hl,(AM + 0x16C0)
        ld de,fs_buf + TXT_F2
        call fs_num
        ld hl,(AM + 0x16BE)
        ld de,fs_buf + TXT_F3
        call fs_num
        ld hl,fs_buf
        ld (fs_ptr),hl
        ld hl,0
        ld (fs_wait),hl
        ld (fs_n),hl
        xor a
        ld (fs_done),a
        ld (fs_col),a
        ld (fs_row),a
fs_lp:  call fs_tick
        call fs_step
        ld hl,(fs_n)
        inc hl
        ld (fs_n),hl
        ld de,50
        or a
        sbc hl,de
        jr c,fs_lp                  ; (not before tick 50)
        ld a,(fs_done)
        or a
        jr nz,fs_end
        call ff_bits
        jr z,fs_lp
fs_end: ld hl,pf_pal
        ld bc,32
        xor a
        call fill
        jp cpu_title                ; (a turbo R: the Z80 again for the title, cold.asm)

; One element of the script ($116CA): a wait going on, a position (00 x y), a character, a wait
; (80-FF 2 n: max(1, 4n) calls, this one the first) or the end (80-FF 7: done).
fs_step:
        ld hl,(fs_wait)
        ld a,h
        or l
        jr z,fst_rd
        dec hl
        ld (fs_wait),hl
        ret
fst_rd: ld hl,(fs_ptr)
        ld a,(hl)
        inc hl
        or a
        jr nz,fst_c
        ld a,(hl)
        inc hl
        ld (fs_col),a
        ld a,(hl)
        inc hl
        ld (fs_row),a
        ld (fs_ptr),hl
        ret
fst_c:  bit 7,a
        jr nz,fst_cmd
        ld (fs_ptr),hl
        jr fs_char
fst_cmd:
        ld a,(hl)
        inc hl
        cp 2
        jr nz,fst_end
        ld e,(hl)
        inc hl
        ld (fs_ptr),hl
        ld d,0
        ex de,hl
        add hl,hl
        add hl,hl                   ; 4n
        ld a,h
        or l
        jr nz,fst_w
        inc hl
fst_w:  dec hl
        ld (fs_wait),hl
        ret
fst_end:
        ld (fs_ptr),hl
        ld a,1
        ld (fs_done),a
        ret

; A = a character: its glyph ($118D6: ' ' 41, from '@' code - 'A', else code - 16h) written over
; the cursor's cell, the cursor one column on.
fs_char:
        ld b,41
        cp 0x20
        jr z,fsc_g
        sub 0x16
        ld b,a
        cp 0x40 - 0x16
        jr c,fsc_g
        sub 0x41 - 0x16
        ld b,a
fsc_g:  ld l,b
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,txt_glyphs
        add hl,de
        ex de,hl                    ; DE = its 8 lines of 4 bytes
        ld a,(fs_col)
        ld c,a
        inc a
        ld (fs_col),a
        ld a,c
        add a,a
        add a,a
        sub 8
        ld c,a                      ; C = the byte in the line (x / 2)
        ld a,(fs_row)
        add a,a
        add a,a
        add a,a
        add a,67                    ; A = its first line
        ld b,8
fsc_ln: push bc
        push af
        ld h,a
        ld l,0
        srl h
        rr l
        ld a,l
        or c
        ld l,a                      ; HL = line * 128 + byte (page 0)
        push de
        ld e,0
        call vram_write
        pop hl
        ld bc,4 * 256 + VDP_DATA
        otir
        ex de,hl
        pop af
        inc a
        pop bc
        djnz fsc_ln
        jp vram_done

; HL = a number (0..32767), DE = its field: the digits from the field's last character back
; ('[' + digit), the field's spaces before them ($11DC6: leading zeros as spaces).
fs_num: ex de,hl
        ld bc,7
        add hl,bc
        ex de,hl
fsn_lp: ld b,16                     ; HL / 10, A = the remainder
        xor a
fsn_d:  add hl,hl
        rla
        cp 10
        jr c,fsn_n
        sub 10
        inc l
fsn_n:  djnz fsn_d
        add a,0x5B
        ld (de),a
        dec de
        ld a,h
        or l
        jr nz,fsn_lp
        ret

; The next 50 Hz tick (a VBLANK; at 60 Hz every sixth one is skipped).
fs_tick:
        call fs_vbl
        ld a,(RG9SAV)
        and 2
        ret nz
        ld hl,fs_div
        inc (hl)
        ld a,(hl)
        cp 6
        ret c
        ld (hl),0
        jr fs_tick
fs_vbl: ld a,(tick)
        ld b,a
fsv_lp: ld a,(tick)
        cp b
        jr z,fsv_lp
        ret

; A register list for the next VBLANK (isr.asm publish): page 0 unscrolled, no sprites; the
; split shows the HUD as in the game.
fs_list:
        call next_list
        push hl
        inc hl
        ld (hl),14                  ; 7 registers (10 on the V9958)
        inc hl
        ex de,hl
        ld hl,fs_regs
        ld bc,12
        ldir
        ex de,hl
        ld a,(spr_set)
        ld (hl),a
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
        ex de,hl
        ld hl,fs_r58
        ld bc,6
        ldir
        ex de,hl
        jp list_tail
fs_regs:
        db 0, 0x97                  ; R#23 first (isr.asm iv_list: the split's R#19 from it)
        db SPLIT_LINE, 0x93         ; R#19: the HUD's split
        db R1_ON, 0x81
        db R8_SPR_OFF, 0x88
        db R2_PAGE0, 0x82
        db 0, 0x92                  ; R#18
fs_r58: db 0, 0x99                  ; V9958: one page (the split sets the HUD's R#25), unscrolled
        db 0, 0x9A
        db 0, 0x9B
fs_clear:
        dw 0, 0, 0, 0, 256, VIEW_LINES  ; SX, SY, DX, DY, NX, NY
        db 0, 0, 0xC0                   ; colour 0, ARG, HMMV

; ----- the bonus stages -----

; load_level1 $8582 after the statistics: Brainstorm ($8382, D0 = 2 after level 1; PIC3 dropped,
; decision 5 of the port): its intro, the stage (msx/puzl.asm, BANK_PUZL at A000h), a continue
; when it is solved ($805E), its result; then the shooting range ($8590: front_range) and the next
; level's briefing (front_brief; rc2.asm ml_ev then starts level 2 after level 1, level 3 after
; level 2). From the state front_stats leaves: the play area black, the HUD below it; a turbo R
; on the Z80 with the display and the interrupts off (cpu_title), the HUD split measured for the
; R800 only (fb_prep).
front_bonus:
        call fb_prep                ; (a turbo R: the Z80's hardware pause off, display_on; g_tick = 0)
        ld hl,txt_bs_intro
        call fe_text                ; ($8384: $114AA through $10762)
        ld a,BANK_PUZL
        call bank_a000
        call bs_stage               ; ($83DE: jsr $17100) -> A = 0 solved, 1 failed, 2 out of time
        push af
        call snd_stop               ; ($83E4: PUZL's player, init and stop all)
        pop af
        or a
        jr nz,fb_res
        ld hl,(AG + 0x805E)
        inc hl
        ld (AG + 0x805E),hl         ; ($83FA: a continue)
        xor a
fb_res: add a,a
        ld e,a
        ld d,0
        ld hl,fb_texts
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        call fe_text                ; ($8400: the result through $10762)
        call front_range            ; ($8590: moveq #1,D0 / bsr $8420; visit 2 runs the same code)
        call front_brief            ; ($859E: the next level's briefing; load_level2's $8548: level 3
                                    ;  follows the level-3 briefing, rc2.asm ml_ev)
        jp cpu_title                ; (a turbo R: the hardware pause on again, the display off)
fb_texts:
        dw txt_bs_ok, txt_bs_fail, txt_bs_time  ; ($840A)

; The bonus stages' set-up, from the state front_stats or cpu_title leaves (front_bonus;
; front_rgtest in PZ_TEST=2 builds). A turbo R's Z80 runs these screens without its hardware
; pause: CHGCPU(80h) turned it on (docs/TURBO_R.md H11, H18), and a PAUSE press would hold the Z80,
; the HUD split and the VBLANK list with it, at any line: the picture garbled while held. The key
; is not read here (the original stages have no pause; front_stats on the R800 ignores it too):
; cpu_title at the end waits for a press left pending, the picture kept (cs_pz), and turns the
; hardware pause on again, so that the title starts as it did after front_stats.
fb_prep:
        ld a,(cpu_tr)
        or a
        jr z,fbp_go
        ld a,(CASPRV)               ; a turbo R: the Z80's hardware pause off (A7h bit 1), first
        and 0xFD                    ;  (a hold inside split_cal would cut a measure short)
        ld (CASPRV),a
        out (TR_PAUSE),a
        call display_on             ; the split measured on the Z80 (split_cal), the line and
                                    ;  VBLANK interrupts and the display on again (other machines
                                    ;  keep theirs: split_cal blanks the HUD a while)
fbp_go: xor a
        ld (g_tick),a               ; (hud_energy keeps the can: PUZL and FRNG never call $89BE)
        ret

; $8420, the shooting range (D0 = 1 after level 1, 5 after level 2: it only picks PIC2 / PIC6,
; dropped by decision 5 of the port; the stage reads the visit from $8050): its intro, the stage
; (msx/frng.asm, BANK_FRNG at A000h), then the rating of its counts, which sets ac_diff ($8060:
; the next level's enemy hit points, docs/RANGE.md 3.10), and its result; a time out gives POOR and
; Brainstorm's OUT OF TIME. screen ($11698). The counts come from the mirror (AM $B04, $B06), where
; the stage leaves them ($1EAC4). fr_rated (rc2.asm, a ret) marks ac_diff set on both paths for
; the trace harness. No snd_stop after the stage: it stopped its sound at its end (frng.asm rg_end,
; as $10768's $FE14 right after FRNG's return), and fe_text stops it again.
front_range:
        ld hl,txt_rg_intro
        call fe_text                ; ($8422: $1142D through $10762)
        ld a,BANK_FRNG
        call bank_a000
        xor a
        ld (AG + (0x804C ^ 1)),a    ; ($845E: clr.b $804C)
        call rg_stage               ; ($8474: jsr $1EA00; the counts stay in AM $B04, $B06)
        ld a,(AG + (0x804C ^ 1))
        or a
        jr z,frg_rate               ; ($847A)
        ld hl,diff_tab + 24
        ld (ac_diff),hl             ; ($8482: $8060 = $C72E, POOR)
        call fr_rated
        ld hl,txt_bs_time
        jp fe_text                  ; ($848C: $11698, Brainstorm's own copy)
frg_rate:
        ld hl,txt_rg_res
        ld de,fs_buf
        ld bc,TXT_RG_LEN
        ldir
        ld hl,(AM + 0x0B06)         ; ($849C: the dummy count into $113E4)
        ld de,fs_buf + TXT_RG_F2
        call fs_num
        ld hl,(AM + 0x0B04)         ; ($84AE: the correct count into $113CA)
        ld de,fs_buf + TXT_RG_F1
        call fs_num
        ld hl,(AM + 0x0B04)         ; ($84C0-$84DC: 6 correct - dummy - 50, in 16 bits)
        ld d,h
        ld e,l
        add hl,hl
        add hl,de
        add hl,hl
        ld de,(AM + 0x0B06)
        or a
        sbc hl,de
        ld de,50
        or a
        sbc hl,de
        ld a,(AG + (0x804A ^ 1))    ; ($84CE: tst.b $804A, the timer's minutes)
        or a
        jr nz,frg_s
        ld de,12
        sbc hl,de                   ; (- 12 below a minute; carry clear: or a)
frg_s:  xor a                       ; ($84DE: below 0 -> 0, else (s div 14) up to 3)
        bit 7,h
        jr nz,frg_r
        ld de,14
frg_d:  or a
        sbc hl,de
        jr c,frg_r
        inc a
        cp 3
        jr nz,frg_d
frg_r:  add a,a
        add a,a
        add a,a                     ; ($84F0: lsl.w #3)
        ld c,a
        ld b,0
        ld hl,diff_tab + 24
        or a
        sbc hl,bc
        ld (ac_diff),hl             ; ($84FC: $8060 = $C716 + 24 - 8 x rating)
        call fr_rated
        ld hl,txt_rg_rate
        add hl,bc
        ld de,fs_buf + TXT_RG_F3
        ld bc,8
        ldir                        ; ($8502: the rating's name into $11400)
        ld hl,fs_buf
        jp fe_text                  ; ($8518: $113A5 through $10762)

        if PZ_TEST = 2
; (Test build, tools/mkrom.py PZ_TEST=2) rc2.asm pz_test's stage: the shooting range alone, from the
; state level 1's set-up and cpu_title leave (a turbo R on the Z80, the display off), then the
; title and a new game as after a level.
front_rgtest:
        call fb_prep
        call front_range
        jp cpu_title
        endif

        if LV_TEST
; (Test build, tools/mkrom.py LV_TEST=2 or 3) rc2.asm lv_test's part: LV_CARRY's score ($8046, a
; BCD long: AG's two words), lives ($8034), credits ($805E) and rating ($8060: ac_diff) over what
; level 1's set-up left (ng_init), and AG $8050 = LV_TEST - 1 (1: level 2, 2: level 3), as the levels
; before, Brainstorm and the range would leave them; then the screens the product shows between the
; range and that level, from the state level 1's set-up leaves (a turbo R: back on the Z80, as after
; the stages): its briefing (front_brief), then cpu_title as at front_bonus' end. rc2.asm lv_next
; follows. (front_l3test: the same routine, the name docs/LEVEL3.md 3.1 gives it)
front_l3test:
front_l2test:
        ld hl,LV_SCORE_H
        ld (AG + 0x8046),hl
        ld hl,LV_SCORE_L
        ld (AG + 0x8048),hl
        ld hl,LV_LIVES
        ld (AG + 0x8034),hl
        ld hl,LV_CREDITS
        ld (AG + 0x805E),hl
        ld hl,diff_tab + 8 * LV_RATING
        ld (ac_diff),hl             ; (front_range's $84FC: $C716 + 8 x the rating)
        ld hl,LV_TEST - 1
        ld (AG + 0x8050),hl         ; (level 2: $81B8's + 1 at level 1's end; level 3: at level 2's)
        call cpu_title              ; (cold.asm: a turbo R, the Z80 again)
        call fb_prep
        call front_brief
        jp cpu_title
        endif

; The next level's briefing at front_bonus' end (docs/LEVEL2.md 3.7): load_level1 $8582's $110F0
; ("TOKUGAWA BREWERY" / "ARREST CAIN") before level 2 (AG $8050 = 1), load_level2's $110B4 ("CIVIC
; CENTRUM" ...) before level 3 (2), else nothing: fe_text with tools/msxtext.py's txt_l2_brief or
; txt_l3_brief (their particle titles typed in the game's font, the original's calls: 393 and 411
; ticks, fire ends them from tick 50 on). Silent, the HUD's messages ticking on below; PIC4 and
; PIC7 after them are dropped (decision 5 of the port).
front_brief:
        ld a,(AG + 0x8050)          ; (the word's low byte)
        ld hl,txt_l2_brief
        dec a
        jp z,fe_text
        ld hl,txt_l3_brief
        dec a
        jp z,fe_text
        ret

; A text screen of the bonus stages ($10762: $10768's screen and loop, then $FE14), HL = its
; script in this bank (positions, characters, FF 02 n, FF 07: tools/msxtext.py txt_bs_*):
; front_stats' screen and loop, the script read in place, with the HUD's work each tick (the VBL
; handler $10266 runs message_ticker $FDA2 during the text screens: the stage's last messages
; tick on). Silent ($FE14), the play area black at its end. A test candidate (TAG) shows TEST n
; below the text (row 10) for the screen's whole length, outside the script: its length stays.
fe_text:
        push hl
        call snd_stop               ; ($10768: $FE14)
        ld hl,fb_init
        call field_call             ; (no play-field BOB holds a list now)
        ld hl,pf_pal
        ld bc,32
        xor a
        call fill                   ; black from the next VBLANK
        call fs_vbl
        ld hl,fs_clear
        call vdp_cmd                ; the play area of page 0 black
        call fs_list                ; page 0 unscrolled, no sprites
fe_on:  call fs_vbl
        ld a,(app_seq)
        ld b,a
        ld a,(pub_seq)
        cp b
        jr nz,fe_on                 ; (until that list is on screen)
        call vdp_wait
        if TAG
        ld a,FE_TAG_COL
        ld (fs_col),a
        ld a,10
        ld (fs_row),a
        ld hl,fe_tag
fe_tg:  ld a,(hl)
        or a
        jr z,fe_tgx
        push hl
        call fs_char
        pop hl
        inc hl
        jr fe_tg
fe_tgx:
        endif
        ld hl,txt_pal
        ld de,pf_pal
        ld bc,32
        ldir                        ; ($109A8 at once)
        pop hl
        ld (fs_ptr),hl
        ld hl,0
        ld (fs_wait),hl
        ld (fs_n),hl
        xor a
        ld (fs_done),a
        ld (fs_col),a
        ld (fs_row),a
fe_lp:  call fs_tick
        call hud_keep               ; ($10266: the panel's messages; its digits)
        call fs_step
        ld hl,(fs_n)
        inc hl
        ld (fs_n),hl
        ld de,50
        or a
        sbc hl,de
        jr c,fe_lp                  ; (not before tick 50)
        ld a,(fs_done)
        or a
        jr nz,fe_end
        call ff_bits
        jr z,fe_lp
fe_end: ld hl,pf_pal
        ld bc,32
        xor a
        call fill
        jp snd_stop                 ; ($FE14)

        if TAG
        if TAG > 9
FE_TAG_COL: equ 14                  ; (TEST nn at x 96-151)
        else
FE_TAG_COL: equ 15                  ; (TEST n at x 104-151)
        endif
fe_tag: db "TEST "
        if TAG > 9
        db 0x30 + TAG / 10
        endif
        db 0x30 + TAG - TAG / 10 * 10, 0
        endif

; ----- pictures -----

; A = the picture's first bank, B = its lines: SCREEN 8 (G7) with it centred, the rest black;
; the display back on.
pic_show:
        ld (ps_bank),a
        ld a,b
        ld (ps_lines),a
        di
        ld a,1
        ld (front_mode),a
        xor a
        ld (split_armed),a
        ei
        ld a,R1_BLANK
        ld b,1
        call wrreg                  ; display off (the VBLANK interrupt stays on)
        ld a,0x0E
        ld b,0
        call wrreg                  ; G7, no line interrupt
        ld a,R8_SPR_OFF
        ld b,8
        call wrreg
        ld a,R2_PAGE0
        ld b,2
        call wrreg
        xor a
        ld b,18
        call wrreg
        xor a
        ld b,23
        call wrreg
        ld a,(vdp_id)
        cp 2
        jr nz,ps_clr
        xor a
        ld b,25
        call wrreg                  ; V9958: no YJK, no border mask, one page
        xor a
        ld b,26
        call wrreg
        xor a
        ld b,27
        call wrreg
ps_clr: call vdp_wait               ; black everywhere (HMMV)
        ld hl,ps_hmmv
        call vdp_cmd
        call vdp_wait
        ld a,(ps_lines)
        ld b,a
        srl a
        neg
        add a,PIC_TOP
        ld h,a                      ; the first line
        ld l,0
        ld e,0
        push bc
        call vram_write
        pop bc
        ld a,(ps_bank)
        call bank_a000
        ld hl,0xA000
ps_lp:  push bc
        ld bc,VDP_DATA              ; (B = 0: 256 bytes, one line)
        otir
        pop bc
        ld a,h
        cp 0xC0
        jr nz,ps_nb
        ld a,(ps_bank)
        inc a
        ld (ps_bank),a
        call bank_a000
        ld hl,0xA000
ps_nb:  djnz ps_lp
        call vram_done
        ld a,R1_ON
        ld b,1
        jp wrreg                    ; display on

ps_hmmv:
        dw 0, 0, 0, 0, 256, 212     ; SX, SY, DX, DY, NX, NY
        db 0, 0, 0xC0               ; colour 0, ARG, HMMV

; Fire (joystick trigger A or a fire key: player.asm key_bits) pressed, after it was released.
; Until fire is pressed once released (vp_rel: NZ) or the music has played to its end
; (mus_end: Z). Meanwhile, when the music on the SCC / OPLL reaches RoboCop's speech
; (mus_speak), the speech plays with the music going on (music.asm vm_music: the interrupts
; off; fire pressed meanwhile: vm_hit, NZ once the speech has played out).
front_fire:
        xor a
        ld (vp_rel),a
ff_lp:  halt
        ld a,(mus_end)
        or a
        jr nz,ff_end
        ld a,(mus_speak)
        or a
        jr z,ff_k
        ld hl,vm_music
        call mus_call
        ld a,(vm_hit)
        or a
        ret nz
        ld a,(vp_rel)               ; fire down as the speech ends, released before it: pressed in
        or a                        ; its last 256 samples, which vm_play does not read: as in the
        jr z,ff_k                   ; speech
        call ff_bits
        jr z,ff_k
        ld (vm_hit),a
        ret
ff_k:   call ff_bits
        ld hl,vp_rel
        jr z,ff_up
        ld a,(hl)
        or a
        jr z,ff_lp
        ret
ff_up:  ld (hl),1
        jr ff_lp
ff_end: xor a
        ret

ff_bits:
        call stick_bits
        and 0x10
        ld c,a
        push bc
        call key_bits
        pop bc
        and 0x10
        or c
        ret

; The game's display again: SCREEN 5 (G4, linear VRAM: what is written next lands where the
; game expects it), display off; the VBLANK interrupt does its frame work (the game sets the
; rest itself: new_game, display_on).
front_done:
        call snd_stop               ; (level_init $8720)
        ld a,R1_BLANK
        ld b,1
        call wrreg
        ld a,R0_IE1_OFF
        ld b,0
        call wrreg
        di
        xor a
        ld (front_mode),a
        ei
        ret

        if DIAG
; ----- test builds (tools/mkrom.py DIAG=1, music.asm dg_main) -----

; dg_txt (32 x 24 characters) on the screen in the game's font (txt_glyphs: strokes colour 1,
; their shadow colour 4): SCREEN 5 page 0, white on black, no sprites, the interrupts off.
dg_show:
        ld hl,dgv_regs
dgsh_r: ld b,(hl)
        inc hl
        ld a,b
        cp 0xFF
        jr z,dgsh_9
        ld a,(hl)
        inc hl
        call dgv_wr
        jr dgsh_r
dgsh_9: ld a,(RG9SAV)
        and 2
        or 0x80                     ; (212 lines, the machine's 50 or 60 Hz)
        ld b,9
        call dgv_wr
        ld a,(vdp_id)
        cp 2
        jr nz,dgsh_p
        xor a
        ld b,25
        call dgv_wr
        xor a
        ld b,26
        call dgv_wr
        xor a
        ld b,27
        call dgv_wr
dgsh_p: xor a
        ld b,16
        call dgv_wr                 ; (palette from entry 0)
        ld hl,dgv_pal
        ld bc,32 * 256 + VDP_PAL
        otir
        xor a                       ; page 0 black (VRAM 0000h-7FFFh)
        out (VDP_CTRL),a
        ld a,0x8E
        out (VDP_CTRL),a
        xor a
        out (VDP_CTRL),a
        ld a,0x40
        out (VDP_CTRL),a
        ld de,0x8000
dgsh_c: xor a
        out (VDP_DATA),a
        dec de
        ld a,d
        or e
        jr nz,dgsh_c
        ld b,0
dgsh_w: push bc
        call dg_row
        pop bc
        inc b
        ld a,b
        cp 24
        jr nz,dgsh_w
        ld a,0x40                   ; display on (no interrupts)
        ld b,1
        jp dgv_wr

; A = a value for VDP register B (the interrupts off).
dgv_wr: out (VDP_CTRL),a
        ld a,b
        or 0x80
        out (VDP_CTRL),a
        ret

; B = a row of dg_txt: its 32 characters, 8 x 8 each, from line 4 + 8 B.
dg_row: ld c,0
dgr_c:  push bc
        ld l,b
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld e,c
        ld d,0
        add hl,de
        ld de,dg_txt
        add hl,de
        ld a,(hl)
        call dg_gl
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,txt_glyphs
        add hl,de
        ex de,hl                    ; DE = the glyph's 8 lines of 4 bytes
        pop bc
        push bc
        ld a,b
        add a,a
        add a,a
        add a,a
        add a,4
        ld h,a
        ld l,0
        srl h
        rr l                        ; HL = its first line x 128
        ld a,c
        add a,a
        add a,a
        or l
        ld l,a                      ; + 4 x column (page 0)
        ld b,8
dgr_l:  push bc
        ld a,h
        rlca
        rlca
        and 3
        out (VDP_CTRL),a
        ld a,0x8E
        out (VDP_CTRL),a            ; R#14
        ld a,l
        out (VDP_CTRL),a
        ld a,h
        and 0x3F
        or 0x40
        out (VDP_CTRL),a
        ex de,hl
        ld bc,4 * 256 + VDP_DATA
        otir
        ex de,hl
        ld bc,128
        add hl,bc
        pop bc
        djnz dgr_l
        pop bc
        inc c
        ld a,c
        cp 32
        jr nz,dgr_c
        ret

; A = a character (20h-5Fh) -> A = its glyph in txt_glyphs (a space for the others).
dg_gl:  sub 0x20
        jr c,dgg_sp
        cp 0x40
        jr nc,dgg_sp
        push hl
        ld hl,dg_gtab
        add a,l
        ld l,a
        jr nc,dgg_n
        inc h
dgg_n:  ld a,(hl)
        pop hl
        ret
dgg_sp: ld a,41
        ret

dg_gtab:    db 41, 40, 39, 41, 41, 43, 41, 41, 41, 41, 41, 41, 37, 41, 36, 41  ; space ! " # $ % ... , - . /
            db 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 41, 41, 41, 41, 41, 38  ; 0-9 : ; < = > ?
            db 41, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14             ; @ A-O
            db 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 41, 41, 41, 41, 41   ; P-Z [ \ ] ^ _
dgv_regs:   db 0, 0x06, 1, 0x00, 2, 0x1F, 7, 0x00, 8, R8_SPR_OFF, 15, 0, 18, 0, 23, 0, 0xFF
dgv_pal:    db 0x00, 0x00, 0x77, 0x07, 0x00, 0x00, 0x00, 0x00, 0x24, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
            db 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        endif
