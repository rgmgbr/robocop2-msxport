; Level 2's vats on the screen (docs/LEVEL2.md 3.5, default 18; level 2's step 14), in level 2's
; logic bank (BANK_L2 at A000h around the calls: tiles.asm l2_call).
;
; The logic (level2.asm lt1) keeps each vat column's look in vat_shown and marks the vat changed
; (vat_chg); the screen shows them here, whole columns, never torn, never an older look.
; - vat_disp: per column and page the look its cells there show (msx.inc: a nibble, 8 + (look &
;   7), 0 none; a column's looks keep their half, vat_shown's bit 3). get_tile's vat rule
;   (vat_tile) draws a vat cell at its column's look on the page being drawn (vat_pg); a column
;   with no cell there yet takes vat_shown, which that page then holds, so that a row or a column
;   the scroll uncovers shows the look of the rest of its column.
; - vat_run draws a column whose look on the page shown is not vat_shown's: one column a window
;   between the HUD split and the VBLANK, its first part started by vdp_cmd_q's rule (only before
;   the VBLANK), the others right after each other (cmd_lock keeps the interrupts' commands off),
;   only when it ends before the beam reaches its first line on the screen even when it starts
;   just before the VBLANK (vat_fits), and only where it meets no play-field BOB nor their work
;   (field.asm vat_meet: the column waits, the BOBs first). The round robin (vat_rr) takes the
;   columns in turn.
; - A column is its rows' tiles T0, T1, T2 from the tile cache (and the first two after the page's
;   line 255), then per such part of the page one HMMM that copies the T1/T2 pair down from 32
;   lines above (it overlaps its source: each line it reads was written 32 lines before).
; - V9938: the page being built (or built) gets the column too, copied from the page shown right
;   after (vat_mirror, a part when the VDP is idle: that page is not shown), and its flip waits for
;   it (vat_bk); a build's start gives its page the looks of the columns its copy brings (field.asm
;   vat_bbinit). The scroll engines' hooks: tiles.asm vat_win and vat_idle.

; A = a vat's record index (0-7) -> HL = its record (lv_tab at 8000h).
vat_recp:
        add a,a
        add a,a
        add a,a
        add a,VAT_REC & 0xFF
        ld l,a
        ld h,VAT_REC / 256
        ret

; HL = a column's vat_disp byte, A = page -> A = its nibble there. Keeps BC, DE, HL.
vat_nib:
        or a
        ld a,(hl)
        jr z,vnb_0
        rrca
        rrca
        rrca
        rrca
vnb_0:  and 15
        ret

; HL = a column's vat_disp byte, A = page, E = a nibble -> written there. Keeps BC, DE, HL.
vat_wnib:
        or a
        ld a,(hl)
        jr nz,vwn_1
        and 0xF0
        or e
        ld (hl),a
        ret
vwn_1:  and 0x0F
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

; A -> HL = A * 16. Keeps BC, DE.
vat_c16:
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ret

; (tiles.asm vat_win through l2_call: between the HUD split and the VBLANK, the VDP idle; level 2)
; The window's first call: a column whose look on the page shown is not vat_shown's drawn there
; when one may be (vat_scan) -> L = 1 when its commands run, else 0.
vat_run:
        ld a,(tick)
        ld hl,vat_wtk
        cp (hl)
        jr z,vr_no
        ld (hl),a
        ld a,(vat_bk)
        or a
        jr nz,vr_no                 ; (V9938: the last column on the other page first)
        ld a,(fb_eng)
        or a
        jr z,vr_r
        ld a,(s38_flip_wait)
        or a
        jr nz,vr_no                 ; (the old page still on screen: after the flip)
        ld a,(s38_vis_page)
        ld (vat_pg),a
        ld a,(s38_vis_c0)
        ld c,a
        ld b,16
        jr vr_go
vr_r:   xor a
        ld (vat_pg),a
        ld a,(prev_cx)
        dec a
        ld c,a
        ld b,19                     ; (the ring: the columns kept)
