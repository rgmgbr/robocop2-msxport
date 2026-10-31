; The play-field BOBs (decision 13): the hostage, the lifts and the vehicle drawn into the play
; field by the VDP, in all 16 colours, like the Amiga's blitter (docs/MSX_ARCHITECTURE.md
; "Play-field BOBs"). Bank BANK_FIELD at A000h around its calls (rc2.asm field_call); it also
; holds the scroll engines' set-up, which runs once per level. The code here calls only fixed
; code: get_tile puts the A000h window's bank back, the tile cache maps 8000h only.

        include "sprites_l1_field.inc"  ; FIELD_N, FIELD_Y0, field_tab (tools/msxsprites.py --pool)
        include "field_l2.inc"      ; level 2's: FIELD_LATE_l2, field_tab_l2 ... (tools/mkrom.py)

; Each level's play-field frames (the descriptor's lv_fld; fb_init copies them to fb_flate ...
; fb_flook): the first frame of its lifts, vehicle and trolleys (FIELD_LATE: the late ones,
; fb_late), its dynamic slot's frames (FIELD_DYN0 to FIELD_DYN1, excluded: the explosions and
; the smoke, both levels' the same, field_dyn and dyn_tab), its field_tab and field_look.
fld_l1: db FIELD_LATE, FIELD_DYN0, FIELD_DYN1
        dw field_tab, field_look
fld_l2: db FIELD_LATE_l2, FIELD_DYN0_l2, FIELD_DYN1_l2
        dw field_tab_l2, field_look_l2

