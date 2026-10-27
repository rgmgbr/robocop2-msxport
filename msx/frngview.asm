; The shooting range's display (docs/RANGE.md 3.3): what the original draws in each pass (rg_want,
; which msx/frng.asm's fr_frame writes) put on the screen in SCREEN 5, the street's art 1:1 in the
; 256 x 162 play area through the camera (s, the page's coarse offset c: tools/msxrange.py), the
; HUD below as in the game. Included by msx/frng.asm: bank BANK_FRNG at A000h, FRONT at 8000h.
;
; - rg_show, at the stage's entry, the play area black and the intro's list on screen (front.asm
;   front_range: fe_text's page 0, no sprites): range_gfx.bin's streams into VRAM (the clean scene
;   in page 2, the sheets in pages 0-3), both display pages built from the clean scene at the
;   camera's start, the 16 line patterns, the colour rows of the line sprites in both sets, both
;   SATs empty.
; - rg_feed, while rg_wait waits and once after each pass: Brainstorm's double buffer (msx/puzl.asm
;   bs_feed). The page not on screen catches up with the wanted state of the last pass, taken whole
;   when its build starts (rgt), so that each page shows one pass. Per element whose drawing
;   changed, the rectangle it covered and the one it covers now (their union when they meet) are
;   restored from the clean scene (HMMM), and every element that meets such a rectangle is drawn
;   again into it in the original's z-order: the pop-ups, each with its position's front layer (the
;   scene where the 6th plane is set), the big target, the dissolve (LMMM with TIMP from the
;   sheets), the box's edges and the crosshair's row (HMMV). One command when the VDP is idle,
;   never waiting for it; then the page's sprite set (the crosshair's vertical line, the box's
;   sides: 16-line sprites of one column, at most 3 on a line) and its register list. Once that
;   list is on screen, the other page is next.
; - rg_hide, before the stage returns: the VDP idle, the last list on screen, the play area black,
;   both SATs empty, page 2's tiles back (page 3 lines 88-161 hold sheet S3 over the field engine's
;   dynamic slot and caches: front.asm fe_text's fb_init, which the result's screen runs first,
;   frees them, as field.asm engines_init does before any field use).
; - The fade (msx/frng.asm rg_fade): pf_pal is the visit's graded palette limited by fade_cap.
;
; Rules (docs/BRAINSTORM.md 3.3): every command through vdp_cmd from rgr_cmd (never cmdbuf); VRAM
; streams between vram_write and vram_done; no OTIR reads past 9FFFh (BANK_FRNG holds A000h); FRONT
; back at 8000h after the uploads; at least 22 T-states between two writes to port 98h (the 5.37
; MHz rule, docs/BRAINSTORM.md 4.6 g); the interrupts keep their own work (fe_text's fb_init left
; no play-field copy pending).

RGS_LEN:    equ RG_ST_LEN + 2       ; a page's shown state (range.inc RG_ST_...), then the pass ($B00)
                                    ;   whose wanted state it is
RGE_N:      equ 9                   ; the elements, in the original's z-order: pop-up 0, its position's
                                    ;   front layer, pop-up 1, its front layer, the big target, the
                                    ;   dissolve, the box's top and bottom edges, the crosshair's row
RGE_LEN:    equ 8                   ; an element: its page rectangle x0, y0, x1, y1 (inclusive), its
                                    ;   command (0: nothing shows), its source's corner x, y (2)