vr_go:  ld hl,-VF_SZ
        add hl,sp
        ld sp,hl
        push hl
        pop ix
        ld (ix+VF_W0),c
        ld (ix+VF_WN),b
        ld a,(act_8000)
        push af
        ld a,(lv_tab)
        call bank_8000
        ld a,(vat_rr)
        ld (ix+VF_LO),a
        ld (ix+VF_HI),0xFF
        call vat_pass               ; (from vat_rr on,
        or a
        jr nz,vr_e
        ld a,(vat_rr)
        or a
        jr z,vr_e
        ld (ix+VF_HI),a
        ld (ix+VF_LO),0
        call vat_pass               ;  then from 0)
vr_e:   ld e,a
        pop af
        call bank_8000
        ld hl,VF_SZ
        add hl,sp
        ld sp,hl
        ld l,e
        ret
vr_no:  ld l,0
        ret

; One pass over the vats (VF_LO..VF_HI: the columns it may draw) -> A = 1 when one was drawn, else
; 0; each vat's flag (vat_chg) set while a column of it in the window waits. (lv_tab at 8000h.)
vat_pass:
        xor a
vsp_v:  ld (ix+VF_V),a
        call vat_recp
        ld a,(hl)
        cp 0xFF
        jr z,vsp_nv                 ; (no such vat)
        ld (ix+VF_ST),0
        ld a,(ix+VF_V)
        call vat_rows               ; D = its first column, B = its columns, E = its first index
        jr c,vsp_f                  ; (none of its rows kept)
vsp_k:  ld a,d
        sub (ix+VF_W0)
        cp (ix+VF_WN)
        jr nc,vsp_nk                ; (outside the window)
        push bc
        push de
        ld d,0
        ld hl,vat_shown
        add hl,de
        ld c,(hl)                   ; C = its look wanted
        ld hl,vat_disp
        add hl,de
        ld a,(vat_pg)
        call vat_nib
        bit 3,a
        jr z,vsp_st
        xor c
        and 7
        jr z,vsp_ok                 ; (the page shows it)
vsp_st: ld (ix+VF_ST),1
        ld a,e
        cp (ix+VF_LO)
        jr c,vsp_ok
        cp (ix+VF_HI)
        jr nc,vsp_ok
        pop de
        push de
        ld a,c
        call vat_try
        push af
        ld a,(lv_tab)
        call bank_8000              ; (tile_src may have mapped a tile bank)
        pop af
        or a
        jr nz,vsp_dn
vsp_ok: pop de
        pop bc
vsp_nk: inc d
        inc e
        djnz vsp_k
vsp_f:  ld a,(ix+VF_V)
        cp 7
        jr nc,vsp_nv
        add a,vat_chg & 0xFF
        ld l,a
        ld h,vat_chg / 256
        ld a,(ix+VF_ST)
        neg                         ; (1: FFh)
        ld (hl),a
vsp_nv: ld a,(ix+VF_V)
        inc a
        cp 8
        jr c,vsp_v
        xor a
        ret
vsp_dn: pop de
        pop bc
        ld a,1
        ret

; A = a vat's record index -> the frame's VF_R0, VF_JA, VF_JB: the rows of its columns the scroll
; engines keep ([prev_cy - 1, prev_cy + 13): VIEW_ROWS), D = its first column, B = its columns,
; E = its first index in vat_shown -> C when none of its rows is kept. (lv_tab at 8000h.)
vat_rows:
        call vat_recp
        ld d,(hl)
        inc l
        ld b,(hl)
        inc l
        ld a,(hl)
        ld (ix+VF_R0),a
        ld c,a                      ; C = its first row
        inc l
        ld a,(hl)
        add a,c
        ld (ix+VF_JB),a             ; (past its last row, for now)
        inc l
        ld e,(hl)
        ld a,(prev_cy)
        dec a                       ; the first row kept (FFh: the row above the map)
        bit 7,a
        jr z,vrw_1
        xor a
vrw_1:  cp c
        jr nc,vrw_2
        ld a,c
