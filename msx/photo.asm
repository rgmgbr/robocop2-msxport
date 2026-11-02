; The movie stills (tools/mkrom.py PHOTOS=1) and level 1's briefing (L1BRIEF=1), in the front end's bank
; (BANK_FRONT at 8000h, after FRONT's own code: nothing before them moves). docs/AMIGA_ANALYSIS.md,
; "Pictures"; docs/MSX_ARCHITECTURE.md, "The photo screens".
;
; show_picture $11E06 (D0 = 0-6: PIC1-PIC7; 8, PIC9, stays front.asm front_over's): the music stopped
; ($FE14), the picture shown at once with its own palette, then 251 VBLs or fire. The port: PIC1-PIC7 and
; PICF (the ending's, $11C54) are SCREEN 8 pictures packed with ZX0 (tools/msxphoto.py, tools/zx0.py) in
; their own banks (PHOTO_..., read at A000h); pho_show unpacks one into VRAM with the display off (black: the
; Amiga loads it from the disk meanwhile), then shows it (G7, centred on the 212 lines as pic_show's);
; pho_photo keeps it 251 ticks of 50 Hz (fs_tick: 5.02 s at 50 and 60 Hz) or until fire is pressed once
; released, then cuts to black. SCREEN 8 has no palette fades: cuts from and to black. Its G7 overwrites
; page 2 (the tile cache) and page 0: lv_vram FFh, so that the next level start (lv_select, lv_cfront,
; rs_init) uploads the level's tiles and atlas again; the stages and the title upload their own.

        if PHOTOS
PHO_TICKS:   equ 251                 ; show_picture's wait: dbf from 250 (one VBL a pass)
pho_buf:     equ pat_slot            ; 256 (256-aligned): the ring of the last 256 bytes unpacked (the sprite
                                    ;   engine's pattern hints, which spr_init fills again at every level
                                    ;   start and restart: engines_init follows every picture)
pho_off:     equ fs_buf              ; ZX0's last offset's low byte (256: 0; fs_buf: the text screens' copy
pho_bk:      equ fs_buf + 1          ;   of a script with numbers, idle while a picture shows); the
pho_a0:      equ fs_buf + 2          ;   stream's bank at A000h; the bank A000h showed before (FRONT2 in
                                    ;   the ending)

; Per picture (show_picture's D0; 7 = PICF): its stream's bank and address (A000h-BFFFh), its lines.
pho_tab: db PHOTO_PIC1_BANK
        dw PHOTO_PIC1_ADDR
        db PHOTO_PIC1_LINES
        db PHOTO_PIC2_BANK
        dw PHOTO_PIC2_ADDR
        db PHOTO_PIC2_LINES
        db PHOTO_PIC3_BANK
        dw PHOTO_PIC3_ADDR
        db PHOTO_PIC3_LINES
        db PHOTO_PIC4_BANK
        dw PHOTO_PIC4_ADDR
        db PHOTO_PIC4_LINES
        db PHOTO_PIC5_BANK
        dw PHOTO_PIC5_ADDR
        db PHOTO_PIC5_LINES
        db PHOTO_PIC6_BANK
        dw PHOTO_PIC6_ADDR
        db PHOTO_PIC6_LINES
        db PHOTO_PIC7_BANK
        dw PHOTO_PIC7_ADDR
        db PHOTO_PIC7_LINES
        db PHOTO_PICF_BANK
        dw PHOTO_PICF_ADDR
        db PHOTO_PICF_LINES

; A = a picture (pho_tab's index): pho_show, then 251 ticks or fire pressed once released (the fire that
; ended the screen before does not skip it), then the display off (the VBLANK interrupt on, front_mode
; still set: the caller's front_done or the next picture follows).
pho_photo:
        call pho_show
        ld hl,PHO_TICKS
        ld c,0                      ; (fire not released yet)
phop_lp: push hl
        push bc
        call fs_tick
        call ff_bits
        pop bc
        pop hl
        jr z,phop_rel
        dec c
        inc c
        jr nz,pho_cut                ; (pressed after a release)
        jr phop_n
phop_rel:
        ld c,1
phop_n:  dec hl
        ld a,h
        or l
        jr nz,phop_lp
pho_cut: ld a,R1_BLANK
        ld b,1
        jp wrreg                    ; (cut to black)

; pho_photo, then the game's display mode with the display off (front.asm front_done: SCREEN 5, the
; VBLANK interrupt's game work again); the caller sets up what follows (a level start: lv_select uploads
; its tiles and atlas, lv_vram FFh).
pho_end: call pho_photo
        jp front_done

; pho_end, then the text screens' display again for the bonus stage that follows (front_bonus,
; front_range: as fe_text left it, the play area black, page 0 unscrolled, the HUD split): the list
; fe_text published (pf_pal black since its end) comes back with the display; page 0's play area
; cleared of the picture's bytes.
pho_mid: call pho_end
        call fb_prep                ; (a turbo R: the display on; g_tick 0)
        ld a,(cpu_tr)
        or a
        call z,display_on
        ld hl,fs_clear
        call vdp_cmd
        jp vdp_wait

; A = a picture: SCREEN 8 (G7) with the display off, black everywhere, the picture unpacked into VRAM
; centred (its first line 106 - lines / 2, as pic_show's), the display on. The A000h window's bank comes
; back (the ending calls from FRONT2 there).
pho_show:
        push af
        ld a,(act_a000)
        ld (pho_a0),a
        call pho_g7
        pop af
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,pho_tab
        add hl,de
        ld a,(hl)                   ; the stream's bank
        ld (pho_bk),a
        call bank_a000
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)                   ; DE = the stream
        inc hl
        ld a,(hl)                   ; its lines
        push de
        srl a
        neg
        add a,PIC_TOP
        ld h,a
        ld l,0                      ; HL = its first line x 256 (G7 page 0)
        call pho_wr
        pop hl
        ld de,pho_buf               ; (the ring of the last 256 bytes)
        call pho_unz
        ld a,(pho_a0)
        call bank_a000
        ld a,R1_ON
        ld b,1
        jp wrreg                    ; the display on

; G7 (SCREEN 8), page 0, no sprites, no scroll, no line interrupt, the display off (the VBLANK interrupt
; on: front_mode, only the frame count and the sound), black everywhere (pic_show's set-up); lv_vram FFh.
pho_g7:  di
        ld a,1
        ld (front_mode),a
        xor a
        ld (split_armed),a
        ei
        ld a,0xFF
        ld (lv_vram),a              ; (page 2's tiles are the picture's bytes from here)
        ld a,R1_BLANK
        ld b,1
        call wrreg
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
        jr nz,phog_c
        xor a
        ld b,25
        call wrreg                  ; V9958: no YJK, no border mask, one page
        xor a
        ld b,26
        call wrreg
        xor a
        ld b,27
        call wrreg
phog_c:  call vdp_wait
        ld hl,ps_hmmv               ; (front.asm: 256 x 212, colour 0)
        call vdp_cmd
        jp vdp_wait

; HL = a VRAM address of G7's page 0: port 98h writes from there (the interrupts off while it goes in: the
; VBLANK interrupt reads S#0). Keeps BC, DE, HL.
pho_wr: di
        ld a,h
        rlca
        rlca
        and 3
        out (VDP_CTRL),a
        ld a,0x8E
        out (VDP_CTRL),a            ; R#14 = A15-A14 (A16 0)
        ld a,l
        out (VDP_CTRL),a
        ld a,h
        and 0x3F
        or 0x40
        out (VDP_CTRL),a
        ei
        ret

; ----- ZX0 (tools/zx0.py: dzx0_standard's format, offsets up to 256) to port 98h -----

; HL = a stream in the A000h window (its bank pho_bk, the next banks after it), DE = pho_buf (256-aligned:
; a ring of the last 256 bytes, E its next place), the VRAM write address set: the stream unpacked to
; port 98h. tools/msxphoto.py packs the pictures with offsets up to 256 only, so a copy reads its bytes
; from the ring, never from VRAM. A' is the bit buffer (ex af,af': the interrupts keep the alternate
; registers); a bit is taken with add a,a in that set (call z,pho_rl: the next byte). BC, DE, HL, AF, AF'.
pho_unz:
        ld a,0x80
        ex af,af'                   ; (the bit buffer: empty)
        ld a,1
        ld (pho_off),a              ; (the last offset: 1)
phu_lit:
        call pho_elias              ; BC = the literals
phl_lp: ld a,(hl)
        inc hl
        out (VDP_DATA),a
        ld (de),a
        inc e
        bit 6,h
        call nz,pho_nbank           ; (C000h: the stream's next bank)
        dec bc
        ld a,b
        or c
        jr nz,phl_lp
        ex af,af'
        add a,a
        call z,pho_rl
        jr c,phu_new                ; 1: a copy from a new offset
        ex af,af'
        call pho_elias              ; 0: a copy from the last offset, BC = its length
        call pho_cp
        ex af,af'
        add a,a
        call z,pho_rl
        jr c,phu_new
        ex af,af'
        jr phu_lit
phu_new:                            ; (AF' in use) the offset's high part + 1, its data bits inverted
        ld bc,1
phm_lp: add a,a
        call z,pho_rl
        jr c,phm_x
        add a,a
        call z,pho_rl
        ccf
        rl c
        rl b
        jr phm_lp
phm_x:  ex af,af'
        dec b
        ret z                       ; (256: the end)
        ld a,c
        and 1
        rrca
        ld c,a                      ; C = (v x 128) & 255 (v 1 or 2: offsets up to 256)
        ld a,(hl)                   ; the low byte: (127 - (offset - 1) % 128) x 2 + the length's first bit
        inc hl
        bit 6,h
        call nz,pho_nbank
        srl a
        push af
        ld b,a
        ld a,c
        sub b
        ld (pho_off),a              ; the offset's low byte (256: 0)
        pop af
        ld bc,1
        jr c,phn_2                  ; (that bit 1: the length - 1 is 1)
        ex af,af'
        add a,a
        call z,pho_rl
        rl c
        rl b
        call phe_lp                 ; (the rest of the Elias code)
phn_2:  inc bc                      ; BC = the length
        call pho_cp
        ex af,af'
        add a,a
        call z,pho_rl
        jr c,phu_new
        ex af,af'
        jr phu_lit

; BC = an interlaced Elias gamma value (phe_lp: AF' in use, BC the value so far).
pho_elias:
        ld bc,1
        ex af,af'
phe_lp: add a,a
        call z,pho_rl
        jr c,phe_x
        add a,a
        call z,pho_rl
        rl c
        rl b
        jr phe_lp
phe_x:  ex af,af'
        ret

; (AF' in use, the carry the marker that left A) A = the stream's next byte shifted up, the marker in
; bit 0, the carry its top bit.
pho_rl: ld a,(hl)
        inc hl
        rla
        bit 6,h
        ret z
pho_nbank:                          ; HL = C000h: the stream's next bank at A000h, HL = A000h; keeps AF, BC
        push af
        ld a,(pho_bk)
        inc a
        ld (pho_bk),a
        call bank_a000
        ld hl,0xA000
        pop af
        ret

; A copy of BC bytes (1 or more) from the last offset back (1-256): from the ring to port 98h and the ring.
pho_cp: push hl
        ld a,(pho_off)
        ld l,a
        ld a,e
        sub l
        ld l,a
        ld h,d
phc_lp: ld a,(hl)
        out (VDP_DATA),a
        ld (de),a
        inc l
        inc e
        dec bc
        ld a,b
        or c
        jr nz,phc_lp
        pop hl
        ret
        endif


        if L1BRIEF
; level_restart's first part (rc2.asm, through front_call, the display off): restart_level0 $8352, the
; level-1 restart, shows the briefing and PIC1 again when the lives are 2 (a death with three lives,
; the tenth hostage's extra life; or a continue, which level 1 does not offer: its credits are 0) and
; then initialises MU1 (silence here); levels 2 and 3 restart without them ($86DC: rts). Then the
; level's tiles and atlas again (PIC1's G7 overwrote page 2) and the tile cache, as lv_cfront's (a
; turbo R: the Z80 for the screens, cpu_title, then the R800 again: tc_reset's cpu_game); pl_init.
rs_init:
        ld hl,(AG + 0x8050)
        ld a,h
        or l
        jp nz,pl_init
        ld hl,(AG + 0x8034)
        ld de,2
        or a
        sbc hl,de
        jp nz,pl_init
        call cpu_title
        ld hl,l1_show
        call front2_call            ; (photo2.asm)
        ld a,0xFF
        ld (lv_vram),a
        ld c,0
        call lvs_vram
        call tc_reset
        jp pl_init

        endif
