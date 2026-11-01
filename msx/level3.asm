; Game logic of level 3, the Civic Centrum (bank BANK_L3, mapped at A000h while the game ticks:
; logic_map; docs/LEVEL3.md 3.2, 3.3). The bank starts with the level header every level bank
; shares (objects.asm lv_htab ... LV_HDR_END), laid out as level1.asm's and level2.asm's: per object
; type 0-52 its handler and death routine, the jumps to the level's start and hazard handler, its
; hazard list, the spawn walk's and the hazards' per-level values and lv_noten. Then
; gen/lvshared_l3.asm, the copy of lvshared.asm tools/mkrom.py writes (its labels and the level
; data's names suffixed _l3), at level 1's addresses (mkrom checks them), then the level's own code:
; its start (l3_init), the beams (lt2), the 6-byte stubs that run the level's own types in their
; bank (level3obj.asm, BANK_L3B, through rc2.asm l3b_call), then its tables (at_l3.inc, cells_l3.inc).
;
; Built by the plan's step A: the types are level3obj.asm's stubs and the three deaths of level 3
; ($C25C, $C360, $C3A8 with debris_add $C398) are not ported yet (their types never die while they
; are stubs: death_none stands for them); step B ports both (docs/level3/HANDOFF.md, step 4).

lv_htab_l3:
        dw obj_none, death_none     ; 0
        dw obj_none, death_none     ; 1
        dw obj_none, death_none     ; 2
        dw obj_none, death_none     ; 3
        dw t4_l3, death_c31e        ; 4: level 1's gunner (the markers; SPERMA's tail)
        dw obj_none, death_none     ; 5
        dw obj_none, death_none     ; 6
        dw obj_none, death_none     ; 7
        dw obj_none, death_none     ; 8
        dw obj_none, death_none     ; 9
        dw obj_none, death_none     ; 10
        dw obj_none, death_none     ; 11
        dw t12_l3, death_c31e       ; 12: level 1's gunner (the markers)
        dw obj_none, death_none     ; 13
        dw obj_none, death_none     ; 14
        dw obj_none, death_none     ; 15
        dw obj_none, death_none     ; 16
        dw obj_none, death_none     ; 17
        dw obj_none, death_none     ; 18
        dw obj_none, death_none     ; 19
        dw obj_none, death_none     ; 20
        dw t21_s, death_none        ; 21: the big walker ($D2FA; its death $C3A8: step B)
        dw t22_s, death_none        ; 22: Cain as RoboCop 2 ($D49C; its death $C25C: step B)
        dw obj_none, death_none     ; 23
        dw obj_none, death_none     ; 24
        dw obj_none, death_none     ; 25
        dw obj_none, death_none     ; 26
        dw obj_none, death_none     ; 27
        dw obj_none, death_none     ; 28
        dw obj_none, death_none     ; 29
        dw obj_none, death_none     ; 30
        dw obj_none, death_none     ; 31
        dw obj_none, death_none     ; 32
        dw t33_s, death_none        ; 33: the truck ($E0A4; its death $C360: step B)
        dw t34_s, death_c35a        ; 34: the small walker ($E1D6)
        dw t35_s, death_c31e        ; 35: the gunner that rises and sinks ($E28C)
        dw t36_s, death_c35a        ; 36: the robot on its up-and-down cycle ($E356)
        dw t37_s, death_c35a        ; 37: the flying machine ($E470)
        dw t38_s, death_c35a        ; 38: the homing missile ($E6D6)
        dw t39_s, death_c35a        ; 39: the bomb ($E7D2)
        dw t40_s, death_c35a        ; 40: the wall turret ($E98C)
        dw t41_s, death_c35a        ; 41: the wall turret ($EB0A)
        dw t42_s, death_c35a        ; 42: the wall turret ($E972, entering 40's at $E9A0)
        dw t43_s, death_none        ; 43: markers off ($EC02; its death $C1FA: an rts)
        dw obj_none, death_none     ; 44
        dw obj_none, death_none     ; 45
        dw t46_s, death_none        ; 46: spawn delay and marker mask 0 ($EE22; never spawned)
        dw t47_s, death_none        ; 47: the camera mode ($EE30)
        dw t48_s, death_none        ; 48: Cain's bursts ($EE5E)
        dw obj_none, death_none     ; 49
        dw t50_s, death_c35a        ; 50: the gunner that stays put ($EEE2)
        dw t51_s, death_c35a        ; 51: the walker ($EE68)
        dw t52_s, death_c35a        ; 52: the bomb ($E8A2)
lv_init_l3:
        jp l3_init
        jp lt2                      ; (lv_tick: the beams, level_tick_2 $9436)
        dw hz_l3                    ; (lv_hz)
        ds lv_swn1 - $              ; (an error when the header's fields drift from objects.asm's)
        db SW_N_l3 - 1              ; (lv_swn1) the spawn list's last entry (cells_l3.inc),
        dw spawn_ram + 14 * (SW_N_l3 - 1)  ; (lv_swlast) its address in RAM (objects.asm uf_last)
        db HZ_XN_l3, HZ_YN_l3       ; (lv_hzxn, lv_hzyn) the hazards' camera cells,
        dw hz_xm_l3, hz_ym_l3, hz_all_l3  ; (lv_hzxm, lv_hzym, lv_hzall) their masks (special.asm hz_update)
        ds lv_noten - $
        jp l3_noten                 ; (lv_noten: the rule takes more than the header's 9 bytes)
        ds LV_HDR_END - $
        include "lvshared_l3.asm"   ; (at LV_HDR_END in every level bank)

; A = an object type -> Z when it is not an enemy (objects.asm uo_cap, uo_free: ENEMY_CAP; the
; plan's 3.3 and default 10): Cain's bombs and missiles 38, 39 and 52 (counted, they would wait for
; Cain's own slot and he would never attack), the wall turrets 40-42 (drawn into the map) and the
; triggers 43, 46, 47 and 48 (they free their slot at once): 38-48 and 52 (44 and 45 never spawn in
; level 3). Counted: 4, 12, 21, 22, 33-37, 50 and 51. Changes A.
l3_noten:
        cp 52
        ret z
        sub 38
        cp 48 - 38 + 1
        sbc a,a                     ; (FFh for 38-48, else 0)
        inc a
        ret

; The level's start (level_init $871A with the header at $86B4, level 2 in $8050's count): the
; lists the game changes are copied into RAM (a new level only: a death keeps them, as the original
; keeps them in its code area), the pointers patched into the code become variables; then level 3's
; part of level_init ($88AC-$88CC): the level started ($15CA set: no gun-opening sequence), aim 5,
; $15DE 4, state 6 and the state the fade-in forces 11 ($F89D; ng_init's 10 for levels 1 and 2), at
; every start, a death's and a continue's too, as level_init runs them. Level 3's code-area words
; (msx.inc obj22_x ... obj40_flag) keep their values across lives, levels and games, as the Amiga's.
l3_init:
        ld a,(lv_fresh)
        or a
        jr z,l3i_hdr
        xor a
        ld (lv_fresh),a
        ld hl,spawn_l3
        ld de,spawn_ram
        ld bc,spawn_l3_end - spawn_l3
        ldir
        ld hl,objl_l3
        ld de,objl_ram
        ld bc,objl_l3_end - objl_l3
        ldir
        call l3i_sp0
        xor a                       ; weapon 0 ($8844: level_init's, after the levels before;
        call set_weapon             ;  a death's restart has rc2.asm level_restart's own)
l3i_hdr:
        ld hl,(l3_hdr + 2)          ; (header +0: the object list, $9C18)
        ld (ac_objlA),hl
        ld hl,spawn_ram
        ld (AM + 0x0B0E),hl         ; ($B0E: the spawn list)
        ld hl,(l3_hdr + 20)         ; (header +20, +22: where obj_relocate sends RoboCop, $87A4)
        ld (AM + 0x15D6),hl
        ld hl,(l3_hdr + 22)
        ld (AM + 0x15D8),hl
        ld hl,(l3_hdr + 26)         ; (header +24: the marker table, $C598 and $C692)
        ld de,mk_tab3 - 0xC624
        add hl,de
        ld (ac_mkptr),hl
        ld (ac_mktab),hl
        ld hl,(l3_hdr + 32)
        ld (AM + 0x16B8),hl         ; (header +32: the spawn delay)
        ld a,(l3_hdr + 34)
        ld (ac_mkmask),a            ; (header +34, the word's low byte)
        ld hl,(l3_hdr + 30)
        ld (AG + 0x804A),hl         ; (header +30: the timer, BCD minutes and seconds)
        xor a
        ld (AG + (0x804C ^ 1)),a    ; (setup_ciab_timer $F9DC: no time out)
        dec a
        ld (p_started),a            ; (st $15CA: the level started, no gun opening)
        ld hl,5
        ld (p_aim),hl               ; ($15DA)
        ld l,4
        ld (p_de),hl                ; ($15DE)
        ld l,6
        ld (p_state),hl             ; ($15E2)
        ld l,0x0B
        ld (fade_st),hl             ; ($F89D: move.b #$B at $88CC)
        jp sw_init_l3               ; (the port: the logic shortcuts' caches from the lists)
l3i_sp0:
        ld hl,sp_l3                 ; the special objects ($8B54: $9008): records into RAM,
        ld de,SP_RAM
        ld bc,sp_l3_end - sp_l3
        ldir
        ld hl,spl_l3                ;   their list (longs) as MSX pointers
        ld de,sp_ptrs
l3i_sp: ld a,(hl)
        inc hl
        ld b,(hl)
        inc hl
        bit 7,b
        jr nz,l3i_spe
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        push hl
        ld hl,SP_RAM - 0x911E       ; (the records' first Amiga address)
        add hl,bc
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ex de,hl
        pop hl
        jr l3i_sp
l3i_spe:
        xor a
        ld (de),a
        inc de
        ld (de),a
        ret

; ----- level_tick_2 ($9436): an electric beam of level 3 -----

; IX = its record (x, top y, the window's x, rows - 1). 32 game frames on, 32 off ($B00 & 20h); on,
; RoboCop with x in [x - 8, x + 16) and y - top in 0 .. (rows - 1 + 3) x 16 loses 0Ch energy a frame
; (a hazard: never multiplied) with the beam's palette flash ($F80E with $10074, as level 1's beam)
; and sound 22h ($B30). Every frame its two columns of cells are written from map_cell(x, top)
; ($EF8E, h_row and h_col): on, the top row from lt2_top by (random & 6) x 2 (a long: the left
; cell's word, then the right one's) and rows - 1 + 1 rows below from lt2_left and lt2_right by
; (random + x + 2n) & 1Eh; off, 1900h and 1880h on top, 1800h and 1780h below. Unlike level 1's
; $933A: two cells wide, 32/32 frames (bit 5), 0Ch, (rows + 2) x 16 below the top in reach.
lt2:    ld a,(g_frame)
        and 0x20
        jp nz,lt2_off
        ld hl,(p_x)
        ld de,8
        add hl,de                   ; D0 = x + 8
        ld e,(ix+0)
        ld d,(ix+1)                 ; D2 = the beam's x
        or a
        sbc hl,de
        jp m,lt2_map                ; (cmp.w D2,D0; bmi)
        ld hl,(p_x)
        ld bc,-0x10
        add hl,bc                   ; D0 - 18h
        or a
        sbc hl,de
        jp p,lt2_map                ; (cmp.w D2,D0; bpl)
        ld hl,(p_y)
        ld e,(ix+2)
        ld d,(ix+3)
        or a
        sbc hl,de                   ; D1 = y - top
        jp m,lt2_map
        ex de,hl
        ld l,(ix+6)
        ld h,(ix+7)
        inc hl
        inc hl
        inc hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl                   ; D7 = (rows - 1 + 3) x 16
        or a
        sbc hl,de
        jp m,lt2_map
        ld a,PAL_BEAM
        call pal_flash
        ld hl,(AM + 0x169A)
        ld de,-0x0C
        add hl,de
        ld (AM + 0x169A),hl         ; (subi.w #$C,$169A)
        ld a,0x22
        ld (snd_b30),a
lt2_map:
        call lt2_cell               ; ($EF8E at x, top)
        ld a,(AM + 0x0B32)
        and 6
        add a,a
        ld e,a
        ld d,0
        ld hl,lt2_top
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)                   ; BC = the long's high word (the left cell)
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a                      ; HL = its low word (the right cell)
        call lt2_put
        ld a,(AM + 0x0B32)
        add a,(ix+0)                ; D3 = random + x
        ld c,a
        ld b,(ix+6)
        inc b                       ; rows - 1 + 1 (dbf)
lt2_bl: push bc
        ld a,c
        and 0x1E
        ld e,a
        ld d,0
        ld hl,lt2_left
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,lt2_right
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        call lt2_put
        pop bc
        inc c
        inc c
        djnz lt2_bl
        ret
lt2_off:
        call lt2_cell
        ld bc,0x1900
        ld hl,0x1880
        call lt2_put
        ld b,(ix+6)
        inc b
lt2_ol: push bc
        ld bc,0x1800
        ld hl,0x1780
        call lt2_put
        pop bc
        djnz lt2_ol
        ret

; h_row, h_col = the cell $EF8E's A0 points at for (x, top) of the record: row y >> 4, or 0 outside
; $EF8E's 51 rows (its constant in every level), column (x >> 4) - 8 (level1.asm t23_cell's rule).
lt2_cell:
        ld l,(ix+0)
        ld h,(ix+1)
        ld a,l
        srl h
        rra
        srl h
        rra
        srl h
        rra
        srl h
        rra
        sub 8
        ld (h_col),a
        ld l,(ix+2)
        ld h,(ix+3)
        ld a,l
        bit 7,h
        jr nz,l2c_0
        srl h
        rra
        srl h
        rra
        srl h
        rra
        srl h
        rra
        inc h
        dec h
        jr nz,l2c_0
        cp 51
        jr c,l2c_r
l2c_0:  xor a
l2c_r:  ld (h_row),a
        ret

; BC = the left cell's map word, HL = the right one's: both into the row h_row from column h_col on
; (the linear map: map_write_lin), then the next row.
lt2_put:
        push hl
        ld a,(h_row)
        ld d,a
        ld a,(h_col)
        ld e,a
        ld h,b
        ld l,c
        call map_write_lin          ; (keeps DE)
        pop hl
        inc e
        call map_write_lin
        ld hl,h_row
        inc (hl)
        ret

; ----- the level's own types (level3obj.asm, BANK_L3B at A000h around each: rc2.asm l3b_call) -----

t21_s:  ld hl,t21
        jp l3b_call
t22_s:  ld hl,t22
        jp l3b_call
t33_s:  ld hl,t33
        jp l3b_call
t34_s:  ld hl,t34
        jp l3b_call
t35_s:  ld hl,t35
        jp l3b_call
t36_s:  ld hl,t36
        jp l3b_call
t37_s:  ld hl,t37
        jp l3b_call
t38_s:  ld hl,t38
        jp l3b_call
t39_s:  ld hl,t39
        jp l3b_call
t40_s:  ld hl,t40
        jp l3b_call
t41_s:  ld hl,t41
        jp l3b_call
t42_s:  ld hl,t42
        jp l3b_call
t43_s:  ld hl,t43
        jp l3b_call
t46_s:  ld hl,t46
        jp l3b_call
t47_s:  ld hl,t47
        jp l3b_call
t48_s:  ld hl,t48
        jp l3b_call
t50_s:  ld hl,t50
        jp l3b_call
t51_s:  ld hl,t51
        jp l3b_call
t52_s:  ld hl,t52
        jp l3b_call