vrw_2:  sub c
        ld (ix+VF_JA),a             ; the first row drawn, from the vat's first
        ld a,(prev_cy)
        add a,VIEW_ROWS - 1         ; past the last row kept
        cp (ix+VF_JB)
        jr nc,vrw_3
        ld (ix+VF_JB),a
vrw_3:  ld a,(ix+VF_JB)
        sub c
        jr c,vrw_no
        jr z,vrw_no
        dec a
        ld (ix+VF_JB),a             ; the last drawn, from the vat's first
        cp (ix+VF_JA)
        ret nc
vrw_no: scf
        ret

; D = a column's map column, E = its index in vat_shown, A = its look wanted (the frame's rows its
; vat's) -> drawn on the page shown when it meets no BOB nor their work (on the V9938 on the page
; being built either, when it holds the column: its mirror follows) and there is time: A = 1, else 0.
vat_try:
        ld (ix+VF_WT),a
        ld (ix+VF_IX),e
        ld (ix+VF_CC),d
        ld a,(vat_pg)
        call vat_meets
        jp nz,vtr_no
        ld a,(fb_eng)
        or a
        jr z,vtr_t
        call vat_bkcol
        jr nz,vtr_t
        ld a,(s38_vis_page)
        xor 1
        call vat_meets
        jp nz,vtr_no
vtr_t:  ld hl,vat_fits
        call field_call
        ld a,l
        or a
        jr nz,vtr_no
        call vat_dsp
        ld a,(vat_pg)
        call vat_nib
        ld (ix+VF_OLD),a
        ld a,(ix+VF_WT)
        and 7
        or 8
        ld e,a
        ld a,(vat_pg)
        call vat_wnib               ; (the new look, so that tile_src gives its tiles)
        ld e,(ix+VF_CC)
        call vat_srcs
        jr nz,vtr_back
        call vat_dst
        ld (ix+VF_N),0
        call vat_gen
        jr c,vtr_back               ; (the VBLANK came first: nothing started)
        xor a
        ld (cmd_lock),a
        ld a,(ix+VF_IX)
        inc a
        ld (vat_rr),a
        ld a,(fb_eng)
        or a
        jr z,vtr_ok
        call vat_bkcol
        jr nz,vtr_ok
        ld a,(ix+VF_IX)             ; V9938: the page being built: the column copied there
        ld (vat_bkc),a              ; (vat_mirror), and its rows drawn there from now on take
        ld a,(prev_cy)              ; the new look
        ld (vat_bky),a
        ld a,1
        ld (vat_bk),a
        call vat_dsp
        ld a,(ix+VF_WT)
        and 7
        or 8
        ld e,a
        ld a,(s38_vis_page)
        xor 1
        call vat_wnib
vtr_ok: ld a,1
        ret
vtr_back:
        call vat_dsp
        ld e,(ix+VF_OLD)
        ld a,(vat_pg)
        call vat_wnib
vtr_no: xor a
        ret

; A = a page -> NZ when the frame's column there meets the play-field BOBs or their work (field.asm
; vat_meet).
vat_meets:
        ld c,a
        ld hl,vat_meet
        call field_call
        ld a,l
        or a
        ret

; -> HL = the frame's column's vat_disp byte (VF_IX). Keeps BC, DE.
vat_dsp:
        ld a,(ix+VF_IX)
        ld hl,vat_disp
        add a,l
        ld l,a
        ret nc
        inc h
        ret

; -> Z when the V9938's page being built (or built) holds the frame's column (VF_CC).
vat_bkcol:
        ld a,(s38_back_c0)
        cp 0xFF
        jr z,vbk_no
        ld b,a
        ld a,(ix+VF_CC)
        sub b
        cp 16
        jr nc,vbk_no
        xor a
        ret
vbk_no: or 1
        ret

