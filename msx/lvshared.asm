; Game logic every level bank shares (docs/LEVEL2.md 3.1, 3.3): the spawn walk's shortcuts
; (sw_ptr, sw_prep ... sw_bits), the handlers of the object types levels 1 and 2 both have (3, 4, 12,
; 13, 15, 30, 31 and 45, the hostage) and their helpers (t_xy, t_face, t_col, t_word).
;
; Every level bank starts with the same header (objects.asm lv_htab ... LV_HDR_END) and includes
; this code right after it: msx/level1.asm this file, level 2's bank gen/lvshared_l2.asm, the
; copy tools/mkrom.py writes with every label defined here suffixed _l2 (z80asm's labels are
; global), and every name of the level's own data used here too (the cells: SW_N, SW_XN, SW_YN, sw_xm,
; sw_ym, sw_all, tools/cellmasks.py cells_lN.inc; the original's tables, tools/amitab.py
; at_lN.inc). The copies assemble to the same bytes but those names' values, so every label here
; has the same address in every level bank: objects.asm and special.asm call sw_prep, sw_dset,
; sw_dclr and sw_cell and read sw_ptr at level 1's addresses whichever level bank is mapped
; (tools/mkrom.py checks that each copy's labels equal level 1's).

; The spawn list's entries' addresses in spawn_ram (objects.asm uo_free), SW_MAX of them in every
; level (the walk reads the first SW_N).
sw_ptr:
        dw spawn_ram + 0, spawn_ram + 14, spawn_ram + 28, spawn_ram + 42
        dw spawn_ram + 56, spawn_ram + 70, spawn_ram + 84, spawn_ram + 98
        dw spawn_ram + 112, spawn_ram + 126, spawn_ram + 140, spawn_ram + 154
        dw spawn_ram + 168, spawn_ram + 182, spawn_ram + 196, spawn_ram + 210
        dw spawn_ram + 224, spawn_ram + 238, spawn_ram + 252, spawn_ram + 266
        dw spawn_ram + 280, spawn_ram + 294, spawn_ram + 308, spawn_ram + 322
        dw spawn_ram + 336, spawn_ram + 350, spawn_ram + 364, spawn_ram + 378
        dw spawn_ram + 392, spawn_ram + 406, spawn_ram + 420, spawn_ram + 434
        dw spawn_ram + 448, spawn_ram + 462, spawn_ram + 476, spawn_ram + 490
        dw spawn_ram + 504, spawn_ram + 518, spawn_ram + 532, spawn_ram + 546

; ----- the game logic's shortcuts (the port): their caches -----

; The spawn walk's candidates this tick (objects.asm uo_free): the entries the walk's window can
; reach from the camera's 64-pixel cells (sw_xm, sw_ym: a mask of entries per cell of camera x
; and per cell of camera y, SW_MB bytes: tools/cellmasks.py, the level's cells_lN.inc) or that
; may hold a count or their spawned bit (sw_dirty), as indices in the list's order, FFh after
; the last (sw_list). The others are outside the window with nothing to reset, so the walk
; leaves them as they are.
; Built again only when the cells or the dirty mask changed (sw_key). Also sw_bc, the walk's
; D0 + 1. Called at update_objects' start: nothing moves the camera inside it.
sw_prep:
        ld hl,(gcam_x)
        ld de,0x5E
        add hl,de
        ld (sw_bc),hl
        ld hl,(gcam_x)
        ld b,SW_XN
        call sw_cell
        ld c,a
        ld hl,(gcam_y)
        ld b,SW_YN
        call sw_cell
        ld b,a                      ; B = the y cell, C = the x cell (FFh: outside the tables)
        ld hl,sw_key
        ld a,c
        cp (hl)
        jr nz,swp_new
        inc hl
        ld a,b
        cp (hl)
        jr nz,swp_new
        inc hl
        ld de,sw_dirty
        ld a,(de)
        cp (hl)
        jr nz,swp_new
        inc hl
        inc de
        ld a,(de)
        cp (hl)
        jr nz,swp_new
        inc hl
        inc de
        ld a,(de)
        cp (hl)
        jr nz,swp_new
        inc hl
        inc de
        ld a,(de)
        cp (hl)
        jr nz,swp_new
        inc hl
        inc de
        ld a,(de)
        cp (hl)
        ret z                       ; (the same: sw_list stands; SW_MB bytes of sw_dirty)