RGE_LMMM:   equ 0x98                ; LMMM with TIMP (the sheets' 0s are transparent)
RGE_HMMV:   equ 0xC0                ; HMMV with RG_GREEN_FILL
RGE_HMMM:   equ 0xD0
RGR_MAX:    equ 2 * RGE_N           ; dirty rectangles at most (x0, y0, x1, y1 each)
RGO_N:      equ 3 + RGE_N           ; a rectangle's commands: its three restores, then the elements

; (Build checks, no bytes: the renderer's RAM in objl_ram after the wanted state and before the
; logic's (msx.inc), the picture and position records as read here, HMMV's fill byte, the blob's
; streams in rvu_tab's order.)
        ds 0 - (rg_want + RGW_ROOM - 1) / rgs0
        ds 0 - (rgs0 + RGS_LEN - 1) / rgs1
        ds 0 - (rgs1 + RGS_LEN - 1) / rgt
        ds 0 - (rgt + RGS_LEN - 1) / rg_rects
        ds 0 - (rg_rects + 4 * RGR_MAX - 1) / rg_el
        ds 0 - (rg_el + RGE_N * RGE_LEN - 1) / rg_elp0
        ds 0 - (rg_elp0 + RGE_N * RGE_LEN - 1) / rg_elp1
        ds 0 - (rg_elp1 + RGE_N * RGE_LEN - 1) / rg_btop
        ds 0 - (RG_PIC_LEN - 12) * (RG_PIC_LEN - 12) - (RG_PIC_SX - 3) * (RG_PIC_SX - 3) - (RG_PIC_SY - 4) * (RG_PIC_SY - 4) - (RG_PIC_TX - 6) * (RG_PIC_TX - 6) - (RG_PIC_TY - 7) * (RG_PIC_TY - 7) - (RG_PIC_W - 8) * (RG_PIC_W - 8) - (RG_PIC_H - 9) * (RG_PIC_H - 9)
        ds 0 - (RG_PLACE_LEN - 8) * (RG_PLACE_LEN - 8) - RG_PLACE_X * RG_PLACE_X - (RG_PLACE_Y - 2) * (RG_PLACE_Y - 2) - (RG_PLACE_W - 3) * (RG_PLACE_W - 3) - (RG_PLACE_H - 4) * (RG_PLACE_H - 4) - (RG_PLACE_FX - 5) * (RG_PLACE_FX - 5) - (RG_PLACE_FY - 6) * (RG_PLACE_FY - 6)
        ds 0 - (RG_GREEN_FILL - 255) * (RG_GREEN_FILL - 255) - RG_ST_C * RG_ST_C
        ds 0 - RG_GFX_SCENE_OFS * RG_GFX_SCENE_OFS - (RG_GFX_STRIP_OFS - RG_GFX_SCENE_LEN) * (RG_GFX_STRIP_OFS - RG_GFX_SCENE_LEN) - (RG_GFX_S0_OFS - RG_GFX_STRIP_OFS - RG_GFX_STRIP_LEN) * (RG_GFX_S0_OFS - RG_GFX_STRIP_OFS - RG_GFX_STRIP_LEN)
        ds 0 - (RG_GFX_S1_OFS - RG_GFX_S0_OFS - RG_GFX_S0_LEN) * (RG_GFX_S1_OFS - RG_GFX_S0_OFS - RG_GFX_S0_LEN) - (RG_GFX_S2_OFS - RG_GFX_S1_OFS - RG_GFX_S1_LEN) * (RG_GFX_S2_OFS - RG_GFX_S1_OFS - RG_GFX_S1_LEN) - (RG_GFX_S3_OFS - RG_GFX_S2_OFS - RG_GFX_S2_LEN) * (RG_GFX_S3_OFS - RG_GFX_S2_OFS - RG_GFX_S2_LEN)

; ----- the entry -----

; The stage's screen, its palette black (above).
rg_show:
        call vdp_wait
        ld hl,RG_GFX_SCENE_OFS
        call rvu_at
        ld ix,rvu_tab
        ld b,6
rvs_s:  push bc                     ; (a stream: its lines one after the other in the blob)
        ld e,(ix + 0)
        ld d,(ix + 1)
        ld c,(ix + 4)
rvs_l:  push bc
        push de
        push hl
        ex de,hl
        ld e,(ix + 2)
        call vram_write
        pop hl
        ld b,(ix + 3)
        call rvu_line
        call vram_done
        pop de
        push hl
        ld hl,128
        add hl,de
        ex de,hl                    ; (its next line in VRAM)
        pop hl
        pop bc
        dec c
        jr nz,rvs_l
        ld bc,5
        add ix,bc
        pop bc
        djnz rvs_s
        ld a,BANK_FRONT
        call bank_8000              ; (FRONT at 8000h again)
        ld a,RG_CAM_START
        ld (rgr_c),a
        ld hl,0
        ld (rgr_rx0),hl             ; (x0 0, y0 0)
        ld hl,(RG_VIEW_H - 1) * 256 + 255
        ld (rgr_rx1),hl             ; (x1 255, y1 161: the whole page)
        xor a
rvs_pg: ld (rgr_page),a             ; both pages: the clean scene at c (the restores of a build)
        xor a
rvs_ph: push af
        call rvo_do
        ld hl,rgr_cmd
        call nc,vdp_cmd
        pop af
        inc a
        cp 3
        jr c,rvs_ph
        ld a,(rgr_page)
        inc a
        cp 2
        jr c,rvs_pg
        ld e,RG_LINE_VRAM >> 16
        ld hl,RG_LINE_VRAM & 0xFFFF
        call vram_write             ; the line patterns: pattern k, column 0 set on rows 0..k (OUT_line.spr)
        ld c,0
rvs_p:  ld d,0
        ld b,16
rvs_r:  ld a,c
        cp d
        ld a,0x80
        jr nc,rvs_o
        xor a
rvs_o:  out (VDP_DATA),a
        inc d
        djnz rvs_r
        ld b,16
        xor a
rvs_z:  out (VDP_DATA),a            ; (its right half)
        djnz rvs_z
        inc c
        ld a,c
        cp RG_LINE_PATS
        jr c,rvs_p
        call vram_done
        ld hl,SPR_COL_A & 0xFFFF
        call rvs_col
        ld hl,SPR_COL_B & 0xFFFF
        call rvs_col
        ld hl,RG_SAT_A & 0xFFFF
        call rvh_sat
        ld hl,RG_SAT_B & 0xFFFF
        call rvh_sat
        ld hl,rgs0
        call rvs_st
        ld hl,rgs1
        call rvs_st
        ld hl,rg_elp0
        ld bc,2 * RGE_N * RGE_LEN   ; (rg_elp1 follows: nothing drawn in either)
        xor a
        call fill
        xor a
        ld (rgr_state),a
        ld (rgr_shown),a            ; (the intro's list: page 0)
        ld hl,(frv_pass)
        ld (rgr_fr),hl              ; (the first build after the first pass)
        ret

; HL = a set's colour table (page 3): the rows of sprites 0 to RG_SPR_MAX - 1 all RG_C_GREEN.
rvs_col:
        ld e,SPR_COL_A >> 16
        call vram_write
        ld a,RG_C_GREEN
        ld c,RG_SPR_MAX
rvs_cs: ld b,16
rvs_cr: out (VDP_DATA),a
        djnz rvs_cr
        dec c
        jr nz,rvs_cs
        jp vram_done

; HL = a page's shown state: the clean scene at the camera's start, nothing drawn, pass 0.
rvs_st: push hl
        ld bc,RGS_LEN
        ld a,RG_NONE
        call fill
        pop ix
        ld a,RG_CAM_START
        ld (ix + RG_ST_C),a
        ld (ix + RG_ST_S),a
        xor a
        ld (ix + RG_ST_CROSS),a
        ld (ix + RG_ST_CROSS + 1),a
        ld (ix + RG_ST_CROSS + 2),a
        ld (ix + RG_ST_CROSS + 3),a
        ld (ix + RG_ST_LEN),a
        ld (ix + RG_ST_LEN + 1),a
        ret

; range_gfx.bin's streams, in the blob's order: VRAM (its low word, its bit 16), bytes a line, lines
; (each line 128 bytes after the one before: tools/msxrange.py)
rvu_tab:
        dw RG_GFX_SCENE_VRAM & 0xFFFF
        db RG_GFX_SCENE_VRAM >> 16, RG_GFX_SCENE_BPL, RG_GFX_SCENE_LINES
        dw RG_GFX_STRIP_VRAM & 0xFFFF
        db RG_GFX_STRIP_VRAM >> 16, RG_GFX_STRIP_BPL, RG_GFX_STRIP_LINES
        dw RG_GFX_S0_VRAM & 0xFFFF
        db RG_GFX_S0_VRAM >> 16, RG_GFX_S0_BPL, RG_GFX_S0_LINES
        dw RG_GFX_S1_VRAM & 0xFFFF
        db RG_GFX_S1_VRAM >> 16, RG_GFX_S1_BPL, RG_GFX_S1_LINES
        dw RG_GFX_S2_VRAM & 0xFFFF
        db RG_GFX_S2_VRAM >> 16, RG_GFX_S2_BPL, RG_GFX_S2_LINES
        dw RG_GFX_S3_VRAM & 0xFFFF
        db RG_GFX_S3_VRAM >> 16, RG_GFX_S3_BPL, RG_GFX_S3_LINES

; HL = an offset in range_gfx.bin -> its bank at 8000h (rgr_bank), HL = its address there.
rvu_at: ld a,h
        rlca
        rlca
        rlca
        and 7
        add a,RANGE_GFX_BANK
        ld (rgr_bank),a
        call bank_8000
        ld a,h
        and 0x1F
        or 0x80
        ld h,a
        ret

; B = bytes (1-128) from HL (rgr_bank at 8000h) to port 98h, the next bank from A000h on (no OTIR
; reads past 9FFFh) -> HL = the next byte's place (rgr_bank). Changes C, D, E.
rvu_line:
        ld a,h
        cp 0x9F
        jr c,rvu_all                ; (256 bytes or more to the window's end)
        ld a,l
        neg                         ; (those left: 256 - L)
        jr z,rvu_all
        cp b
        jr nc,rvu_all
        ld e,a
        ld a,b
        sub e
        ld d,a                      ; (the rest, from the next bank)
        ld b,e
        ld c,VDP_DATA
        otir
        call rvu_nb
        ld b,d
rvu_all:
        ld c,VDP_DATA
        otir
        ld a,h
        cp 0xA0
        ret nz
rvu_nb: ld a,(rgr_bank)
        inc a
        ld (rgr_bank),a
        call bank_8000
        ld hl,0x8000
        ret

; ----- the renderer -----

; The state machine (above): idle (rgr_state 0), preparing the build (3: the target's elements and
; the dirty rectangles, a group of elements a call), building (1: a command a call), finishing (4:
; the page's sprites, its shown state, its list), published (2).
; Each call does a bounded piece of work (a few thousand T-states), so that the pass after the next
; VBLANK starts on time.
rg_feed:
        ld a,(rgr_state)
        dec a
        jr z,rvf_bld
        dec a
        jr z,rvf_pub
        dec a
        jr z,rvf_prep
        dec a
        jr z,rvf_end
        ld hl,(frv_pass)
        ld de,(rgr_fr)
        or a
        sbc hl,de
        ret z                       ; (no pass since the last build started)
        ld hl,(frv_pass)
        ld (rgr_fr),hl
        call rvb_start
        ret z                       ; (the page on screen shows that pass's state already)
        ld a,3
        ld (rgr_state),a
        ret
rvf_prep:
        call rvb_group
        ret nc
        ld a,1
        ld (rgr_state),a            ; (the commands from the next call on)
        ret
rvf_bld:
        call vdp_busy
        ret nz
        call rvo_next
        jr c,rvf_fin
        ld hl,rgr_cmd
        jp vdp_cmd
rvf_fin:
        ld a,4
        ld (rgr_state),a            ; (the last command is done: the page is complete)
        ret
rvf_end:
        call rva_sat                ; (the page's sprite set)
        ld a,(rgr_page)
        call rvb_spage
        push de
        ex de,hl
        ld hl,rgt
        ld bc,RGS_LEN
        ldir                        ; (what the page holds now: its shown state,
        pop de
        ld hl,rg_el
        ld bc,RGE_N * RGE_LEN
        ldir                        ;  its elements)
        call rg_list
        ld a,2
        ld (rgr_state),a
        ret
rvf_pub:
        ld a,(app_seq)
        ld b,a
        ld a,(pub_seq)
        cp b
        ret nz                      ; (not on screen yet)
        ld a,(rgr_page)
        ld (rgr_shown),a
        xor a
        ld (rgr_state),a
        ret

; A = a page -> HL = its shown state, DE = its elements.
rvb_spage:
        or a
        ld hl,rgs0
        ld de,rg_elp0
        ret z
        ld hl,rgs1
        ld de,rg_elp1
        ret

; A build's start: the wanted state taken whole (rgt: its page's c for its camera s, its pass) -> Z
; when the page on screen shows it already (its pass is this one then); else (NZ) the other page is
; the target, no dirty rectangle yet (the whole page when its c is another, or it was never built),
; its groups of elements next (rvb_group).
rvb_start:
        ld hl,rg_want
        ld de,rgt
        ld bc,RG_ST_LEN
        ldir
        ld hl,(frv_pass)
        ld (rgt + RG_ST_LEN),hl
        ld a,(rgt + RG_ST_S)
        add a,RG_C_ROUND
        and 0xF0
        ld (rgt + RG_ST_C),a        ; (the multiple of 16 that R#18 shows s from)
        ld a,(rgr_shown)
        call rvb_spage
        ld de,rgt
        ld b,RG_ST_LEN
rvb_eq: ld a,(de)
        cp (hl)
        jr nz,rvb_go
        inc hl
        inc de
        djnz rvb_eq
        ld de,(frv_pass)
        ld (hl),e                   ; (that page shows this pass's state too)
        inc hl
        ld (hl),d
        xor a                       ; (Z)
        ret
rvb_go: ld a,(rgr_shown)
        xor 1
        ld (rgr_page),a
        xor a
        ld (rgr_ri),a
        ld (rgr_ph),a
        ld (rgr_rn),a
        ld (rgr_eg),a
        ld (rgr_full),a
        ld a,(rgr_page)
        call rvb_spage
        ld a,(rgt + RG_ST_C)
        cp (hl)                     ; (the page's c: RG_ST_C is 0)
        jr z,rvb_nz
        ld a,1
        ld (rgr_full),a             ; (another c, or never built: the whole page)
        ld bc,0
        ld de,255 * 256 + RG_VIEW_H - 1
        call rvd_add
rvb_nz: or 1
        ret

; The target's elements, a group at a time (rvg_tab: each pop-up and its front layer, the big target,
; the dissolve, the box's edges, the crosshair's row): a group whose state bytes the target page
; holds already keeps that page's elements; another is made again (rvm_...) and, unless the whole
; page is dirty, the elements that changed give dirty rectangles (rvd_el) -> NC after a group made
; again (one a call), carry once the last group is done.
rvb_group:
        ld a,(rgr_eg)
        cp RGG_N
        ccf
        ret c
        ld l,a
        ld h,0
        add hl,hl
        ld d,h
        ld e,l
        add hl,hl
        add hl,de                   ; (6 x the group)
        ld de,rvg_tab
        add hl,de
        ld c,(hl)                   ; (its state's offset,
        inc hl
        ld b,(hl)                   ;  length,
        inc hl
        ld e,(hl)                   ;  first element,
        inc hl
        ld d,(hl)                   ;  elements,
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a                      ;  routine)
        ld (rgr_rt),hl
        ld (rgr_ge),de
        ld a,c
        ld (rgr_go),a
        ld a,(rgr_full)
        or a
        jr nz,rvg_make
        ld a,(rgr_page)
        call rvb_spage
        push de                     ; (the page's elements)
        ld a,c
        call rv_addh                ; (the group's state bytes in the page's state,
        ld de,rgt
        ld a,c
        call rv_adde                ;  and in the target)
rvg_cmp: ld a,(de)
        cp (hl)
        jr nz,rvg_mk
        inc hl
        inc de
        djnz rvg_cmp
        ld a,(rgr_ge)               ; the same: the page's elements
        add a,a
        add a,a
        add a,a
        ld c,a
        ld b,0
        pop hl
        add hl,bc
        ld de,rg_el
        ex de,hl
        add hl,bc
        ex de,hl
        ld a,(rgr_ge + 1)
        add a,a
        add a,a
        add a,a
        ld c,a
        ldir
        ld hl,rgr_eg
        inc (hl)
        jr rvb_group
rvg_mk: pop de
rvg_make:
        ld a,(rgt + RG_ST_C)
        ld (rgr_c),a
        ld a,(rgr_ge)
        add a,a
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,rg_el
        add hl,de
        ld (rgr_ep),hl
        ld a,(rgr_go)
        ld e,a
        ld ix,rgt
        add ix,de                   ; (the group's record)
        ld hl,(rgr_rt)
        call rv_jphl                ; its elements
        ld a,(rgr_full)
        or a
        jr nz,rvg_nx
        ld a,(rgr_page)
        call rvb_spage
        ld a,(rgr_ge)
        add a,a
        add a,a
        add a,a
        ld c,a
        ld b,0
        ex de,hl
        add hl,bc
        push hl
        pop ix                      ; (as the page holds them)
        ld iy,rg_el
        add iy,bc                   ; (as the target has them)
        ld a,(rgr_ge + 1)
        ld b,a
rvg_d:  push bc
        call rvd_el
        ld de,RGE_LEN
        add ix,de
        add iy,de
        pop bc
        djnz rvg_d
rvg_nx: ld hl,rgr_eg
        inc (hl)
        or a                        ; (NC)
        ret
rv_jphl:
        jp (hl)

; per group: its state bytes' offset and length, its first element, its elements, its routine (IX =
; its state bytes in rgt, rgr_ep = its first element in rg_el)
rvg_tab:
        db RG_ST_POP, RG_POP_LEN, 0, 2
        dw rvm_pop
        db RG_ST_POP + RG_POP_LEN, RG_POP_LEN, 2, 2
        dw rvm_pop
        db RG_ST_BIG, RG_BIG_LEN, 4, 1
        dw rvm_big
        db RG_ST_FX, RG_FX_LEN, 5, 1
        dw rvm_fx
        db RG_ST_BOX, RG_ST_LEN - RG_ST_BOX, 6, 2
        dw rvm_box
        db RG_ST_CROSS, RG_ST_BOX - RG_ST_CROSS, 8, 1
        dw rvm_cross
RGG_N:      equ 6

; IX = an element as the page holds it, IY = as the target has it: when they differ, the rectangles
; to restore and compose again (their union when they meet).
rvd_el: ld a,(ix + 4)
        or (iy + 4)
        ret z                       ; (neither shows)
        push ix
        pop hl
        push iy
        pop de
        ld b,RGE_LEN
rvd_eq: ld a,(de)
        cp (hl)
        jr nz,rvd_ne
        inc hl
        inc de
        djnz rvd_eq
        ret                         ; (the same drawing)
rvd_ne: ld a,(ix + 4)
        or a
        jr z,rvd_new
        ld a,(iy + 4)
        or a
        jr z,rvd_old
        ld a,(iy + 2)               ; do they meet?
        cp (ix + 0)
        jr c,rvd_old
        ld a,(ix + 2)
        cp (iy + 0)
        jr c,rvd_old
        ld a,(iy + 3)
        cp (ix + 1)
        jr c,rvd_old
        ld a,(ix + 3)
        cp (iy + 1)
        jr c,rvd_old
        ld b,(ix + 0)               ; their union
        ld a,(iy + 0)
        cp b
        jr nc,rvd_1
        ld b,a
rvd_1:  ld c,(ix + 1)
        ld a,(iy + 1)
        cp c
        jr nc,rvd_2
        ld c,a
rvd_2:  ld d,(ix + 2)
        ld a,(iy + 2)
        cp d
        jr c,rvd_3
        ld d,a
rvd_3:  ld e,(ix + 3)
        ld a,(iy + 3)
        cp e
        jr c,rvd_add
        ld e,a
        jr rvd_add
rvd_old:
        ld b,(ix + 0)
        ld c,(ix + 1)
        ld d,(ix + 2)
        ld e,(ix + 3)
        call rvd_add
        ld a,(iy + 4)
        or a
        ret z
rvd_new:
        ld b,(iy + 0)
        ld c,(iy + 1)
        ld d,(iy + 2)
        ld e,(iy + 3)
; B, C, D, E = a rectangle of the page (x0, y0, x1, y1): widened to whole bytes (HMMM's), added to
; the dirty rectangles unless one of them holds it; with no room left, the whole page instead.
rvd_add:
        ld a,b
        and 0xFE
        ld b,a
        ld a,d
        or 1
        ld d,a
        ld hl,rg_rects
        ld a,(rgr_rn)
        or a
        jr z,rvd_put
rvd_lp: push af
        ld a,b
        cp (hl)
        jr c,rvd_n0
        inc hl
        ld a,c
        cp (hl)
        jr c,rvd_n1
        inc hl
        ld a,(hl)
        cp d
        jr c,rvd_n2
        inc hl
        ld a,(hl)
        cp e
        jr c,rvd_n3
        pop af
        ret                         ; (inside one already)
rvd_n0: inc hl
rvd_n1: inc hl
rvd_n2: inc hl
rvd_n3: inc hl
        pop af
        dec a
        jr nz,rvd_lp
rvd_put:
        ld a,(rgr_rn)
        cp RGR_MAX
        jr nc,rvd_full
        inc a
        ld (rgr_rn),a
        ld (hl),b
        inc hl
        ld (hl),c
        inc hl
        ld (hl),d
        inc hl
        ld (hl),e
        ret
rvd_full:
        ld a,1
        ld (rgr_rn),a
        ld hl,rg_rects
        ld (hl),0
        inc hl
        ld (hl),0
        inc hl
        ld (hl),255
        inc hl
        ld (hl),RG_VIEW_H - 1
        ret

; The build's next command into rgr_cmd -> NC; carry when every rectangle is done. A rectangle's
; commands (RGO_N): its restores from the clean scene (rvo_do 0-2), then each element of the target
; that meets it, cut to it, in z-order (3 on).
rvo_next:
        ld a,(rgr_ri)
        ld hl,rgr_rn
        cp (hl)
        ccf
        ret c                       ; (no rectangle left)
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,rg_rects
        add hl,de
        ld de,rgr_rx0
        ld bc,4
        ldir                        ; (the rectangle)
        ld a,(rgr_ph)
        ld b,a
        inc a
        cp RGO_N
        jr c,rvn_s
        ld hl,rgr_ri
        inc (hl)
        xor a
rvn_s:  ld (rgr_ph),a
        ld a,b
        call rvo_do
        jr c,rvo_next
        ret

; A = a command of the rectangle rgr_rx0..rgr_ry1 (page x 0-255, lines 0-161) in page rgr_page at
; the camera's coarse offset rgr_c -> NC with it in rgr_cmd, carry when it has nothing to draw.
; 0-2: its restore from page 2's clean scene (the strip's upper and lower blocks for Amiga columns
; 0-63, the main part for 64 on); 3 on: the target's element A - 3 cut to it.
rvo_do: cp 3
        jp nc,rvo_el
        or a
        jr z,rvo_p0
        dec a
        jr z,rvo_p1
        ld a,(rgr_c)                ; the main part: Amiga columns 64 on, page 2 from x 0
        ld c,a
        ld b,0
        ld a,(rgr_rx1)
        ld l,a
        ld h,0
        add hl,bc                   ; (its last Amiga column, a1)
        ld de,RG_SPLIT_COL
        or a
        sbc hl,de
        ret c                       ; (left of column 64)
        push hl
        ld a,(rgr_rx0)
        ld l,a
        ld h,0
        add hl,bc
        or a
        sbc hl,de
        jr nc,rv2_x
        ld hl,0                     ; (from column 64)
rv2_x:  ex de,hl                    ; DE = SX: the first column - 64
        pop hl
        or a
        sbc hl,de
        inc hl
        ld (rgr_nx),hl
        ld a,e
        add a,RG_SPLIT_COL
        sub c
        ld b,a                      ; DX: the first column - c
        ex de,hl
        ld a,(rgr_ry0)
        ld c,a
        ld a,(rgr_ry1)
        sub c
        inc a
        ld (rgr_ny),a
        ld a,c
        ld de,RG_SCENE_Y
        call rv_adde
        ld a,RGE_HMMM
        jp rvo_set
rvo_p0: call rvo_strip              ; the strip's upper block: rows RG_TOP-90 (lines 0-80)
        ret c
        ld a,(rgr_ry0)
        cp RG_STRIP_ROWS
        ccf
        ret c
        ld c,a
        ld a,(rgr_ry1)
        cp RG_STRIP_ROWS
        jr c,rv0_y
        ld a,RG_STRIP_ROWS - 1
rv0_y:  sub c
        inc a
        ld (rgr_ny),a
        ld a,c
        ld de,RG_STRIP_Y
        call rv_adde
        ld a,RGE_HMMM
        jp rvo_set
rvo_p1: call rvo_strip              ; its lower block: rows 91-171 (lines 81-161) at x + RG_STRIP_X2
        ret c
        ld a,(rgr_ry1)
        cp RG_STRIP_ROWS
        ret c
        ld a,(rgr_ry0)
        cp RG_STRIP_ROWS
        jr nc,rv1_y
        ld a,RG_STRIP_ROWS
rv1_y:  ld c,a
        ld a,(rgr_ry1)
        sub c
        inc a
        ld (rgr_ny),a
        ld a,c
        sub RG_STRIP_ROWS
        ld de,RG_STRIP_Y
        call rv_adde
        ld a,l
        add a,RG_STRIP_X2
        ld l,a
        ld a,RGE_HMMM
        jp rvo_set
; -> carry when the rectangle has no Amiga column below 64; else HL = its first (a0: the strip's
; x), rgr_nx = its columns there, B = their page x.
rvo_strip:
        ld a,(rgr_c)
        ld c,a
        ld a,(rgr_rx0)
        add a,c
        ret c
        cp RG_SPLIT_COL
        ccf
        ret c
        ld l,a
        ld h,0
        ld e,a
        ld a,(rgr_rx1)
        add a,c
        jr c,rvt_m
        cp RG_SPLIT_COL
        jr c,rvt_n
rvt_m:  ld a,RG_SPLIT_COL - 1
rvt_n:  sub e
        inc a
        ld (rgr_nx),a
        xor a
        ld (rgr_nx + 1),a
        ld a,(rgr_rx0)
        ld b,a
        ret                         ; (NC)
; an element of the target, cut to the rectangle
rvo_el: sub 3
        add a,a
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld iy,rg_el
        add iy,de
        ld a,(iy + 4)
        or a
        scf
        ret z                       ; (nothing of it shows)
        ld a,(rgr_rx0)
        cp (iy + 0)
        jr nc,rvq_1
        ld a,(iy + 0)
rvq_1:  ld (rgr_ex0),a              ; (the larger x0,
        ld a,(rgr_ry0)
        cp (iy + 1)
        jr nc,rvq_2
        ld a,(iy + 1)
rvq_2:  ld (rgr_ey0),a              ;  y0,
        ld a,(rgr_rx1)
        cp (iy + 2)
        jr c,rvq_3
        ld a,(iy + 2)
rvq_3:  ld (rgr_ex1),a              ;  the smaller x1,
        ld a,(rgr_ry1)
        cp (iy + 3)
        jr c,rvq_4
        ld a,(iy + 3)
rvq_4:  ld (rgr_ey1),a              ;  y1)
        ld hl,rgr_ex0
        ld a,(rgr_ex1)
        cp (hl)
        ret c                       ; (no column in common)
        ld b,(hl)                   ; (DX)
        sub b
        ld l,a
        ld h,0
        inc hl
        ld (rgr_nx),hl
        ld hl,rgr_ey0
        ld a,(rgr_ey1)
        cp (hl)
        ret c                       ; (no line in common)
        ld c,(hl)                   ; (DY's line)
        sub c
        inc a
        ld (rgr_ny),a
        ld a,b
        sub (iy + 0)
        add a,(iy + 5)
        ld l,a
        ld h,0                      ; SX: its source x + the cut
        ld a,c
        sub (iy + 1)
        ld e,(iy + 6)
        ld d,(iy + 7)
        call rv_adde                ; SY
        ld a,(iy + 4)
; HL = SX, DE = SY, B = DX, C = DY's line in the page being built, rgr_nx, rgr_ny, A = the command
; -> rgr_cmd (R#32-R#46), NC.
rvo_set:
        ld (rgr_cmd + 14),a
        ld (rgr_cmd + 0),hl
        ld (rgr_cmd + 2),de
        ld a,b
        ld (rgr_cmd + 4),a
        ld a,c
        ld (rgr_cmd + 6),a
        ld a,(rgr_page)
        ld (rgr_cmd + 7),a          ; (DY in that page)
        ld hl,(rgr_nx)
        ld (rgr_cmd + 8),hl
        ld a,(rgr_ny)
        ld (rgr_cmd + 10),a
        xor a
        ld (rgr_cmd + 5),a
        ld (rgr_cmd + 11),a
        ld (rgr_cmd + 13),a         ; (ARG: rightwards, downwards, VRAM to VRAM)
        dec a
        ld (rgr_cmd + 12),a         ; (CLR: HMMV's two green pixels, RG_GREEN_FILL; the moves ignore it)
        or a
        ret

; DE = DE + A (A unsigned).
rv_adde:
        add a,e
        ld e,a
        ret nc
        inc d
        ret

; ----- the elements -----

; The elements of a group (rvb_group), IX = its state bytes in rgt, from rgr_ep on: per element, at
; the coarse offset rgr_c, the part of the page it draws (Amiga columns c..c + 255, rows
; RG_TOP..RG_TOP + RG_VIEW_H - 1), its command, the source of that part's corner; command 0 when
; nothing of it shows. The pop-ups are cut to their position's rectangle (each front layer covers its
; pop-up's part), the big target at its clip (bitplane x below clip - 128), the box's edges to rows
; 0..RG_EDGE_ROWS - 1 (tools/msxrange.py page_rows' rules).

; the crosshair's row ($B9E, all 320 columns) while it is on ($B9A not 0): IX = RG_ST_CROSS's bytes
rvm_cross:
        ld a,(ix + 0)
        or (ix + 1)
        jp z,rvm_no
        ld e,(ix + 2)
        ld d,(ix + 3)
        ld a,(rgr_c)
        ld l,a
        ld h,0
        ld bc,1                     ; (B = 0: 256 columns; one row)
        ld iy,rgw_x0
        call rv_setr
        ld a,RGE_HMMV
        jp rvm_put

; IX = a pop-up's record (RG_POP_...): its picture cut to its position's rectangle, then the
; position's front layer over the same part.
rvm_pop:
        ld a,(ix + RG_POP_PLACE)
        cp RG_NONE
        jp z,rvm_no2
        add a,a
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,rgt_places
        add hl,de
        push hl
        ld a,(ix + RG_POP_PIC)
        ld l,(ix + RG_POP_X)
        ld h,(ix + RG_POP_X + 1)
        ld e,(ix + RG_POP_Y)
        ld d,(ix + RG_POP_Y + 1)
        call rvm_org                ; (the picture's block)
        pop hl
        push hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        push de
        ld e,(hl)
        inc hl
        ld b,(hl)
        inc hl
        ld c,(hl)
        ld d,0
        pop hl
        ld iy,rgk_x0
        call rv_setr                ; (the position's rectangle)
        call rv_and
        ld a,RGE_LMMM
        call rvm_put
        pop hl                      ; the front layer: its block covers the position's rectangle
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (rgw_ax),de
        ld e,(hl)
        ld d,0
        ld (rgw_ay),de
        inc hl
        inc hl
        inc hl
        ld a,(hl)
        ld (rgw_sx),a
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (rgw_sy),de
        ld a,RGE_LMMM
        jp rvm_put                  ; (the same part: rgw is cut already)
rvm_no2:
        call rvm_no
rvm_no: ld iy,(rgr_ep)              ; (an element of which nothing shows)
        ld (iy + 4),0
rvm_nx: ld de,RGE_LEN
        add iy,de
        ld (rgr_ep),iy
        ret

; the big target ($1F3F6's draw), cut at its clip: IX = RG_ST_BIG's bytes
rvm_big:
        ld a,(ix + RG_BIG_PIC)
        cp RG_NONE
        jp z,rvm_no
        ld l,(ix + RG_BIG_X)
        ld h,(ix + RG_BIG_X + 1)
        ld e,(ix + RG_BIG_Y)
        ld d,(ix + RG_BIG_Y + 1)
        call rvm_org
        ld l,(ix + RG_BIG_CLIP)
        ld h,(ix + RG_BIG_CLIP + 1)
        ld de,-129
        add hl,de
        ex de,hl                    ; (its last column: bitplane x clip - 128 - 1)
        ld hl,rgw_x0 + 2
        call rv_le
        ld a,RGE_LMMM
        jp rvm_put

; the dissolve's frame ($1F83A's draw): IX = RG_ST_FX's bytes
rvm_fx: ld a,(ix + RG_FX_PIC)
        cp RG_NONE
        jp z,rvm_no
        ld l,(ix + RG_FX_X)
        ld h,(ix + RG_FX_X + 1)
        ld e,(ix + RG_FX_Y)
        ld d,(ix + RG_FX_Y + 1)
        call rvm_org
        ld a,RGE_LMMM
        jp rvm_put

; the fire box's top and bottom edges while n is 1-8 ($1ED5A: rows Y -/+ 16n below RG_EDGE_ROWS,
; from bitplane x C - 16n - RG_EDGE_DX, 32n wide): IX = RG_ST_BOX's bytes
rvm_box:
        ld a,(ix + RG_BOX_N)
        dec a
        cp 8
        jp nc,rvm_no2               ; (0 or RG_NONE: no box)
        inc a
        add a,a
        add a,a
        add a,a
        add a,a
        ld (rgw_n16),a
        ld c,a
        ld b,0
        ld l,(ix + RG_BOX_Y)
        ld h,(ix + RG_BOX_Y + 1)
        or a
        sbc hl,bc
        call rvm_edge               ; (the top one)
        ld a,(rgw_n16)
        ld c,a
        ld b,0
        ld l,(ix + RG_BOX_Y)
        ld h,(ix + RG_BOX_Y + 1)
        add hl,bc                   ; (the bottom one)
rvm_edge:
        bit 7,h
        jp nz,rvm_no                ; (above row 0)
        ld de,RG_EDGE_ROWS
        push hl
        or a
        sbc hl,de
        pop de                      ; (the row)
        jp p,rvm_no                 ; (row RG_EDGE_ROWS on)
        ld a,(rgw_n16)
        ld c,a
        ld b,0
        ld l,(ix + RG_BOX_C)
        ld h,(ix + RG_BOX_C + 1)
        or a
        sbc hl,bc
        ld bc,-RG_EDGE_DX
        add hl,bc                   ; (C - 16n - RG_EDGE_DX)
        ld a,(rgw_n16)
        add a,a
        ld b,a                      ; (32n; n = 8: 0, 256 columns)
        ld c,1
        ld iy,rgw_x0
        call rv_setr
        ld a,RGE_HMMV
        jp rvm_put

; A = a picture (rgt_pics), HL = its draw's D0 (bitplane x + 128), DE = D1 (its top row) -> rgw: its
; block's box (the trimmed picture); rgw_ax, rgw_ay: the block's corner; rgw_sx, rgw_sy: where the
; sheets hold that corner.
rvm_org:
        ld bc,-128
        add hl,bc
        ld (rgw_ax),hl
        ld (rgw_ay),de
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        ld b,h
        ld c,l
        add hl,hl
        add hl,bc                   ; (12 x the picture: RG_PIC_LEN)
        ld bc,rgt_pics + RG_PIC_SX
        add hl,bc
        ld a,(hl)
        ld (rgw_sx),a
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        ld (rgw_sy),bc
        ld a,(hl)                   ; (the trim)
        inc hl
        ld de,(rgw_ax)
        call rv_adde
        ld (rgw_ax),de
        ld a,(hl)
        inc hl
        ld de,(rgw_ay)
        call rv_adde
        ld (rgw_ay),de
        ld b,(hl)                   ; (its size)
        inc hl
        ld c,(hl)
        ld hl,(rgw_ax)
        ld iy,rgw_x0
; HL = x, DE = y, B = w (0: 256), C = h (1-255) -> the rectangle at IY: x0, x1, y0, y1 (words).
rv_setr:
        ld (iy + 0),l
        ld (iy + 1),h
        ld (iy + 4),e
        ld (iy + 5),d
        ld a,b
        dec a
        call rv_addh
        ld (iy + 2),l
        ld (iy + 3),h
        ex de,hl
        ld a,c
        dec a
        call rv_addh
        ld (iy + 6),l
        ld (iy + 7),h
        ret
rv_addh:
        add a,l
        ld l,a
        ret nc
        inc h
        ret

; rgw cut to rgk (x0, x1, y0, y1: signed words, within +-4000).
rv_and: ld hl,rgw_x0
        ld de,(rgk_x0)
        call rv_ge
        ld hl,rgw_x0 + 2
        ld de,(rgk_x0 + 2)
        call rv_le
        ld hl,rgw_x0 + 4
        ld de,(rgk_x0 + 4)
        call rv_ge
        ld hl,rgw_x0 + 6
        ld de,(rgk_x0 + 6)
; HL = a bound (a signed word), DE = a value: the bound at most DE. Changes BC.
rv_le:  ld c,(hl)
        inc hl
        ld b,(hl)
        push hl
        ld h,b
        ld l,c
        or a
        sbc hl,de                   ; (the bound - DE)
        pop hl
        ret m
        ld (hl),d
        dec hl
        ld (hl),e
        ret
; HL = a bound, DE = a value: the bound at least DE. Changes BC.
rv_ge:  ld c,(hl)
        inc hl
        ld b,(hl)
        push hl
        ld h,d
        ld l,e
        or a
        sbc hl,bc                   ; (DE - the bound)
        pop hl
        ret m
        ld (hl),d
        dec hl
        ld (hl),e
        ret

; rgw cut to the view -> the next element: its page rectangle, A = its command, the source of its
; corner (rgw_sx + x0 - rgw_ax, rgw_sy + y0 - rgw_ay; 0 for HMMV); command 0 when nothing is left.
rvm_put:
        push af
        ld a,(rgr_c)
        ld l,a
        ld h,0
        ld de,RG_TOP
        ld bc,RG_VIEW_H             ; (B = 0: 256 columns)
        ld iy,rgk_x0
        call rv_setr
        call rv_and
        ld hl,(rgw_x0 + 2)
        ld de,(rgw_x0)
        or a
        sbc hl,de
        jp m,rvm_none
        ld hl,(rgw_x0 + 6)
        ld de,(rgw_x0 + 4)
        or a
        sbc hl,de
        jp m,rvm_none
        ld iy,(rgr_ep)
        ld a,(rgr_c)
        ld c,a
        ld a,(rgw_x0)
        sub c
        ld (iy + 0),a
        ld a,(rgw_x0 + 2)
        sub c
        ld (iy + 2),a
        ld a,(rgw_x0 + 4)
        sub RG_TOP
        ld (iy + 1),a
        ld a,(rgw_x0 + 6)
        sub RG_TOP
        ld (iy + 3),a
        pop af
        ld (iy + 4),a
        cp RGE_HMMV
        jr nz,rvm_src
        xor a
        ld (iy + 5),a
        ld (iy + 6),a
        ld (iy + 7),a
        jp rvm_nx
rvm_src:
        ld hl,(rgw_x0)
        ld de,(rgw_ax)
        or a
        sbc hl,de
        ld a,(rgw_sx)
        add a,l
        ld (iy + 5),a
        ld hl,(rgw_x0 + 4)
        ld de,(rgw_ay)
        or a
        sbc hl,de
        ld de,(rgw_sy)
        add hl,de
        ld (iy + 6),l
        ld (iy + 7),h
        jp rvm_nx
rvm_none:
        pop af
        jp rvm_no

; ----- the sprites and the list -----

; The target's sprites into its page's set (RG_SAT_A for page 0, RG_SAT_B for page 1), in
; tools/msxrange.py sat's order: the crosshair's line (lines 0 to RG_SPR_LINES - 1 at page x $B9A -
; RG_LINE_DX - c), then the box's left and right sides (32n rows from its top row Y - 16n, cut to
; the same lines, at page x C -/+ 16n - RG_SIDE_DX - c, while Y - 16n >= RG_SIDE_TOP: default 18),
; then Y = 216. A column off the page has no sprite.
rva_sat:
        ld a,(rgr_page)
        or a
        ld hl,RG_SAT_A & 0xFFFF
        jr z,rva_a
        ld hl,RG_SAT_B & 0xFFFF
rva_a:  ld e,RG_SAT_A >> 16
        call vram_write
        ld ix,rgt
        ld l,(ix + RG_ST_CROSS)
        ld h,(ix + RG_ST_CROSS + 1)
        ld a,h
        or l
        jr z,rva_box
        ld de,-RG_LINE_DX
        add hl,de
        call rva_x
        jr c,rva_box
        ld de,RG_SPR_LINES          ; (D = 0: from line 0)
        call rva_col
rva_box:
        ld ix,rgt + RG_ST_BOX       ; (the box's bytes)
        ld a,(ix + RG_BOX_N)
        dec a
        cp 8
        jp nc,rva_end               ; (no box)
        inc a
        add a,a
        add a,a
        add a,a
        add a,a
        ld (rgw_n16),a
        ld c,a
        ld b,0
        ld l,(ix + RG_BOX_Y)
        ld h,(ix + RG_BOX_Y + 1)
        or a
        sbc hl,bc                   ; (its top row)
        ld de,RG_SIDE_TOP
        push hl
        or a
        sbc hl,de
        pop hl
        jp m,rva_end                ; (above RG_SIDE_TOP: the sides never show)
        ld de,-RG_TOP
        add hl,de                   ; (its first line, from -12 on)
        push hl
        ld a,(rgw_n16)
        ld e,a
        ld d,0
        sla e
        rl d                        ; (32n)
        add hl,de                   ; (the line after its last)
        ld de,RG_SPR_LINES
        push hl
        or a
        sbc hl,de
        pop hl
        jp m,rva_e
        ld l,RG_SPR_LINES
rva_e:  ld e,l
        pop hl
        ld d,l
        bit 7,h
        jr z,rva_d
        ld d,0
rva_d:  push de                     ; (D, E: its lines on the page)
        ld a,(rgw_n16)
        ld c,a
        ld b,0
        ld l,(ix + RG_BOX_C)
        ld h,(ix + RG_BOX_C + 1)
        or a
        sbc hl,bc
        ld de,-RG_SIDE_DX
        add hl,de
        call rva_x
        pop de
        push de
        call nc,rva_col             ; (the left side)
        ld a,(rgw_n16)
        ld c,a
        ld b,0
        ld l,(ix + RG_BOX_C)
        ld h,(ix + RG_BOX_C + 1)
        add hl,bc
        ld de,-RG_SIDE_DX
        add hl,de
        call rva_x
        pop de
        call nc,rva_col             ; (the right side)
rva_end:
        ld a,RG_SAT_END
        out (VDP_DATA),a
        jp vram_done

; HL = a bitplane x -> C = its page x (x - c) and NC; carry when it is off the page.
rva_x:  ld a,(rgt + RG_ST_C)
        ld e,a
        ld d,0
        or a
        sbc hl,de
        jp m,rva_no
        ld a,h
        or a
        jr nz,rva_no
        ld c,l
        ret
rva_no: scf
        ret

; C = a page x, D = the first line, E = the line after the last: a column of 16-line sprites (each
; at least 22 T-states after the write before: the 5.37 MHz rule).
rva_col:
        ld a,d
        cp e
        ret nc
        ld a,e
        sub d
        cp 16
        jr c,rva_k
        ld a,16
rva_k:  ld b,a                      ; (its lines)
        ld a,d
        dec a
        out (VDP_DATA),a            ; Y: the line before its first
        ld a,c
        nop
        out (VDP_DATA),a            ; X
        ld a,b
        dec a
        add a,a
        add a,a
        out (VDP_DATA),a            ; the pattern of its lines
        xor a
        nop
        out (VDP_DATA),a
        ld a,d
        add a,b
        ld d,a
        jr rva_col

; The register list of the page built (msx/puzl.asm bs_list's): its page and sprite set, R#18 =
; (s - c) & 15 (level 1's sign: msx/scroll9938.asm), R#25-R#27 = 0 on a V9958; the split shows the
; HUD as in the game.
rg_list:
        call next_list
        push hl
        inc hl
        ld (hl),14                  ; 7 registers (10 on the V9958)
        inc hl
        ex de,hl
        ld hl,rvl_regs
        ld bc,8
        ldir
        ex de,hl
        ld a,(rgr_page)
        or a
        ld bc,R2_PAGE0 * 256 + R5_SET_A
        jr z,rvl_a
        ld bc,R2_PAGE1 * 256 + R5_SET_B
rvl_a:  ld (hl),b
        inc hl
        ld (hl),0x82
        inc hl
        ld a,(rgt + RG_ST_C)
        ld e,a
        ld a,(rgt + RG_ST_S)
        sub e
        and 15
        ld (hl),a                   ; R#18
        inc hl
        ld (hl),0x92
        inc hl
        ld (hl),c
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
        ld b,3
        ld a,0x99
rvl_58: ld (hl),0                   ; V9958: R#25-R#27 = 0 (one page, unscrolled)
        inc hl
        ld (hl),a
        inc hl
        inc a
        djnz rvl_58
        jp list_tail
rvl_regs:
        db 0, 0x97                  ; R#23 first (isr.asm iv_list: the split's R#19 from it)
        db SPLIT_LINE, 0x93         ; R#19: the HUD's split
        db R1_ON, 0x81
        db R8_SPR_ON, 0x88

; ----- the exit -----

; The stage's end (above): the VDP idle (a build in progress is dropped: its page is not on screen),
; the last published list on screen, the play area black from the next VBLANK on (its sprites too:
; they are colour RG_C_GREEN), then both SATs empty and page 2's tiles back (cold.asm tiles_upload:
; the bytes vdp_setup wrote; the title uploads them again in the product). front.asm fe_text then
; shows page 0 without sprites, R#18 = 0.
rg_hide:
        call vdp_wait
rvh_w:  ld a,(app_seq)
        ld b,a
        ld a,(pub_seq)
        cp b
        jr nz,rvh_w
        ld hl,pf_pal
        ld bc,32
        xor a
        call fill
        ld a,(tick)
        ld b,a
rvh_v:  ld a,(tick)
        cp b
        jr z,rvh_v
        ld hl,RG_SAT_A & 0xFFFF
        call rvh_sat
        ld hl,RG_SAT_B & 0xFFFF
        call rvh_sat
        ld a,BANK_FRONT
        call bank_8000
        ld e,4
        jp tiles_upload

; HL = a SAT's low 16 bits (page 3): its first entry Y = 216, no sprite.
rvh_sat:
        ld e,RG_SAT_A >> 16
        call vram_write
        ld a,RG_SAT_END
        out (VDP_DATA),a
        jp vram_done