; The frame's VF_DX, VF_PG: the column's place on the page shown (the ring: x & 255, its page the
; x's bit 8; a V9938 page: from its first column).
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

; IX = a column's frame -> its parts sent in order (the window's chain: vat_emit): the tiles of its
; rows the copies cannot bring (the first three, and the first two after the page's line 255), then
; one copy for each part of the page -> C when its first part was too late for the blank (nothing
; started).
vat_gen:
        ld a,(ix+VF_JA)
vg_t:   ld c,a                      ; C = the row (the vat's)
        call vat_seg                ; A = max(the first row of its part of the page, 1)
        add a,2
        ld b,a
        ld a,c
        cp b
        jr nc,vg_tn                 ; (a copy brings it)
        call vat_tpart
        call vat_emit
        ret c
vg_tn:  ld a,c
        cp (ix+VF_JB)
        jr nc,vg_o
        inc a
        jr vg_t
vg_o:   ld a,(ix+VF_JA)             ; the copies: per part of the page, from its row a to b
vg_ol:  ld c,a                      ; C = a
        call vat_send               ; A = b (the part's last row drawn)
        ld b,a                      ; B = b
        ld a,c
        or a
        jr nz,vg_om
        inc a                       ; (from row 1: row 0 is T0)
vg_om:  ld d,a                      ; D = m = max(a, 1)
        add a,2
        ld e,a
        ld a,b
        cp e
        jr c,vg_on                  ; (b < m + 2: no copy)
        sub d
        dec a
        ld e,a                      ; E = its rows: b - m - 1
        push bc
        ld a,d
        call vat_opart
        call vat_emit
        pop bc
        ret c
vg_on:  ld a,b
        cp (ix+VF_JB)
        jr c,vg_more
        or a                        ; (NC: the walk ended)
        ret
vg_more:
        inc a
        jr vg_ol

; C = a row of the column -> A = the last row drawn of its part of the page (to the page's line 255,
; at most the last drawn). Keeps BC, DE.
vat_send:
        ld a,(ix+VF_R0)
        add a,c
        and 15
        cpl
        add a,16
        add a,c                     ; a + 15 - its slot
        cp (ix+VF_JB)
        ret c
        ld a,(ix+VF_JB)
        ret

; C = a row of the column -> A = max(the first row of its part of the page, 1) (a part: the rows
; from the first drawn, or from one at the page's line 0, to the next such). Keeps C, DE.
vat_seg:
        ld a,(ix+VF_R0)
        add a,c
        and 15                      ; its slot (its 16 lines' place on the page)
        ld b,a
        ld a,c
        sub (ix+VF_JA)
        cp b
        ld a,(ix+VF_JA)
        jr c,vsg_a                  ; (the first drawn row is in its part)
        ld a,c
        sub b
vsg_a:  or a
        ret nz
        inc a
        ret

; A = a row of the column -> A = its first line on the page: ((first row + row) & 15) * 16.
; Keeps BC, DE.
vat_ln: add a,(ix+VF_R0)
        and 15
        rlca
        rlca
        rlca
        rlca
        ret

; C = a row of the column -> vat_cmd = the 16 x 16 copy of its tile (T0, T1, T2 by the row) from
; the tile cache. Keeps BC.
vat_tpart:
        push bc
        ld a,c
        or a
        ld b,0                      ; (T0)
        jr z,vtp_t
        ld b,4                      ; (T1)
        bit 0,c
        jr nz,vtp_t
        ld b,8                      ; (T2)
vtp_t:  push ix
        pop hl
        ld de,VF_S
        add hl,de
        ld e,b
        add hl,de
        ld de,vat_cmd
        ld bc,4
        ldir                        ; SX, SY
        pop bc
        push bc
        ld a,c
        call vat_ln
        ld e,a                      ; (DY)
        ld a,16
        call vat_cdst
        pop bc
        ret

; A = m, E = the rows (1-15) -> vat_cmd = the copy of rows m .. onto rows m + 2 .. (the T1/T2 pair
; repeated down: it reads 32 lines above what it writes). Keeps BC, DE.
vat_opart:
        push de
        call vat_ln
        ld (vat_cmd + 2),a          ; SY: row m
        add a,32
        ld d,a                      ; (DY: row m + 2)
        ld a,(ix+VF_PG)
        ld (vat_cmd + 3),a
        ld a,(ix+VF_DX)
        ld (vat_cmd + 0),a
        xor a
        ld (vat_cmd + 1),a
        ld a,e
        ld e,d
        rlca
        rlca
        rlca
        rlca                        ; NY: 16 lines a row
        call vat_cdst
        pop de
        ret

; E = DY's line, A = NY -> vat_cmd's DX, DY, NX = 16, NY, CLR and ARG 0, HMMM. Keeps BC, DE.
vat_cdst:
        ld (vat_cmd + 10),a
        xor a
        ld (vat_cmd + 11),a
        ld (vat_cmd + 5),a
        ld (vat_cmd + 9),a
        ld (vat_cmd + 12),a
        ld (vat_cmd + 13),a
        ld a,e
        ld (vat_cmd + 6),a
        ld a,(ix+VF_PG)
        ld (vat_cmd + 7),a
        ld a,(ix+VF_DX)
        ld (vat_cmd + 4),a
        ld a,16
        ld (vat_cmd + 8),a
        ld a,FB_HMMM
        ld (vat_cmd + 14),a
        ret

; vat_cmd = the chain's next part: the first only before the VBLANK interrupt (vdp.asm vdp_cmd_q's
; rule; cmd_lock then stays 1: the interrupts start no command of theirs between the parts), the
; others once the one before is done -> C when the first was too late (nothing started). Keeps BC.
vat_emit:
        push bc
        ld a,(ix+VF_N)
        or a
        jr nz,ve_nx
        ld a,1
        ld (cmd_lock),a
        call vdp_busy
        jr nz,ve_late
        call ve_regs
        di
        ld a,(split_armed)
        or a
        jr nz,ve_lt
        ld a,b
        out (VDP_IND),a             ; R#46: it starts
        ei
        jr ve_ok
ve_lt:  ei
ve_late:
        xor a
        ld (cmd_lock),a
        pop bc
        scf
        ret
ve_nx:  call vdp_wait               ; (the part before; cmd_lock still 1)
        call ve_regs
        ld a,b
        out (VDP_IND),a             ; R#46: it starts
ve_ok:  inc (ix+VF_N)
        pop bc
        or a
        ret
; R#32-R#45 from vat_cmd (R#17 auto-incrementing: R#46 next) -> B = R#46's byte.
ve_regs:
        di
        ld a,32
        out (VDP_CTRL),a
        ld a,0x80+17
        out (VDP_CTRL),a
        ei
        ld hl,vat_cmd
        ld bc,14*256 + VDP_IND
        otir
        ld b,(hl)
        ret

; E = the map column -> the frame's T0, T1, T2 (SX, SY) at the look its nibble on page vat_pg
; gives, from the tile cache (which then holds them); twice, so that none of the three lost its
; slot to another one's load -> NZ when one did (later then). Keeps DE.
vat_srcs:
        ld c,0
vss_a:  call vat_src1
        push bc
        push de
        ex de,hl
        ld hl,cmdbuf
        ld bc,4
        ldir
        pop de
        pop bc
        inc c
        ld a,c
        cp 3
        jr c,vss_a
        ld c,0
vss_b:  call vat_src1
        push de
        ld de,cmdbuf
        ld b,4
vss_bc: ld a,(de)
        cp (hl)
        jr nz,vss_mv
        inc de
        inc hl
        djnz vss_bc
        pop de
        inc c
        ld a,c
        cp 3
        jr c,vss_b
        xor a
        ret
vss_mv: pop de
        or 1
        ret
; C = 0, 1, 2 (T0, T1, T2), E = the map column -> cmdbuf's SX, SY: tile_src of the column's row C
; (at its look on page vat_pg), HL = the frame's place for them. Keeps BC, DE.
vat_src1:
        ld a,(ix+VF_R0)
        add a,c
        call tile_src
        push ix
        pop hl
        ld a,c
        add a,a
        add a,a
        add a,VF_S
        add a,l
        ld l,a
        ret nc
        inc h
        ret

; (tiles.asm vat_idle through l2_call: the V9938, vat_bk set, the VDP idle; level 2) The last column
; drawn on the page shown copied onto the page being built (it is not shown: any time), a part (its
; rows down to the page's line 255, then those after it) a call; the flip waits for it. Again from
; its first part when the kept rows moved; dropped when no page is built or it does not hold the
; column (the next build's copy brings it). Then the play-field BOBs over it there, if any, composed
; again (tiles.asm fb_meetq).
vat_mirror:
        ld a,(fb_eng)
        or a
        jr z,vmr_off
        ld a,(s38_flip_wait)
        or a
        ret nz
        ld a,(s38_back_c0)
        cp 0xFF
        jr z,vmr_off
        ld hl,-VF_SZ
        add hl,sp
        ld sp,hl
        push hl
        pop ix
        ld a,(act_8000)
        push af
        ld a,(lv_tab)
        call bank_8000
        call vmr_go
        pop af
        call bank_8000
        ld hl,VF_SZ
        add hl,sp
        ld sp,hl
        ret
vmr_off:
        xor a
        ld (vat_bk),a
        ret
vmr_go: xor a                       ; the column's vat
vmg_v:  ld (ix+VF_V),a
        call vat_recp
        ld a,(hl)
        cp 0xFF
        jr z,vmg_nv
        ld a,l
        add a,4
        ld l,a
        ld a,(vat_bkc)
        sub (hl)                    ; (its column in this vat?)
        dec l
        dec l
        dec l
        cp (hl)
        jr c,vmg_got
vmg_nv: ld a,(ix+VF_V)
        inc a
        cp 8
        jr c,vmg_v
        jr vmr_off
vmg_got:
        push af
        ld a,(ix+VF_V)
        call vat_rows               ; D = its first column
        pop bc                      ; B = its column in the vat
        jr c,vmr_off                ; (none of its rows kept now)
        ld a,d
        add a,b
        ld (ix+VF_CC),a
        call vat_bkcol
        jr nz,vmr_off
        ld a,(vat_bky)
        ld hl,prev_cy
        cp (hl)
        jr z,vmg_y
        ld a,(hl)
        ld (vat_bky),a
        ld a,1
        ld (vat_bk),a               ; (the kept rows moved: again from its first part)
vmg_y:  ld a,(ix+VF_JA)             ; its part: the first, or the one after the page's line 255
        ld c,a
        call vat_send
        ld b,a
        ld a,(vat_bk)
        dec a
        jr z,vmg_p
        ld a,b
        cp (ix+VF_JB)
        jr nc,vmg_end               ; (no second part)
        inc a
        ld c,a
        ld b,(ix+VF_JB)
vmg_p:  ld a,(ix+VF_CC)             ; rows C .. B: the page shown's column onto the page built's
        ld hl,s38_back_c0
        sub (hl)
        rlca
        rlca
        rlca
        rlca
        ld (ix+VF_DX),a             ; (DX)
        ld a,(s38_vis_page)
        ld (vat_cmd + 3),a
        xor 1
        ld (ix+VF_PG),a
        ld a,(ix+VF_CC)
        ld hl,s38_vis_c0
        sub (hl)
        rlca
        rlca
        rlca
        rlca
        ld (vat_cmd + 0),a          ; SX
        xor a
        ld (vat_cmd + 1),a
        ld a,c
        call vat_ln
        ld (vat_cmd + 2),a          ; SY, and the same line for DY
        ld e,a
        ld a,b
        sub c
        inc a
        rlca
        rlca
        rlca
        rlca                        ; NY
        call vat_cdst
        push bc
        ld hl,vat_cmd
        call vdp_cmd
        pop bc
        ld hl,vat_bk
        inc (hl)
        ld a,b
        cp (ix+VF_JB)
        ret c                       ; (its second part next)
vmg_end:
        xor a
        ld (vat_bk),a
        ld a,(ix+VF_JA)
vmg_b:  push af
        add a,(ix+VF_R0)
        ld d,a
        ld e,(ix+VF_CC)
        ld a,(s38_vis_page)
        xor 1
        call fb_meetq
        pop af
        cp (ix+VF_JB)
        ret nc
        inc a
        jr vmg_b
