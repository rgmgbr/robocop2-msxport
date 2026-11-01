; The front end's second bank (BANK_FRONT2 at A000h around its calls, FRONT at 8000h: frontx.asm
; front2_call; docs/ENDING.md): the game completed (level_load_3 $86DE: front_ending) and the high
; scores (high_score_entry $12082: hs_entry; the table hs_tab0, hs_tab1 in RAM, msx.inc), with
; FRONT's text screens' pieces (fs_step, fs_char, fs_tick, fs_list, ff_bits) and their scripts here
; (ending.inc, tools/msxtext.py). Every routine it calls puts the A000h window back (act_a000).

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
