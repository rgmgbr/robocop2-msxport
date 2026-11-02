; The front end's second bank (BANK_FRONT2 at A000h around its calls, FRONT at 8000h: frontx.asm
; front2_call; docs/ENDING.md): the game completed (level_load_3 $86DE: front_ending) and the high
; scores (high_score_entry $12082: hs_entry; the table hs_tab0, hs_tab1 in RAM, msx.inc), with
; FRONT's text screens' pieces (fs_step, fs_char, fs_tick, fs_list, ff_bits) and their scripts here
; (ending.inc, tools/msxtext.py); the play-field atlas's upload at power-on and at a level's start
; (field_upload); the scroll engines' set-up (engines_init, engines_jump: from the main loop's code
; through rc2.asm f2_call); and the play-field BOBs' set-up and the V9938 builds' start and sync
; (fb_init, fb_bbinit, fs_sync: performance campaign 2's R3). Every routine it calls puts the A000h
; window back (act_a000).

; At the power-on (frontx.asm ci_hook): the high scores' table from its defaults ($11FF6 in the
; Amiga's code, kept until the power goes: IAN 100000 ... PAUL 7500).
hs_init:
        ld hl,hs_def
        ld de,hs_tab0
        ld bc,3 * HS_SIZE
        ldir
        ld de,hs_tab1
        ld bc,3 * HS_SIZE
        ldir
        ret

; level_load_3 $86DE (load-table entries 3 and 7: after level 3, rc2.asm ml_ev; frontx.asm
; fr_ending, the one way in): the text screen
; $112C5 (WELL DONE, its particle title typed as the briefings', 341 calls, fire from tick 50, which
; types the rest at once: et_go; tools/msxtext.py txt_end), then $11C54's tune, CMP tune 1 as it
; plays it (tune.asm tn_cmp: its 4,916 ticks, the 1801h passes of its loop), or fire pressed once
; released (the PIC9 rule; the original takes fire at once, after its disk loads), with the WELL
; DONE screen kept on (PICF dropped, decision 5: docs/ENDING.md default 2); then the play area black
; and the sound stopped ($11D26, $FE14), and high_score_entry $12082 (hs_entry). From the state
; front_bonus or a level's end leaves: a turbo R on the Z80 (cpu_title), the game's display
; (fb_prep); cpu_title at the end, as front_bonus.
front_ending:
        call cpu_title
        call fb_prep
        ld hl,txt_end
        call et_keep                ; ($86E4: $10762, its $FE14 after the tune here)
        ld hl,tn_cmp
        call mus_call               ; ($11CCA-$11CD8: CMP's init, stop all, tune 1)
        xor a
        ld (tn_hold),a              ; (no stage's pass to wait for: its tick 0 at the next tick)
        ld c,a                      ; (fire not released yet)
fen_lp: push bc
        call fs_tick
        call hud_keep
        call ff_bits
        pop bc
        jr z,fen_r
        dec c
        inc c
        jr nz,fen_x                 ; (pressed after a release: $11CF8)
        jr fen_t
fen_r:  ld c,1
fen_t:  ld hl,(tn_left)
        ld a,h
        or l
        jr nz,fen_lp                ; (the tune's ticks)
fen_x:  call et_black               ; ($11D26, $FE14)
        call hs_entry               ; ($86F0: $12082)
        jp cpu_title

; high_score_entry $12082 (front_over after PIC9: frontx.asm fo_hsc; front_ending): the score $8046's
; low 7 digits against the table's last entry ($120C4); a greater one ($120CC: ties do not enter)
; takes that entry with a blank name ($120D6), typed on the name entry's screen (hs_name: $1215C),
; and moves up past every lower score above it ($1211C's bubble passes: ties keep the older entry
; above); then the table (hs_best: the port's, docs/ENDING.md default 3). The game's display first
; after PIC9 (fc_disp). hs_ran 1 when the entry ran. Builds with a script skip it as they skip the
; title (their drives type no name).
hs_entry:
        xor a
        ld (hs_ran),a
        if INPUT_SCRIPT
        ret
        endif
        ld hl,hs_sc                 ; ($12090-$120B8: the score as digits, the low 7 compared)
        ld a,(AG + (0x8046 ^ 1))
        and 0x0F
        ld (hl),a
        inc hl
        ld a,(AG + (0x8047 ^ 1))
        ld (hl),a
        inc hl
        ld a,(AG + (0x8048 ^ 1))
        ld (hl),a
        inc hl
        ld a,(AG + (0x8049 ^ 1))
        ld (hl),a
        ld de,HS_NAME5 + 9          ; ($120BC: entry 6's score)
        ld hl,hs_sc
        call hs_cmp
        ret nc                      ; ($120D4: not greater)
        ld a,1
        ld (hs_ran),a
        call fc_disp
        ld hl,HS_NAME5              ; ($120D6-$120F0: entry 6 = the score and a blank name)
        ld b,9
hse_sp: ld (hl),0x20
        inc hl
        djnz hse_sp
        ex de,hl
        ld hl,hs_sc
        ld bc,4
        ldir
        call hs_name                ; ($120F4-$120F8: HI1, $1215C)
        ld a,HS_COUNT - 1           ; ($1211C: up past the lower scores)
hse_up: ld (hs_i),a                 ; (the lower entry)
        dec a
        call hs_ptr
        push hl                     ; (the upper)
        ld a,(hs_i)
        call hs_ptr
        pop de
        push de
        push hl
        ld bc,9
        add hl,bc
        ex de,hl
        add hl,bc
        ex de,hl                    ; DE = the upper's score, HL = the lower's
        call hs_cmp                 ; ($1212A: C when the lower's is greater)
        pop hl
        pop de
        jr nc,hs_best               ; (in its place)
        call hs_swap                ; ($1213C: 18 bytes there, the whole entry here)
        ld a,(hs_i)
        dec a
        jr nz,hse_up

; The table after an entry (the port's: the original shows it in the title's attract, which the
; frozen title has not; docs/ENDING.md default 3): the attract's particles 0 and 1 (its write and
; unwrite of $11FF6, 748 calls) as one text screen, TODAYS BEST and the 6 entries typed at once in
; the 8 x 8 font (BEST_COL, BEST_ROW: the original's 16-line pitch, 2 rows), then txt_best's waits;
; fire ends it from tick 50, the play area black at its end.
hs_best:
        call et_open
        ld a,BEST_COL
        ld (fs_col),a
        ld a,BEST_ROW & 0xFF
        ld (fs_row),a
        ld hl,hs_head
        ld b,15
        call hs_text                ; ("   TODAYS BEST ")
        xor a
hsb_lp: push af
        call hs_ptr
        ld a,BEST_COL + 1
        ld (fs_col),a
        ld a,(fs_row)
        add a,2
        ld (fs_row),a
        ld b,9
        call hs_text                ; (the name; HL on to the score)
        ld a,0x20
        call hs_chr
        ld a,(hl)
        call hs_dig                 ; (the score's 7 digits: '[' + digit)
        ld b,3
hsb_d:  inc hl
        ld a,(hl)
        rrca
        rrca
        rrca
        rrca
        call hs_dig
        ld a,(hl)
        call hs_dig
        djnz hsb_d
        pop af
        inc a
        cp HS_COUNT
        jr nz,hsb_lp
        ld hl,txt_best
        call et_go
        jp et_black

; B characters from HL typed at the cursor (fs_char), HL past them.
hs_text:
        ld a,(hl)
        inc hl
        call hs_chr
        djnz hs_text
        ret

; A's low digit typed at the cursor ('[' + digit). Keeps B, HL.
hs_dig: and 0x0F
        add a,0x5B
; A typed at the cursor. Keeps B, HL.
hs_chr: push hl
        push bc
        call fs_char
        pop bc
        pop hl
        ret

; A = an entry -> HL = its first byte (hs_tab0's three, then hs_tab1's). Uses AF, DE.
hs_ptr: ld hl,hs_tab0
        cp 3
        jr c,hsp_n
        ld hl,hs_tab1
        sub 3
hsp_n:  ld de,HS_SIZE
        inc a
hsp_lp: dec a
        ret z
        add hl,de
        jr hsp_lp

; DE = an entry's score, HL = another (4 BCD bytes, the high ones first) -> C when HL's is the
; greater ($120C6's digit by digit: bmi). Uses AF, B, DE, HL.
hs_cmp: ld b,4
hsc_lp: ld a,(de)
        cp (hl)
        ret nz
        inc de
        inc hl
        djnz hsc_lp
        ret

; Two entries at HL and DE swapped. Uses AF, BC, DE, HL.
hs_swap:
        ld b,HS_SIZE
hsw_lp: ld a,(de)
        ld c,(hl)
        ld (hl),a
        ld a,c
        ld (de),a
        inc hl
        inc de
        djnz hsw_lp
        ret

; $1215C: the name entry. Its screen ($115C9 through $10768: et_keep, the text left on), HI1's
; effects on this machine's chips ($12300 starts HI1's tune 1, which that screen's $FE14 stops before
; its first tick: here the ending's descriptor, tune.asm tn_cmp, its tune cut to no tick and its
; effects 3 and 4 HI1's), the name field (entry 6's name, $12066, drawn by $12218) with the mark under
; its second position ($1217E), then a key at a time (hs_key: $1225C): Return ends, Backspace takes
; the last character back (the mark there), any other while the name is not full goes at the next
; position, the mark after it but after the last. Return: the marks cleared, the play area black
; ($121D2: the palette at once; $BCA8 clears the buffers), effect 4 ($121FA), heard out (its 14
; ticks) before the next screen's stop.
hs_name:
        ld hl,txt_hisc
        call et_keep                ; ($1215C: $10768)
        ld hl,tn_cmp
        call mus_call
        ld hl,1
        ld (tn_left),hl             ; (no tick of its tune)
        xor a
        ld (tn_hold),a
        ld (hs_i),a                 ; ($12164)
        inc a
        ld (hs_lat),a               ; ($12082: st.b $15EF, a key held from before waits for its release)
        ld a,HS_MARK
        ld (HS_NAME5 + 1),a         ; ($1217E)
hsn_d:  call hs_draw                ; ($12184, $121C4)
hsn_k:  call hs_key                 ; ($1218C) A = the character
        ld hl,hs_i
        ld c,(hl)                   ; C = the next position ($12192)
        ld b,0
        cp 0x0D
        jr z,hsn_r                  ; ($1219A: Return)
        cp 0x7F
        jr z,hsn_b                  ; ($121A0: Backspace)
        ld e,a
        ld a,c
        cp 9
        jr z,hsn_k                  ; ($121A8: the name full)
        inc (hl)                    ; ($121C0)
        ld hl,HS_NAME5
        add hl,bc
        ld (hl),e                   ; ($121B0)
        cp 8
        jr z,hsn_d                  ; ($121B4: after the last, no mark)
        inc hl
        ld (hl),HS_MARK             ; ($121BA)
        jr hsn_d
hsn_b:  ld a,c                      ; ($12240)
        or a
        jr z,hsn_d
        dec (hl)                    ; ($12244)
        ld hl,HS_NAME5 - 1
        add hl,bc
        ld (hl),HS_MARK             ; ($1224E: the mark on the character taken back)
        cp 9
        jr z,hsn_d                  ; (after a full name: the place after it is the table's space)
        inc hl
        ld (hl),0x20                ; ($12248)
        jr hsn_d
hsn_r:  ld hl,HS_NAME5              ; ($12204-$12212: the marks cleared)
        add hl,bc
        ld a,c
        cp 9
        jr z,hsn_e
        ld (hl),0x20
        cp 8
        jr z,hsn_e
        inc hl
        ld (hl),0x20
hsn_e:  ld hl,pf_pal
        ld bc,32
        xor a
        call fill                   ; ($121D6: black)
        ld a,4
        call snd_ffx                ; ($121FA)
        ld b,16
hsn_w:  push bc
        call fs_tick
        call hud_keep
        pop bc
        djnz hsn_w
        ret

; $12218: the name's 9 characters at (HS_X, HS_Y), 8 pixels apart ($118CE at column 16 + i, row 10 of
; the front buffer, no text origin: bitplane x 128 + 8i, lines 80-87).
hs_draw:
        ld hl,HS_NAME5
        ld c,HS_X
hsd_lp: push bc
        push hl
        ld a,(hl)
        call et_gl
        ld a,HS_Y
        call et_cell
        pop hl
        pop bc
        inc hl
        ld a,c
        add a,4
        ld c,a
        cp HS_X + 4 * 9
        jr nz,hsd_lp
        ret

; $1225C: the next key taken, one a press (after one, every key let go first: $15EF), with effect 3
; ($1228A) -> A = its character ($12296's: 'A'-'Z', '[' + digit for the main rows' and the keypad's
; digits, space, 7Fh Backspace, 0Dh Return). A tick at a time, with the HUD's work as in the text
; screens.
hs_key: call fs_tick
        call hud_keep
        call kb_char
        ld hl,hs_lat
        or a
        jr nz,hsk_k
        ld (hl),a                   ; ($12258: no key, the latch cleared)
        jr hs_key
hsk_k:  bit 0,(hl)
        jr nz,hs_key                ; ($12268: still held)
        ld (hl),1                   ; ($1226A)
        push af
        ld a,3
        call snd_ffx
        pop af
        ret

; The first of the name entry's keys pressed ($122C8's raw codes: here the MSX keyboard's matrix,
; kb_tab) -> A = its character, 0: none. Uses AF, BC, DE, HL.
kb_char:
        ld hl,kb_tab
kbc_lp: ld a,(hl)
        cp 0xFF
        jr z,kbc_no
        inc hl
        ld d,(hl)                   ; (the row's keys taken)
        inc hl
        ld e,(hl)                   ; (the character of its bit 0)
        inc hl
        push hl
        call kb_row                 ; C = the row's keys pressed
        pop hl
        ld a,c
        and d
        jr z,kbc_lp
kbc_b:  rrca
        jr c,kbc_c
        inc e
        jr kbc_b
kbc_c:  ld a,e
        ret
kbc_no: xor a
        ret
; per row (the MSX matrix: the MSX2 Technical Handbook, figure 5.17B): the row, its keys, the
; character of its bit 0 (the character = it + the key's bit)
kb_tab: db 0, 0xFF, 0x5B            ; 0-7: '[' + digit ($12296's)
        db 1, 0x03, 0x5B + 8        ; 8, 9
        db 2, 0xC0, 0x41 - 6        ; A, B
        db 3, 0xFF, 0x43            ; C-J
        db 4, 0xFF, 0x4B            ; K-R
        db 5, 0xFF, 0x53            ; S-Z
        db 7, 0x20, 0x7F - 5        ; BS: 7Fh
        db 7, 0x80, 0x0D - 7        ; RETURN: 0Dh
        db 8, 0x01, 0x20            ; SPACE
        db 9, 0xF8, 0x5B - 3        ; the keypad's 0-4
        db 10, 0x1F, 0x5B + 5       ;   5-9
        db 0xFF

; ($18014) A = an effect of the ending's sound (HI1's 3 or 4) to msx/tune.asm from its next tick:
; puzl.asm snd_bfx's 12 bytes (of two requests before a tick the higher; the ticks run again).
snd_ffx:
        ld hl,tn_req
        cp (hl)
        ret c
        ld (hl),a
        ld a,2
        ld (fx_act),a
        ret

; The game's display again after a picture (PIC9: front_mode set), as front_cont's set-up: a turbo R
; on the Z80 (cpu_title), front_done's SCREEN 5, fb_prep, which measures the split and turns the
; display on on a turbo R, and display_on on the other machines; nothing when it is on (front_mode
; clear: at the ending).
fc_disp:
        ld a,(front_mode)
        or a
        ret z
        call cpu_title
        call front_done
        call fb_prep
        ld a,(cpu_tr)
        or a
        ret nz
        jp display_on

; ----- front.asm fe_text's pieces for these screens (its bytes unchanged there) -----

; fe_text's screen and loop, HL = its script, the text left on at its end ($10768 without $10762's
; $FE14: the name entry's screen, the ending's while its tune plays); et_open sets the screen up to
; its text (TAG's line drawn), et_go runs a script from there; et_black is fe_text's end.
et_keep:
        push hl
        call et_open
        pop hl
et_go:  push hl
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
etg_lp: call fs_tick
        call hud_keep               ; ($10266: the panel's messages; its digits)
        call fs_step
        ld hl,(fs_n)
        inc hl
        ld (fs_n),hl
        ld de,50
        or a
        sbc hl,de
        jr c,etg_lp                 ; (not before tick 50)
        ld a,(fs_done)
        or a
        ret nz
        call ff_bits
        jr z,etg_lp
; Fire before the script's end: the rest of its characters typed at once, its waits skipped, so that
; a screen kept on after it is whole (WELL DONE during the tune, the name entry's: docs/ENDING.md
; default 10; the table screen's script is its waits alone, its screen black at once after it).
etg_all:
        ld hl,0
        ld (fs_wait),hl
        call fs_step
        ld a,(fs_done)
        or a
        jr z,etg_all
        ret
et_open:
        call snd_stop               ; ($10768: $FE14)
        call fb_init                ; (no play-field BOB holds a list now)
        ld hl,pf_pal
        ld bc,32
        xor a
        call fill                   ; black from the next VBLANK
        call fs_vbl
        ld hl,fs_clear
        call vdp_cmd                ; the play area of page 0 black
        call fs_list                ; page 0 unscrolled, no sprites
eto_on: call fs_vbl
        ld a,(app_seq)
        ld b,a
        ld a,(pub_seq)
        cp b
        jr nz,eto_on                ; (until that list is on screen)
        call vdp_wait
        if TAG
        ld a,FE_TAG_COL
        ld (fs_col),a
        ld a,10
        ld (fs_row),a
        ld hl,fe_tag
eto_tg: ld a,(hl)
        or a
        ret z
        push hl
        call fs_char
        pop hl
        inc hl
        jr eto_tg
        else
        ret
        endif
et_black:
        ld hl,pf_pal
        ld bc,32
        xor a
        call fill
        jp snd_stop                 ; ($FE14)

; fs_char's pieces for the name ($118CE: a cell anywhere): A = a character -> DE = its glyph's 8
; lines of 4 bytes ($118D6: ' ' 41, from '@' code - 'A', else code - 16h); et_cell: DE = a glyph, C =
; its cell's byte in the line (x / 2), A = its first line: written there.
et_gl:  ld b,41
        cp 0x20
        jr z,etg_g
        sub 0x16
        ld b,a
        cp 0x40 - 0x16
        jr c,etg_g
        sub 0x41 - 0x16
        ld b,a
etg_g:  ld l,b
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,txt_glyphs
        add hl,de
        ex de,hl
        ret
et_cell:
        ld b,8
etc_ln: push bc
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
        djnz etc_ln
        jp vram_done

        include "ending.inc"        ; the ending's and the high scores' texts (tools/msxtext.py)

; The level's atlas (bank lv_fimg on: tools/msxsprites.py field_frames, tools/mkrom.py atlas_banks)
; into VRAM, above the caches: at power-on, after the tiles (cold.asm vdp_setup), and at each
; level's start (cold.asm lvs_vram), both through front2_call (FRONT at 8000h, this bank at A000h;
; in field.asm's bank until performance campaign 2's field-2 needed its room: this runs once a
; level). Frame by frame, as the ROM keeps no empty part of it: per bank its frames (bit 7: the
; next bank holds more of them), then [atlas line, x / 2, bytes a line, lines, mirrored, the
; pixels' offset (2) in the bank] each; a mirrored frame is another's pixels read from the right,
; each byte's two pixels swapped. Keeps the 8000h window's bank.
field_upload:
        ld a,(act_8000)
        push af
        ld a,(lv_fimg)
fu_bnk: push af                     ; (a bank of the atlas)
        call bank_8000
        ld ix,0x8001
        ld a,(0x8000)               ; frames
        and 0x7F
fu_frm: push af
        ld l,(ix+5)
        ld h,(ix+6)
        ld de,0x8000
        add hl,de                   ; HL = the frame's pixels
        ld b,(ix+3)
        ld a,(ix+0)
        add a,FIELD_Y0
        ld d,a                      ; D = its first line in page 3
fu_lin: push bc
        push hl
        ld a,d                      ; the line in VRAM: 18000h + line * 128 + x / 2
        srl a
        or 0x80
        ld h,a
        ld a,d
        rrca
        and 0x80
        add a,(ix+1)
        ld l,a
        ld e,1
        push de
        call vram_write
        pop de
        pop hl
        push hl
        ld b,(ix+2)                 ; bytes a line
        ld c,VDP_DATA
        ld a,(ix+4)
        or a
        jr nz,fu_mir
        otir
        jr fu_nl
fu_mir: ld a,l                      ; mirrored: from the line's end, the two pixels swapped
        add a,b
        ld l,a
        jr nc,fu_ml
        inc h
fu_ml:  dec hl
        ld a,(hl)
        rrca
        rrca
        rrca
        rrca
        out (VDP_DATA),a
        djnz fu_ml
fu_nl:  pop hl
        ld c,(ix+2)
        ld b,0
        add hl,bc                   ; the next line's pixels
        inc d
        pop bc
        djnz fu_lin
        ld de,7
        add ix,de
        pop af
        dec a
        jr nz,fu_frm
        pop af
        inc a                       ; (the next bank)
        ld hl,0x8000
        bit 7,(hl)                  ; (another bank of the atlas follows)
        jr nz,fu_bnk
        call vram_done
        pop af
        jp bank_8000

; ----- the scroll engines' set-up (performance campaign 2's R2, docs/PERF2_PLAN.md 5.2: from
; field.asm's bank, whose room went to the field engine; through rc2.asm f2_call: this bank at
; A000h, 8000h as the caller left it). It runs once at a level's start (rc2.asm lv_go), at a
; restart or a continue (level_restart) and at the cracked wall's jump (engines_jump), never in a
; frame's work; field.asm's vat_init through field_call, fb_init here (R3, below). -----

; The scroll engine of the VDP found (vdp_id; FORCE_V9938) on the camera's view, the split, the
; sprite engine.
engines_init:
        ld hl,vat_init
        call field_call             ; (level 2's vats: none drawn yet)
        call fb_init                ; (first: the set-up's tiles ask it, tiles.asm fb_mark)
        ld a,(vdp_id)
        cp 2
        jr nz,init38
        if FORCE_V9938
        jr init38
        endif
        xor a
        ld (fb_eng),a               ; (field.asm: the ring)
        ld a,2
        call split_init             ; A = 2: V9958 engine
        call scroll_init            ; V9958 engine
        ld hl,scroll_publish
        ld (pub_vec),hl
        ld hl,scroll_update
        ld de,scroll_work
        jr init_go
init38: ld a,1
        ld (fb_eng),a               ; (field.asm: two pages)
        xor a
        call split_init
        call s38_init               ; V9938 engine
        ld hl,s38_publish
        ld (pub_vec),hl
        ld hl,s38_update
        ld de,s38_work
init_go:
        ld (update_vec),hl
        ld (idle_vec),de
        jp sprites_init

; After the cracked wall's relocation (mapobj.asm act_10, obj_relocate $9FC4: RoboCop and the
; camera somewhere else in the map, the palette fading in from black): the view drawn around the
; new camera at once, as at the level's start, while the display, the HUD and the interrupts go
; on (the scroll engines would walk there a column at a time, the ticks held meanwhile). The play
; field goes black first (on screen from the next VBLANK: the old view is drawn over); the
; play-field BOBs and the cells waiting to be redrawn are forgotten (the whole view comes from
; the map); the split and the sprites go on as they are.
engines_jump:
        xor a
        call pal_fade               ; ($16CD = 0: pl_fade brings it back)
        ld a,(tick)
        ld b,a
ej_vbl: ld a,(tick)
        cp b
        jr z,ej_vbl
        call pl_view                ; v_x, v_y (cam_x, cam_y) on the new camera
        di                          ; (the interrupts start the play field's copies)
        call fb_init
        ei
        ld hl,vat_init
        call field_call             ; (level 2's vats: the whole view drawn again)
        ld hl,rd_bits
        ld bc,40
        xor a
        call fill
        xor a
        ld (rd_head),a
        ld (rd_tail),a
        ld (rd_phase),a
        ld (cam_held),a
        ld a,(fb_eng)
        or a
        jp z,scroll_init            ; (V9958 engine)
        jp s38_init


; Fills the initial ring and clears the queues.
scroll_init:
        ld a,R25_PLAY
        ld b,25
        call wrreg                  ; R#25 = SP2 (512 px ring) + MSK (hides the left 8 px)
        ld hl,0                     ; (the camera: set by the game, pl_init)
        ld (frame),hl
        ld (late),hl
        ld (stall),hl
        ld (vstall),hl
        ld (tiles_drawn),hl
        ld a,0xFF
        ld (q_col),a
        ld (q_row),a
        call cam_cells              ; B = cx, C = cy
        ld a,b
        ld (prev_cx),a
        ld a,c
        ld (prev_cy),a
        ; rows cy-1 .. cy+12, columns cx-1 .. cx+17
        ld a,c
        dec a
        ld d,a                      ; current row
si_row: ld a,b
        dec a
        ld e,a
si_col: push bc
        push de
        ld a,d
        call draw_tile
        pop de
        pop bc
        inc e
        ld a,b
        add a,18
        cp e
        jr nz,si_col
        inc d
        ld a,c
        add a,VIEW_ROWS-1
        cp d
        jr nz,si_row
        jp scroll_publish


        if CAM38
; ----- CAM38 (tools/mkrom.py): the MSX2's camera, for the user's choice (scroll9938.asm, player.asm) -----
; The V9938 engine shows the view the game wants (v_x) but for its page's edge: while the next page is built the
; view waits there, and the flip shows it 16 px further at once (RoboCop walks on in the picture, then the view
; throws him back). 1 (lock): the view shown catches up at most CAM_K px a picture faster than the game's view
; (s38_glide), and the ticks wait while it lags CAM_LK px or more (cam_lock): RoboCop stays where the game's
; camera puts him, the scene waits for the page instead. 2 (pace): 1, and while the next page is not built the
; view crosses the page shown no faster than the last page took (s38_pace). The V9958 as always.
CAM_K:      equ 4
CAM_LK:     equ 4

; The view shown in x (cam_x = v_x, s38_update) moves at most the game's view's step since the last picture +
; CAM_K px from the last picture's (sp_cam_x); a jump of the game's view (64 px or more from the view shown: a
; level's start, a teleport) is shown at once. The page's own hold comes after it, as always.
s38_glide:
        ld hl,(v_x)
        ld de,(s38_lv)
        ld (s38_lv),hl
        or a
        sbc hl,de
        call sg_abs                 ; HL = the game's view's step
        ld a,h
        or a
        ret nz                      ; (a jump)
        ld a,l
        add a,CAM_K
        ret c
        ld c,a                      ; C = the most the view shown moves now
        ld hl,(v_x)
        ld de,(sp_cam_x)
        or a
        sbc hl,de                   ; HL = v_x - the view shown last
        ld b,0                      ; (B = 0: v_x on its right)
        jr nc,sg_r
        inc b
        call sg_neg
sg_r:   ld a,h
        or a
        ret nz                      ; (a jump)
        ld a,l
        cp 64
        ret nc                      ; (a jump)
        cp c
        ret c                       ; (within the step: v_x)
        ld l,c
        ld h,0
        dec b
        jr nz,sg_set
        call sg_neg
sg_set: add hl,de                   ; the view shown last + or - C
        ld (cam_x),hl
        ret
sg_abs: bit 7,h
        ret z
sg_neg: xor a                       ; HL = -HL
        sub l
        ld l,a
        sbc a,a
        sub h
        ld h,a
        ret

; The cadence (player.asm): E = 0 (D = 0) while the V9938 engine's view shown lags CAM_LK px or more behind the
; game's in x: no tick (the view catches up first, RoboCop waits with the scene); else E = 1. Keeps BC.
cam_lock:
        ld de,1
        ld a,(fb_eng)
        or a
        ret z                       ; (the V9958's ring: as always)
        ld hl,(v_x)
        ld de,(cam_x)
        or a
        sbc hl,de
        call sg_abs
        ld de,CAM_LK
        or a
        sbc hl,de
        ld de,0
        ret nc
        inc e
        ret
        endif

        if CAM38 == 2
; While the next page on the side the view moves to (dir_x) is not built, the view shown crosses the page shown
; no faster than the last page was built (s38_tb: the VBLANKs from flip to flip when the camera waited for it,
; held at the page's edge or paced; 0: the build kept up, no pace): at most f = min(15, 16 x the VBLANKs since
; the flip / s38_tb) px from the edge it came in by, never back (the view shown last, when it was beyond that
; already). Keeps BC.
s38_pace:
        ld a,(cam_held)
        or a
        jr z,cpc_p
        ld (s38_lim),a              ; (held at the page's edge: the camera waited for it)
cpc_p:  ld hl,s38_pc0
        ld a,(s38_vis_c0)
        cp (hl)
        jr z,cpc_t
        ld (hl),a                   ; a flip: s38_tb = the VBLANKs since the last one when the camera
        ld hl,s38_tflip             ; waited for this page (held or paced), else 0 (the build kept up)
        ld a,(tick)
        sub (hl)
        push af
        ld a,(tick)
        ld (hl),a
        pop af
        ld hl,s38_lim
        bit 0,(hl)
        ld (hl),0
        jr nz,cpc_tb
        xor a
cpc_tb: ld (s38_tb),a
cpc_t:  ld hl,s38_tflip
        ld a,(tick)
        sub (hl)
        cp 200
        jr c,cpc_a
        ld a,(tick)                 ; (a long wait: kept at 200 VBLANKs)
        sub 200
        ld (hl),a
        ld a,200
cpc_a:  ld e,a                      ; E = the VBLANKs since the flip
        ld a,(s38_tb)
        or a
        ret z                       ; (no pace)
        ld d,a
        ld a,(s38_flip_wait)
        or a
        jr nz,cpc_go                ; (the flip not on screen yet: nothing built)
        ld a,(s38_vis_c0)
        inc a
        ld hl,dir_x
        bit 0,(hl)
        jr z,cpc_c
        sub 2
cpc_c:  ld hl,s38_back_c0
        cp (hl)
        jr nz,cpc_go                ; (built for the other side, or none)
        ld a,(s38_phase)
        or a
        jr z,cpc_go
        ld a,(s38_i)
        cp VIEW_ROWS
        ret z                       ; (built: free)
cpc_go: ld l,e
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl                   ; HL = 16 x the VBLANKs since the flip
        ld e,d
        ld d,0                      ; DE = the last page's VBLANKs
        ld a,0xFF
cpc_d:  inc a
        cp 15
        jr nc,cpc_f
        or a
        sbc hl,de
        jr nc,cpc_d
cpc_f:  ld e,a                      ; E = f
        ld a,(s38_vis_c0)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl                   ; HL = the page's first x
        ld a,(dir_x)
        or a
        jr nz,cpc_l
        ld d,0
        add hl,de
        ex de,hl                    ; DE = the most (moving right)
        ld hl,(cam_x)
        or a
        sbc hl,de
        ret c
        ret z
        ld hl,(sp_cam_x)
        or a
        sbc hl,de
        jr c,cpc_set
        jr z,cpc_set                ; (the view shown last within: the most)
        ld de,(sp_cam_x)
        ld hl,(cam_x)
        or a
        sbc hl,de
        ret c
        jr cpc_set                  ; (the view shown last: never back)
cpc_l:  ld a,15
        sub e
        ld e,a
        ld d,0
        add hl,de
        ex de,hl                    ; DE = the least (moving left)
        ld hl,(cam_x)
        or a
        sbc hl,de
        ret nc
        ld hl,(sp_cam_x)
        or a
        sbc hl,de
        jr nc,cpc_set               ; (the view shown last within: the least)
        ld de,(sp_cam_x)
        ld hl,(cam_x)
        or a
        sbc hl,de
        ret nc
cpc_set:
        ld (cam_x),de
        ld a,1
        ld (s38_lim),a
        ret
        endif

; (scroll9938.asm)
s38_init:
        xor a
        ld b,25
        call wrreg                  ; no V9958 scroll (FORCE_V9938 on an MSX2+)
        ld hl,0                     ; (the camera: set by the game, pl_init)
        ld (frame),hl
        ld (late),hl
        ld (stall),hl
        ld (vstall),hl
        ld (tiles_drawn),hl
        xor a
        ld (s38_vis_page),a
        ld (s38_flip_wait),a
        if CAM38
        ld (s38_tb),a               ; (CAM38: no pace yet, the game's view's last step from here)
        ld (s38_lim),a
        ld hl,(v_x)
        ld (s38_lv),hl
        endif
        ld a,0xFF
        ld (s38_back_c0),a
        ld (s38_rq),a
        call cam_cells
        ld a,b
        ld (s38_vis_c0),a
        ld a,c
        ld (prev_cy),a
        dec a
        ld (s38_tmp_row),a
s38i_row:
        ld a,(s38_vis_c0)
        ld e,a
s38i_col:
        push de
        ld a,(s38_vis_c0)
        ld c,a
        ld d,0
        ld a,(s38_tmp_row)
        call tile_to_page
        pop de
        inc e
        ld a,(s38_vis_c0)
        add a,16
        cp e
        jr nz,s38i_col
        ld a,(s38_tmp_row)
        inc a
        ld (s38_tmp_row),a
        ld b,a
        ld a,(prev_cy)
        add a,VIEW_ROWS-1
        cp b
        jr nz,s38i_row
        jp s38_publish


; ----- the play-field BOBs' code that runs once a level, or once a V9938 build (performance campaign
; 2's R3, docs/PERF2_PLAN.md 5.2: from field.asm's bank, whose room went to the field engine's work).
; Reached through rc2.asm f2_call (BANK_FRONT2 at A000h around it, act_a000 put back); it reaches
; field.asm's routines through field_call (their arguments in BC, DE and RAM: field_call takes A and
; HL), and keeps its own copies of the small ones that take them (fs_dnp, fs_lsz, fs_bxs). -----

; At a level's start (engines_init, engines_jump), and before the front end's text screens (front.asm
; through f2_call, et_open): the pages hold no BOB, no cache holds anything, the dynamic slot and the
; frame cache no frame, nothing to do; the level's play-field frames' tables (field.asm fb_fldcp:
; lv_fld's fld_l1, fld_l2, fld_l3 are in BANK_FIELD).
fb_init:
        ld hl,fb_fldcp
        call field_call
        ld hl,fc_res
        ld b,FC_MAX
        ld a,0xFF
fbi_fc: ld (hl),a                   ; (no place of the frame cache holds a frame)
        inc hl
        djnz fbi_fc
        xor a
        ld (dyn_res),a
        ld (dyn_res + 1),a
        ld (fb_dsn),a
        ld (fb_wn),a
        ld (fb_dn0),a
        ld (fb_dn1),a
        ld (fb_qn),a
        ld (fb_bbn),a
        ld (fb_ph),a
        ld (fb_busy),a
        ld (fb_n),a
        ld (fb_cq),a
        ld (fb_lost),a
        ld (fb_hold),a
        ld (fb_vok),a
        ld (fb_qlk),a
        ld (fb_stg),a
        ld (fb_rdy),a
        ld (fb_shc),a
        ld (fb_lkf0),a              ; (nothing known of the pages' pixels; no look-only diff)
        ld (fb_lkf1),a
        ld (fb_lkq),a
        ld a,FB_SX
        ld (fb_sbx),a
        ld a,0xFF
        ld (fb_bsync),a
        ld (fb_bsq),a
        ld (fb_vlast),a
        ld hl,fb_cache
        ld de,FB_CSZ - 1
        ld b,FB_GMAX
fi_c:   ld (hl),a                   ; (owner FFFFh: free)
        inc hl
        ld (hl),a
        add hl,de
        djnz fi_c
        ret

; (scroll9938.asm s38_target through f2_call) A V9938 build begins: the displayed page's work under
; way (the item being composed and those waiting) is where its copy may bring something its list does
; not show; the rest the copy brings as it is, the BOBs with it, in their place (they were composed
; again in full until 2026-10-21: one build's items held the page shown's for ~12 pictures). Called
; when the target is set, before the build draws anything (field.asm fb_bbcell adds its cells from
; then on). Since performance campaign 2's V9938-SYNC, for a target that changed without a flip (the
; view turned back) the page being built's work for the target before is dropped: a copy of its sync
; prepared and not started (it would write this page at that target's place, after this build's tiles
; maybe), its items queued (their list and place are that target's); the item being composed, of
; either page, goes into fb_bb (its copy may come after this build's copy).
fb_bbinit:
        if VAT_ANIM
        ld hl,vat_bbinit
        call field_call             ; (level 2's vats: the looks its copy brings)
        endif
        ld a,0xFF
        ld (fb_bsq),a               ; (its sync not begun: fs_sync)
        di
        ld a,(fb_ph)
        or a
        jr nz,fbi_k
        ld a,(fb_rdy)               ; (fb_ph 0, fb_rdy 1: only the sync's copy, fs_copy)
        dec a
        jr nz,fbi_k
        ld (fb_rdy),a
fbi_k:  ei
        push ix
        ld a,1
        ld (fb_qlk),a               ; (meanwhile the VBLANK holds the picture: isr.asm fb_pend)
        ld a,(s38_vis_page)
        xor 1
        ld c,a
        ld hl,fqp_lp                ; (field.asm fq_purge, the page in C)
        call field_call
        xor a
        ld (fb_qlk),a
        pop ix
        ld (fb_bbn),a
        ld a,(fb_ph)
        or a
        jr z,fbi_q0
        ld hl,fb_cur + 3
        call fbi_add
fbi_q0: ld a,(fb_qn)
        or a
        ret z
        ld b,a
        ld hl,fb_q
fbi_ql: push bc
        push hl
        call fbi_one
        pop hl
        ld de,FB_QSZ
        add hl,de
        pop bc
        djnz fbi_ql
        ret

; HL = an item: its rectangle into fb_bb when it is the displayed page's (fbi_add: HL = a rectangle).
fbi_one:
        ld a,(s38_vis_page)
        cp (hl)
        ret nz
        inc hl
        inc hl
        inc hl
fbi_add:
        ld de,fb_r
        ld bc,8
        ldir
        ld hl,fb_bbadd
        jp field_call

; (field.asm fb_sync through f2_call, from fb_step and fn_take: the V9938, the build's copy done, the page
; being built not synced; no item being composed, none of the page shown's published ones waiting) The
; page being built's sync, a step a call (performance campaign 2's V9938-SYNC, docs/PERF2_PLAN.md item 7).
; It begins with the page's list: the page shown's (fb_want: fb_frame gives the page shown fb_want at
; every picture; fs_begin). Then each rectangle of fb_bb (where the copy may have brought something else
; than the BOBs wanted, the build's tiles that meet them among it), in the kept rows and the page's
; columns (fs_rect): its part in the new column, which the page shown does not hold, composed (an item:
; the tiles, then the BOBs) when a BOB of the list may meet it (its box: else the tiles are all there);
; the rest copied from the page shown with one HMMM (fs_copy: the page copy's 16-px shift) where that page
; holds its list's composition: composed when a change of the page shown met it since the sync began
; (fs_dirty, fb_sdm: the page shown may hold the change by now); left for later while an item of the page
; shown waiting in the queue meets it (fs_qmeet: its cells waiting for the BOBs among them; queued before
; the change marks, it brings that page to the list there). Then the marker (fs_mark: fb_bsync once taken,
; the flip may come). VAT_ANIM=1 builds compose every rectangle, as before (their vats' columns are not
; checked here). -> L 0 when it queued items (taken now), 1 when it did nothing (a rectangle waits for the
; page shown, or no room for its items in the queue: an item is taken first), 2 when a copy of its is
; prepared (fb_rdy 1: fb_work starts it, or the interrupts, ifg_rdy).
fs_sync:
        ld l,2
        ld a,(fb_rdy)
        or a
        ret nz                      ; (its copy, not started yet)
        dec l
        ld a,(s38_back_c0)
        cp 0xFF
        ret z                       ; (no page being built)
        ld hl,fb_bsq
        cp (hl)
        call nz,fs_begin            ; (the build's sync begins)
        ld l,1
        ld a,(fb_sbi)
        inc a
        ret z                       ; (FFh: the marker queued, taken in its turn)
        ld a,(fb_qn)                ; (room for a rectangle's two items)
        cp FB_QMAX - 1
        ret nc
        xor a
        ld (fb_cmd + 9),a           ; (none waiting for the page shown yet)
        ld a,(fb_bbn)
        or a
        jr z,fs_mark
        ld b,a                      ; B = rectangles, C = rectangle k's bit, IX = rectangle k
        ld c,1
        ld ix,fb_bb
fyn_lp: ld a,(fb_sbi)
        and c
        jr nz,fyn_nx                ; (done)
        push bc
        if VAT_ANIM
        push ix
        pop hl
        ld de,fb_r
        ld bc,8
        ldir
        call fs_comp                ; (composed whole: done)
        pop bc
        call syn_done
        ld l,0
        ret
        else
        call fs_rect                ; -> L 0 queued, 1 nothing of it (done), 2 a copy, 3 it waits
        pop bc
        ld a,l
        cp 3
        jr z,fyn_w
        dec a
        ret nz                      ; (L 0, 2: the caller takes the items or starts the copy)
        endif
fyn_nx: ld de,8
        add ix,de
        sla c
        djnz fyn_lp
        ld a,(fb_cmd + 9)
        or a
        ld l,1
        ret nz                      ; (a rectangle waits for the page shown's work: later)
        jr fs_mark
fyn_w:  ld (fb_cmd + 9),a
        jr fyn_nx

; C = rectangle k's bit: it is done (fb_sbi).
syn_done:
        ld a,(fb_sbi)
        or c
        ld (fb_sbi),a
        ret

; The build's sync begins (A = its target): the page being built's list and box are fb_want's (the page
; shown's), no rectangle of fb_bb done, none met by a change yet.
fs_begin:
        ld (fb_bsq),a
        xor a
        ld (fb_sbi),a
        ld (fb_sdm),a
        ld a,(s38_vis_page)
        xor 1
        push af
        call fs_dnp
        ex de,hl
        ld hl,fb_wn
        call fs_lsz
        ldir
        pop af
        jp fs_bxs

; Every rectangle done: the marker (its build target), after the sync's items; fn_take sets fb_bsync
; when it takes it (L 0), or later when the queue has no room (L 1).
fs_mark:
        ld a,(fb_qn)
        cp FB_QMAX
        ret nc
        ld a,0xFF
        ld (fb_sbi),a
        ld hl,0xFFFF
        ld (fb_own),hl
        ld a,(s38_back_c0)
        ld (fb_r),a
        ld a,(s38_vis_page)
        xor 1
        or 0x80
        ld c,a
        ld hl,fq_new
        call field_call
        ld l,0
        ret

; fb_r composed on the page being built: an item of no owner (its background from the tiles, then the
; BOBs of its list). Keeps IX.
fs_comp:
        ld hl,0xFFFF
        ld (fb_own),hl
        ld a,(s38_vis_page)
        xor 1
        ld c,a
        ld hl,fb_queuec
        jp field_call

; IX = a rectangle of fb_bb not done, C = its bit: its part in the kept rows and the page being built's
; columns, even x edges (fb_r; kept in fb_cmd's first bytes meanwhile, nothing of the field engine's
; prepared: fs_sync's fb_rdy 0): the part in the new column composed when the list's box meets it, the
; rectangle then the rest alone (so that it is not composed again); the rest copied (fs_copy) or composed,
; or left for later -> L 0 when it queued, 1 when nothing of it is in the page (done), 2 when a copy is
; prepared, 3 when it waits for the page shown's work there.
fs_rect:
        push bc
        push ix
        pop hl
        ld de,fb_r
        ld bc,8
        ldir
        ld a,(prev_cy)              ; the kept rows: [(prev_cy - 1) * 16, (prev_cy + 13) * 16)
        call fs_c16
        push hl
        ld de,16 * VIEW_ROWS - 16
        add hl,de
        ex de,hl
        pop hl
        ld bc,-16
        add hl,bc
        call fs_cly
        jp nc,fyr_no
        ld a,(s38_back_c0)          ; the page's columns: [back_c0 * 16, back_c0 * 16 + 256)
        call fs_c16
        ld d,h
        ld e,l
        inc d
        call fs_clx
        jp nc,fyr_no
        ld a,(fb_r)                 ; even x edges (two pixels a byte)
        and 0xFE
        ld (fb_r),a
        ld hl,(fb_r + 4)
        inc hl
        res 0,l
        ld (fb_r + 4),hl
        ld hl,fb_r
        ld de,fb_cmd
        ld bc,8
        ldir
        xor a
        ld (fb_cmd + 8),a           ; (nothing queued yet)
        call fs_newc                ; the new column: [bx + 240, bx + 256) built for the right, else
        call fs_clx                 ; [bx, bx + 16)
        jr nc,fyr_ov
        call fs_lbox                ; (no BOB of the list there: its tiles, drawn by the build, are all)
        jr nc,fyr_ov
        call fs_comp
        ld a,1
        ld (fb_cmd + 8),a
fyr_ov: ld hl,fb_cmd
        ld de,fb_r
        ld bc,8
        ldir
        call fs_ovx                 ; the rest: [bx, bx + 240) built for the right, else [bx + 16, bx + 256)
        call fs_clx
        jr nc,fyr_dn
        ld hl,(fb_r)                ; (the rectangle: the rest's columns alone from now on, its new column's
        ld (ix+0),l                 ;  part done)
        ld (ix+1),h
        ld hl,(fb_r + 4)
        ld (ix+4),l
        ld (ix+5),h
        pop bc
        push bc
        ld a,(fb_sdm)
        and c
        jr nz,fyr_cp                ; (a change of the page shown met it since the sync began)
        call fs_qmeet
        jr c,fyr_w                  ; (the page shown's queued work there: later)
        pop bc
        jp fs_copy
fyr_cp: call fs_comp
        ld a,1
        ld (fb_cmd + 8),a
fyr_dn: pop bc
        call syn_done
fyr_rt: ld l,0
        ld a,(fb_cmd + 8)
        or a
        ret nz
        inc l
        ret
fyr_w:  pop bc
        ld a,(fb_cmd + 8)
        or a
        ld l,0
        ret nz                      ; (its new column's part queued: taken first)
        ld l,3
        ret
fyr_no: pop bc
        call syn_done
        ld l,1
        ret

; -> HL, DE = the columns both pages hold, as map x: [bx, bx + 240) on a page built for the right, else
; [bx + 16, bx + 256) (bx = back_c0 * 16).
fs_ovx: ld a,(s38_back_c0)
        call fs_c16
        ld a,(s38_back_dir)
        or a
        jr z,fyo_r
        ld de,16
        add hl,de
fyo_r:  ld d,h
        ld e,l
        push hl
        ld hl,240
        add hl,de
        ex de,hl
        pop hl
        ret

; -> C when a BOB of the page being built's list meets fb_r (each entry's rectangle: field.asm fb_rect
; through field_call; fb_tr holds fb_r meanwhile). Keeps IX.
fs_lbox:
        ld a,(s38_vis_page)
        xor 1
        call fs_dnp
        ld a,(hl)
        or a
        ret z                       ; (none: NC)
        push ix
        inc hl
        push hl
        pop ix                      ; IX = its first entry, B = its entries
        ld b,a
        ld hl,fb_r
        ld de,fb_tr
        ld c,8
        push bc
        ld b,0
        ldir
        pop bc
fyb_lp: ld hl,fb_rect
        call field_call             ; (fb_r = the entry's rectangle; keeps BC, IX)
        push ix
        ld ix,fb_tr
        call fs_meet
        pop ix
        jr c,fyb_x                  ; (it meets)
        ld de,FB_ENT
        add ix,de
        djnz fyb_lp
        or a
fyb_x:  push af
        ld hl,fb_tr                 ; (fb_r again)
        ld de,fb_r
        ld bc,8
        ldir
        pop af
        pop ix
        ret

; -> HL = the new column's first map x, DE = past it (the page being built's: back_c0 + 15 built for the
; right, back_c0 built for the left).
fs_newc:
        ld a,(s38_back_c0)
        ld e,a
        ld a,(s38_back_dir)
        or a
        ld a,e
        jr nz,fyw_l
        add a,15
fyw_l:  call fs_c16
        ld d,h
        ld e,l
        push hl
        ld hl,16
        add hl,de
        ex de,hl
        pop hl
        ret

; fb_r (in the columns both pages hold, the kept rows, even x edges) of rectangle IX (C: its bit) copied
; from the page shown onto the page being built with one HMMM (fb_cmd, fb_rdy 1; it writes the page not
; shown: any time): SX = x - vis_c0 * 16, DX = x - back_c0 * 16, each page's line y & 255; the rectangle
; done. One across the pages' line 256 is copied in two calls: this one's part ends there, and the rest
; stays the rectangle's (IX), not done -> L 2.
fs_copy:
        ld hl,(fb_r + 2)            ; the line 256 after y0
        ld l,0
        inc h
        ld de,(fb_r + 6)
        or a
        sbc hl,de
        jr nc,fyc_d                 ; (y1 at or before it: one part)
        add hl,de
        ld (ix+2),l                 ; the rest: [that line, y1) in the same columns
        ld (ix+3),h
        ld (fb_r + 6),hl
        jr fyc_1
fyc_d:  call syn_done
fyc_1:  ld a,(s38_vis_c0)           ; SX, SY: the page shown
        call fs_c16
        ex de,hl
        ld hl,(fb_r)
        or a
        sbc hl,de
        ld (fb_cmd),hl
        ld a,(fb_r + 2)
        ld (fb_cmd + 2),a
        ld (fb_cmd + 6),a
        ld a,(s38_vis_page)
        ld (fb_cmd + 3),a
        xor 1
        ld (fb_cmd + 7),a           ; DX, DY: the page being built
        ld a,(s38_back_c0)
        call fs_c16
        ex de,hl
        ld hl,(fb_r)
        or a
        sbc hl,de
        ld (fb_cmd + 4),hl
        ld hl,(fb_r + 4)            ; NX, NY
        ld de,(fb_r)
        or a
        sbc hl,de
        ld (fb_cmd + 8),hl
        ld hl,(fb_r + 6)
        ld de,(fb_r + 2)
        or a
        sbc hl,de
        ld (fb_cmd + 10),hl
        xor a
        ld (fb_cmd + 12),a
        ld (fb_cmd + 13),a
        ld a,FB_HMMM
        ld (fb_cmd + 14),a
        ld a,1
        ld (fb_rdy),a
        ld l,2
        ret

; -> C when an item of the page shown waiting in the queue meets fb_r (its pixels there are not its list's
; composition yet). Keeps IX.
fs_qmeet:
        push ix
        ld a,(fb_qn)
        or a
        jr z,fyq_x
        ld b,a
        ld ix,fb_q + 3
fyq_lp: ld a,(s38_vis_page)
        cp (ix-3)
        jr nz,fyq_n
        call fs_meet
        jr c,fyq_x
fyq_n:  ld de,FB_QSZ
        add ix,de
        djnz fyq_lp
        or a
fyq_x:  pop ix
        ret

; (field.asm fb_bbadd through f2_call) A change of the page shown (fb_r) while the build's sync is under
; way: the rectangles of fb_bb it has not done yet that meet it are composed, not copied (fb_sdm): by the
; time the sync gets to one, the page shown may hold the change there, while the page being built keeps
; the list the sync began with. Keeps IX.
fs_dirty:
        ld a,(fb_sbi)
        inc a
        ret z                       ; (FFh: every one done, the marker queued)
        ld a,(fb_bbn)
        or a
        ret z
        push ix
        ld b,a
        ld c,1
        ld ix,fb_bb
fyd_lp: ld a,(fb_sbi)
        and c
        jr nz,fyd_n                 ; (done)
        call fs_meet
        jr nc,fyd_n
        ld a,(fb_sdm)
        or c
        ld (fb_sdm),a
fyd_n:  ld de,8
        add ix,de
        sla c
        djnz fyd_lp
        pop ix
        ret

; fb_r's x clipped to [HL, DE) (fs_clx), or its y (fs_cly) -> C when something is left. (Map coordinates:
; their differences never near 32768, as field.asm fb_meet's.) Keeps IX.
fs_clx: push ix
        ld ix,fb_r
        jr fyl_go
fs_cly: push ix
        ld ix,fb_r + 2
fyl_go: push de
        ld e,(ix+0)                 ; the first: the larger
        ld d,(ix+1)
        push hl
        or a
        sbc hl,de
        pop hl
        jp m,fyl_lo
        ld (ix+0),l
        ld (ix+1),h
fyl_lo: pop de
        ld l,(ix+4)                 ; past the last: the smaller
        ld h,(ix+5)
        or a
        sbc hl,de
        jp m,fyl_hi
        ld (ix+4),e
        ld (ix+5),d
fyl_hi: ld l,(ix+0)                 ; something left: first < past the last
        ld h,(ix+1)
        ld e,(ix+4)
        ld d,(ix+5)
        or a
        sbc hl,de
        ld a,h
        rla
        pop ix
        ret

; (field.asm fb_meet's copy) IX = a rectangle (x0, y0, x1, y1) -> C when it meets fb_r (or touches it).
; Keeps BC, IX.
fs_meet:
        ld hl,(fb_r + 4)
        ld e,(ix+0)
        ld d,(ix+1)
        or a
        sbc hl,de
        jp m,fym_no
        ld l,(ix+4)
        ld h,(ix+5)
        ld de,(fb_r)
        or a
        sbc hl,de
        jp m,fym_no
        ld hl,(fb_r + 6)
        ld e,(ix+2)
        ld d,(ix+3)
        or a
        sbc hl,de
        jp m,fym_no
        ld l,(ix+6)
        ld h,(ix+7)
        ld de,(fb_r + 2)
        or a
        sbc hl,de
        jp m,fym_no
        scf
        ret
fym_no: or a
        ret

; (field.asm fb_c16's copy) A = a cell -> HL = A * 16. Keeps BC, DE.
fs_c16: ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ret

; (field.asm fb_dnp's copy) A = page (0/1) -> HL = its list (count, then the entries). Keeps BC, DE.
fs_dnp: or a
        ld hl,fb_dn0
        ret z
        ld hl,fb_dn1
        ret

; (field.asm fb_lsz's copy) HL = a list -> BC = its bytes: the count, then FB_ENT an entry (a count
; FFh, unknown: the count only). Keeps DE, HL.
fs_lsz: ld a,(hl)
        cp FB_MAX + 1
        jr c,fsl_n
        xor a
fsl_n:  ld c,a
        add a,a
        add a,a
        add a,a
        sub c                       ; * FB_ENT (7)
        inc a
        ld c,a
        ld b,0
        ret

; (field.asm fbx_set's copy) A = page (0/1): its list's box = fb_want's (fb_wbx).
fs_bxs: ld hl,fb_wbx
        ld de,fb_pbx0
        or a
        jr z,fsb_c
        ld de,fb_pbx1
fsb_c:  ld bc,8
        ldir
        ret


; ----- scroll-1's V9938 burst (performance campaign 2, docs/PERF2_PLAN.md item 6, the V9938's part: lane W2C's,
; with V9938-SYNC; here, through rc2.asm f2_call, so that the fixed area keeps its room) -----

; (scroll9938.asm s38_work through f2_call: the V9938's build in its first phase, the VDP idle) The new column's
; tiles in a row (s38_col_tile: tile_to_page waits for the tile before, so each next one is set up while it is
; copied), while fs_stop38 lets them go on; its last one starts the copy's phase. Until then one tile a call
; of s38_work, the next at the next idle point: a column took 224 ms of the MSX2's kill floors for about 11 ms
; of VDP (a_scroll's measurement on 3b11042). The pending row's tiles stay one a call: in a row they kept the
; CPU waiting for the VDP inside the logic's frames (tour3's lifts, 545-1065, -2.3 % on C-BIOS_MSX2 and -2.2 %
; on the Expert against the code before, with V9938-SYNC; the column alone -0.3 and 0.0 %).
s38_colb:
        call s38_col_tile
        ld hl,s38_i
        inc (hl)
        ld a,(hl)
        cp VIEW_ROWS
        jr nc,fyk_end
        call fs_stop38
        jr nc,s38_colb
        ret
fyk_end:
        ld (hl),0
        ld a,1
        ld (s38_phase),a
        ret

; After a tile of the burst: C when it stops, NC when the next tile may follow. Between the HUD split and the
; VBLANK the changed cells' window first (scroll9938.asm s38_rburst, as at s38_work's start: their first page
; waits for that window); then it stops while the play-field BOBs have any work (fb_busy: a flip waits for
; their sync of the page being built, the pictures for their work on the page shown; with it, a play-field copy
; waiting for the blank, fb_cq 1 or 3, or their work of a published picture, fb_pend), or in VAT_ANIM=1 builds a
; vat column waits for the blank (vat_fr's VF_RDY: vat_win draws it in the window between the HUD split and the
; VBLANK, which a burst would keep busy; the shifted copy shrinks to one slot for it, s38_copy_chunk).
fs_stop38:
        ld a,(split_armed)
        or a
        call z,s38_rburst
        ld a,(fb_busy)
        cp 1
        ccf
        ret c
        if VAT_ANIM
        ld a,(vat_fr + VF_RDY)
        or a
        scf
        ret nz
        endif
        ld a,(fb_cq)
        rra
        ret c
        call fb_pend
        ret z                       ; (NC: fb_pend's Z exits clear the carry)
        scf
        ret