; The level's atlas (bank lv_fimg on: tools/msxsprites.py field_frames, tools/mkrom.py atlas_banks)
; into VRAM, above the caches: at power-on, after the tiles (vdp.asm vdp_setup), and at each
; level's start (cold.asm lv_select). Frame by frame, as the ROM keeps no empty part of it: per
; bank its frames (bit 7: the next bank holds more of them), then [atlas line, x / 2, bytes a
; line, lines, mirrored, the pixels' offset (2) in the bank] each; a mirrored frame is another's
; pixels read from the right, each byte's two pixels swapped. Keeps the 8000h window's bank.
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

; The scroll engine of the VDP found (vdp_id; FORCE_V9938) on the camera's view, the split, the
; sprite engine.
engines_init:
        call vat_init               ; (level 2's vats: none drawn yet)
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
        call vat_init               ; (level 2's vats: the whole view drawn again)
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


; ----- the play-field BOBs -----
;
; Each picture fb_frame compares the BOBs the tick wants (fb_want: place in the map, owner) with
; what each page shows (fb_dr0 / fb_dr1, the V9958's ring being page 0) and queues the
; rectangles that changed (where a BOB was, where one is now) with their owner; a cell the scroll
; engines draw or the game changes where a BOB is goes into the queue too (fb_cellq: the
; changed cells on the page shown are composed here instead of drawn, never a hole in a BOB; a
; cell outside the box around a list's BOBs, fb_wbx and fb_pbx0/1, is tested against none).
; Rectangles of a page that meet are merged, so that an item always holds every change around
; it. fb_work composes one item at a time, a VDP command after another (each prepared while the
; one before runs and started by whoever finds the VDP idle first: the main loop's idle points,
; rc2.asm idle_work, or the interrupts, isr.asm ifg_rdy), in the scratch (page 3, 64 x 64 at FB_SX,
; FB_CY): the background, then every BOB the page's list holds over it from the atlas (LMMM
; with TIMP, the first drawn by the game first), then the scratch onto the page (HMMM). The
; background of an owner's item comes from its cache (one HMMM, up to four where the cache
; wraps): FB_GMAX blocks of 4 x 4 cells (64 x 64 px, page 3 x 64g, FB_CY) holding the tiles of a
; window of the map around it, cell (r, c) at ((r - oy) & 3, (c - ox) & 3), filled one cell at a
; time where needed (tiles.asm fb_inval forgets a cell whose tile the game changed); an item
; without an owner, or with more than 4 x 4 cells, takes its background tile by tile from the tile
; cache. On the page shown the copy starts only where the beam is off the play area: the split
; interrupt starts it (isr.asm, fb_cq), the main loop only when it is short enough for what is
; left of the blank (fb_mayq): the screen never shows half a change.
; V9938: the next page is built from a 16 px shifted copy of the displayed one, which brings the
; BOBs too, as they were when copied: once the copy is done, everywhere a BOB may have been
; (fb_bb) and every BOB wanted is composed on that page before it may be shown (fb_sync,
; fb_bsync).

FB_CY:      equ 112                     ; page 3 lines 112-175: the caches (x 0-191), the scratch
FB_SX:      equ 192                     ;   (x 192-255)
FB_HMMM:    equ 0xD0
FB_LMMMT:   equ 0x98                    ; LMMM with TIMP: colour 0 not written
FB_MAPW:    equ MAP_COLS * 16                ; (the map's height: lv_maph, the level's)
FP_FILL:    equ 1                       ; phases: the cache's cells under the piece,
FP_BG:      equ 2                       ;   the background from the cache,
FP_TILE:    equ 3                       ;   the background from the tiles,
FP_BOB:     equ 4                       ;   the BOBs,
FP_COPY:    equ 5                       ;   the copy onto the page,
FP_WAIT:    equ 6                       ;   the copy waiting for the blank
FB_BURST:   equ 16                      ; 16 x 16 copies in a row in one call (each next one set up
                                        ; while the one before runs, which takes about as long:
                                        ; vdp_cmd waits for it; a piece's 4 x 4 cells at most)
FB_STEPS:   equ 3                       ; steps of the work in one fb_work call at most

; At a level's start (engines_init): the pages hold no BOB, no cache holds anything, the dynamic
; slot no frame, nothing to do; the level's play-field frames' tables (lv_fld: fld_l1, fld_l2).
fb_init:
        ld hl,(lv_fld)
        ld de,fb_flate
        ld bc,7
        ldir
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
        ld a,FB_SX
        ld (fb_sbx),a
        ld a,0xFF
        ld (fb_bsync),a
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

; Once a picture (main loop, before the sprites' frame): what each page must show now.
fb_frame:
        call fb_wants
        ld a,(fb_eng)
        or a
        jr nz,fbf_38
        call fb_diff                ; (A = 0: the V9958's ring)
        jr fbf_end
fbf_38: ld a,(s38_vis_page)
        ld hl,fb_vlast
        cp (hl)
        jr z,fbf_b
        ld (hl),a                   ; a flip: the page hidden now is built again from the other
        xor 1
        push af
        call fb_dnp
        ld (hl),0xFF
        pop af
        call fq_purge               ; (what waited for it is not needed any more)
fbf_b:  ld a,(s38_vis_page)         ; (a new build: scroll9938.asm s38_target, fb_bbinit)
        call fb_diff
        ld a,(fb_bsync)             ; the page being built once it holds the BOBs
        ld b,a
        ld a,(s38_back_c0)
        cp b
        jr nz,fbf_end
        ld a,(s38_vis_page)
        xor 1
        or 0x40
        call fb_diff
fbf_end:
        ld a,1
        ld (fb_busy),a              ; (fb_work clears it when nothing is left)
        ret

; fb_want from the tick's list (fb_new: frame, the record's x, y, owner): x - 143 (map x, as the
; sprites' bf_show) and the frame's offset (a removed frame shown as another, field_tab); the frame
; it looks like (field_look), so that a removed frame drawn where the one shown instead was drawn
; changes nothing (the explosion's and the smoke's other steps). With them fb_wbx, the box around
; all their rectangles (fb_rect's): a cell outside it meets none of them (fb_bbcell, fb_cellq).
fb_wants:
        ld a,(fb_n)
        ld (fb_wn),a
        or a
        ret z
        ld b,a
        ld hl,0x4000                ; (the box: beyond the map on every side until a BOB is in)
        ld (fb_wbx),hl
        ld (fb_wbx + 2),hl
        ld hl,-0x4000
        ld (fb_wbx + 4),hl
        ld (fb_wbx + 6),hl
        ld ix,fb_new
        ld iy,fb_want
fw_lp:  ld e,(ix+0)
        ld d,0
        ld hl,(fb_flook)            ; (the level's field_look)
        add hl,de
        ld a,(hl)
        ld (iy+0),a
        ld a,e
        call fb_tab
        ld de,4
        add hl,de
        ld a,(hl)                   ; dx (signed)
        inc hl
        push hl
        ld e,a
        rla
        sbc a,a
        ld d,a
        ld l,(ix+1)
        ld h,(ix+2)
        add hl,de
        ld de,-143
        add hl,de
        ld (iy+1),l
        ld (iy+2),h
        pop hl
        ld a,(hl)                   ; dy
        ld e,a
        rla
        sbc a,a
        ld d,a
        ld l,(ix+3)
        ld h,(ix+4)
        add hl,de
        ld (iy+3),l
        ld (iy+4),h
        ld a,(ix+5)
        ld (iy+5),a
        ld a,(ix+6)
        ld (iy+6),a
        push bc
        ld a,(iy+0)                 ; the box takes its rectangle in (the frame it looks like, as
        call fb_tab                 ; fb_rect: x0, y0 the smallest, x1, y1 the largest)
        inc hl
        inc hl
        ld c,(hl)                   ; width
        inc hl
        ld b,(hl)                   ; height
        ld e,(iy+1)
        ld d,(iy+2)
        ld hl,(fb_wbx)
        or a
        sbc hl,de
        jp m,fw_bx1
        ld (fb_wbx),de
fw_bx1: ld l,c
        ld h,0
        add hl,de
        ex de,hl
        ld hl,(fb_wbx + 4)
        or a
        sbc hl,de
        jp p,fw_by0
        ld (fb_wbx + 4),de
fw_by0: ld e,(iy+3)
        ld d,(iy+4)
        ld hl,(fb_wbx + 2)
        or a
        sbc hl,de
        jp m,fw_by1
        ld (fb_wbx + 2),de
fw_by1: ld l,b
        ld h,0
        add hl,de
        ex de,hl
        ld hl,(fb_wbx + 6)
        or a
        sbc hl,de
        jp p,fw_bn
        ld (fb_wbx + 6),de
fw_bn:  pop bc
        ld de,FB_ENT
        add ix,de
        add iy,de
        dec b
        jp nz,fw_lp
        ret

; A = frame -> HL = its field_tab entry (x, y, width, height, dx, dy). Keeps BC.
fb_tab: ld l,a
        ld h,0
        ld e,l
        ld d,h
        add hl,hl
        add hl,de
        add hl,hl                   ; * 6
        ld de,(fb_ftab)             ; (the level's field_tab)
        add hl,de
        ret

; A = page (0/1) -> IX = the box around its list's BOBs (fb_pbx0 / fb_pbx1, set with the list:
; fbx_set; meaningful while the list holds any). Keeps BC, DE, HL.
fb_bxp: ld ix,fb_pbx0
        or a
        ret z
        ld ix,fb_pbx1
        ret

; A = page (0/1): its list's box = fb_want's (fb_wbx; the list is a copy of fb_want from now).
fbx_set:
        ld hl,fb_wbx
        ld de,fb_pbx0
        or a
        jr z,fxs_c
        ld de,fb_pbx1
fxs_c:  ld bc,8
        ldir
        ret

; HL = a list -> BC = its bytes: the count, then FB_ENT an entry (a count FFh, unknown: the count
; only, as no entry of it is read). Keeps DE, HL.
fb_lsz: ld a,(hl)
        cp FB_MAX + 1
        jr c,fls_n
        xor a
fls_n:  ld c,a
        add a,a
        add a,a
        add a,a
        sub c                       ; * FB_ENT (7)
        inc a
        ld c,a
        ld b,0
        ret

; A = page (0/1) -> HL = its list (count, then the entries). Keeps BC, DE.
fb_dnp: or a
        ld hl,fb_dn0
        ret z
        ld hl,fb_dn1
        ret

; IX = an entry (frame, x, y, ...) -> fb_r = its rectangle in the map. Keeps BC, IX, IY.
fb_rect:
        ld a,(ix+0)
        call fb_tab
        inc hl
        inc hl
        ld e,(hl)                   ; width
        inc hl
        ld a,(hl)                   ; height
        ld l,(ix+1)
        ld h,(ix+2)
        ld (fb_r),hl
        ld d,0
        add hl,de
        ld (fb_r + 4),hl
        ld l,(ix+3)
        ld h,(ix+4)
        ld (fb_r + 2),hl
        ld e,a
        add hl,de
        ld (fb_r + 6),hl
        ret

; A = page (| 40h: the page being built, | 0 the one shown): its changes against fb_want queued
; (on the V9938's displayed page also noted in fb_bb), then its list becomes fb_want.
fb_diff:
        ld (fb_dpg),a
        and 1
        call fb_dnp
        ld a,(fb_wn)                ; the page shows the list wanted already: nothing changes
        cp (hl)
        jr nz,fd_go
        or a
        ret z
        ld c,a
        add a,a
        add a,a
        add a,a
        sub c                       ; (FB_ENT bytes an entry)
        ld b,a
        ld de,fb_want
        push hl
        inc hl
fd_eq:  ld a,(de)
        cp (hl)
        jr nz,fd_ne
        inc de
        inc hl
        djnz fd_eq
        pop hl
        ret
fd_ne:  pop hl
fd_go:  ld a,(hl)
        inc a
        jr z,fd_unk                 ; (FFh unknown: the sync composes that page)
        dec a
fd_unk: ld (fb_dcnt),a
        inc hl
        ld (fb_dptr),hl
        ld a,(fb_dcnt)              ; each BOB drawn that is not wanted: where it was
        or a
        jr z,fd_want
        ld b,a
        ld ix,(fb_dptr)
fd_dlp: push bc
        push ix
        pop hl
        ld de,fb_want
        ld a,(fb_wn)
        call fb_find
        call nz,fb_qent
        ld de,FB_ENT
        add ix,de
        pop bc
        djnz fd_dlp
fd_want:
        ld a,(fb_wn)                ; each BOB wanted that is not drawn: where it is now
        or a
        jr z,fd_copy
        ld b,a
        ld ix,fb_want
fd_wlp: push bc
        push ix
        pop hl
        ld de,(fb_dptr)
        ld a,(fb_dcnt)
        call fb_find
        call nz,fb_qent
        ld de,FB_ENT
        add ix,de
        pop bc
        djnz fd_wlp
fd_copy:
        ld a,(fb_dpg)               ; the page's list = fb_want, its box fb_want's
        and 1
        push af
        call fb_dnp
        ex de,hl
        ld hl,fb_wn
        call fb_lsz
        ldir
        pop af
        jp fbx_set

; IX = an entry: its rectangle and owner into the queue for fb_diff's page. Keeps IX.
fb_qent:
        call fb_rect
        ld a,(ix+5)
        ld (fb_own),a
        ld a,(ix+6)
        ld (fb_own + 1),a
        ; (falls through)

; fb_r (owner fb_own) into the queue for fb_diff's page; on the V9938's displayed page also into
; fb_bb. Keeps IX.
fb_qdiff:
        ld a,(fb_dpg)
        and 0x41
        push af
        and 1
        call fb_queue
        pop af
        and 0x40
        ret nz
        ld a,(fb_eng)
        or a
        ret z
        jp fb_bbadd

; HL = an entry, DE = a list of A entries -> Z when the list has the same entry. Keeps IX, IY.
fb_find:
        or a
        jr z,fdf_no
        ld b,a
fdf_lp: push bc
        push hl
        push de
        ld b,FB_ENT
fdf_cmp:
        ld a,(de)
        cp (hl)
        jr nz,fdf_ne
        inc hl
        inc de
        djnz fdf_cmp
        pop de
        pop hl
        pop bc
        xor a                       ; (Z)
        ret
fdf_ne: pop de
        pop hl
        ld a,e
        add a,FB_ENT
        ld e,a
        jr nc,fdf_nc
        inc d
fdf_nc: pop bc
        djnz fdf_lp
fdf_no: or 1                        ; (NZ)
        ret

; A = a cell -> HL = A * 16 (A < 256 cells; fb_c16m: A - 1, which may be -1). Keeps BC, DE.
fb_c16m:
        dec a
        cp 0xFF
        jr nz,fb_c16
        ld hl,-16
        ret
fb_c16: ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ret

; HL = a map coordinate (0 or more) -> A = its cell (HL >> 4). Keeps BC, DE.
fb_cell:
        ld a,l
        srl h
        rra
        srl h
        rra
        srl h
        rra
        srl h
        rra
        ret

; HL, DE (signed) -> C when HL < DE, Z when they are equal. Keeps BC, DE, HL.
fb_cmp: push hl
        or a
        sbc hl,de
        ld a,h
        pop hl
        jp pe,fcm_ov                ; (signed overflow: the sign flips)
        rla
        ret
fcm_ov: rla
        ccf
        ret

; fb_r into fb_bb (the rectangles the V9938's next page may hold from its copy): merged with
; one it meets, else added; when full, merged with the last. Keeps IX.
fb_bbadd:
        push ix
        call fba_go
        pop ix
        ret
fba_go: ld a,(fb_bbn)
        or a
        jr z,fba_new
        ld b,a
        ld ix,fb_bb
fba_lp: call fb_meet
        jr c,fba_mrg
        ld de,8
        add ix,de
        djnz fba_lp
        ld a,(fb_bbn)
        cp FB_BBMAX
        jr nc,fba_last
fba_new:
        ld a,(fb_bbn)
        inc a
        ld (fb_bbn),a
        dec a
        add a,a
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,fb_bb
        add hl,de
        ex de,hl
        ld hl,fb_r
        ld bc,8
        ldir
        ret
fba_last:
        ld ix,fb_bb + (FB_BBMAX - 1) * 8
fba_mrg:
        jp fb_union

; IX = a rectangle (x0, y0, x1, y1) -> C when it meets fb_r (or touches it). Keeps BC, IX. (The
; sign of a difference of two map coordinates, never near 32768 apart: no fb_cmp here.)
fb_meet:
        ld hl,(fb_r + 4)            ; its x0 <= fb_r's x1 (touching counts)
        ld e,(ix+0)
        ld d,(ix+1)
        or a
        sbc hl,de
        jp m,fmt_no
        ld l,(ix+4)                 ; fb_r's x0 <= its x1
        ld h,(ix+5)
        ld de,(fb_r)
        or a
        sbc hl,de
        jp m,fmt_no
        ld hl,(fb_r + 6)            ; its y0 <= fb_r's y1
        ld e,(ix+2)
        ld d,(ix+3)
        or a
        sbc hl,de
        jp m,fmt_no
        ld l,(ix+6)                 ; fb_r's y0 <= its y1
        ld h,(ix+7)
        ld de,(fb_r + 2)
        or a
        sbc hl,de
        jp m,fmt_no
        scf
        ret
fmt_no: or a
        ret

; IX = a rectangle: it becomes the union of itself and fb_r. Keeps BC, IX.
fb_union:
        ld hl,(fb_r)                ; x0: the smaller
        ld e,(ix+0)
        ld d,(ix+1)
        or a
        sbc hl,de
        jp p,fu_1
        add hl,de
        ld (ix+0),l
        ld (ix+1),h
fu_1:   ld hl,(fb_r + 2)            ; y0
        ld e,(ix+2)
        ld d,(ix+3)
        or a
        sbc hl,de
        jp p,fu_2
        add hl,de
        ld (ix+2),l
        ld (ix+3),h
fu_2:   ld hl,(fb_r + 4)            ; x1: the larger
        ld e,(ix+4)
        ld d,(ix+5)
        or a
        sbc hl,de
        jp m,fu_3
        jr z,fu_3
        add hl,de
        ld (ix+4),l
        ld (ix+5),h
fu_3:   ld hl,(fb_r + 6)            ; y1
        ld e,(ix+6)
        ld d,(ix+7)
        or a
        sbc hl,de
        ret m
        ret z
        add hl,de
        ld (ix+6),l
        ld (ix+7),h
        ret

; (scroll9938.asm s38_target) A V9938 build begins: the displayed page's work under way (the item
; being composed and those waiting) is where its copy may bring something its list does not show;
; the rest the copy brings as it is, the BOBs with it, in their place (they were composed again in
; full until 2026-10-21: one build's items held the page shown's for ~12 pictures). Called when the
; target is set, before the build draws anything (fb_bbcell adds its cells from then on).
fb_bbinit:
        call vat_bbinit             ; (level 2's vats: the looks its copy brings)
        xor a
        ld (fb_bbn),a
        ld a,(fb_ph)
        or a
        jr z,fbi_q0
        ld hl,fb_cur
        call fbi_one
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

; HL = an item: its rectangle into fb_bb when it is the displayed page's.
fbi_one:
        ld a,(s38_vis_page)
        cp (hl)
        ret nz
        inc hl
        inc hl
        inc hl
        ld de,fb_r
        ld bc,8
        ldir
        jp fb_bbadd

; A = page (or a marker | 80h), fb_r = a rectangle, fb_own = its owner (FFFFh: none): into the
; queue, clipped to the map, stamped with the picture being prepared (fb_tick: on the page shown
; it is not copied before that picture is published, rc2.asm do_publish). One of the same page
; it meets, or of the same owner, takes it in (and the union goes in again, as it may now meet another; the stamp is
; the older of the two, so that the hold still waits for it); the owner stays when only one has
; one. When full: merged with one of
; that page (lost when there is none: fb_lost). Keeps IX (the callers walk their lists with it).
fb_queue:
        push ix
        push af
        ld a,1
        ld (fb_qlk),a               ; (meanwhile the VBLANK holds the picture: isr.asm fb_pend)
        pop af
        call fq_go
        xor a
        ld (fb_qlk),a
        pop ix
        ret
fq_go:  ld c,a
        ld a,(fb_tick)
        ld (fb_stp),a
        ld hl,(fb_r)                ; x0 >= 0
        bit 7,h
        jr z,fq_x1
        ld hl,0
        ld (fb_r),hl
fq_x1:  ld hl,(fb_r + 4)            ; x1 <= map width
        ld de,FB_MAPW
        call fb_cmp
        jr c,fq_y0
        ld (fb_r + 4),de
fq_y0:  ld hl,(fb_r + 2)
        bit 7,h
        jr z,fq_y1
        ld hl,0
        ld (fb_r + 2),hl
fq_y1:  ld hl,(fb_r + 6)
        ld de,(lv_maph)
        call fb_cmp
        jr c,fq_e
        ld (fb_r + 6),de
fq_e:   ld hl,(fb_r)                ; empty?
        ld de,(fb_r + 4)
        call fb_cmp
        ret nc
        ld hl,(fb_r + 2)
        ld de,(fb_r + 6)
        call fb_cmp
        ret nc
fq_add: ld a,(fb_qn)
        or a
        jp z,fq_new
        ld b,a
        ld ix,fb_q
fq_lp:  ld a,(ix+0)
        cp c
        jr nz,fq_nx
        ld a,(fb_own)               ; of the same owner: all its BOBs change in one copy
        cp (ix+1)
        jr nz,fq_ot
        ld a,(fb_own + 1)
        cp (ix+2)
        jr nz,fq_ot
        inc a
        jp nz,fq_mrg                ; (FFFFh: no owner)
fq_ot:  inc ix                      ; another's it meets: merged when four pieces hold both (the
        inc ix                      ; most fb_stage composes before copying any: a bigger item
        inc ix                      ; reaches the page in pieces a picture apart)
        call fb_meet
        dec ix
        dec ix
        dec ix
        jr nc,fq_nx
        call fq_fits
        jp nc,fq_mrg
fq_nx:  ld de,FB_QSZ
        add ix,de
        djnz fq_lp
        ld a,(fb_qn)
        cp FB_QMAX
        jr c,fq_new
        ld b,a                      ; full: one of that page takes it
        ld ix,fb_q
fq_fl:  ld a,(ix+0)
        cp c
        jr z,fq_mrg
        ld de,FB_QSZ
        add ix,de
        djnz fq_fl
        ld hl,fb_lost
        inc (hl)
        ret
fq_mrg: ld l,(ix+1)                 ; the owner: the same, or the one of the two that has one
        ld h,(ix+2)
        ld de,(fb_own)
        ld a,l
        and h
        inc a
        jr z,fq_mr                  ; (the item has none: fb_own's)
        ld a,e
        and d
        inc a
        jr z,fq_mo                  ; (fb_own none: the item's)
        or a
        sbc hl,de
        jr z,fq_mr                  ; (the same)
        add hl,de                   ; (two: a BOB's before an explosion's, so that the hold and the
        ld a,h                      ; order, fn_take, still see the BOB's change; its background
        or a                        ; cache serves the union as well)
        jr z,fq_mr
fq_mo:  ld (fb_own),hl
fq_mr:  ld a,(fb_tick)              ; the stamp: the older picture of the two (the hold still
        sub (ix+11)                 ; waits for what the item held)
        ld e,a
        ld a,(fb_tick)
        ld hl,fb_stp
        sub (hl)
        cp e
        jr nc,fq_ms
        ld a,(ix+11)
        ld (hl),a
fq_ms:  inc ix
        inc ix
        inc ix
        call fb_union               ; the item's rectangle grows by fb_r
        push ix
        pop hl
        ld de,fb_r
        push bc
        ld bc,8
        ldir                        ; and fb_r becomes it
        pop bc
        dec ix
        dec ix
        dec ix
        push bc
        call fq_del                 ; the item out, the union in again
        pop bc
        jp fq_add
fq_new: ld a,(fb_qn)
        inc a
        ld (fb_qn),a
        dec a
        call fq_addr
        ld (hl),c
        inc hl
        ld a,(fb_own)
        ld (hl),a
        inc hl
        ld a,(fb_own + 1)
        ld (hl),a
        inc hl
        ex de,hl
        ld hl,fb_r
        ld bc,8
        ldir
        ld a,(fb_stp)
        ld (de),a
        ret

; IX = an item of the queue -> NC when its rectangle and fb_r together take at most four pieces of
; 64 x 64 (x0 and x1 even as fb_clip makes them; fb_stage composes up to four before any copy).
; Keeps BC, IX.
fq_fits:
        push bc
        ld l,(ix+3)
        ld h,(ix+4)
        ld de,(fb_r)
        call fb_cmp
        jr c,fqf_x0
        ex de,hl                    ; HL = the smaller x0
fqf_x0: res 0,l
        push hl
        ld l,(ix+7)
        ld h,(ix+8)
        ld de,(fb_r + 4)
        call fb_cmp
        jr nc,fqf_x1
        ex de,hl                    ; HL = the larger x1
fqf_x1: inc hl
        res 0,l
        pop de
        or a
        sbc hl,de
        call fst_n
        ld c,a                      ; pieces across
        ld l,(ix+5)
        ld h,(ix+6)
        ld de,(fb_r + 2)
        call fb_cmp
        jr c,fqf_y0
        ex de,hl
fqf_y0: push hl
        ld l,(ix+9)
        ld h,(ix+10)
        ld de,(fb_r + 6)
        call fb_cmp
        jr nc,fqf_y1
        ex de,hl
fqf_y1: pop de
        or a
        sbc hl,de
        call fst_n
        ld b,a                      ; down
        xor a
fqf_m:  add a,c
        jr c,fqf_no
        djnz fqf_m
        cp 5
        ccf
        pop bc
        ret
fqf_no: pop bc
        scf
        ret

; A = an index -> HL = that item of the queue (FB_QSZ = 12). Keeps BC, DE.
fq_addr:
        push de
        ld l,a
        ld h,0
        ld e,l
        ld d,h
        add hl,hl
        add hl,de                   ; * 3
        add hl,hl
        add hl,hl                   ; * FB_QSZ (12)
        ld de,fb_q
        add hl,de
        pop de
        ret

; IX = an item of the queue: out of it (the ones after it move up).
fq_del: ld a,(fb_qn)
        call fq_addr                ; HL = the queue's end
        push ix
        pop de
        or a
        sbc hl,de
        ld bc,-FB_QSZ
        add hl,bc                   ; the bytes after the item
        ld b,h
        ld c,l
        ld hl,FB_QSZ
        add hl,de
        ld a,b
        or c
        jr z,fqd_n
        ldir
fqd_n:  ld hl,fb_qn
        dec (hl)
        ret

; A = page: its items out of the queue.
fq_purge:
        ld c,a
fqp_lp: ld a,(fb_qn)
        or a
        ret z
        ld b,a
        ld ix,fb_q
fqp_s:  ld a,(ix+0)
        cp c
        jr z,fqp_d
        ld de,FB_QSZ
        add ix,de
        djnz fqp_s
        ret
fqp_d:  push bc
        call fq_del
        pop bc
        jr fqp_lp

; Once a VDP command is free (rc2.asm idle_work, the VDP idle): the command prepared at the call
; before starts (unless the interrupts started it meanwhile, fb_rdy 2: done by now, the VDP being
; idle), then a step of the work prepares the next one (fb_rdy 1), which starts here when the VDP
; is idle by then (or runs a short copy of ours, fb_shc: waited for), else from the interrupts
; (isr.asm ifg_rdy) or at the next call; FB_STEPS steps a call at most. A step: an item taken
; (fb_next) and its first command, a phase's next command (the fill's and the tiles' burst counts
; as one), a copy left waiting for the blank, the item's end. Composing writes page 3 only (the
; scratch, the caches, the dynamic slot), off the screen: those commands may start at any time;
; the copy onto the page shown keeps its rules (fb_cq, fb_mayq, the interrupts).
fb_work:
        xor a
        ld (fb_shc),a               ; (the VDP is idle: nothing of ours runs)
        ld a,FB_STEPS
        ld (fb_wk),a
fwk_lp: ld a,(fb_rdy)
        or a
        jr z,fwk_st
        dec a
        jr z,fwk_go
        xor a                       ; (the interrupts started it)
        ld (fb_rdy),a
        jr fwk_st
fwk_go: call fb_go
        ret nz                      ; (a long command of ours still runs: later)
fwk_st: call fb_step
        ld a,(fb_rdy)
        or a
        ret z                       ; nothing prepared: no work, or a copy waits for the blank
        ld hl,fb_wk
        dec (hl)
        ret z
        jr fwk_lp

; One step of the work (fb_work).
fb_step:
        ld a,(fb_ph)
        or a
        jr nz,fwk_ph
        call fb_next
        jr z,fwk_ph
        call fb_sync
        jr z,fb_step                ; (queued: taken now)
        xor a
        ld (fb_busy),a
        ret
fwk_ph: ld a,(fb_ph)
        dec a
        jp z,fb_fill
        dec a
        jp z,fb_bg
        dec a
        jp z,fb_tiles
        dec a
        jp z,fb_bobs
        dec a
        jp z,fb_copy
        jp fb_wait

; The queue's first item into fb_cur, clipped to what its page keeps (a marker: the V9938's page
; being built holds the BOBs now), its page's list as the BOBs it shows (fb_sn) -> Z with its
; first piece set up, NZ when there is none.
fb_next:
        ld a,(fb_qn)
        or a
        jr nz,fn_take
        ld (fb_qlk),a               ; (A = 0)
        or 1
        ret
fn_take:
        ld a,1                      ; (until its phase is set, or the queue is empty, the VBLANK holds
        ld (fb_qlk),a               ; the picture: isr.asm fb_pend)
        ld c,0                      ; first the page shown's items of a published picture, the oldest
        ld a,(fb_eng)               ; picture's first (fn_key; a lift's or the vehicle's changes every
        or a                        ; tick: taking them before an explosion's starved it for 9
        jr z,fn_pg                  ; pictures); then the first other that is not late, else the first
        ld a,(s38_vis_page)
        ld c,a
fn_pg:  xor a
        ld (fb_bki),a
        ld a,(fb_qn)
        ld b,a
        ld ix,fb_q
fn_lp:  call fn_pub
        jr nz,fn_nx
        call fn_key
        ld hl,fb_bki
        cp (hl)
        jr c,fn_nx
        jr z,fn_nx                  ; (the same rank: the earlier)
        ld (hl),a
        ld (fb_bkp),ix
fn_nx:  push bc
        ld bc,FB_QSZ
        add ix,bc
        pop bc
        djnz fn_lp
        ld a,(fb_bki)
        or a
        jr z,fn_s3
        ld ix,(fb_bkp)
        jr fn_got
fn_s3:  ld a,(fb_qn)
        ld b,a
        ld ix,fb_q
fn_sel: call fb_late
        jr z,fn_got
        ld de,FB_QSZ
        add ix,de
        djnz fn_sel
        ld ix,fb_q
fn_got: push ix
        pop hl
        ld de,fb_cur
        ld bc,FB_QSZ
        ldir
        call fq_del
        ld a,(fb_cur)
        bit 7,a
        jr z,fn_rect
        ld a,(fb_cur + 3)           ; a marker: its build target
        ld b,a
        ld a,(s38_back_c0)
        cp b
        jp nz,fb_next
        ld (fb_bsync),a
        jp fb_next
fn_rect:
        call fb_clip
        jp c,fb_next                ; (nothing of it is kept)
        ld a,(fb_cur)
        call fb_dnp
        ld de,fb_sn
        call fb_lsz
        ldir
        ld a,(fb_sn)
        inc a
        jr nz,fn_sn
        ld (fb_sn),a                ; (unknown: none)
fn_sn:  call fb_stage
        ld hl,(fb_cur + 3)
        ld (fb_px),hl
        ld hl,(fb_cur + 5)
        ld (fb_px + 2),hl
        call fb_piece
        xor a
        ld (fb_qlk),a
        ret

; IX = a published item of the page shown -> A = its rank: the older its picture the higher; for
; the same picture first a BOB's change or a cell's (the picture waits for them, in their order:
; a BOB's before a cell's would leave it whole), then a lift's or the vehicle's on the screen
; (fb_late: their copy the one right before the picture goes on screen, RoboCop riding them), then
; an explosion's (never waited for: a step drawn late shows the next one). Keeps BC, IX.
fn_key:
        ld a,(ix+2)
        or a
        ld d,1
        jr z,fnk_a                  ; (an explosion's: owner high byte 0)
        call fb_late
        ld d,2
        jr nz,fnk_a
        ld d,3
fnk_a:  ld a,(fb_tick)
        sub (ix+11)                 ; its picture's age (1 or more)
        cp 63
        jr c,fnk_c
        ld a,63
fnk_c:  add a,a
        add a,a
        add a,d
        ret

; IX = an item of the queue, C = the page shown -> Z when it is that page's and its picture is
; published (its stamp not fb_tick). Keeps BC, IX.
fn_pub: ld a,(ix+0)
        cp c
        ret nz
        ld a,(fb_tick)
        cp (ix+11)
        jr z,fnp_n
        xor a
        ret
fnp_n:  or 1
        ret

; IX = an item of the queue -> NZ when it is late: on the page shown, on the screen (the view:
; map x cam_x .. cam_x + 247, y cam_y .. cam_y + 162) and meeting a BOB of a lift or of the
; vehicle (frames from FIELD_LATE) of that page's list. Keeps BC, IX.
fb_late:
        push bc
        ld a,(ix+0)
        bit 7,a
        jr nz,fla_no                ; (a marker)
        ld c,a
        ld a,(fb_eng)
        or a
        jr z,fla_p
        ld a,(s38_vis_page)
fla_p:  cp c
        jr nz,fla_no
        ld hl,(cam_x)               ; on the screen?
        ld (fb_r),hl
        ld de,247
        add hl,de
        ld (fb_r + 4),hl
        ld hl,(cam_y)
        ld (fb_r + 2),hl
        ld de,162
        add hl,de
        ld (fb_r + 6),hl
        push ix
        inc ix
        inc ix
        inc ix
        call fb_meet
        pop ix
        jr nc,fla_no
        ld a,c
        call fb_dnp
        ld a,(hl)
        inc a
        jr z,fla_no
        dec a
        jr z,fla_no
        ld b,a
        inc hl
        push ix
        push hl
        pop iy
fla_lp: ld a,(iy+0)
        ld hl,fb_flate              ; (the level's FIELD_LATE)
        cp (hl)
        jr c,fla_nx
        push iy
        pop ix
        call fb_rect
        pop ix
        push ix
        inc ix
        inc ix
        inc ix
        call fb_meet
        jr c,fla_yes
fla_nx: ld de,FB_ENT
        add iy,de
        djnz fla_lp
        pop ix
fla_no: pop bc
        xor a
        ret
fla_yes:
        pop ix
        pop bc
        or 1
        ret

; fb_cur clipped to what its page keeps (the V9958's ring: the kept columns and rows; a V9938
; page: its 16 columns and the kept rows), x0 and x1 even -> C when nothing is left.
fb_clip:
        call fb_window              ; HL = x0, DE = x1 of the page's window (C: none)
        ret c
        push de
        ld de,(fb_cur + 3)
        call fb_cmp
        jr c,fcl_x0
        ld (fb_cur + 3),hl
fcl_x0: pop hl                      ; HL = window's x1
        ld de,(fb_cur + 7)
        ex de,hl
        call fb_cmp                 ; rect's x1 < window's x1 ?
        jr c,fcl_x1
        ld (fb_cur + 7),de
fcl_x1: ld a,(prev_cy)              ; rows: [prev_cy-1, prev_cy+13)
        call fb_c16m
        ld de,(fb_cur + 5)
        call fb_cmp
        jr c,fcl_y0
        ld (fb_cur + 5),hl
fcl_y0: ld a,(prev_cy)
        add a,VIEW_ROWS - 1
        call fb_c16
        ld de,(fb_cur + 9)
        ex de,hl
        call fb_cmp
        jr c,fcl_y1
        ld (fb_cur + 9),de
fcl_y1: ld a,(fb_cur + 3)           ; even edges (two pixels a byte)
        and 0xFE
        ld (fb_cur + 3),a
        ld hl,(fb_cur + 7)
        inc hl
        ld a,l
        and 0xFE
        ld l,a
        ld (fb_cur + 7),hl
        ld hl,(fb_cur + 3)          ; empty?
        ld de,(fb_cur + 7)
        call fb_cmp
        ccf
        ret c
        ld hl,(fb_cur + 5)
        ld de,(fb_cur + 9)
        call fb_cmp
        ccf
        ret

; The window of fb_cur's page -> HL = its first map x, DE = past its last; C when the page keeps
; nothing (a V9938 page not being built).
fb_window:
        ld a,(fb_eng)
        or a
        jr nz,fwi_38
        ld a,(prev_cx)              ; V9958: columns [prev_cx-1, prev_cx+18)
        call fb_c16m
        push hl
        ld a,(prev_cx)
        add a,18
        call fb_c16
        ex de,hl
        pop hl
        or a
        ret
fwi_38: ld a,(fb_cur)
        ld hl,s38_vis_page
        cp (hl)
        ld a,(s38_vis_c0)
        jr z,fwi_c
        ld a,(s38_flip_wait)        ; (the old page: on screen until the flip is)
        or a
        ld a,(s38_old_c0)
        jr nz,fwi_c
        ld a,(s38_back_c0)
        cp 0xFF
        scf
        ret z
fwi_c:  call fb_c16
        ld de,256
        ex de,hl
        add hl,de
        ex de,hl
        or a
        ret

; The piece from fb_px: up to 64 x 64 (the scratch) of fb_cur, its cells (fb_cc) and the source of
; its background: the owner's cache when the piece is the whole item and has at most 4 rows and 4
; columns of cells (5: the narrower edge column from the tiles, fb_slc), else the tiles.
fb_piece:
        xor a
        ld (fb_cpi),a
        ld (fb_cq),a
        ld (fb_c2),a
        ld (fb_dsn),a
        dec a
        ld (fb_slc),a
        ld hl,(fb_px)
        ld de,64
        add hl,de
        ex de,hl
        ld hl,(fb_cur + 7)
        call fb_cmp
        jr c,fp_x
        ex de,hl
fp_x:   ld (fb_pe),hl
        ld hl,(fb_px + 2)
        ld de,64
        add hl,de
        ex de,hl
        ld hl,(fb_cur + 9)
        call fb_cmp
        jr c,fp_y
        ex de,hl
fp_y:   ld (fb_pe + 2),hl
        ld hl,(fb_px)               ; the cells: first and last column and row
        call fb_cell
        ld (fb_cc),a
        ld hl,(fb_px + 2)
        call fb_cell
        ld (fb_cc + 1),a
        ld hl,(fb_pe)
        dec hl
        call fb_cell
        ld (fb_cc + 2),a
        ld hl,(fb_pe + 2)
        dec hl
        call fb_cell
        ld (fb_cc + 3),a
        call vat_inbox              ; (level 2: a piece over a vat cell takes its background from the
        jp nz,fp_tiles              ;  tiles, which follow its column's look)
        ld hl,(fb_cur + 1)          ; an owner's?
        ld a,h
        and l
        inc a
        jr z,fp_tiles
        ld hl,(fb_px)               ; the whole item?
        ld de,(fb_cur + 3)
        or a
        sbc hl,de
        jr nz,fp_tiles
        ld hl,(fb_px + 2)
        ld de,(fb_cur + 5)
        or a
        sbc hl,de
        jr nz,fp_tiles
        ld hl,(fb_pe)
        ld de,(fb_cur + 7)
        or a
        sbc hl,de
        jr nz,fp_tiles
        ld hl,(fb_pe + 2)
        ld de,(fb_cur + 9)
        or a
        sbc hl,de
        jr nz,fp_tiles
        ld a,(fb_cc + 1)            ; at most 4 rows,
        ld b,a
        ld a,(fb_cc + 3)
        sub b
        cp 4
        jr nc,fp_tiles
        ld a,(fb_cc)                ; 4 columns (5: the narrower edge one from the tiles)
        ld b,a
        ld a,(fb_cc + 2)
        sub b
        cp 4
        jr c,fp_cache
        jr nz,fp_tiles
        ld a,(fb_px)                ; the left edge column's width: 16 - (x0 & 15)
        and 15
        neg
        add a,16
        ld c,a
        ld a,(fb_pe)                ; the right one's: ((x1 - 1) & 15) + 1
        dec a
        and 15
        inc a
        cp c
        jr c,fp_slr
        ld a,(fb_cc)                ; (the left one)
        ld (fb_slc),a
        inc a
        ld (fb_cc),a
        jr fp_cache
fp_slr: ld a,(fb_cc + 2)            ; (the right one)
        ld (fb_slc),a
        dec a
        ld (fb_cc + 2),a
fp_cache:
        call fb_cfind
        ld a,FP_FILL
        jr fp_ph
fp_tiles:
        ld a,0xFF
        ld (fb_cgi),a
        ld a,FP_TILE
fp_ph:  ld (fb_ph),a
        ld a,(fb_cc + 1)            ; the first cell
        ld (fb_ci),a
        ld a,(fb_cc)
        ld (fb_ci + 1),a
        ret

; The cache of fb_cur's owner (else a free one, else the one used least recently) for the piece:
; fb_cgi, its window moved over the piece's cells (the cells that come into it not held).
fb_cfind:
        ld hl,(fb_cur + 1)
        ld ix,fb_cache
        ld de,FB_CSZ
        ld bc,FB_GMAX * 256         ; (C: the index)
fcf_lp: ld a,(ix+0)
        cp l
        jr nz,fcf_nx
        ld a,(ix+1)
        cp h
        jr z,fcf_got
fcf_nx: add ix,de
        inc c
        djnz fcf_lp
        ld ix,fb_cache              ; none: a free one, else the oldest
        ld iy,fb_cache
        ld bc,FB_GMAX * 256
        xor a
        ld (fb_cgi),a
        ld (fb_rw),a                ; (the oldest's age)
fcf_al: ld a,(ix+0)
        and (ix+1)
        inc a
        jr z,fcf_fr
        ld a,(fb_tick)
        sub (ix+8)
        push hl
        ld hl,fb_rw
        cp (hl)
        jr c,fcf_an
        ld (hl),a
        ld a,c
        ld (fb_cgi),a
        push ix
        pop iy
fcf_an: pop hl
        add ix,de
        inc c
        djnz fcf_al
        push iy
        pop ix
        ld a,(fb_cgi)
        ld c,a
fcf_fr: ld (ix+0),l                 ; the owner's now: no cell held, the window on the piece
        ld (ix+1),h
        xor a
        ld (ix+6),a
        ld (ix+7),a
        ld a,(fb_cc)
        ld (ix+2),a
        ld (ix+4),a
        ld a,(fb_cc + 1)
        ld (ix+3),a
        ld (ix+5),a
fcf_got:
        ld a,c
        ld (fb_cgi),a
        ld a,(fb_tick)
        ld (ix+8),a
        ld a,(fb_cc)                ; columns: the window from c0, or up to c1
        cp (ix+2)
        jr c,fcf_xm
        ld a,(ix+2)
        add a,3
        ld b,a
        ld a,(fb_cc + 2)
        cp b
        jr c,fcf_y
        jr z,fcf_y
        sub 3
fcf_xm: call fcf_mvx
fcf_y:  ld a,(fb_cc + 1)            ; rows the same way
        cp (ix+3)
        jr c,fcf_ym
        ld a,(ix+3)
        add a,3
        ld b,a
        ld a,(fb_cc + 3)
        cp b
        ret c
        ret z
        sub 3
fcf_ym: jp fcf_mvy

; A = the window's new first column (IX = the cache): the columns coming in are not held.
fcf_mvx:
        ld c,a
        sub (ix+2)
        ld (ix+2),c
        jr nc,fmx_r
        neg                         ; to the left: -d columns from the new first one
        ld b,a
        ld a,c
        jr fmx_go
fmx_r:  ld b,a                      ; to the right: d columns up to the new last one
        ld a,c
        add a,4
        sub b
fmx_go: ld c,a
        ld a,b
        cp 4
        jr nc,fm_all
fmx_lp: ld a,c
        sub (ix+4)
        and 3
        ld e,0x11                   ; the column's bit in each row
        jr z,fmx_m
fmx_sh: sla e
        dec a
        jr nz,fmx_sh
fmx_m:  ld a,e
        cpl
        ld e,a
        ld a,(ix+6)
        and e
        ld (ix+6),a
        ld a,(ix+7)
        and e
        ld (ix+7),a
        inc c
        djnz fmx_lp
        ret
fm_all: xor a
        ld (ix+6),a
        ld (ix+7),a
        ret

; A = the window's new first row (IX = the cache): the rows coming in are not held.
fcf_mvy:
        ld c,a
        sub (ix+3)
        ld (ix+3),c
        jr nc,fmy_r
        neg
        ld b,a
        ld a,c
        jr fmy_go
fmy_r:  ld b,a
        ld a,c
        add a,4
        sub b
fmy_go: ld c,a
        ld a,b
        cp 4
        jr nc,fm_all
fmy_lp: ld a,c
        sub (ix+5)
        and 3
        ld e,0xF0                   ; rows 0 and 2: the low nibble, 1 and 3: the high one
        bit 0,a
        jr z,fmy_n
        ld e,0x0F
fmy_n:  bit 1,a
        jr nz,fmy_hi
        ld a,(ix+6)
        and e
        ld (ix+6),a
        jr fmy_nx
fmy_hi: ld a,(ix+7)
        and e
        ld (ix+7),a
fmy_nx: inc c
        djnz fmy_lp
        ret

; IX = the item's cache (fb_cgi).
fb_cix: ld a,(fb_cgi)
        ld ix,fb_cache
        or a
        ret z
        ld de,FB_CSZ
fcx_lp: add ix,de
        dec a
        jr nz,fcx_lp
        ret

; D = row, E = column of a cell in the window of the cache IX -> HL = its byte of the held cells,
; A = its bit. Keeps BC, DE, IX.
fb_cbit:
        push bc
        ld a,e
        sub (ix+4)
        and 3
        ld c,a
        ld a,d
        sub (ix+5)
        and 3
        add a,a
        add a,a
        add a,c                     ; row * 4 + column in the cache
        ld c,a
        and 7
        ld b,a
        ld a,1
        inc b
fcb_sh: dec b
        jr z,fcb_m
        add a,a
        jr fcb_sh
fcb_m:  push ix
        pop hl
        bit 3,c
        ld bc,6
        jr z,fcb_b
        inc c
fcb_b:  add hl,bc
        pop bc
        ret

; The next cell of the piece (fb_ci: row, column within fb_cc).
fb_cnext:
        ld a,(fb_ci + 1)
        inc a
        ld hl,fb_cc + 2
        cp (hl)
        jr z,fcn_c
        jr c,fcn_c
        ld a,(fb_cc)
        ld (fb_ci + 1),a
        ld hl,fb_ci
        inc (hl)
        ret
fcn_c:  ld (fb_ci + 1),a
        ret

; Phase FP_FILL: the next cells of the piece the cache does not hold (FB_BURST at most), from the
; tile cache into it (HMMM); then the background.
fb_fill:
        call fb_cix
        ld a,FB_BURST
        ld (fb_bn),a
ffl_lp: ld a,(fb_cc + 3)
        ld b,a
        ld a,(fb_ci)
        cp b
        jr z,ffl_c
        jr nc,ffl_done
ffl_c:  ld d,a
        ld a,(fb_ci + 1)
        ld e,a
        call fb_cbit
        and (hl)
        jr nz,ffl_held
        call fb_cbit                ; held from now (fb_inval forgets it when the tile changes)
        or (hl)
        ld (hl),a
        call fb_cnext
        ld a,d
        call tile_src               ; cmdbuf: SX, SY of the tile (keeps BC, DE)
        ld hl,(cmdbuf)
        ld (fb_cmd),hl
        ld hl,(cmdbuf + 2)
        ld (fb_cmd + 2),hl
        ld a,e                      ; DX: the cache's column
        sub (ix+4)
        and 3
        add a,a
        add a,a
        add a,a
        add a,a
        ld b,a
        ld a,(fb_cgi)
        rrca
        rrca                        ; * 64
        add a,b
        ld (fb_cmd + 4),a
        xor a
        ld (fb_cmd + 5),a
        ld a,d                      ; DY: its row, page 3
        sub (ix+5)
        and 3
        add a,a
        add a,a
        add a,a
        add a,a
        add a,FB_CY
        ld (fb_cmd + 6),a
        ld a,3
        ld (fb_cmd + 7),a
        ld hl,16
        ld (fb_cmd + 8),hl
        ld (fb_cmd + 10),hl
        ld a,FB_HMMM
        call fb_issue_now
        ld hl,fb_bn
        dec (hl)
        ret z
        jr ffl_lp
ffl_held:
        call fb_cnext
        jr ffl_lp
ffl_done:
        xor a
        ld (fb_ci),a
        ld a,FP_BG
        ld (fb_ph),a
        ; (falls through)

; Phase FP_BG: the piece's background from the cache into the scratch, in up to four parts where
; the cache wraps (HMMM); then the BOBs.
fb_bg:  call fb_cix
        ld a,(fb_ci)
        or a
        jr nz,fbg_p
        ld a,(fb_cc)                ; the wraps: the first cell after the piece's first with
        ld b,a                      ; column / row 0 in the cache
        sub (ix+4)
        and 3
        ld c,a
        ld a,b
        add a,4
        sub c
        call fb_c16
        ld (fb_xs),hl
        ld a,(fb_cc + 1)
        ld b,a
        sub (ix+5)
        and 3
        ld c,a
        ld a,b
        add a,4
        sub c
        call fb_c16
        ld (fb_ys),hl
        ld a,(fb_cc)                ; the parts: only the cache's columns of the piece
        call fb_c16
        ld de,(fb_px)
        call fb_cmp
        jr nc,fbg_l0
        ex de,hl
fbg_l0: ld (fb_lx0),hl
        ld a,(fb_cc + 2)
        inc a
        call fb_c16
        ld de,(fb_pe)
        call fb_cmp
        jr c,fbg_l1
        ex de,hl
fbg_l1: ld (fb_lx1),hl
fbg_p:  ld a,(fb_ci)
        cp 4
        jr nc,fbg_done
        inc a
        ld (fb_ci),a
        dec a
        call fb_part
        jr nc,fbg_p                 ; (empty)
        ld hl,(fb_r)                ; SX: the cache's column and the x within it
        call fb_cell
        sub (ix+4)
        and 3
        add a,a
        add a,a
        add a,a
        add a,a
        ld b,a
        ld a,(fb_r)
        and 15
        add a,b
        ld b,a
        ld a,(fb_cgi)
        rrca
        rrca
        add a,b
        ld (fb_cmd),a
        xor a
        ld (fb_cmd + 1),a
        ld hl,(fb_r + 2)            ; SY
        call fb_cell
        sub (ix+5)
        and 3
        add a,a
        add a,a
        add a,a
        add a,a
        ld b,a
        ld a,(fb_r + 2)
        and 15
        add a,b
        add a,FB_CY
        ld (fb_cmd + 2),a
        ld a,3
        ld (fb_cmd + 3),a
        call fb_dscr
        ld a,FB_HMMM
        jp fb_issue
fbg_done:
        ld a,(fb_slc)               ; the edge column the cache does not hold: from the tiles
        inc a
        jr z,fbg_bob
        dec a
        ld (fb_cc),a
        ld (fb_cc + 2),a
        ld (fb_ci + 1),a
        ld a,(fb_cc + 1)
        ld (fb_ci),a
        ld a,0xFF
        ld (fb_slc),a
        ld a,FP_TILE
        ld (fb_ph),a
        jp fb_tiles
fbg_bob:
        ld a,FP_BOB
        ld (fb_ph),a
        ld a,(fb_sn)
        ld (fb_ci),a
        jp fb_bobs

; A = a part (bit 0: right of fb_xs, bit 1: below fb_ys) -> fb_r = that part of the piece within
; the columns fb_lx0..fb_lx1, C when it is not empty.
fb_part:
        push af
        rrca
        jr c,fpa_r
        ld hl,(fb_px)               ; left: [x0, min(xs, x1))
        ld (fb_r),hl
        ld hl,(fb_xs)
        ld de,(fb_pe)
        call fb_cmp
        jr c,fpa_l
        ex de,hl
fpa_l:  ld (fb_r + 4),hl
        jr fpa_y
fpa_r:  ld hl,(fb_xs)               ; right: [xs, x1)
        ld (fb_r),hl
        ld hl,(fb_pe)
        ld (fb_r + 4),hl
fpa_y:  pop af
        and 2
        jr nz,fpa_b
        ld hl,(fb_px + 2)
        ld (fb_r + 2),hl
        ld hl,(fb_ys)
        ld de,(fb_pe + 2)
        call fb_cmp
        jr c,fpa_t
        ex de,hl
fpa_t:  ld (fb_r + 6),hl
        jr fpa_e
fpa_b:  ld hl,(fb_ys)
        ld (fb_r + 2),hl
        ld hl,(fb_pe + 2)
        ld (fb_r + 6),hl
fpa_e:  ld hl,(fb_lx0)
        ld de,(fb_r)
        call fb_cmp
        jr c,fpa_c0
        ld (fb_r),hl
fpa_c0: ld hl,(fb_lx1)
        ld de,(fb_r + 4)
        call fb_cmp
        jr nc,fpa_c1
        ld (fb_r + 4),hl
fpa_c1: ld hl,(fb_r)
        ld de,(fb_r + 4)
        call fb_cmp
        ret nc
        ld hl,(fb_r + 2)
        ld de,(fb_r + 6)
        jp fb_cmp

; fb_cmd's destination: fb_r in the scratch (relative to the piece), and its size.
fb_dscr:
        ld hl,(fb_r)
        ld de,(fb_px)
        or a
        sbc hl,de
        ld a,(fb_sbx)
        add a,l
        ld (fb_cmd + 4),a
        xor a
        ld (fb_cmd + 5),a
        ld hl,(fb_r + 2)
        ld de,(fb_px + 2)
        or a
        sbc hl,de
        ld a,l
        add a,FB_CY
        ld (fb_cmd + 6),a
        ld a,3
        ld (fb_cmd + 7),a
fb_nxy: ld hl,(fb_r + 4)
        ld de,(fb_r)
        or a
        sbc hl,de
        ld (fb_cmd + 8),hl
        ld hl,(fb_r + 6)
        ld de,(fb_r + 2)
        or a
        sbc hl,de
        ld (fb_cmd + 10),hl
        ret

; fb_r = fb_r inside the piece -> C when something is left.
fb_rpiece:
        ld hl,(fb_px)
        ld de,(fb_r)
        call fb_cmp
        jr c,frp_1
        ld (fb_r),hl
frp_1:  ld hl,(fb_pe)
        ld de,(fb_r + 4)
        call fb_cmp
        jr nc,frp_2
        ld (fb_r + 4),hl
frp_2:  ld hl,(fb_px + 2)
        ld de,(fb_r + 2)
        call fb_cmp
        jr c,frp_3
        ld (fb_r + 2),hl
frp_3:  ld hl,(fb_pe + 2)
        ld de,(fb_r + 6)
        call fb_cmp
        jr nc,frp_4
        ld (fb_r + 6),hl
frp_4:  ld hl,(fb_r)
        ld de,(fb_r + 4)
        call fb_cmp
        ret nc
        ld hl,(fb_r + 2)
        ld de,(fb_r + 6)
        jp fb_cmp

; Phase FP_TILE: the next cells of the piece (FB_BURST at most) from the tile cache into the
; scratch (HMMM: the part of each cell inside the piece); then the BOBs.
fb_tiles:
        ld a,FB_BURST
        ld (fb_bn),a
ftl_lp: ld a,(fb_cc + 3)
        ld b,a
        ld a,(fb_ci)
        cp b
        jr z,ftl_go
        jr c,ftl_go
        ld a,FP_BOB
        ld (fb_ph),a
        ld a,(fb_sn)
        ld (fb_ci),a
        jp fb_bobs
ftl_go: ld (fb_rw),a
        ld a,(fb_ci + 1)
        ld (fb_cl),a
        call fb_cnext
        ld a,(fb_rw)                ; the cell inside the piece
        call fb_c16
        ld (fb_r + 2),hl
        ld de,16
        add hl,de
        ld (fb_r + 6),hl
        ld a,(fb_cl)
        call fb_c16
        ld (fb_r),hl
        ld de,16
        add hl,de
        ld (fb_r + 4),hl
        call fb_rpiece
        ld a,(fb_cur)
        and 1
        ld (vat_pg),a               ; (level 2's vat cells: the looks of the item's page)
        ld a,(fb_cl)
        ld e,a
        ld a,(fb_rw)
        call tile_src               ; cmdbuf: SX, SY of the tile
        ld a,(fb_r)
        and 15
        ld b,a
        ld a,(cmdbuf)
        add a,b
        ld (fb_cmd),a
        xor a
        ld (fb_cmd + 1),a
        ld a,(fb_r + 2)
        and 15
        ld b,a
        ld a,(cmdbuf + 2)
        add a,b
        ld (fb_cmd + 2),a
        ld a,(cmdbuf + 3)
        ld (fb_cmd + 3),a
        call fb_dscr
        ld a,FB_HMMM
        call fb_issue_now
        ld hl,fb_bn
        dec (hl)
        ret z
        jp ftl_lp

; A = command: fb_cmd's CLR, ARG and CMD set, the command ready (fb_rdy 1): fb_work starts it when
; the VDP is idle, else the interrupts (isr.asm ifg_rdy) or the next call do.
fb_issue:
        ld (fb_cmd + 14),a
        xor a
        ld (fb_cmd + 12),a
        ld (fb_cmd + 13),a
        inc a
        ld (fb_rdy),a
        ret

; A = command (a burst's 16 x 16 copy): as fb_issue, but started now, once the one before is done
; (vdp_cmd; both short: the wait is about as long as the set-up of the next); fb_shc notes that
; the command running is a short one of ours (fb_go waits for it rather than leave the next one
; to the interrupts).
fb_issue_now:
        ld (fb_cmd + 14),a
        xor a
        ld (fb_cmd + 12),a
        ld (fb_cmd + 13),a
        inc a
        ld (fb_shc),a
        ld hl,fb_cmd
        jp vdp_cmd

; The command ready (fb_rdy 1) starts now, the VDP idle (a short copy of ours still running is
; waited for: fb_shc) -> Z; NZ when a long command runs (the interrupts or the next call start
; it) or the interrupts started it just before (fb_rdy 2). cmd_lock keeps the interrupts off the
; command registers meanwhile.
fb_go:  ld a,1
        ld (cmd_lock),a
        ld a,(fb_rdy)
        dec a
        jr nz,fgo_no
        ld a,(fb_shc)
        or a
        jr z,fgo_b
        call vdp_wait
        jr fgo_w
fgo_b:  call vdp_busy
        jr nz,fgo_no
fgo_w:  di
        ld a,32
        out (VDP_CTRL),a
        ld a,0x80+17
        out (VDP_CTRL),a
        ei
        ld hl,fb_cmd
        ld bc,15*256 + VDP_IND
        otir                        ; R#32-R#46: it starts
        xor a
        ld (fb_rdy),a
        ld (fb_shc),a
        ld (cmd_lock),a
        ret
fgo_no: xor a
        ld (cmd_lock),a
        inc a
        ret

; Phase FP_BOB: the next BOB of the page's list (fb_sn) over the piece into the scratch (LMMM with
; TIMP: the part inside the piece), from the last in the list (the game drew it first); then the
; copy. A frame of the dynamic slot (FIELD_DYN0..FIELD_DYN1: the explosion, the smoke) is made
; resident there first (fb_dyn); its lines are strips of DYN_H side by side: an LMMM a strip, one
; a call (fb_dsn).
fb_bobs:
        ld a,(fb_dsn)
        or a
        jp nz,fbb_ds                ; (the next strip of a dynamic frame)
        ld a,(fb_ci)
        or a
        jr nz,fbb_1
        ld a,(fb_stg)               ; (staged pieces: the next one composed before any copy)
        or a
        jr z,fbb_cp
        ld a,(fb_scp)
        or a
        jp z,fst_done
fbb_cp: ld a,FP_COPY
        ld (fb_ph),a
        jp fb_copy
fbb_1:  dec a
        ld (fb_ci),a
        call fbb_ix
        call fb_rect
        call fb_rpiece
        jr nc,fb_bobs               ; (none of it there)
        ld a,(ix+0)
        ld hl,fb_fdyn0              ; (the level's FIELD_DYN0, FIELD_DYN1)
        cp (hl)
        jr c,fbb_at
        inc hl
        cp (hl)
        jr c,fbb_dy
fbb_at: call fb_tab                 ; source: the atlas + (part - BOB's place)
        ld a,(hl)                   ; atlas x
        inc hl
        ld c,(hl)                   ; atlas y
        ld hl,(fb_r)
        ld e,(ix+1)
        ld d,(ix+2)
        or a
        sbc hl,de
        add a,l
        ld (fb_cmd),a               ; SX
        xor a
        ld (fb_cmd + 1),a
        ld hl,(fb_r + 2)
        ld e,(ix+3)
        ld d,(ix+4)
        or a
        sbc hl,de
        ld a,l
        add a,c
fbb_sy: add a,FIELD_Y0
        ld (fb_cmd + 2),a           ; SY: the atlas, page 3
        ld a,3
fbb_pg: ld (fb_cmd + 3),a
        call fb_dscr
        ld a,FB_LMMMT
        jp fb_issue

; (fb_bobs) A dynamic frame, IX its entry, fb_r its part inside the piece: the frame resident,
; then the part's lines fb_ds..fb_dse strip by strip.
fbb_df: ld hl,fb_ci                 ; (the frame must be loaded while the VDP is busy: this BOB
        inc (hl)                    ;  again at the next call, nothing prepared now)
        ret
fbb_dy: call fb_dyn
        jr c,fbb_df
        ld hl,fb_r
        ld de,fb_dpr
        ld bc,8
        ldir                        ; (the part)
        ld e,(ix+3)
        ld d,(ix+4)                 ; the frame's top
        ld hl,(fb_r + 2)
        or a
        sbc hl,de
        ld a,l
        ld (fb_ds),a                ; the part's first line in the frame,
        ld hl,(fb_r + 6)
        or a
        sbc hl,de
        ld a,l
        ld (fb_dse),a               ;   past its last
        ld a,1
        ld (fb_dsn),a
        jr fbb_d1
fbb_ds: call fbb_ix
fbb_d1: ld a,(fb_ds)                ; B = its strip, C = its line there
        ld b,0
fbd_s:  cp DYN_H
        jr c,fbd_l
        sub DYN_H
        inc b
        jr fbd_s
fbd_l:  ld c,a
        ld a,DYN_H                  ; E = its lines in the strip: to the strip's end or the part's
        sub c
        ld e,a
        ld a,(fb_dse)
        ld hl,fb_ds
        sub (hl)
        cp e
        jr nc,fbd_n
        ld e,a
fbd_n:  ld hl,(fb_dpr)              ; fb_r = the part's lines there
        ld (fb_r),hl
        ld hl,(fb_dpr + 4)
        ld (fb_r + 4),hl
        push de
        ld a,(fb_ds)
        ld e,a
        ld d,0
        ld l,(ix+3)
        ld h,(ix+4)
        add hl,de
        ld (fb_r + 2),hl
        pop de
        push de
        ld d,0
        add hl,de
        ld (fb_r + 6),hl
        pop de
        ld a,(fb_ds)                ; the next strip's first line (the part's end: done)
        add a,e
        ld (fb_ds),a
        ld hl,fb_dse
        cp (hl)
        jr c,fbd_m
        xor a
        ld (fb_dsn),a
fbd_m:  ld a,(ix+0)                 ; source: atlas x + strip * width + (part x - BOB x),
        call fb_tab                 ; DYN_Y + its line in the strip
        ld a,(hl)
        inc hl
        inc hl
        ld d,(hl)                   ; (width)
        inc b
        jr fbd_x
fbd_w:  add a,d
fbd_x:  djnz fbd_w
        ld hl,(fb_r)
        ld e,(ix+1)
        ld d,(ix+2)
        or a
        sbc hl,de
        add a,l
        ld (fb_cmd),a               ; SX
        xor a
        ld (fb_cmd + 1),a
        ld a,(lv_dyn)               ; SY: the level's dynamic slot, its page
        add a,c
        ld (fb_cmd + 2),a
        ld a,(lv_dynp)
        jp fbb_pg

; IX = fb_snap's entry fb_ci (7 bytes each). Keeps BC.
fbb_ix: ld a,(fb_ci)
        ld e,a
        add a,a
        add a,a
        add a,a
        sub e                       ; * 7
        ld e,a
        ld d,0
        ld ix,fb_snap
        add ix,de
        ret

; A = a dynamic frame (FIELD_DYN0..): its pixels (field_dyn: a frame of dyn_tab) resident in the
; dynamic slot (dyn_res), else copied there from the ROM now (bank FIELD_DYN_BANK + its bank at
; 8000h, line by line into strips of DYN_H side by side from its atlas x; the VDP idle first: no
; command may read the slot; C when it is busy and nothing was done) and the frames whose place
; it takes forgotten. Keeps IX.
fb_dyn: push ix
        ld c,a                      ; (the frame)
        ld hl,fb_fdyn0
        sub (hl)                    ; (the level's FIELD_DYN0)
        ld e,a
        ld d,0
        ld hl,field_dyn
        add hl,de
        ld l,(hl)
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl                   ; * 8
        ld de,dyn_tab
        add hl,de
        push hl
        pop ix                      ; IX = its dyn_tab entry
        ld de,(dyn_res)
        ld a,(ix+0)
        and e
        jp nz,fdy_x
        ld a,(ix+1)
        and d
        jp nz,fdy_x                 ; (resident)
        call vdp_busy
        jp nz,fdy_bz                ; (a command runs: later)
        ld a,(ix+2)
        cpl
        and e
        or (ix+0)
        ld e,a
        ld a,(ix+3)
        cpl
        and d
        or (ix+1)
        ld d,a
        ld (dyn_res),de
fdy_ld:                             ; (a copy)
        ld a,c
        call fb_tab                 ; its atlas x, width, height
        ld a,(hl)
        srl a
        ld e,a                      ; E = the strip's x / 2
        inc hl
        inc hl
        ld a,(hl)
        srl a
        ld c,a                      ; C = bytes a line
        inc hl
        ld b,(hl)                   ; B = lines
        ld a,b                      ; D = its strips, fb_dse = the last one's lines
        ld d,0
fdy_s:  inc d
        sub DYN_H
        jr z,fdy_sx
        jr nc,fdy_s
        add a,DYN_H
        jr fdy_sl
fdy_sx: ld a,DYN_H
fdy_sl: ld (fb_dse),a
        ld a,b                      ; B = the slot's lines it takes (DYN_H, or its own when fewer)
        cp DYN_H
        jr c,fdy_k
        ld a,DYN_H
fdy_k:  ld b,a
        ld a,(act_8000)
        push af
        ld a,(ix+4)
        add a,FIELD_DYN_BANK
        call bank_8000
        ld l,(ix+5)
        ld h,(ix+6)                 ; HL = its pixels: a line of the slot after another, as VRAM
        xor a                       ; holds them (its strips' lines side by side)
        ld (fb_ds),a                ; (the slot's line)
fdy_ln: push bc
        push de
        push hl
        ld hl,lv_dyn                ; VRAM 10000h + (lv_dynp & 1) * 8000h + (lv_dyn (DYN_Y) + line)
        ld a,(fb_ds)                ;   * 128 + E: the level's dynamic slot (page 3 or 2)
        add a,(hl)
        ld l,a
        srl a
        ld h,a
        ld a,(lv_dynp)
        rrca
        and 0x80
        or h
        ld h,a
        ld a,l
        rrca
        and 0x80
        add a,e
        ld l,a
        ld e,1
        call vram_write
        pop hl
        pop de
        pop bc
        push bc
        ld a,(fb_ds)                ; its bytes: C a strip that has the line (all D, or D - 1 past
        push hl                     ; the last one's lines)
        ld hl,fb_dse
        cp (hl)
        pop hl
        ld b,d
        jr c,fdy_b
        dec b
fdy_b:  xor a
fdy_by: add a,c
        djnz fdy_by
        ld b,a
        ld c,VDP_DATA
        otir
        pop bc
        ld a,(fb_ds)
        inc a
        ld (fb_ds),a
        djnz fdy_ln
        call vram_done
        pop af
        call bank_8000
fdy_x:  pop ix
        or a                        ; (NC)
        ret
fdy_bz: pop ix
        scf
        ret

; Phase FP_COPY: the next part of the piece from the scratch onto its page (HMMM; the V9958's ring
; in parts that do not cross its x 256 or its y 256, a V9938 page in parts that do not cross y
; 256), once it is still kept there (else the whole item again); on the page shown all its parts
; together (fb_cmd, then fb_cmd2 ...: up to four on the V9958, its ring crossed at x 256 and at
; y 256), which wait for the blank (FP_WAIT). Then the next piece, or the next item.
fb_copy:
        ld a,(fb_cpi)
        cp 4
        jp nc,fcp_done
        call fb_inwin
        jp nc,fcp_redo
        ld a,(fb_cpi)
        or a
        jr nz,fcp_part
        ld hl,(fb_px)               ; the parts: right of the next x 256 (V9958), below y 256
        ld l,0
        inc h
        ld a,(fb_eng)
        or a
        jr z,fcp_xs
        ld hl,0x7FFF
fcp_xs: ld (fb_xs),hl
        ld hl,(fb_px + 2)
        ld l,0
        inc h
        ld (fb_ys),hl
        ld hl,0                     ; (all its columns)
        ld (fb_lx0),hl
        ld hl,0x7FFF
        ld (fb_lx1),hl
fcp_part:
        ld a,(fb_cpi)
        cp 4
        jp nc,fcp_done
        inc a
        ld (fb_cpi),a
        dec a
        call fb_part
        jr nc,fcp_part
        ld hl,(fb_r + 2)            ; (its top, fb_mayq)
        ld (fb_cpy),hl
        ld hl,fb_cmd
        call fb_pcmd
        call fb_shown
        jr z,fcp_wait
        ld a,1                      ; (the hidden page: no beam to wait for; ready, as fb_issue)
        ld (fb_rdy),a
        ret
fcp_wait:
        xor a                       ; the piece's other parts: right after this one, each when the
        ld (fb_c2),a                ; one before is done (fb_cmd2 ..., the split interrupt), so that
        ld (fb_cn),a                ; all show from the same frame (until 2026-10-28 two at a time:
        ld hl,fb_cmd2               ; a piece across the ring's x 256 and y 256, level 2's trolleys at
        ld (fb_cp),hl               ; y 508, showed its top lines a picture early)
fcw_nx: ld a,(fb_cpi)
        cp 4
        jr nc,fcw_one
        inc a
        ld (fb_cpi),a
        dec a
        call fb_part
        jr nc,fcw_nx
        ld a,(fb_cn)                ; (its command: fb_cmd2 + 15 x the parts before it)
        ld e,a
        add a,a
        add a,a
        add a,a
        add a,a
        sub e
        ld e,a
        ld d,0
        ld hl,fb_cmd2
        add hl,de
        call fb_pcmd
        ld hl,fb_cn
        inc (hl)
        ld a,1
        ld (fb_c2),a
        jr fcw_nx
fcw_one:
        call fb_fits                ; (the VBLANK interrupt may start it too when it keeps ahead of
        ld a,0                      ; the beam from there, not a pair)
        jr nz,fcw_v
        ld a,(fb_c2)
        or a
        ld a,0
        jr nz,fcw_v
        inc a
fcw_v:  ld (fb_vok),a
        call fb_lastp               ; (the split interrupt may start it from now: fb_cq = 1, 3 when
        ld a,1                      ; it is the item's last part)
        jr nz,fcw_n
        ld a,3
fcw_n:  ld (fb_cq),a
        ld a,FP_WAIT
        ld (fb_ph),a
        ; (falls through)

; Phase FP_WAIT: the part prepared for the page shown (with the others, fb_c2), started by the
; split interrupt (fb_cq 2, 4 for the item's last part: isr.asm) or here when what is left of the
; blank is enough (fb_mayq); then the next piece (the next call, the VDP idle again).
fb_wait:
        ld a,(fb_cq)
        and 1
        jr z,fwt_done
        call fb_mayq
        ret nz
        jp fb_qstart
fwt_done:
        ld a,(fb_c2)                ; (the other parts the interrupts could not start: now)
        cp 3
        ret z                       ; (3: the VBLANK interrupt starts them after its list, isr.asm)
        dec a
        jr nz,fwt_c
        ld (fb_c2),a
        ld hl,(fb_cp)
fwt_ch: call vdp_cmd                ; (HL: past its 15 bytes, the next part's)
        ld a,(fb_cn)
        dec a
        ld (fb_cn),a
        jr nz,fwt_ch
        ret
fwt_c:  ld a,(fb_cq)                ; (it ran: the VDP is idle again; the last part's 4 stays
        cp 4                        ; until the item is done: fb_pend)
        jr z,fwt_4
        xor a
        ld (fb_cq),a
fwt_4:  ld a,FP_COPY
        ld (fb_ph),a
        jp fb_copy

; HL = 15 bytes: the copy of fb_r from the scratch onto fb_cur's page (HMMM; the V9958's ring: x
; 256 and up on page 1; a V9938 page: x less its first column's).
fb_pcmd:
        push hl
        pop iy
        ld hl,(fb_r)                ; SX, SY: the scratch
        ld de,(fb_px)
        or a
        sbc hl,de
        ld a,(fb_sbx)
        add a,l
        ld (iy+0),a
        ld (iy+1),0
        ld hl,(fb_r + 2)
        ld de,(fb_px + 2)
        or a
        sbc hl,de
        ld a,l
        add a,FB_CY
        ld (iy+2),a
        ld (iy+3),3
        ld hl,(fb_r)                ; DX: the page's x
        ld a,(fb_eng)
        or a
        jr nz,fpc_d38
        ld (iy+4),l
        ld a,h
        and 1
        jr fpc_dy
fpc_d38:
        ld a,(fb_cur)
        call fb_page_c0
        call fb_c16
        ex de,hl
        ld hl,(fb_r)
        or a
        sbc hl,de
        ld (iy+4),l
        ld a,(fb_cur)
        and 1
fpc_dy: ld (iy+7),a                 ; DY: the ring line, the page
        ld (iy+5),0
        ld a,(fb_r + 2)
        ld (iy+6),a
        ld hl,(fb_r + 4)            ; NX, NY
        ld de,(fb_r)
        or a
        sbc hl,de
        ld (iy+8),l
        ld (iy+9),h
        ld hl,(fb_r + 6)
        ld de,(fb_r + 2)
        or a
        sbc hl,de
        ld (iy+10),l
        ld (iy+11),h
        ld (iy+12),0
        ld (iy+13),0
        ld (iy+14),FB_HMMM
        ret

; -> Z when the copy's part just prepared is the item's last: the parts after it are empty and no
; piece follows.
fb_lastp:
        ld a,(fb_cpi)
flp_lp: cp 4
        jr nc,flp_pc
        ld b,a
        push bc
        call fb_part
        pop bc
        jr c,flp_no
        ld a,b
        inc a
        jr flp_lp
flp_pc: ld hl,(fb_pe)
        ld de,(fb_cur + 7)
        call fb_cmp
        jr c,flp_no
        ld hl,(fb_pe + 2)
        ld de,(fb_cur + 9)
        call fb_cmp
        jr c,flp_no
        xor a
        ret
flp_no: or 1
        ret

; The piece done: the next staged piece's copy, else the next piece (to the right, else the next
; band), or the item is done.
fcp_done:
        ld a,(fb_stg)
        or a
        jr z,fcp_next
        ld hl,fb_spk
        inc (hl)
        cp (hl)
        jp nz,fst_load
        xor a
        ld (fb_stg),a
        ld (fb_ph),a
        ret
fcp_next:
        ld hl,(fb_pe)
        ld (fb_px),hl
        ld de,(fb_cur + 7)
        call fb_cmp
        jr c,fcn_p
        ld hl,(fb_cur + 3)
        ld (fb_px),hl
        ld hl,(fb_pe + 2)
        ld (fb_px + 2),hl
        ld de,(fb_cur + 9)
        call fb_cmp
        jr c,fcn_p
        xor a
        ld (fb_ph),a
        ret
fcn_p:  call fb_piece               ; (its first command in this step)
        jp fwk_ph

; The page's window moved: the whole item again.
fcp_redo:
        ld hl,fb_cur + 3
        ld de,fb_r
        ld bc,8
        ldir
        ld hl,(fb_cur + 1)
        ld (fb_own),hl
        ld a,(fb_cur)
        call fb_queue
        xor a
        ld (fb_ph),a
        ld (fb_cq),a
        ld (fb_stg),a
        ret

; The item fb_cur (clipped) at its start: on the page shown, one of 2 to 4 pieces of 64 x 64 is
; staged (fb_stg): each piece composed in a 64 x 64 of its own (the scratch, then the caches'
; places, whose tiles are forgotten: such an item takes its background from the tiles), then all
; copied in a row, the pieces after the first right away; until 2026-10-21 each piece was copied
; when composed and the page showed the item half old, half new for as many pictures as the rest
; took (a smoke next to a hostage: 7).
fb_stage:
        xor a
        ld (fb_stg),a
        ld (fb_spk),a
        ld (fb_scp),a
        ld a,FB_SX
        ld (fb_sbx),a
        call fb_shown
        ret nz
        ld hl,(fb_cur + 7)
        ld de,(fb_cur + 3)
        or a
        sbc hl,de
        call fst_n
        ld c,a                      ; pieces across
        ld hl,(fb_cur + 9)
        ld de,(fb_cur + 5)
        or a
        sbc hl,de
        call fst_n
        ld b,a                      ; down
        xor a
fsg_m:  add a,c
        djnz fsg_m
        cp 2
        ret c                       ; (one: as always)
        cp 5
        ret nc                      ; (more than four: one at a time)
        ld (fb_stg),a
        dec a
        ld b,a                      ; the caches lent: 0 .. pieces - 2
        ld hl,fb_cache
        ld de,FB_CSZ
fsg_c:  ld (hl),0xFF                ; (owner FFFFh: free)
        inc hl
        ld (hl),0xFF
        dec hl
        add hl,de
        djnz fsg_c
        ret

; HL = a length (1 or more) -> A = the 64 px pieces it takes.
fst_n:  ld de,63
        add hl,de
        add hl,hl
        add hl,hl
        ld a,h
        ret

; (fb_bobs) A staged piece composed: its place noted, then the next piece in a cache's place, or
; once all are, their copies from the first.
fst_done:
        call fst_slot
        ex de,hl
        ld hl,fb_px
        ld bc,4
        ldir
        ld hl,fb_pe
        ld bc,4
        ldir
        ld hl,fb_spk
        inc (hl)
        ld a,(fb_stg)
        cp (hl)
        jr z,fst_cp
        ld a,(hl)
        dec a
        rrca
        rrca                        ; (the cache's x: * 64)
        ld (fb_sbx),a
        jp fcp_next
fst_cp: ld a,1
        ld (fb_scp),a
        xor a
        ld (fb_spk),a
        ; (falls through)
; The staged piece fb_spk's place back (fb_px, fb_pe, fb_sbx), then its copy.
fst_load:
        call fst_slot
        ld de,fb_px
        ld bc,4
        ldir
        ld de,fb_pe
        ld bc,4
        ldir
        ld a,(fb_spk)
        or a
        ld a,FB_SX
        jr z,fsl_x
        ld a,(fb_spk)
        dec a
        rrca
        rrca
fsl_x:  ld (fb_sbx),a
        xor a
        ld (fb_cpi),a
        ld (fb_c2),a
        ld a,FP_COPY
        ld (fb_ph),a
        jp fb_copy

; -> HL = the staged piece fb_spk's place (fb_spx + 8 * fb_spk). Keeps BC.
fst_slot:
        ld a,(fb_spk)
        add a,a
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,fb_spx
        add hl,de
        ret

; -> Z when the copy prepared is a staged piece's after the first (it starts right away). Keeps BC,
; DE, HL.
fst_more:
        ld a,(fb_scp)
        or a
        jr z,fsm_n
        ld a,(fb_spk)
        or a
        jr z,fsm_n
        xor a
        ret
fsm_n:  or 1
        ret

; -> C when the piece is still inside its page's window.
fb_inwin:
        call fb_window              ; HL = its first map x, DE = past its last (C: none)
        ccf
        ret nc
        push de
        ld de,(fb_px)
        call fb_cmp                 ; window x0 <= piece x0 ?
        pop de
        jr c,fiw_1
        jr nz,fiw_no
fiw_1:  ld hl,(fb_pe)
        call fb_cmp                 ; piece x1 <= window x1 ?
        jr c,fiw_2
        jr nz,fiw_no
fiw_2:  ld a,(prev_cy)              ; inside the kept rows
        call fb_c16m
        ld de,(fb_px + 2)
        ex de,hl
        call fb_cmp
        jr c,fiw_no
        ld a,(prev_cy)
        add a,VIEW_ROWS - 1
        call fb_c16
        ex de,hl
        ld hl,(fb_pe + 2)
        call fb_cmp
        ret c
        jr z,fiw_yes
fiw_no: or a
        ret
fiw_yes:
        scf
        ret

; -> Z when the main loop may start the prepared copy now: its picture published (its stamp not
; fb_tick) with its sprites uploaded (pk_state not 1), between the HUD split and the VBLANK
; (split_armed = 0) and short enough to keep ahead of the beam even when started just before the
; VBLANK (NY * (NX * 13 / 16 - 16) <= 778 + 16 * its top line on the screen: in 4 us units,
; 6.3 us a byte, 63.5 us a line, 49 lines from the VBLANK to the play area's first line).
fb_mayq:
        ld a,(fb_c2)                ; (a pair: the split interrupt's)
        or a
        jr nz,fmq_no
        ld a,(fb_tick)
        ld hl,fb_cur + 11
        cp (hl)
        jr z,fmq_no
        ld a,(pk_state)
        cp 1
        jr z,fmq_no                 ; (its sprites' uploads still running: isr.asm)
        call fst_more
        jr z,fmq_ok                 ; (a staged piece after the first: right away)
        ld a,(split_armed)
        or a
        ret nz
        ; (falls through)

; -> Z when the prepared copy keeps ahead of the beam even when started at the VBLANK.
fb_fits:
        ld a,(fb_cmd + 8)
        ld l,a
        ld h,0
        ld d,h
        ld e,l
        add hl,hl
        add hl,hl
        push hl
        add hl,hl
        pop bc
        add hl,bc
        add hl,de                   ; NX * 13
        ld a,l
        srl h
        rra
        srl h
        rra
        srl h
        rra
        srl h
        rra
        sub 16
        jr c,fmq_ok                 ; (as fast as the beam)
        jr z,fmq_ok
        ld b,a
        ld a,(fb_cmd + 10)
        ld e,a
        ld d,0
        ld hl,0
fmq_m:  add hl,de
        djnz fmq_m
        push hl
        ld hl,(fb_cpy)              ; its top on the screen (0 or more)
        ld de,(cam_y)
        or a
        sbc hl,de
        jr nc,fmq_y
        ld hl,0
fmq_y:  add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,778
        add hl,de
        ex de,hl
        pop hl
        or a
        sbc hl,de
        jr nc,fmq_no                ; (too long: the split interrupt starts it)
fmq_ok: xor a
        ret
fmq_no: or 1
        ret

; The prepared copy started now when it is still the time, the split interrupt did not take it
; (fb_cq 1 or 3, then 2 or 4) and the VDP is idle (a command this call started may still run) ->
; Z when started. cmd_lock keeps the interrupt off the command registers.
fb_qstart:
        ld a,1
        ld (cmd_lock),a
        ld a,(fb_cq)
        and 1
        jr z,fqs_no
        call vdp_busy
        jr nz,fqs_no
        di
        ld a,32
        out (VDP_CTRL),a
        ld a,0x80+17
        out (VDP_CTRL),a
        ei
        ld hl,fb_cmd
        ld bc,14*256 + VDP_IND
        otir                        ; R#32-R#45
        ld b,(hl)
        di
        ld a,(split_armed)
        or a
        jr z,fqs_go
        call fst_more
        jr nz,fqs_ei
fqs_go: ld a,b
        out (VDP_CTRL),a
        ld a,0x80+46
        out (VDP_CTRL),a            ; R#46: it starts
        ld a,(fb_cq)
        inc a
        ld (fb_cq),a
        ei
        xor a
        ld (cmd_lock),a
        ret
fqs_ei: ei
fqs_no: xor a
        ld (cmd_lock),a
        inc a
        ret

; A = a V9938 page -> A = its first column (displayed: s38_vis_c0; the old one until a flip is on
; screen: s38_old_c0; else the one being built).
fb_page_c0:
        ld hl,s38_vis_page
        cp (hl)
        ld a,(s38_vis_c0)
        ret z
        ld a,(s38_flip_wait)
        or a
        ld a,(s38_old_c0)
        ret nz
        ld a,(s38_back_c0)
        ret

; -> Z when fb_cur's page is on screen (the V9958's ring always; a V9938 page displayed, or the
; old one until a flip is on screen). Keeps HL.
fb_shown:
        ld a,(fb_eng)
        or a
        ret z
        push hl
        ld a,(fb_cur)
        ld hl,s38_vis_page
        cp (hl)
        jr z,fsh_x
        ld a,(s38_flip_wait)
        or a
        jr z,fsh_n
        xor a
        jr fsh_x
fsh_n:  or 1
fsh_x:  pop hl
        ret

; V9938, nothing queued: once the page being built has its copy, where it may show something else
; than the BOBs wanted (fb_bb: the displayed page's changes since the build began, the cells drawn
; on it meeting a BOB: fb_bbcell) is composed on it, then a marker lets it be shown (fb_bsync) ->
; Z when queued.
fb_sync:
        ld a,(fb_eng)
        or a
        jp z,fs_no
        ld a,(s38_back_c0)
        cp 0xFF
        jp z,fs_no
        ld hl,fb_bsync
        cp (hl)
        jp z,fs_no
        ld a,(s38_phase)
        or a
        jp z,fs_no
        ld a,(s38_i)
        cp VIEW_ROWS
        jp nz,fs_no
        ld a,(s38_vis_page)
        xor 1
        ld (fb_dpg),a
        ld hl,0xFFFF                ; (no owner)
        ld (fb_own),hl
        ld a,(fb_bbn)               ; where the copy may have brought something else
        or a
        jr z,fs_m
        ld b,a
        ld hl,fb_bb
fs_bl:  push bc
        ld de,fb_r
        ld bc,8
        ldir
        push hl
        ld a,(fb_dpg)
        call fb_queue
        pop hl
        pop bc
        djnz fs_bl
fs_m:   ld a,(fb_dpg)               ; its list: fb_want, its box
        call fb_dnp
        ex de,hl
        ld hl,fb_wn
        call fb_lsz
        ldir
        ld a,(fb_dpg)
        call fbx_set
        ld a,(fb_qn)                ; the marker (its build target), last
        cp FB_QMAX
        jr nc,fs_full
        ld a,(s38_back_c0)
        ld (fb_r),a
        ld a,(fb_dpg)
        or 0x80
        ld c,a
        call fq_new
        xor a
        ret
fs_full:
        xor a                       ; (no room for the marker: the next call adds it)
        ret
fs_no:  or 1
        ret

; (tiles.asm fb_mark38) D = row, E = column of a tile drawn on the V9938's page being built before
; it holds the BOBs (its new column, a new row, a cell the game changed): where it meets a BOB
; wanted it goes into fb_bb, which the sync composes. The box around them first: a cell outside it
; (most) meets none.
fb_bbcell:
        ld a,(fb_wn)
        or a
        ret z
        ld b,a
        ld a,d
        call fb_c16
        ld (fb_r + 2),hl
        ld a,e
        call fb_c16
        ld (fb_r),hl
        ld de,16
        add hl,de
        ld (fb_r + 4),hl
        ld hl,(fb_r + 2)
        add hl,de
        ld (fb_r + 6),hl
        ld ix,fb_wbx
        call fb_meet
        ret nc
        ld hl,fb_r                  ; (fb_rect takes fb_r: the cell into fb_tr)
        ld de,fb_tr
        push bc
        ld bc,8
        ldir
        pop bc
        ld ix,fb_want
fbc_lp: push bc
        call fb_rect
        push ix
        ld ix,fb_tr
        call fb_meet
        pop ix
        pop bc
        jr c,fbc_yes
        ld de,FB_ENT
        add ix,de
        djnz fbc_lp
        ret
fbc_yes:
        ld hl,fb_tr
        ld de,fb_r
        ld bc,8
        ldir
        jp fb_bbadd

; (tiles.asm fb_redraw, fb_meetq) D = row, E = column of a cell drawn (or about to be) on page
; fb_cqp: when it meets the item being composed, a queued item of that page or a BOB of its list,
; it is queued as an item (fb_cqr = 1: composed here with the BOBs over it). Keeps DE.
fb_cellq:
        push de
        xor a
        ld (fb_cqr),a
        ld a,(fb_cqp)
        ld c,a
        ld a,d
        call fb_c16
        ld (fb_r + 2),hl
        ld de,16
        add hl,de
        ld (fb_r + 6),hl
        pop de
        push de
        ld a,e
        call fb_c16
        ld (fb_r),hl
        ld de,16
        add hl,de
        ld (fb_r + 4),hl
        ld a,(fb_ph)                ; the item being composed
        or a
        jr z,fcq_q
        ld a,(fb_cur)
        cp c
        jr nz,fcq_q
        ld ix,fb_cur + 3
        call fb_meet
        jr c,fcq_yes
fcq_q:  ld a,(fb_qn)                ; a queued item of that page
        or a
        jr z,fcq_l
        ld b,a
        ld ix,fb_q
fcq_ql: ld a,(ix+0)
        cp c
        jr nz,fcq_qn
        inc ix
        inc ix
        inc ix
        call fb_meet
        jr c,fcq_yes
        dec ix
        dec ix
        dec ix
fcq_qn: ld de,FB_QSZ
        add ix,de
        djnz fcq_ql
fcq_l:  ld a,c                      ; a BOB of its list
        call fb_dnp
        ld a,(hl)
        inc a
        jr z,fcq_no
        dec a
        jr z,fcq_no
        ld b,a
        push hl
        ld a,c                      ; (the box around them first: a cell outside it meets none)
        call fb_bxp
        call fb_meet
        pop hl
        jr nc,fcq_no
        inc hl
        push hl
        pop ix
        ld hl,fb_r                  ; (fb_rect takes fb_r: the cell into fb_tr)
        ld de,fb_tr
        push bc
        ld bc,8
        ldir
        pop bc
fcq_ll: call fb_rect
        push ix
        ld ix,fb_tr
        call fb_meet
        pop ix
        jr c,fcq_bob
        ld de,FB_ENT
        add ix,de
        djnz fcq_ll
fcq_no: pop de
        ret
fcq_bob:
        ld hl,fb_tr
        ld de,fb_r
        push bc
        ld bc,8
        ldir
        pop bc
fcq_yes:
        ld hl,0xFFFF
        ld (fb_own),hl
        ld a,c
        call fb_queue
        ld a,1
        ld (fb_cqr),a
        ld (fb_busy),a
        pop de
        ret

; (tiles.asm fb_invf: map_write) D = row, E = column of a cell whose tile changed: the caches
; holding it copy it again when they need it. Keeps DE.
fb_inval:
        ld hl,fb_cache
        ld b,FB_GMAX
fiv_lp: push hl
        ld a,(hl)
        inc hl
        and (hl)
        inc a
        jr z,fiv_nx                 ; (free)
        inc hl
        ld a,e
        sub (hl)
        cp 4
        jr nc,fiv_nx                ; (not in its window)
        inc hl
        ld a,d
        sub (hl)
        cp 4
        jr nc,fiv_nx
        inc hl
        ld a,e
        sub (hl)
        and 3
        ld c,a
        inc hl
        ld a,d
        sub (hl)
        and 3
        add a,a
        add a,a
        add a,c                     ; its bit: row * 4 + column in the cache
        inc hl
        bit 3,a
        jr z,fiv_lo
        inc hl
fiv_lo: and 7
        ld c,a
        ld a,0xFE
        inc c
fiv_sh: dec c
        jr z,fiv_m
        rlca
        jr fiv_sh
fiv_m:  and (hl)
        ld (hl),a
fiv_nx: pop hl
        ld a,FB_CSZ
        add a,l
        ld l,a
        jr nc,fiv_nc
        inc h
fiv_nc: djnz fiv_lp
        ret

; (tiles.asm atr_put: map_write) D = row, E = column 0..159, C = attributes (7 bits) that are not
; the cell's: the packed map's cell (page-0 RAM, cold.asm atr_load) gets their code, a value
; without one taking a free code (atr_lut's FFh); none left: counted in atr_lost, the cell as it
; was (tools/mapcells.py rules it out). Rows past the map: nothing. Keeps DE.
atr_new:
        ld a,d
        ld hl,lv_rows               ; (the level's)
        cp (hl)
        ret nc
        add a,a
        add a,atr_rows & 0xFF
        ld l,a
        ld a,0
        adc a,atr_rows / 256
        ld h,a
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a                      ; the row's 80 bytes
        ld a,e
        srl a
        add a,l
        ld l,a
        jr nc,an_nb
        inc h
an_nb:  push hl                     ; (the cell's byte)
        ld hl,atr_lut               ; (atr_lut does not cross a 256-byte boundary)
        ld b,16
an_f:   ld a,(hl)
        cp c
        jr z,an_code                ; (their code)
        inc l
        djnz an_f
        ld l,atr_lut & 0xFF
        ld b,16
an_e:   ld a,(hl)
        inc a
        jr z,an_new                 ; (a free code)
        inc l
        djnz an_e
        pop hl
        ld hl,atr_lost
        inc (hl)
        ret
an_new: ld (hl),c                   ; (theirs now)
an_code:
        ld a,l
        sub atr_lut & 0xFF
        ld b,a                      ; the code
        pop hl
        ld a,(hl)
        bit 0,e
        jr nz,an_odd
        and 0x0F                    ; (an even column: the high nibble)
        rlc b
        rlc b
        rlc b
        rlc b
        jr an_w
an_odd: and 0xF0
an_w:   or b
        ld (hl),a
        ret

; ----- level 2's vats: what the play field needs of them (docs/LEVEL2.md 3.5; level 2's step 14) -----
; vats.asm (BANK_L2, level 2's logic bank) draws the vats' columns and get_tile's vat rule; here:
; their state cleared at each full redraw (vat_init), a piece over a vat cell composed from the tiles,
; never a cache (vat_inbox), a V9938 build's page given the looks its copy brings (vat_bbinit), and
; whether a column meets the play-field BOBs or their work (vat_meet, for vats.asm).

VAT_REC:    equ L2_VATS + 0x40          ; per vat: first column, columns, first row, rows (its record's
                                        ;   + 2), first index in vat_shown (tools/mapcells.py vat_tables)
VAT_TIL:    equ L2_VATS + 0x80          ; the tiles (words) of T0[16], T1[16], T2[16]
        if (VAT_TIL & 0xFF) + 96 > 0x100
vat_til_page:                           ; (an error: vat_srcs takes VAT_TIL's 96 bytes in one page)
vat_til_page:
        endif
VAT_LB:     equ 12                      ; lines (63.5 us) the VDP takes at most for 16 lines of a column
VAT_LP:     equ 15                      ;   and for its parts' starts (5 at most, 15 registers each)
VAT_LM:     equ 40                      ; lines the VBLANK interrupt may hold the next part back
VAT_LV:     equ 49                      ; lines from the VBLANK to the play area's first (60 Hz)
VAT_LB0:    equ 4                       ; lines from the blank's end to the play area's first, at least
VAT_KZ:     equ 4                       ; VBLANKs from a column to the next on the Z80 (the R800: 1)
; the column being prepared or ready (vat_fr, msx.inc: IX = vat_fr in vats.asm, vat_* here)
VF_DX:      equ 0                       ; its x on the page shown (DX)
VF_PG:      equ 1                       ; DY's high byte (the V9938's page; the ring's x 256 and up)
VF_R0:      equ 2                       ; its vat's first row
VF_JA:      equ 3                       ; its first and last row drawn (the vat's own: 0..)
VF_JB:      equ 4
VF_N:       equ 5                       ; parts started
VF_LN:      equ 6                       ; lines it takes (vat_fits)
VF_S:       equ 7                       ; 12: T0, T1, T2's SX, SY (tile_src's)
VF_W0:      equ 19                      ; the window: the page's first column (the ring: the kept ones)
VF_WN:      equ 20                      ;   and its columns
VF_LO:      equ 21                      ; the columns (vat_shown's indexes) a pass may take: from,
VF_HI:      equ 22                      ;   to (excluded)
VF_ST:      equ 23                      ; 1: a column of the vat in the window waits
VF_V:       equ 24                      ; the vat (its record's index)
VF_WT:      equ 25                      ; the column: its look wanted,
VF_IX:      equ 26                      ;   its index in vat_shown,
VF_CC:      equ 27                      ;   its map column
VF_RDY:     equ 28                      ; 1: ready for the next window (vats.asm vat_run)
VF_EC:      equ 29                      ; the engines then: the page's first column (the ring: prev_cx),
VF_EY:      equ 30                      ;   prev_cy,
VF_EP:      equ 31                      ;   the page shown
VF_STK:     equ 32                      ; the tick of vats.asm vat_prep's last look for a column
VF_T:       equ 33                      ; 6: T0, T1, T2's tiles
VF_FS:      equ 39                      ; vat_fits: bit 0 it may start between the split and the VBLANK,
                                        ;   bit 1 in the blank after the VBLANK (S#2 VR)
VF_TRY:     equ 40                      ; columns vat_prep may still try this time
VF_SZ:      equ 41


; (engines_init, engines_jump: every level) No vat column drawn on any page, nothing to do; level
; 2's vat_disp cleared (vat_chg's 7 bytes are free in the other levels).
vat_init:
        xor a
        ld (vat_pg),a
        ld (vat_bk),a
        ld (vat_rr),a
        ld (vat_fr + VF_RDY),a
        ld hl,vat_chg
        ld b,7
vin_c:  ld (hl),a
        inc hl
        djnz vin_c
        ld a,(tick)
        dec a
        ld (vat_wtk),a
        xor a
        ld (vat_on),a
        ld a,(lv_logic)
        cp BANK_L2
        ret nz
        ld a,1
        ld (vat_on),a
        ld hl,vat_disp
        ld bc,VAT_COLS_l2
        xor a
        jp fill

; A = a vat's record index (0-7) -> HL = its record (lv_tab at 8000h).
vf_recp:
        add a,a
        add a,a
        add a,a
        add a,VAT_REC & 0xFF
        ld l,a
        ld h,VAT_REC / 256
        ret

; HL = a column's vat_disp byte, A = page -> A = its nibble there. Keeps BC, DE, HL.
vf_nib: or a
        ld a,(hl)
        jr z,vfn_0
        rrca
        rrca
        rrca
        rrca
vfn_0:  and 15
        ret

; HL = a column's vat_disp byte, A = page, E = a nibble -> written there. Keeps BC, DE, HL.
vf_wnib:
        or a
        ld a,(hl)
        jr nz,vfw_1
        and 0xF0
        or e
        ld (hl),a
        ret
vfw_1:  and 0x0F
        push bc
        ld b,a
        ld a,e
        rlca
        rlca
        rlca
        rlca
        or b
        pop bc
        ld (hl),a
        ret

; (tiles.asm get_tile through field_call, level 2) D = row, E = column of a cell without a map patch
; -> HL = its tile: when a vat covers it T0, T1 or T2 at its column's look on page vat_pg (that page's
; nibble; none yet: vat_shown's, which the page then holds), else the map's (gt_map's way, through the
; 8000h window). Keeps BC, DE (and the 8000h window).
vat_tile:
        push bc
        ld a,(act_8000)
        push af
        ld a,(lv_tab)
        call bank_8000
        ld a,d
        cp 64
        jr nc,vt_no
        ld l,a
        ld h,L2_VATS / 256          ; (the row's vats, bit v: L2_VATS is 256-byte aligned)
        ld a,(hl)
        or a
        jr z,vt_no
        ld c,a
        xor a
vt_lp:  srl c
        jr c,vt_v
vt_nx:  inc a
        inc c
        dec c
        jr nz,vt_lp
vt_no:  ld a,d                      ; (no vat: the map's tile, as tiles.asm gt_map reads it)
        ld l,a
        ld h,0
        ld c,a
        ld b,h
        add hl,hl
        add hl,bc                   ; row * 3 (rowtab: bank, address at A000h)
        ld bc,rowtab
        add hl,bc
        ld a,(lv_mapb)
        add a,(hl)
        call bank_8000
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld c,e
        ld b,0
        add hl,bc
        add hl,bc
        res 5,h                     ; (A000h-BFFFh: at 8000h-9FFFh here)
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        pop af
        pop bc
        jp bank_8000
vt_v:   push af                     ; (the vat's index)
        call vf_recp
        ld a,e
        sub (hl)                    ; its column in the vat
        inc l
        cp (hl)
        jr c,vt_hit
        pop af
        jr vt_nx
vt_hit: pop bc
        ld b,a                      ; B = the cell's column in the vat
        inc l
        ld a,d
        sub (hl)
        ld c,a                      ; C = its row in the vat (0: T0, odd: T1, even: T2)
        inc l
        inc l
        ld a,(hl)
        add a,b                     ; its column's index in vat_shown
        push de
        ld e,a
        ld d,0
        ld hl,vat_shown
        add hl,de
        ld b,(hl)                   ; B = vat_shown's look (its half: bit 3)
        ld hl,vat_disp
        add hl,de
        ld a,(vat_pg)
        call vf_nib
        bit 3,a
        jr nz,vt_has
        ld a,b                      ; none drawn on that page: vat_shown's, which it now holds
        and 7
        or 8
        ld e,a
        ld a,(vat_pg)
        call vf_wnib
        ld a,e
vt_has: and 7
        ld e,a
        ld a,b
        and 8
        or e                        ; the look
        add a,a
        ld e,a
        ld a,c
        or a
        jr z,vt_t                   ; (T0)
        ld a,32                     ; (T1)
        bit 0,c
        jr nz,vt_t1
        ld a,64                     ; (T2)
vt_t1:  add a,e
        ld e,a
vt_t:   ld d,0
        ld hl,VAT_TIL
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        pop de
        pop af
        pop bc
        jp bank_8000

; (fb_piece, level 2) -> NZ when the piece's cells (fb_cc) hold a vat cell: its background then
; comes from the tiles (the vat rule's look on its page), never from a cache (a vat cell's tile
; changes with its look). Keeps BC, DE.
vat_inbox:
        ld a,(lv_logic)
        cp BANK_L2
        ret nz                      ; (Z: no vats)
        push bc
        push de
        ld a,(act_8000)
        push af
        ld a,(lv_tab)
        call bank_8000
        ld b,8
        xor a
vib_lp: push af
        call vf_recp
        ld a,(hl)
        inc a
        jr z,vib_nx                 ; (no such vat)
        ld a,(fb_cc + 2)            ; its first column <= the piece's last,
        cp (hl)
        jr c,vib_nx
        ld a,(hl)
        inc l
        add a,(hl)
        dec a
        ld c,a
        ld a,(fb_cc)                ; its last >= the piece's first,
        cp c
        jr z,vib_c
        jr nc,vib_nx
vib_c:  inc l
        ld a,(fb_cc + 3)            ; and the same for the rows
        cp (hl)
        jr c,vib_nx
        ld a,(hl)
        inc l
        add a,(hl)
        dec a
        ld c,a
        ld a,(fb_cc + 1)
        cp c
        jr z,vib_yes
        jr c,vib_yes
vib_nx: pop af
        inc a
        djnz vib_lp
        pop af
        call bank_8000
        pop de
        pop bc
        xor a
        ret
vib_yes:
        pop af
        pop af
        call bank_8000
        pop de
        pop bc
        or 1
        ret

; (fb_bbinit: a V9938 build begins, level 2) The page being built holds, once its copy is made, the
; looks the page shown has of the columns the copy brings (the columns of both pages), none of the
; others' yet. The last column's mirror is not needed any more: the copy brings it.
vat_bbinit:
        ld a,(lv_logic)
        cp BANK_L2
        ret nz
        xor a
        ld (vat_bk),a
        ld a,(act_8000)
        push af
        ld a,(lv_tab)
        call bank_8000
        xor a
vbi_v:  push af
        call vf_recp
        ld a,(hl)
        cp 0xFF
        jr z,vbi_nv
        ld d,a                      ; D = the map column
        inc l
        ld b,(hl)                   ; B = the vat's columns
        inc l
        inc l
        inc l
        ld e,(hl)
        push de
        ld d,0
        ld hl,vat_disp
        add hl,de                   ; HL = its first column's byte
        pop de
vbi_c:  ld c,0                      ; (none)
        ld a,(s38_vis_c0)
        neg
        add a,d
        cp 16
        jr nc,vbi_w
        ld a,(s38_back_c0)
        neg
        add a,d
        cp 16
        jr nc,vbi_w
        ld c,(hl)                   ; (both pages: the copy brings the shown page's look)
        ld a,(s38_vis_page)
        or a
        ld a,c
        jr z,vbi_lo
        rrca
        rrca
        rrca
        rrca
vbi_lo: and 15
        ld c,a
vbi_w:  ld a,(s38_vis_page)         ; (the page built: the other one's nibble)
        or a
        ld a,(hl)
        jr nz,vbi_hi
        and 0x0F
        ld e,a
        ld a,c
        rlca
        rlca
        rlca
        rlca
        or e
        jr vbi_s
vbi_hi: and 0xF0
        or c
vbi_s:  ld (hl),a
        inc hl
        inc d
        djnz vbi_c
vbi_nv: pop af
        inc a
        cp 8
        jr c,vbi_v
        pop af
        jp bank_8000

; (vats.asm through field_call) C = a page, IX = vat_fr -> L = 1 when its column over its rows drawn
; (fb_r: vat_rect) meets the play-field BOBs' work there (the item being composed, one queued), the box
; around that page's list or around the BOBs wanted (fb_wbx), or, on the V9938's page being built, what
; its copy may bring (fb_bb); else L = 0. Keeps IX.
vat_meet:
        call vat_rect
        push ix
        call vmt_go
        pop ix
        ld l,0
        ret nc
        inc l
        ret
vmt_go: ld a,(fb_ph)                ; the item being composed
        or a
        jr z,vmt_q
        ld a,(fb_cur)
        cp c
        jr nz,vmt_q
        ld ix,fb_cur + 3
        call fb_meet
        ret c
vmt_q:  ld a,(fb_qn)                ; a queued item of that page
        or a
        jr z,vmt_l
        ld b,a
        ld ix,fb_q + 3
vmt_ql: ld a,(ix-3)
        cp c
        jr nz,vmt_qn
        call fb_meet
        ret c
vmt_qn: ld de,FB_QSZ
        add ix,de
        djnz vmt_ql
vmt_l:  ld a,c                      ; the box around its list's BOBs
        call fb_dnp
        ld a,(hl)
        inc a
        jr z,vmt_w                  ; (unknown)
        dec a
        jr z,vmt_w                  ; (none)
        ld a,c
        call fb_bxp
        call fb_meet
        ret c
vmt_w:  ld a,(fb_wn)                ; the box around the BOBs wanted
        or a
        jr z,vmt_b
        ld ix,fb_wbx
        call fb_meet
        ret c
vmt_b:  ld a,(fb_eng)               ; the V9938's page being built: what its copy may bring
        or a
        ret z
        ld a,(s38_vis_page)
        cp c
        jr z,vmt_n
        ld a,(fb_bbn)
        or a
        jr z,vmt_n
        ld b,a
        ld ix,fb_bb
vmt_bl: call fb_meet
        ret c
        ld de,8
        add ix,de
        djnz vmt_bl
vmt_n:  or a
        ret

; fb_r = the frame's column (VF_CC) over its rows drawn, in the map.
vat_rect:
        ld a,(ix+VF_CC)
        call fb_c16
        ld (fb_r),hl
        ld de,16
        add hl,de
        ld (fb_r + 4),hl
        ld a,(ix+VF_R0)
        add a,(ix+VF_JA)
        call fb_c16
        ld (fb_r + 2),hl
        ld a,(ix+VF_R0)
        add a,(ix+VF_JB)
        inc a
        call fb_c16
        ld (fb_r + 6),hl
        ret

; (vats.asm through field_call: IX = vat_fr) -> L = 0 when its column (its rows drawn: VAT_LB lines
; each, VAT_LP its parts' starts) may start now and end before the beam reaches its first line on the
; screen (R#23: the list's on screen and the one published for the next VBLANK, the least), else 1;
; VF_FS bit 0: when started between the HUD split and the VBLANK (VAT_LV lines from the VBLANK to the
; play area, VAT_LM for that interrupt), bit 1: when started in the blank after the VBLANK (S#2 VR).
vat_fits:
        ld a,(ix+VF_JB)
        sub (ix+VF_JA)
        inc a
        ld b,a
        ld a,VAT_LP
vft_m:  add a,VAT_LB
        djnz vft_m
        ld (ix+VF_LN),a             ; (its lines)
        ld hl,(vbl_ptr)
        inc hl
        inc hl
        ld a,(hl)                   ; (every list starts with R#23)
        call vft_ya
        ld c,a                      ; C = its first line on the screen now (FFh: none)
        ld a,(pk_state)
        or a
        jr z,vft_1
        ld hl,(pk_list)
        inc hl
        inc hl
        ld a,(hl)
        call vft_ya
        cp c
        jr nc,vft_1
        ld c,a                      ; (the next picture's, when less)
vft_1:  ld b,3
        ld a,c
        inc a
        jr z,vft_e                  ; (none of it shows)
        ld b,0
        ld a,(ix+VF_LN)
        add a,VAT_LB0
        cp c
        jr z,vft_b
        jr nc,vft_a
vft_b:  set 1,b
vft_a:  ld a,(ix+VF_LN)
        ld l,a
        ld h,0
        ld de,VAT_LM
        add hl,de                   ; its lines + the VBLANK's
        ex de,hl
        ld l,c
        ld h,0
        push bc
        ld bc,VAT_LV
        add hl,bc                   ; the lines left at worst: from the VBLANK to its first line
        pop bc
        or a
        sbc hl,de
        jr c,vft_e
        set 0,b
vft_e:  ld (ix+VF_FS),b
        ld l,0
        ld a,b
        or a
        ret nz
        inc l
        ret
; A = R#23 -> A = the first line of the column (VF_R0, VF_JA, VF_JB) on the screen, FFh when none.
vft_ya: ld e,a
        ld a,(ix+VF_R0)
        add a,(ix+VF_JA)
        and 15
        rlca
        rlca
        rlca
        rlca
        sub e                       ; (its first row's line - R#23) & 255
        cp VIEW_LINES
        ret c                       ; (its top on the screen)
        neg
        ld d,a                      ; (R#23 - its first line) & 255: the screen's top in it?
        ld a,(ix+VF_JB)
        sub (ix+VF_JA)
        inc a
        rlca
        rlca
        rlca
        rlca                        ; (its lines)
        cp d
        jr z,vya_n
        jr c,vya_n
        xor a                       ; (it covers the screen's top)
        ret
vya_n:  ld a,0xFF
        ret

; (vats.asm vat_mirror through field_call: IX = vat_fr, C = the V9938's page being built) Its column,
; just copied there from the page shown, which may have play-field BOBs over it: where it meets them or
; their work on that page, the sync composes it again before the page may be shown (fb_bb, fb_bsync).
vat_mmark:
        call vat_meet
        dec l
        ret nz
        call vat_rect
        call fb_bbadd
        ld a,0xFF
        ld (fb_bsync),a
        ret

; (vats.asm through field_call: IX = vat_fr, its column's look VF_WT; lv_tab at 8000h) -> its tiles T0,
; T1, T2 at that look (VF_T: VAT_TIL's) and their places in the tile cache (VF_S: tiles.asm tile_srct,
; which loads them): L = 1 when one of the three lost its place to another's load (later then), else 0.
; Keeps the 8000h window's bank.
vat_srcs:
        ld c,0
vss_a:  ld a,c                      ; tile c: VAT_TIL + 32 c + 2 look
        add a,a
        add a,a
        add a,a
        add a,a
        ld l,a
        ld a,(ix+VF_WT)
        add a,l
        add a,a
        ld l,a
        ld h,VAT_TIL / 256          ; (VAT_TIL: 9780h, its 96 bytes in one page)
        ld a,l
        add a,VAT_TIL & 0xFF
        ld l,a
        ld e,(hl)
        inc hl
        ld d,(hl)
        push ix
        pop hl
        ld a,c
        add a,a
        add a,VF_T
        add a,l
        ld l,a
        jr nc,vss_t
        inc h
vss_t:  ld (hl),e
        inc hl
        ld (hl),d                   ; its tile
        ex de,hl
        ld a,(act_8000)
        push af
        call tile_srct              ; (keeps BC, DE)
        pop af
        call bank_8000              ; (a load maps its tile's bank)
        push ix
        pop hl
        ld a,c
        add a,a
        add a,a
        add a,VF_S
        add a,l
        ld l,a
        jr nc,vss_s
        inc h
vss_s:  ex de,hl
        ld hl,cmdbuf
        push bc
        ld bc,4
        ldir                        ; its place
        pop bc
        inc c
        ld a,c
        cp 3
        jr c,vss_a
        jp vat_valid                ; (the three still in their places)

; (also vats.asm through field_call) IX = vat_fr -> L = 0 when the tile cache's slots of VF_S still
; hold the tiles of VF_T, else 1. Keeps IX.
vat_valid:
        push ix
        pop hl
        ld de,VF_S
        add hl,de                   ; HL = VF_S's first place
        push ix
        pop de
        ld a,e
        add a,VF_T
        ld e,a
        jr nc,vvl_0
        inc d                       ; DE = VF_T's first tile
vvl_0:  ld b,3
vvl_lp: push hl
        ld a,(hl)                   ; SX: (s & 15) * 16
        rrca
        rrca
        rrca
        rrca
        and 15
        inc hl
        inc hl
        or (hl)                     ; SY's low byte: s & F0h (TC_SLOTS 256 at most)
        push de
        ld l,a
        ld h,0
        add hl,hl
        ld de,TC_TILE
        add hl,de                   ; HL = TC_TILE[s]
        pop de
        ld a,(de)
        cp (hl)
        jr nz,vvl_no
        inc de
        inc hl
        ld a,(de)
        cp (hl)
        jr nz,vvl_no
        inc de
        pop hl
        inc hl
        inc hl
        inc hl
        inc hl
        djnz vvl_lp
        ld l,0
        ret
vvl_no: pop hl
        ld l,1
        ret

; (vats.asm through field_call) IX = vat_fr -> its VF_DX, VF_PG: its column's place on the page shown
; (the ring: x & 255, its page the x's bit 8; a V9938 page: from its first column).
vat_dst:
        ld a,(fb_eng)
        or a
        jr nz,vds_38
        ld a,(ix+VF_CC)
        add a,a
        add a,a
        add a,a
        add a,a
        ld (ix+VF_DX),a
        ld a,(ix+VF_CC)
        rrca
        rrca
        rrca
        rrca
        and 1
        ld (ix+VF_PG),a
        ret
vds_38: ld a,(ix+VF_CC)
        ld hl,s38_vis_c0
        sub (hl)
        add a,a
        add a,a
        add a,a
        add a,a
        ld (ix+VF_DX),a
        ld a,(s38_vis_page)
        ld (ix+VF_PG),a
        ret

        if EXTJOY
; (isr.asm through field_call, test builds) A list goes on screen: the play-field BOBs its page
; holds (fb_vis: how many, then frame, x, y of each), what tools check the pictures against.
; Keeps DE.
fb_visrec:
        ld a,(fb_eng)
        or a
        jr z,fvr_0
        ld a,(s38_vis_page)
fvr_0:  or a
        ld hl,fb_dn0
        jr z,fvr_l
        ld hl,fb_dn1
fvr_l:  push de
        ld de,fb_vis
        ldi
        ld b,FB_MAX
fvr_lp: ld c,5
fvr_e:  ld a,(hl)
        ld (de),a
        inc hl
        inc de
        dec c
        jr nz,fvr_e
        inc hl
        inc hl
        djnz fvr_lp
        pop de
        ret
        endif