swp_new:
        ld hl,sw_key
        ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ex de,hl
        ld hl,sw_dirty
        push bc
        ld bc,SW_MB
        ldir
        pop bc
        ld hl,sw_all
        ld a,c
        cp 0xFF
        jr z,swp_x
        ld e,a
        add a,a
        add a,a
        add a,e                     ; (a cell's mask: SW_MB = 5 bytes)
        ld e,a
        ld d,0
        ld hl,sw_xm
        add hl,de
swp_x:  ld (sw_px),hl
        ld hl,sw_all
        ld a,b
        cp 0xFF
        jr z,swp_y
        ld e,a
        add a,a
        add a,a
        add a,e
        ld e,a
        ld d,0
        ld hl,sw_ym
        add hl,de
swp_y:  ex de,hl                    ; DE = the y cell's mask
        ld hl,(sw_px)               ; HL = the x cell's
        ld ix,sw_dirty
        ld iy,sw_list
        ld c,0                      ; the index of the byte's bit 0
swp_b:  ld a,(de)
        and (hl)
        or (ix+0)
        jr z,swp_nb
        ld b,c
swp_bt: srl a
        jr nc,swp_bn
        ld (iy+0),b
        inc iy
swp_bn: inc b
        or a
        jr nz,swp_bt
swp_nb: inc hl
        inc de
        inc ix
        ld a,c
        add a,8
        ld c,a
        cp SW_MAX
        jr c,swp_b
        ld (iy+0),0xFF
        ret

; HL = a camera coordinate, B = a table's cells -> A = its 64-pixel cell (HL / 64), or FFh
; outside the table (negative, or past the last cell: the callers then take every entry). Uses E.
sw_cell:
        ld a,h
        cp 0x40
        jr nc,swc_out               ; (negative, or 4000h and more)
        ld a,l
        rlca
        rlca
        and 3
        ld e,a
        ld a,h
        add a,a
        add a,a
        or e
        cp b
        ret c
swc_out:
        ld a,0xFF
        ret

; Every life (the level's init: level1.asm l1_init): the lifts' rest flags cleared (special.asm
; sp_update: worked out again at their next run), the spawn walk's dirty mask from the list's
; contents (a death keeps the list: an entry counting or spawned once is dirty) and the candidates
; built again at the next tick (sw_key: no cell is FEh).
sw_init:
        ld hl,sp_rest
        ld b,SP_REST_N
        xor a
swi_r:  ld (hl),a
        inc hl
        djnz swi_r
        ld hl,sw_dirty
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a                   ; (SW_MB bytes)
        ld a,0xFE
        ld (sw_key),a
        ld hl,spawn_ram + 10
        xor a
swi_lp: ld (sw_k),a
        push af
        ld a,(hl)                   ; the count (+10, +11) and the spawned byte (+12 ^ 1)
        inc hl
        or (hl)
        inc hl
        inc hl
        or (hl)
        dec hl
        dec hl
        dec hl
        push hl
        call nz,sw_dset
        pop hl
        ld de,14
        add hl,de
        pop af
        inc a
        cp SW_N
        jr c,swi_lp
        ret

; Entry sw_k's dirty bit set (sw_dset) or cleared (sw_dclr). Both use AF, DE, HL.
sw_dset:
        call sw_dbit
        or (hl)
        ld (hl),a
        ret
sw_dclr:
        call sw_dbit
        cpl
        and (hl)
        ld (hl),a
        ret
sw_dbit:                            ; -> HL = the byte of sw_dirty with entry sw_k's bit, A = the bit
        ld a,(sw_k)
        ld e,a
        rrca
        rrca
        rrca
        and 7                       ; (k / 8: 0-4)
        add a,sw_dirty & 0xFF       ; (sw_dirty's SW_MB bytes within one 256-byte page)
        ld l,a
        ld h,sw_dirty / 256
        ld a,e
        and 7
        ld e,a
        ld d,0
        push hl
        ld hl,sw_bits
        add hl,de
        ld a,(hl)
        pop hl
        ret
sw_bits: db 1,2,4,8,16,32,64,128

; ----- type 3: a walker ($CB6E) -----

; walker2's legs; more than 90 pixels from RoboCop, on every 16th step it kneels (-40h + 1, the
; step counter back to 0); its torso ($4F1D6 + t3_gfx, t3_size by walker2's D2; 16 pixels
; further right when facing right) as the last part.
t3:     call walker2
        ld hl,(t_x)
        ld de,(p_x)
        or a
        sbc hl,de
        jp p,t3_d
        ex de,hl
        ld hl,0
        or a
        sbc hl,de
t3_d:   ld de,0x5A
        or a
        sbc hl,de
        jp m,t3_draw
        ld a,(ix+OS_L0)
        and 15
        jr nz,t3_draw
        ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        inc hl
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h
        xor a
        ld (ix+OS_L0),a
        ld (ix+OS_L0+1),a
t3_draw:
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,t3_size
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld (bob_d4),bc
        ld hl,t3_gfx
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0xF1D6
        ld a,0x04
        call a2_set
        ld hl,(t_x)
        ld a,(ix+OS_FACE)
        or a
        jr nz,t3_x
        ld de,0x10
        add hl,de
t3_x:   ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        jp bob_part2

; t_x, t_y = the slot's x, y.
t_xy:   ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld (t_y),hl
        ret

; The facing byte = FFh when x >= RoboCop's x, else 0 (spl) -> A, Z when 0.
t_face: ld hl,(t_x)
        ld de,(p_x)
        or a
        sbc hl,de
        ld a,0
        jp m,tf_set
        dec a
tf_set: ld (ix+OS_FACE),a
        or a
        ret

; -> A = 0 / 2 / 4: RoboCop's 32-pixel column (x & FFE0h) left of / equal to / right of the
; object's (x - 24 & FFE0h), Z when equal.
t_col:  ld hl,(t_x)
        ld de,-0x18
        add hl,de
        ld a,l
        and 0xE0
        ld l,a
        ex de,hl
        ld hl,(p_x)
        ld a,l
        and 0xE0
        ld l,a
        or a
        sbc hl,de
        ld a,2
        ret z
        ld a,0
        ret m
        ld a,4
        or a
        ret

; HL = a pointer to a word table entry -> BC = the word, HL past it.
t_word: ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        ret

; ----- type 12: a gunner behind cover ($CEF8) -----

; Its gun follows RoboCop's 32-pixel column against its own (D3 = 0 left, 2 level, 4 right).
; The cover ($567F6, 6C3h) at (x + 4, y + 15h); when ($B02 & 2Eh) = 0, the muzzle flash
; ($6C940 - 50h * D3, 402h) and a bullet (type 3, direction 10 - D3) 7 px right of it and 21h
; down; the gunner ($56076 + t12_gfx, 803h) at x + t12_dx.
t12:    call t_xy
        call t_col
        ld (t_save),a
        ld hl,(t_x)
        inc hl
        inc hl
        inc hl
        inc hl
        ld (bob_x),hl
        ld hl,(t_y)
        ld de,0x15
        add hl,de
        ld (bob_y),hl
        ld hl,0x67F6
        ld (bob_a2),hl
        ld a,0x05
        ld (bob_a2+2),a
        ld hl,0x6C3
        ld (bob_d4),hl
        call bob_part
        ld a,(AM + 0x0B02)
        and 0x2E
        jr nz,t12_gun
        ld a,(t_save)
        ld e,a
        ld d,0
        ld hl,t12_my
        add hl,de
        call t_word
        ld hl,(t_y)
        add hl,bc
        ld (bob_y),hl
        ld hl,t12_mx
        add hl,de
        call t_word
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        ld l,e
        ld h,d
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld c,l
        ld b,h
        add hl,hl
        add hl,hl
        add hl,bc                   ; D3 * 50h
        ex de,hl
        ld hl,0xC940
        or a
        sbc hl,de
        ld (bob_a2),hl
        ld a,0x06
        ld (bob_a2+2),a
        ld hl,0x402
        ld (bob_d4),hl
        call bob_draw
        ld hl,(bob_x)
        ld de,7
        add hl,de
        ld (eb_x),hl
        ld hl,(t_y)
        ld de,0x21
        add hl,de
        ld (eb_y),hl
        ld a,3
        ld (eb_type),a
        ld a,(t_save)
        neg
        add a,10
        ld (eb_dir),a
        call ebullet_add
t12_gun:
        ld a,(t_save)
        ld e,a
        ld d,0
        ld hl,t12_dx
        add hl,de
        call t_word
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        ld hl,t12_gfx
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0x6076
        ld a,0x05
        call a2_set
        ld hl,0x803
        ld (bob_d4),hl
        jp bob_part2

; ----- type 13: a gunner standing ($CE72) -----

; On its first frame it chooses its look by the frame (bit 1 of $B01: the other torso). With
; RoboCop in its 32-pixel column, every 8th frame a bullet (type 3, direction 1Ah) from
; (x + 15, y + 18h) and the drawing 1 px up; legs ($56F12, 803h) at (x + 2, y + 15h), torso
; ($56A12, + 280h for the other look) at (x, y + 7).
t13:    ld a,(ix-0x40)              ; (byte A3 - 3Fh)
        or a
        jr nz,t13_go
        ld (ix-0x40),0xFF
        ld a,(AM + (0x0B01 ^ 1))
        bit 1,a
        jr z,t13_go
        ld (ix-0x3F),0xFF           ; (byte A3 - 40h)
t13_go: call t_xy
        call t_col
        jr nz,t13_d
        ld a,(g_frame)
        and 7
        jr nz,t13_d
        ld hl,(t_x)
        ld de,0x0F
        add hl,de
        ld (eb_x),hl
        ld hl,(t_y)
        ld de,0x18
        add hl,de
        ld (eb_y),hl
        ld a,3
        ld (eb_type),a
        ld a,0x1A
        ld (eb_dir),a
        call ebullet_add
        ld hl,(t_y)
        dec hl
        ld (t_y),hl
t13_d:  ld hl,(t_x)
        inc hl
        inc hl
        ld (bob_x),hl
        ld hl,(t_y)
        ld de,0x15
        add hl,de
        ld (bob_y),hl
        ld hl,0x6F12
        ld (bob_a2),hl
        ld a,0x05
        ld (bob_a2+2),a
        ld hl,0x803
        ld (bob_d4),hl
        call bob_part
        ld hl,(t_x)
        ld (bob_x),hl
        ld hl,(t_y)
        ld de,7
        add hl,de
        ld (bob_y),hl
        ld hl,0x6A12
        ld a,(ix-0x3F)
        or a
        jr z,t13_t
        ld hl,0x6A12 + 0x280
t13_t:  ld (bob_a2),hl
        ld a,0x05
        ld (bob_a2+2),a
        ld hl,0x803
        ld (bob_d4),hl
        jp bob_part2

; ----- type 45: a hostage ($ED1E) -----

; Inside the window it waves (sound 9 every 64 frames); on its first frame its y snaps to its
; cell (+4) and the cell offset (y & 15) is its number among the level's hostages ($16DB: a
; rescued one does not come back). RoboCop touching it rescues it ($ECAC).
t45:    call obj_window
        jr c,t45_gone
        ld a,(ix+OS_B3)
        or a
        jr nz,t45_on
        ld (ix+OS_B3),0xFF
        ld a,(ix+OS_Y)
        and 15
        ld (ix+OS_YF),a
        ld (ix+OS_YF+1),0           ; (its y fraction holds the number)
        ld (ix+OS_L40),a
        ld (ix+OS_L40+1),0
        ld e,a
        ld a,(ix+OS_Y)
        and 0xF0
        add a,4
        ld (ix+OS_Y),a
        ld d,0
        ld hl,AM + 0x16DB
        add hl,de
        ld a,l
        xor 1
        ld l,a                      ; ($16DB + n: a byte)
        ld a,(hl)
        or a
        jr z,t45_on
t45_gone:
        ld a,0xFF                   ; D0 = -1: freed
        ret
t45_on: ld a,(ix+OS_TOUCH)
        or a
        jp nz,t45_save
        ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        inc hl
        inc hl
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
        ld a,l
        and 0x7F
        cp 0x68
        jr nz,t45_d
        ld a,9
        ld (snd_b30),a
t45_d:  ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld de,8
        add hl,de
        ld (bob_x),hl
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld de,0x1B
        add hl,de
        ld (bob_y),hl
        ld hl,0xB31C
        ld (bob_a2),hl
        ld a,0x04
        ld (bob_a2+2),a
        ld hl,0x503
        ld (bob_d4),hl
        call bob_part               ; legs
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (bob_x),hl
        ld a,(g_frame)
        and 0x1E
        ld e,a
        ld d,0
        ld hl,t45_dy
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        add hl,bc
        ld (bob_y),hl
        ld hl,t45_gfx
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0x98DC
        ld a,0x04
        call a2_set
        ld hl,0x704
        ld (bob_d4),hl
        jp bob_part2                ; waving top

; $ECAC: rescued.
t45_save:
        ld hl,0x2100
        ld (AG + 0x8032),hl         ; (move.w: key $21 new, the counts are shown next frame)
        ld e,(ix+OS_L40)
        ld d,(ix+OS_L40+1)
        ld hl,AM + 0x16DB
        add hl,de
        ld a,l
        xor 1
        ld l,a
        ld (hl),0xFF
        ld hl,(AM + 0x16BE)
        inc hl
        ld (AM + 0x16BE),hl
        ld a,HUD_MSG_ED04           ; "MAN RESCUED."
        call game_msg
        ld a,0x13
        ld (snd_b2f),a
        ld hl,(AM + 0x169A)
        ld de,0x20
        add hl,de
        ld (AM + 0x169A),hl
        jp extra_life

; ----- type 4: a gunman behind cover ($CFB0) -----

; Legs, then the torso and arm aimed at RoboCop ($D0A6, from 38h below its y); every 64th
; value of $B02 (& 3Eh = 0) the muzzle flash and a bullet (type 3) in that direction.
t4:     ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (bob_x),hl
        ld (t_x),hl
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld (t_y),hl
        ld de,0x1A
        add hl,de
        ld (bob_y),hl
        ld hl,0x860A
        ld (bob_a2),hl
        ld a,0x05
        ld (bob_a2+2),a
        ld hl,0x743
        ld (bob_d4),hl
        call bob_part               ; legs
        ld hl,(t_y)
        ld de,0x38
        add hl,de
        ex de,hl
        ld hl,(t_x)
        call aim_at                 ; A = direction (D3)
        ld (t_save),a
        ld a,(AM + 0x0B02)
        and 0x3E
        jr nz,t4_torso
        ld a,(t_save)               ; fires: the muzzle flash
        ld e,a
        ld d,0
        ld hl,t4_gx
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        ld bc,6
        add hl,bc
        ld (eb_x),hl
        ld hl,t4_gy
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_y)
        add hl,bc
        ld (bob_y),hl
        ld bc,0x0A
        add hl,bc
        ld (eb_y),hl
        ld a,(t_save)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl                   ; D3 * 16
        ld d,h
        ld e,l
        add hl,hl
        add hl,hl
        add hl,de                   ; D3 * 50h
        ex de,hl
        ld hl,0xC620
        ld a,0x06
        call a2_set
        ld hl,0x402
        ld (bob_d4),hl
        call bob_draw
        ld a,3
        ld (eb_type),a
        ld a,(t_save)
        ld (eb_dir),a
        call ebullet_add
