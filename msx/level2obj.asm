; Level 2's own object types (bank BANK_L2, included by level2.asm; docs/LEVEL2.md 2.5, 3.3): 1, the
; walking gunman ($C736, walk_d6), 2, the armed suspect and its arrest ($C868, $C91A), 5, the drip
; ($D0E2), 6, the rolling tyre ($D1E2, $D1CA-$D1E1) with its death ($C33E), 14, the grenadier
; ($CE0A), 16, the walker with a big gun ($CD7A), and 49, the homing drone ($E6C0, $E728-$E7B1).
;
; The original's routines with its variables (the AM / AG mirror) and tables (at_l2.inc: t1_gfx,
; t1_dy, t5_*, t6_gfx, fly_*), as level1.asm's types: IX = the slot (objects.asm OS_...; a byte at
; Amiga offset d at IX + (d ^ 1), a word at IX + d), update_objects runs the handler with $16BA's
; high byte set and frees the slot when it returns A (D0's high byte) negative. The handlers' own
; damages to RoboCop follow the port's rule (decisions 17 and 19, docs/LEVEL2.md default 26): the
; drip's 0Ah times DAMAGE_X, the drone's 18h as a missile's, at most twice; trace builds
; (DAMAGE_X=1) keep the original's.

; ----- type 1: a walking gunman, legs and torso ($C736) -----

; The step counter (A3) goes on; it falls or stands ($EF72 at y + 2Ch), walks 4 px ($EF42); on 4
; frames in 64 (& 2Dh) a bullet and the muzzle flash ($6CDA0, 403h) on its side: facing right type
; 6 in direction 4 from x + 28h; facing left (the original's leftover registers, kept: Q2) type D6
; as $EF42 leaves it (0 after a step: the slot written, no bullet; 2 after a turn at a wall, the
; missile) in direction 10h (D7 = the type * 16 from update_objects), from x - 18h; both 12h down,
; the flash 8 down. Legs ($3E810 + t1_gfx by the step and the facing before the step, 5C3h) at
; (x, y + 15h), torso ($404D0 at x - 2, $40674 at x + 2 facing right, 543h) at y + t1_dy, the
; facing after the step (x is the one of before the step).
t1:     ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        inc hl
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h           ; (A3).w + 1
        ld a,l
        and 0x0E
        ld c,a
        ld a,(ix+OS_FACE)
        or a
        jr nz,t1_f
        ld a,c
        add a,0x10
        ld c,a
t1_f:   ld a,c
        ld (t_d2),a                 ; D2
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl                 ; D0
        ld e,(ix+OS_Y)
        ld d,(ix+OS_Y+1)
        ex de,hl
        ld bc,0x2C
        add hl,bc
        ld (ao_y),hl
        ex de,hl
        call obj_fall               ; ($EF72 at (x, y + 2Ch))
        ld hl,-0x2C
        add hl,de
        ld (t_y),hl                 ; D1
        ld a,4
        call walk_d6                ; ($EF42) -> A = D6
        ld (t_save),a
        ld a,(g_frame)
        and 0x2D
        jr nz,t1_legs
        ld a,(ix+OS_FACE)
        or a
        jr z,t1_fr
        ld hl,(t_x)
        ld de,-0x18
        add hl,de
        ld bc,0xCDA0                ; ($6CDA0)
        ld a,(t_save)               ; (D6)
        ld e,0x10                   ; (D7)
        jr t1_fire
t1_fr:  ld hl,(t_x)
        ld de,0x28
        add hl,de
        ld bc,0xCEE0                ; ($6CEE0)
        ld a,6
        ld e,4
t1_fire:
        ld (eb_type),a
        ld a,e
        ld (eb_dir),a
        ld (eb_x),hl
        ld (bob_x),hl
        ld (bob_a2),bc
        ld a,0x06
        ld (bob_a2+2),a
        ld hl,(t_y)
        ld de,0x12
        add hl,de
        ld (eb_y),hl
        ld de,-0x0A
        add hl,de
        ld (bob_y),hl
        call ebullet_add
        ld hl,0x403
        ld (bob_d4),hl
        call l2_flash               ; the muzzle flash
t1_legs:
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,t1_gfx
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0xE810
        ld a,0x03
        call a2_set                 ; $3E810 + t1_gfx
        ld hl,0x5C3
        ld (bob_d4),hl
        ld hl,(t_x)
        ld (bob_x),hl
        ld hl,(t_y)
        ld de,0x15
        add hl,de
        ld (bob_y),hl
        call bob_part               ; legs
        ld a,(t_d2)
        and 0x0E
        ld e,a
        ld d,0
        ld hl,t1_dy
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,(t_y)
        add hl,de
        ld (bob_y),hl
        ld hl,(t_x)
        dec hl
        dec hl
        ld de,0x04D0                ; ($404D0)
        ld a,(ix+OS_FACE)
        or a
        jr nz,t1_t
        inc hl
        inc hl
        inc hl
        inc hl
        ld de,0x0674                ; ($40674)
t1_t:   ld (bob_x),hl
        ld (bob_a2),de
        ld a,0x04
        ld (bob_a2+2),a
        ld hl,0x543
        ld (bob_d4),hl
        jp bob_part2                ; torso (the result: D0)

; $EF42 with the D6 it leaves (type 1's leftover, Q2): A = step; the cell beside the one obj_fall
; found, on the side the object faces, must be a walkway (attributes & 18h = 8) and the cell above
; that no wall (bit 1), else the object turns round; then x += the step. -> A = D6: 0 after a
; step; on a turn the beside cell's attributes & 18h, or 2 for a wall above it. objects.asm
; obj_walk's code but the result. Keeps IX.
walk_d6:
        ld c,a
        ld b,1
        ld a,(ix+OS_FACE)
        or a
        jr z,wd_r
        ld b,-1
        ld a,c
        neg
        ld c,a
wd_r:   ld a,(ao_row)
        ld d,a
        ld a,(ao_col)
        add a,b
        ld e,a
        push bc
        push de
        call atr_lin
        pop de
        pop bc
        and 0x18
        cp 8
        jr nz,wd_turn
        dec d
        push bc
        call atr_lin
        pop bc
        and 2
        jr nz,wd_turn
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld a,c
        ld e,a
        rla
        sbc a,a
        ld d,a
        add hl,de
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        xor a
        ret
wd_turn:
        ld c,a
        ld a,(ix+OS_FACE)
        cpl
        ld (ix+OS_FACE),a
        ld a,c
        ret

; ----- type 2: the armed suspect, Cain ($C868), and the arrest ($C91A) -----

; "ARREST ARMED EMEMY." every 64 frames; x held at 180h; the camera's x offset 500h ($B2D8:
; player_move's target, the view pinned at the map's left edge). Its count (-40h).w: from 46h the
; shooting pose ($3D910, else $3D280), and on the frames with count & 33h = 0 the muzzle flash
; ($6CDA0, 403h) at (x - 14h, y + 6) and a bullet (type 5, direction 0Ch) from (x, y + 10h) with
; the accelerations -2000h (x), -1000h (y; +3000h when count & 40h). Drawn white on the frames
; with bit 3 (E04h). Then always ($C91A, its pushed return): the hit points back to 4 (five hits
; in one frame would still kill it: $C2D8); touched by RoboCop, "ARREST SUCESSFUL.", sound 21h,
; the level done ($16D0, $16C4 = 40h) and the slot freed; never freed by clipping.
t2:     ld a,(g_frame)
        and 0x3F
        jr nz,t2_c
        ld a,HUD_MSG_DC76           ; "ARREST ARMED EMEMY."
        call game_msg
t2_c:   ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        inc hl
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h          ; (-40h).w + 1
        ld (t_save),hl              ; (D4)
        ld hl,0x180
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld (t_y),hl                 ; D1
        ld hl,0x500
        ld (ac_camdx),hl            ; ($B2D8)
        ld hl,(t_save)
        ld de,-0x46
        add hl,de
        bit 7,h
        ld hl,0xD280                ; ($3D280)
        jp nz,t2_draw
        ld a,(t_save)
        and 0x33
        jr nz,t2_sp
        ld hl,0x180 - 0x14
        ld (bob_x),hl
        ld hl,(t_y)
        ld de,6
        add hl,de
        ld (bob_y),hl
        ld hl,0xCDA0                ; ($6CDA0)
        ld (bob_a2),hl
        ld a,0x06
        ld (bob_a2+2),a
        ld hl,0x403
        ld (bob_d4),hl
        call l2_flash               ; the muzzle flash
        ld hl,0x180
        ld (eb_x),hl
        ld hl,(t_y)
        ld de,0x10
        add hl,de
        ld (eb_y),hl
        ld a,5
        ld (eb_type),a
        ld a,0x0C
        ld (eb_dir),a
        call ebullet_add
        jr z,t2_sp
        ld hl,(eb_slot)
        ld de,0xC0
        add hl,de
        ld (hl),0xFF
        inc hl
        ld (hl),0xFF
        inc hl
        ld (hl),0x00
        inc hl
        ld (hl),0xE0                ; +C0h: -2000h
        ld de,0x1D
        add hl,de
        ld (hl),0xFF
        inc hl
        ld (hl),0xFF
        inc hl
        ld (hl),0x00
        inc hl
        ld (hl),0xF0                ; +E0h: -1000h
        ld a,(t_save)
        and 0x40
        jr z,t2_sp
        dec hl
        dec hl
        dec hl
        xor a
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),0x30                ; +E0h: +3000h
t2_sp:  ld hl,0xD910                ; ($3D910)
t2_draw:
        ld (bob_a2),hl
        ld a,0x03
        ld (bob_a2+2),a
        ld hl,0xE04
        ld (bob_d4),hl
        ld hl,0x180
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        ld a,(g_frame)
        and 8
        jr z,t2_p2
        call bob_flashd
        jr t2_arr
t2_p2:  call bob_part2
t2_arr: ld (ix+OS_HP),4             ; ($C91A)
        ld a,(ix+OS_TOUCH)
        or a
        ret z                       ; (A = 0: D0 = 0)
        ld a,HUD_MSG_DC8A           ; "ARREST SUCESSFUL."
        call game_msg
        ld a,0x21
        ld (snd_b2c),a
        ld a,0xFF
        ld (AM + (0x16D0 ^ 1)),a    ; the level done
        ld hl,0x40
        ld (AM + 0x16C4),hl
        ld a,0xFF                   ; (D0 = -1: freed)
        ret

; ----- type 5: a drip ($D0E2) -----

; Byte 0 its state, byte 1 its frame count n. 0: it grows (n + 1; from 5 it falls). 1: it falls
; (vy + 8000h, y + vy) until the cell 18h below its y is solid ($EF8E) or RoboCop touches it (then
; also its own damage, energy - 0Ah): the splash (state 2, sound 12h, vy's high word 1, y + 2).
; 2: n + 1, gone at 0Ch. Drawn ($3BFC0 + t5_gfx, t5_size by n - 1) at (x + t5_dx - 0Ah, y) with x
; and y of before this frame's fall; freed when not drawn.
t5:     ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl                 ; D0
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld (t_y),hl                 ; D1
        ld a,(ix+1)                 ; (byte 0)
        or a
        jr nz,t5_1
        inc (ix+0)                  ; (byte 1)
        ld a,(ix+0)
        cp 5
        jp m,t5_draw
        inc (ix+1)
        jr t5_draw
t5_1:   dec a
        jr nz,t5_2
        ld hl,(t_y)
        ld de,0x18
        add hl,de
        ld (ao_y),hl
        ex de,hl
        ld hl,(t_x)
        call map_cell               ; ($EF8E) carry: solid (D6)
        sbc a,a
        ld c,a
        ld a,(ix+OS_TOUCH)
        or a
        jr z,t5_nt
        ld hl,(AM + 0x169A)
        ld de,0 - 0x0A * DAMAGE_X   ; (its own damage: decision 17)
        add hl,de
        ld (AM + 0x169A),hl
        jr t5_hit
t5_nt:  ld a,c
        or a
        jr z,t5_fall
t5_hit: inc (ix+1)
        ld a,0x12
        ld (snd_b2e),a
        ld (ix+OS_L60),1
        ld (ix+OS_L60+1),0          ; (-60h).w = 1
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        inc hl
        inc hl
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h            ; (-80h).w + 2
        jr t5_draw
t5_fall:
        call l2_fall8
        jr t5_draw
t5_2:   inc (ix+0)
        ld a,(ix+0)
        cp 0x0C
        jp m,t5_draw
        ld a,0xFF                   ; (D0 = -1)
        ret
t5_draw:
        ld a,(ix+0)
        and 0x3F
        dec a
        add a,a
        ld e,a
        ld d,0                      ; (n is 1 or more here)
        push de
        ld hl,t5_gfx
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0xBFC0
        ld a,0x03
        call a2_set                 ; $3BFC0 + t5_gfx
        pop de
        ld hl,t5_dx
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld bc,-0x0A
        add hl,bc
        ld (bob_x),hl
        ld hl,t5_size
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld (bob_d4),bc
        ld hl,(t_y)
        ld (bob_y),hl
        jp bob_draw                 ; (the result: D0)

; The slot's vy (the long at -60h) + 8000h, then its y (16.16 at -80h) + vy. Keeps IX.
l2_fall8:
        ld l,(ix+OS_L60+2)
        ld h,(ix+OS_L60+3)          ; vy's low word
        ld bc,0x8000
        add hl,bc
        ld (ix+OS_L60+2),l
        ld (ix+OS_L60+3),h
        ld c,l
        ld b,h
        ld l,(ix+OS_L60)
        ld h,(ix+OS_L60+1)
        ld de,0
        adc hl,de
        ld (ix+OS_L60),l
        ld (ix+OS_L60+1),h          ; vy's high word (+ the carry)
        ex de,hl                    ; DE:BC = vy
        ld l,(ix+OS_YF)
        ld h,(ix+OS_YF+1)
        add hl,bc
        ld (ix+OS_YF),l
        ld (ix+OS_YF+1),h
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        adc hl,de
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
        ret

; ----- type 6: a rolling tyre ($D1E2; $D1CA, $D1D0, $D1DE) -----

; Byte 0: launched; byte 1 its animation count; byte 2 the last draw's D0 (low byte: 0 drawn).
; Not launched: gone while RoboCop is not at y 1A0h-1D0h or 16 were killed ($15F2); while the gap
; ($D1DC: barrel_gap, a code-area word kept across lives, levels and games) counts down, or on the
; frames with & 13h, it waits at (0, 0); else it starts at (78h, 160h) with the gap 2, vy's high
; word 1 and a bounce speed of -7.0 (-4.5 on the frames with bit 2). Then it rolls: the frame
; ($3C920 + t6_gfx by count & 0Eh; 6 back to 0) and the count + 2, vy + 8000h, x + 3, y + vy;
; from x A0h, on a solid cell 18h below its y ($EF8E: its y snapped for the drawing only) it
; bounces: sound 19h when it was drawn, vy = the bounce speed, frame 6, count 8. Gone from camera
; x + 1E8h; drawn with bob_part2 (603h) at the x of before this frame's step.
t6:     ld a,(ix+1)                 ; (byte 0)
        or a
        jp nz,t6_go
        ld hl,(p_y)
        ld de,-0x1A0
        add hl,de
        bit 7,h
        jr nz,t6_free               ; above y 1A0h
        ld hl,(p_y)
        ld de,-0x1D1
        add hl,de
        bit 7,h
        jr z,t6_free                ; from 1D1h
        ld hl,(AM + 0x15F2)
        ld de,-0x10
        add hl,de
        bit 7,h
        jr z,t6_free                ; 16 killed ($D1DE)
        ld hl,(barrel_gap)
        ld a,h
        or l
        jr z,t6_f
        dec hl
        ld (barrel_gap),hl          ; ($D1CA)
        jr t6_hold
t6_f:   ld a,(g_frame)
        and 0x13
        jr nz,t6_hold
        ld hl,2
        ld (barrel_gap),hl
        ld (ix+1),0xFF
        ld hl,0x78
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        ld hl,0x160
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
        ld hl,0xFFF9                ; -7.0 (FFF90000h)
        ld de,0
        ld a,(g_frame)
        and 4
        jr z,t6_b
        ld hl,0xFFFB                ; -4.5 (FFFB8000h)
        ld de,0x8000
t6_b:   ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h
        ld (ix+OS_L40+2),e
        ld (ix+OS_L40+3),d          ; the bounce speed (the long at -40h)
        ld (ix+OS_L60),1
        ld (ix+OS_L60+1),0          ; (-60h).w = 1
        jr t6_go
t6_hold:                            ; ($D1D0)
        xor a
        ld (ix+OS_X),a
        ld (ix+OS_X+1),a
        ld (ix+OS_Y),a
        ld (ix+OS_Y+1),a
        ret                         ; (A = 0: D0 = 0)
t6_free:                            ; ($D1DE)
        ld a,0xFF
        ret
t6_go:  ld a,(ix+0)                 ; (byte 1)
        and 0x0E
        cp 6
        jr nz,t6_a
        ld (ix+0),0
        xor a
t6_a:   ld (t_d2),a                 ; D5
        ld a,(ix+0)
        add a,2
        ld (ix+0),a
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl                 ; D0
        inc hl
        inc hl
        inc hl
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h            ; x + 3
        call l2_fall8               ; vy + 8000h, y + vy
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld (t_y),hl                 ; D1
        ld hl,(t_x)
        ld de,-0xA0
        add hl,de
        bit 7,h
        jr nz,t6_end
        ld hl,(t_y)
        ld de,0x18
        add hl,de
        ld (ao_y),hl
        ex de,hl
        ld hl,(t_x)
        call map_cell               ; ($EF8E)
        jr nc,t6_end
        ld hl,-0x18
        add hl,de
        ld (t_y),hl                 ; (its y snapped, for the drawing)
        ld a,(ix+OS_FACE)           ; (byte 2: not drawn last time)
        or a
        jr nz,t6_s
        ld a,0x19
        ld (snd_b2e),a
t6_s:   ld a,(ix+OS_L40)
        ld (ix+OS_L60),a
        ld a,(ix+OS_L40+1)
        ld (ix+OS_L60+1),a
        ld a,(ix+OS_L40+2)
        ld (ix+OS_L60+2),a
        ld a,(ix+OS_L40+3)
        ld (ix+OS_L60+3),a          ; vy = the bounce speed
        ld a,6
        ld (t_d2),a
        ld (ix+0),8
t6_end: ld hl,(gcam_x)
        ld de,0x1E8
        add hl,de
        ex de,hl
        ld hl,(t_x)
        or a
        sbc hl,de
        jp p,t6_free                ; from camera x + 1E8h
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,t6_gfx
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0xC920
        ld a,0x03
        call a2_set                 ; $3C920 + t6_gfx
        ld hl,0x603
        ld (bob_d4),hl
        ld hl,(t_x)
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        call bob_part2
        ld a,0
        jr z,t6_d                   ; drawn: D0 = 0
        ld a,(AM + 0x16BA)          ; (not drawn: D0 = $16BA's word, the byte stored its low one)
t6_d:   ld (ix+OS_FACE),a           ; (byte 2)
        xor a                       ; (D0 = 0)
        ret

; ----- death $C33E (type 6) -----

; $15F2 + 1 (cleared at each life); every 4th kill drops a pickup at its place ($F98C: energy 1Ch
; at the 16th, else a nuke 24h), which leaves D1's low word 0: the explosion then comes at y 0.
; The explosion: type 0 ($C35A clears D5 first).
death_c33e:
        ld hl,(AM + 0x15F2)
        inc hl
        ld (AM + 0x15F2),hl
        ld a,l
        and 3
        jp nz,death_c35a
        ld de,0x24
        ld a,l
        cp 0x10
        jr nz,dc33e_p
        ld a,h
        or a
        jr nz,dc33e_p
        ld e,0x1C
dc33e_p:
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld c,(ix+OS_Y)
        ld b,(ix+OS_Y+1)
        call pickup_drop
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld de,0
        ld bc,0
        jp expl_add

; ----- type 14: a grenadier that stays put ($CE0A) -----

; It faces RoboCop (spl); on 2 frames in 64 (& 2Fh) the muzzle smoke (explosion type 1) at
; (x + D6 - 4, y - 4) and a grenade (bullet type 4, direction 20h left / 14h right, lobbed: its
; y acceleration 4000h) from (x + D6 - 4, y + 2), D6 = 0 facing left, 2Ch right. Drawn ($3DFA0,
; facing right $3E3D8; 904h) at its place.
t14:    call t_xy_l2
        call t_face_l2
        ld hl,0xDFA0                ; ($3DFA0)
        ld bc,0x2000                ; (D7 20h, D6 0)
        jr nz,t14_f
        ld hl,0xE3D8                ; ($3E3D8)
        ld bc,0x142C                ; (D7 14h, D6 2Ch)
t14_f:  ld (bob_a2),hl
        ld a,0x03
        ld (bob_a2+2),a
        ld a,(g_frame)
        and 0x2F
        jr nz,t14_d
        ld a,b
        ld (eb_dir),a
        ld hl,(t_x)
        ld b,0
        add hl,bc
        ld de,-4
        add hl,de
        ld (eb_x),hl
        ld de,(t_y)
        dec de
        dec de
        dec de
        dec de
        ld bc,0x0001
        call expl_add               ; the muzzle smoke
        ld hl,(t_y)
        inc hl
        inc hl
        ld (eb_y),hl
        ld a,4
        ld (eb_type),a
        call ebullet_add
        jr z,t14_d
        ld hl,(eb_slot)
        ld de,0xE3
        add hl,de
        ld (hl),0x40                ; +E0h: 4000h
t14_d:  ld hl,0x904
        ld (bob_d4),hl
        ld hl,(t_x)
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        jp bob_part2                ; (the result: D0)

; ----- type 16: a walker with a big gun ($CD7A) -----

; walker1's legs ($C948); its count (-3Eh).w from 1Eh fires at 20h and 28h (a bullet and the
; muzzle flash: facing left type 5 in direction 1Eh from x - 20h, right type 6 in direction 16h
; from x + 32h, both at y + 0Ah from its legs' y + 2, the flash 6 down) and wraps at 2Eh. The body
; ($40818, + 5A0h aiming from count 14h, + 2D0h facing right; 604h) at x - 9 (+ 4 aiming, + 12h
; facing right), y + 2 (+ 2 aiming).
t16:    call walker1                ; t_x, t_y, t_d2
        ld hl,(t_y)
        inc hl
        inc hl
        ld (t_y),hl                 ; D1 + 2
        ld l,(ix+OS_L40+2)
        ld h,(ix+OS_L40+3)
        inc hl
        ld (ix+OS_L40+2),l
        ld (ix+OS_L40+3),h          ; (-3Eh).w + 1
        ld a,l
        ld (t_save),a
        ld de,-0x1E
        add hl,de
        bit 7,h
        jr nz,t16_b                 ; below 1Eh
        ld de,-0x10
        add hl,de
        bit 7,h
        jr nz,t16_7
        xor a
        ld (ix+OS_L40+2),a
        ld (ix+OS_L40+3),a          ; from 2Eh: 0
t16_7:  ld a,(t_save)
        and 7
        jr nz,t16_b
        ld hl,(t_x)
        ld a,(ix+OS_FACE)
        or a
        jr z,t16_r
        ld de,-0x20
        add hl,de
        ld bc,0xCDA0                ; ($6CDA0)
        ld de,0x1E05                ; (D7 1Eh, D6 5)
        jr t16_fire
t16_r:  ld de,0x32
        add hl,de
        ld bc,0xCEE0                ; ($6CEE0)
        ld de,0x1606                ; (D7 16h, D6 6)
t16_fire:
        ld (eb_x),hl
        ld (bob_x),hl
        ld (bob_a2),bc
        ld a,0x06
        ld (bob_a2+2),a
        ld a,d
        ld (eb_dir),a
        ld a,e
        ld (eb_type),a
        ld hl,(t_y)
        ld de,0x0A
        add hl,de
        ld (eb_y),hl
        ld de,-4
        add hl,de
        ld (bob_y),hl
        call ebullet_add
        ld hl,0x403
        ld (bob_d4),hl
        call l2_flash               ; the muzzle flash
t16_b:  ld hl,(t_x)
        ld de,-9
        add hl,de
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        ld de,0x0818                ; ($40818)
        ld l,(ix+OS_L40+2)
        ld h,(ix+OS_L40+3)
        ld bc,-0x14
        add hl,bc
        bit 7,h
        jr nz,t16_f
        ld de,0x0818 + 0x5A0        ; (aiming)
        ld hl,(bob_x)
        inc hl
        inc hl
        inc hl
        inc hl
        ld (bob_x),hl
        ld hl,(bob_y)
        inc hl
        inc hl
        ld (bob_y),hl
t16_f:  ld a,(ix+OS_FACE)
        or a
        jr nz,t16_d
        ld hl,(bob_x)
        ld bc,0x12
        add hl,bc
        ld (bob_x),hl
        ld hl,0x2D0
        add hl,de
        ex de,hl
t16_d:  ld (bob_a2),de
        ld a,0x04
        ld (bob_a2+2),a
        ld hl,0x604
        ld (bob_d4),hl
        jp bob_part2                ; (the result: D0)

; The muzzle flash of types 1, 2 and 16 (drawn before their other parts, on the frames they fire):
; bob_draw as an owner of its own, bob_own + 1 (no object's address), as RoboCop's flash has one
; (shots.asm). A BOB's identity is its owner and its place among the owner's BOBs (bob.asm), so the
; flash drawn first would move the parts after it to other places on its frames: the legs' sprite
; object would change hands (an older frame or nothing shown for a picture). The display's only.
l2_flash:
        ld hl,(bob_own)
        inc hl
        ld (bob_own),hl
        call bob_draw
        ld hl,(bob_own)
        dec hl
        ld (bob_own),hl
        ret

; ----- type 49: a homing drone ($E6C0) and its flight ($E728-$E7B1, type 38's too) -----

; Word 0 its direction counter, byte 3 started, (-60h).w the target, (-40h).w its life. First
; frame: started, heading down (10h). Each frame it moves half a step of its heading D2 = word 0
; & 1Eh (fly_dx, fly_dy; fly_half: a negative step a little less); the counter turns by one
; towards the target, and when it is there the target becomes twice $D0A6's direction to RoboCop
; from (x, y + 34h). Drawn ($41358 + fly_gfx, 402h; the result unused). Touching RoboCop: its own
; damage (energy - 18h) and gone in an explosion (type 0 at x - 8, y - 8), as when its life (from
; 0: 65,536 frames) runs out; never freed by clipping.
t49:    ld a,(ix+OS_B3)
        or a
        jr nz,t49_f
        ld (ix+OS_B3),0xFF
        ld (ix+OS_L0),0x10
        ld (ix+OS_L0+1),0
t49_f:  ld a,(ix+OS_L0)
        and 0x1E
        ld (t_d2),a                 ; D2
        ld e,a
        ld d,0
        ld hl,fly_dx
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        push ix
        pop hl
        ld de,OS_X
        add hl,de
        call fly_half
        ld (t_x),de                 ; D0
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,fly_dy
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        push ix
        pop hl
        ld de,OS_Y
        add hl,de
        call fly_half
        ld (t_y),de                 ; D1
        ld a,(ix+OS_L60)            ; D3: the target (0-1Ch)
        ld c,a
        ld a,(t_d2)
        cp c
        jr nz,t49_t
        ld hl,(t_y)
        ld de,0x34
        add hl,de
        ex de,hl
        ld hl,(t_x)
        call aim_at                 ; ($D0A6) A = direction
        add a,a
        ld (ix+OS_L60),a
        ld (ix+OS_L60+1),0
        jr t49_d
t49_t:  ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        jr c,t49_up
        dec hl
        jr t49_s
t49_up: inc hl
t49_s:  ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
t49_d:  ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,fly_gfx
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0x1358
        ld a,0x04
        call a2_set                 ; $41358 + fly_gfx
        ld hl,0x402
        ld (bob_d4),hl
        ld hl,(t_x)
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        call bob_part2
        ld a,(ix+OS_TOUCH)
        or a
        jr nz,t49_hit
        ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        dec hl
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h
        ld a,h
        or l
        jr z,t49_boom
        xor a                       ; (D0 = 0)
        ret
t49_hit:
        ld hl,(AM + 0x169A)
        if DAMAGE_X > 1
        ld de,0 - 0x18 * 2          ; (its own damage as a missile's: decisions 17 and 19)
        else
        ld de,0 - 0x18
        endif
        add hl,de
        ld (AM + 0x169A),hl
t49_boom:
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld de,-8
        add hl,de
        push hl
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        add hl,de
        ex de,hl
        pop hl
        ld bc,0
        call expl_add
        ld a,0xFF                   ; (D0 = -1)
        ret

; HL = a 16.16 long (its integer word, then its fraction), BC = a step: the long + the flight's
; half step, the original's ext.l, swap, asr.l #1: (step << 16 | FFFFh for a negative step) >> 1,
; so a negative step loses its half (-9: FFFB.FFFFh, -4 - 1/65536). -> DE = its new integer
; word. Keeps IX.
fly_half:
        ld a,b
        sra b
        rr c                        ; (the step >> 1, its bit 0 into the carry)
        ld de,0
        rr d                        ; (8000h when odd)
        rla
        jr nc,fh_add
        ld e,0xFF                   ; (a negative step: its sign word FFFFh shifted in)
        ld a,d
        or 0x7F
        ld d,a
fh_add: push hl
        inc hl
        inc hl
        ld a,(hl)
        add a,e
        ld (hl),a
        inc hl
        ld a,(hl)
        adc a,d
        ld (hl),a
        pop hl
        ld a,(hl)
        adc a,c
        ld (hl),a
        ld e,a
        inc hl
        ld a,(hl)
        adc a,b
        ld (hl),a
        ld d,a
        ret
