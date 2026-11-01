; Game logic of level 2, the Tokugawa brewery (bank BANK_L2, mapped at A000h while the game ticks:
; logic_map; docs/LEVEL2.md 3.2, 3.3). The bank starts with the level header every level bank
; shares (objects.asm lv_htab ... LV_HDR_END), laid out as level1.asm's: per object type 0-52 its
; handler and death routine, the jumps to the level's start and hazard handler, its hazard list,
; the spawn walk's and the hazards' per-level values and lv_noten. Then gen/lvshared_l2.asm, the
; copy of lvshared.asm tools/mkrom.py writes (its labels and the level data's names suffixed _l2),
; at level 1's addresses (mkrom checks them), then the level's own code (level2obj.asm: the types
; only level 2 has) and tables (at_l2.inc, cells_l2.inc).

lv_htab_l2:
        dw obj_none, death_none     ; 0
        dw t1, death_c31e           ; 1: the walking gunman ($C736, level2obj.asm)
        dw t2, death_c2d8           ; 2: the armed suspect, Cain ($C868)
        dw t3_l2, death_c2ee        ; 3
        dw t4_l2, death_c31e        ; 4
        dw t5, death_none           ; 5: the drip ($D0E2; its death $C1FA: an rts)
        dw t6, death_c33e           ; 6: the rolling tyre ($D1E2; its death $C33E)
        dw obj_none, death_none     ; 7
        dw obj_none, death_none     ; 8
        dw obj_none, death_none     ; 9
        dw obj_none, death_none     ; 10
        dw obj_none, death_none     ; 11
        dw t12_l2, death_c31e       ; 12
        dw t13_l2, death_c31e       ; 13
        dw t14, death_c2ee          ; 14: the grenadier ($CE0A)
        dw t15_l2, death_c31e       ; 15
        dw t16, death_c31e          ; 16: the walker with a big gun ($CD7A)
        dw obj_none, death_none     ; 17
        dw t15_l2, death_c31e       ; 18 (as level 1's: the same record)
        dw obj_none, death_none     ; 19
        dw obj_none, death_none     ; 20
        dw obj_none, death_none     ; 21
        dw obj_none, death_none     ; 22
        dw obj_none, death_none     ; 23
        dw obj_none, death_none     ; 24
        dw obj_none, death_none     ; 25
        dw obj_none, death_none     ; 26
        dw obj_none, death_none     ; 27
        dw obj_none, death_none     ; 28
        dw obj_none, death_none     ; 29
        dw t30_l2, death_c31e       ; 30
        dw t31_l2, death_c31e       ; 31
        dw obj_none, death_none     ; 32
        dw obj_none, death_none     ; 33
        dw obj_none, death_none     ; 34
        dw obj_none, death_none     ; 35
        dw obj_none, death_none     ; 36
        dw obj_none, death_none     ; 37
        dw obj_none, death_none     ; 38 (level 3's: launched by its own types only)
        dw obj_none, death_none     ; 39
        dw obj_none, death_none     ; 40
        dw obj_none, death_none     ; 41
        dw obj_none, death_none     ; 42
        dw obj_none, death_none     ; 43
        dw obj_none, death_none     ; 44
        dw t45_l2, death_c1fc       ; 45: hostage
        dw obj_none, death_none     ; 46
        dw obj_none, death_none     ; 47
        dw obj_none, death_none     ; 48
        dw t49, death_c35a          ; 49: the homing drone ($E6C0)
        dw obj_none, death_none     ; 50
        dw obj_none, death_none     ; 51
        dw obj_none, death_none     ; 52
lv_init_l2:
        jp l2_init
        jp lt1                      ; (lv_tick: the vats, level_tick_1 $91BC)
        dw hz_l2                    ; (lv_hz)
        ds lv_swn1 - $              ; (an error when the header's fields drift from objects.asm's)
        db SW_N_l2 - 1              ; (lv_swn1) the spawn list's last entry (cells_l2.inc),
        dw spawn_ram + 14 * (SW_N_l2 - 1)  ; (lv_swlast) its address in RAM (objects.asm uf_last)
        db HZ_XN_l2, HZ_YN_l2       ; (lv_hzxn, lv_hzyn) the hazards' camera cells,
        dw hz_xm_l2, hz_ym_l2, hz_all_l2  ; (lv_hzxm, lv_hzym, lv_hzall) their masks (special.asm hz_update)
        ds lv_noten - $
; (lv_noten) A = an object type -> Z when it is not an enemy (objects.asm uo_cap, uo_free:
; ENEMY_CAP): only 45, the hostage (decision 18; docs/LEVEL2.md default 25: types 2, 5, 6 and 49
; count). At most LV_HDR_END - lv_noten bytes.
        cp 45
        ret
        ds LV_HDR_END - $
        include "lvshared_l2.asm"   ; (at LV_HDR_END in every level bank)

; The level's start (level_init $871A with the header at $868C, level 1 in $8050's count): the
; lists the game changes are copied into RAM (a new level only: a death keeps them, as the
; original keeps them in its code area), the pointers patched into the code become variables.
; The vats' phases ($92DA-$9307, code-area words level_tick_1 changes) are set again at each
; new level 2 (docs/LEVEL2.md default 22), and so are their looks: vat_shown the static map's
; (vat_sh0, tools/mapcells.py), vat_disp and vat_chg cleared (none drawn, none changed: 3.5).
l2_init:
        ld a,(lv_fresh)
        or a
        jr z,l2i_hdr
        xor a
        ld (lv_fresh),a
        ld hl,spawn_l2
        ld de,spawn_ram
        ld bc,spawn_l2_end - spawn_l2
        ldir
        ld hl,objl_l2
        ld de,objl_ram
        ld bc,objl_l2_end - objl_l2
        ldir
        ld hl,vat_ph0
        ld de,vat_phase
        ld bc,vat_ph0_end - vat_ph0
        ldir
        ld hl,vat_sh0
        ld de,vat_shown
        ld bc,VAT_COLS_l2
        ldir
        ld hl,vat_disp              ; (vat_chg follows it)
        ld bc,vat_chg + 7 - vat_disp
        xor a
        call fill
        call l2i_sp0
        xor a                       ; weapon 0 ($8844: level_init's, after the levels before;
        call set_weapon             ;  a death's restart has rc2.asm level_restart's own)
l2i_hdr:
        ld hl,(l2_hdr + 2)          ; (header +0: the object list, $9C18)
        ld (ac_objlA),hl
        ld hl,spawn_ram
        ld (AM + 0x0B0E),hl         ; ($B0E: the spawn list)
        ld hl,(l2_hdr + 20)         ; (header +20, +22: where obj_relocate sends RoboCop, $87A4)
        ld (AM + 0x15D6),hl
        ld hl,(l2_hdr + 22)
        ld (AM + 0x15D8),hl
        ld hl,(l2_hdr + 26)         ; (header +24: the marker table, $C598 and $C692)
        ld de,mk_tab2 - 0xC5EC
        add hl,de
        ld (ac_mkptr),hl
        ld (ac_mktab),hl
        ld hl,(l2_hdr + 32)
        ld (AM + 0x16B8),hl         ; (header +32: the spawn delay)
        ld a,(l2_hdr + 34)
        ld (ac_mkmask),a            ; (header +34, the word's low byte)
        ld hl,(l2_hdr + 30)
        ld (AG + 0x804A),hl         ; (header +30: the timer, BCD minutes and seconds)
        xor a
        ld (AG + (0x804C ^ 1)),a    ; (setup_ciab_timer $F9DC: no time out)
        jp sw_init_l2               ; (the port: the logic shortcuts' caches from the lists)
l2i_sp0:
        ld hl,sp_l2                 ; the special objects ($8B54: $8FE0): records into RAM,
        ld de,SP_RAM
        ld bc,sp_l2_end - sp_l2
        ldir
        ld hl,spl_l2                ;   their list (longs) as MSX pointers
        ld de,sp_ptrs
l2i_sp: ld a,(hl)
        inc hl
        ld b,(hl)
        inc hl
        bit 7,b
        jr nz,l2i_spe
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        push hl
        ld hl,SP_RAM - 0x9088       ; (the records' first Amiga address)
        add hl,bc
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ex de,hl
        pop hl
        jr l2i_sp
l2i_spe:
        xor a
        ld (de),a
        inc de
        ld (de),a
        ret

; ----- level_tick_1 ($91BC): a vat of level 2 -----

; IX = its record (x left, y, x right, rows: hz_update, only inside the window). Every frame: the
; bubbling (sound 1Ah, $B2E) when the random word's low nibble is 0; RoboCop within 10h of its x
; range and d = camera y + 98h - y in 0..4Ch: the copper's sprite cut line ($10356, vat_cut_line:
; he sinks into the liquid) is CBh - d, and above line 90h he is under (st $169A: the energy
; target's high byte, st $16CC: dying; sound 10h). Odd game frames: each of its (x right - x left)
; / 16 + 1 columns takes look d = (phase k & 0Eh) + 10h when the high byte of phase k + 1 is not 0
; (vat_phase, $92DA: one table for every vat, from column 0; the first vat in the window this frame,
; $15F0 clear, steps phase k's low byte by 2 first). The original writes the column's rows + 2 map
; words from three tables by d ($927A, $929A, $92BA: attributes 0, nothing the logic reads); the
; port keeps d / 2 per column in vat_shown (the 7 vats' 103 columns in hz_l2's order: a vat's first
; is the count of the columns of the records before it) and marks the vat changed when one of its
; columns' looks changed (vat_chg): the display draws the vats from them (docs/LEVEL2.md 3.5,
; default 17). Then $15F0 is set.
lt1:    ld a,(AM + 0x0B32)          ; (the random word's low byte)
        and 0x0F
        jr nz,lt1_p
        ld a,0x1A
        ld (snd_b2e),a
lt1_p:  ld hl,(p_x)
        ld de,0x10
        add hl,de                   ; D0 = x + 10h
        ld e,(ix+0)
        ld d,(ix+1)                 ; D2 = x left
        or a
        sbc hl,de
        jp m,lt1_odd                ; (cmp.w D2,D0; bmi)
        ld hl,(p_x)
        ld de,-0x10
        add hl,de                   ; D0 = x - 10h
        ld e,(ix+4)
        ld d,(ix+5)                 ; D4 = x right
        or a
        sbc hl,de
        jp p,lt1_odd                ; (cmp.w D4,D0; bpl)
        ld hl,(gcam_y)
        ld de,0x98
        add hl,de
        ld e,(ix+2)
        ld d,(ix+3)
        or a
        sbc hl,de                   ; D1 = camera y + 98h - y
        jp m,lt1_odd
        ld a,h
        or a
        jr nz,lt1_odd
        ld a,l
        cp 0x4D
        jr nc,lt1_odd
        ld a,0xCB
        sub l                       ; D7 = CBh - D1
        ld (vat_cut_line),a
        cp 0x90
        jr nc,lt1_odd
        ld a,0xFF
        ld (AM + (0x169A ^ 1)),a    ; (st $169A)
        ld (AM + (0x16CC ^ 1)),a    ; (st $16CC)
        ld a,0x10
        ld (snd_b2e),a
lt1_odd:
        ld a,(g_frame)              ; (btst #0,$B01)
        rra
        ret nc
        ld hl,hz_l2                 ; C = the vat's first column in vat_shown, B = its index
        ld bc,0
lt1_v:  push ix
        pop de
        or a
        sbc hl,de
        add hl,de
        jr z,lt1_go
        call lt1_n
        inc a
        add a,c
        ld c,a
        ld de,8
        add hl,de
        inc b
        jr lt1_v
lt1_go: call lt1_n
        inc a
        push af                     ; its columns (dbf D5: D5 + 1)
        ld a,b
        add a,vat_chg & 0xFF
        ld e,a
        ld a,0
        adc a,vat_chg / 256
        ld d,a
        push de
        pop ix                      ; IX = its changed flag
        ld a,c
        add a,vat_shown & 0xFF
        ld e,a
        ld a,0
        adc a,vat_shown / 256
        ld d,a                      ; DE = its first column's shown look
        pop bc                      ; B = its columns
        ld hl,vat_phase             ; (column k: the low byte of word k, little-endian)
lt1_c:  ld a,(AM + (0x15F0 ^ 1))    ; (tst.b $15F0)
        or a
        jr nz,lt1_d
        inc (hl)
        inc (hl)                    ; (addq.b #2,(1,A2))
lt1_d:  ld a,(hl)
        and 0x0E
        rrca
        ld c,a                      ; (phase & 0Eh) / 2
        inc hl
        inc hl
        inc hl                      ; the high byte of phase k + 1
        ld a,(hl)
        or a
        ld a,c
        jr z,lt1_s
        add a,8                     ; (+ 10h)
lt1_s:  dec hl                      ; the low byte of phase k + 1
        ex de,hl
        cp (hl)
        jr z,lt1_k
        ld (hl),a
        ld (ix+0),0xFF              ; (the vat changed)
lt1_k:  inc hl
        ex de,hl
        djnz lt1_c
        ld a,0xFF
        ld (AM + (0x15F0 ^ 1)),a    ; (st $15F0)
        ret

; HL = a hazard record -> A = (x right - x left) >> 4 (its columns - 1; lsr.w). Keeps HL, B, C.
lt1_n:  push hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        inc hl
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        or a
        sbc hl,de
        srl h
        rr l
        srl h
        rr l
        srl h
        rr l
        srl h
        rr l
        ld a,l
        pop hl
        ret

        include "level2obj.asm"     ; (the types only level 2 has)
        include "vats_l2.inc"       ; vat_shown's start (tools/mkrom.py: tools/mapcells.py vat_tables)
        ds (VAT_COLS_l2 - (vat_disp - vat_shown)) * 0x4000  ; (an error when vat_shown has not the vats' room)
        if VAT_ANIM                 ; (the vats' display: VAT_ANIM=1 builds only, docs/LEVEL3.md default 9)
        include "vats.asm"          ; (the vats on the screen: get_tile's vat rule, the columns)
        endif