t4_torso:
        ld a,(t_save)
        ld e,a
        ld d,0
        ld hl,t4_tx
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        ld hl,t4_ty
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_y)
        add hl,bc
        ld (bob_y),hl
        ld hl,t4_tsize
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld (bob_d4),bc
        ld hl,t4_tgfx
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0x7192
        ld a,0x05
        call a2_set
        jp bob_part2                ; torso and arm (the result: D0)

; ----- types 15 and 18: a walking gunman ($CA78) -----
t15:    call walker1
        jp gunman_aim

; ----- type 30: a gunman walking, kneeling to shoot ($CA14) -----
t30:    call walker2
        ld a,(t_d2)
        and 0x0E
        ld e,a
        ld d,0
        ld hl,t30_dy
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,(t_y)
        add hl,de
        ld (t_y),hl
        ld hl,(t_x)
        inc hl
        inc hl
        ld a,(ix+OS_FACE)
        or a
        jr z,t30_x
        ld de,-4
        add hl,de
t30_x:  ld (t_x),hl
        jp gunman_aim

; ----- type 31: a gunman standing ($CA3E): aims every frame, faces left -----
t31:    ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld (t_y),hl
        ld de,0x38
        add hl,de
        ex de,hl
        ld hl,(t_x)
        call aim_at
        ld (ix+OS_XF),a
        ld (ix+OS_XF+1),0
        ld (ix+OS_FACE),0xFF
        ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        inc hl
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
        ld hl,(t_x)
        ld de,8
        add hl,de
        ld (bob_x),hl
        ld hl,(t_y)
        ld de,0x17
        add hl,de
        ld (bob_y),hl
        ld hl,0x860A
        ld (bob_a2),hl
        ld a,0x05
        ld (bob_a2+2),a
        ld hl,0x743
        ld (bob_d4),hl
        call bob_part               ; legs
        jp gunman
