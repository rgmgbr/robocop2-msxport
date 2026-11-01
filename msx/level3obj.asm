; Level 3's own object types (bank BANK_L3B, mapped at A000h around each handler by rc2.asm l3b_call,
; which level3.asm's handler table reaches through 6-byte stubs; docs/LEVEL3.md 2.4, 2.5, 3.2, 3.3): types
; 21, 22 (Cain), 33-43, 46, 47, 48, 50, 51 and 52, with their tables (at_l3b.inc: tools/amitab.py, bank
; l3b of analysis/amiga_tables.tsv). While a handler runs BANK_L3 is not mapped: it calls the fixed code
; and LC1 (objects.asm, shots.asm, hits.asm at 8000h), never level3.asm's code or lvshared_l3.asm's
; helpers (copies of their own here: l3_xy, l3_flash, type 38's flight from level2obj.asm's t49).
;
; The original's routines with its variables (the AM / AG mirror) and tables, as level2obj.asm's types:
; IX = the slot (objects.asm OS_...; a byte at Amiga offset d at IX + (d ^ 1), a word at IX + d, a long
; its high word first); a handler returns D0's high byte in A (negative frees the slot: objects.asm
; obj_call). The handlers' own damages to RoboCop: types 38, 39 and 52 touching him take 18h, never
; multiplied (docs/LEVEL3.md default 12, as level 2's drone).
;
; Level 3's code-area words (msx/msx.inc obj22_x ... obj40_flag) keep their values across lives,
; levels and games, as the Amiga's: the patched bytes are kept XOR'ed with the image's values, so
; that AC_VARS' zero at the power-on reads as the image's byte (analysis/amiga_ram_l3.tsv xor=):
; obj22_step = $D583 XOR 3, obj40_flag = $E9F5 XOR 42h.
;
; The original's D1 that type 22 reads: update_objects ($C3E4) calls every handler with D1 as the slot
; before left it, and type 22 alone reads it (cmpi.w #$30,D1 / bmi $D546: sound 0Eh, $B2D). The port
; keeps that D1 in uo_d1 (objects.asm: uo_free sets it to camera y - 28h, its own D1, at every free
; slot's visit): every level-3 handler leaves its last D1 there (l3_tail after its last BOB, else its
; own), the shared types 4 and 12 and the deaths through level3.asm's wrappers; slot 0's is
; read_joystick's ($BDEC: FF00h or FF10h).

L3_B1E:     equ -0x1D               ; the byte at Amiga offset -1Eh (OS_XF's high byte)
L3_B1D:     equ -0x1E               ; the byte at -1Dh (OS_XF's low byte)
L3_B7E:     equ -0x7D               ; the byte at -7Eh (OS_YF's high byte)
L3_B7D:     equ -0x7E               ; the byte at -7Dh (OS_YF's low byte)
L3_B80:     equ -0x7F               ; the byte at -80h (y's high byte)
L3_B0:      equ 1                   ; the byte at 0 (the word (A3)'s high byte)
L3_B1:      equ 0                   ; the byte at 1 (its low byte)

; ----- helpers -----

; t_x, t_y = the slot's x, y.
l3_xy:  ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld (t_y),hl
        ret

; DE = dx, BC = dy: bob_x = t_x + dx, bob_y = t_y + dy.
l3_at:  ld hl,(t_x)
        add hl,de
        ld (bob_x),hl
        ld hl,(t_y)
        add hl,bc
        ld (bob_y),hl
        ret

; A:HL = a BOB's graphics (A2), DE = its BLTSIZE (D4).
l3_gfx: ld (bob_a2),hl
        ld (bob_a2+2),a
        ld (bob_d4),de
        ret

; A muzzle flash drawn before an object's last parts: bob_draw as an owner of its own (bob_own + 1),
; so that the parts after it keep their places among the owner's BOBs (level2obj.asm l2_flash).
l3_flash:
        ld hl,(bob_own)
        inc hl
        ld (bob_own),hl
        call bob_draw
        ld hl,(bob_own)
        dec hl
        ld (bob_own),hl
        ret

; $AC56 as a handler's last BOB (bob_part2), then uo_d1 as draw_bob left D1 (l3_tail).
l3_p2:  call bob_part2

; A = the result of a handler's last BOB (bob_x, bob_y, bob_d4; 0 drawn), the flags as it left them:
; uo_d1 = the D1 draw_bob ($AB08) leaves. Drawn: the shift (x - camera x - ($B0A & 15), which is
; (x + 1) & 15, $B0A's nibble being ~camera x & 15 when the objects run) ror 4, ORed with the minterm
; 0FCAh (0BFAh for a hit flash: the same sign, all that type 22 tests). Not drawn: y - camera y when
; it is out left or right (draw_bob's first tests: x - camera x >= 1C0h, or <= 8Eh with (8Eh - that)
; >> 4 >= its words), else (out above or below) that, made 0 when negative. Keeps A and the flags.
l3_tail:
        push af
        or a
        jr nz,lt_out
        ld a,(bob_x)
        inc a
        rrca
        rrca
        rrca
        rrca
        or 0x0F
        ld h,a
        ld l,0xCA
        jr lt_set
lt_out: ld hl,(bob_y)
        ld de,(gcam_y)
        or a
        sbc hl,de
        push hl                     ; D1 = y - camera y
        ld hl,(bob_x)
        ld de,(gcam_x)
        or a
        sbc hl,de                   ; D0 = x - camera x
        ld de,0x1C0
        or a
        sbc hl,de
        jp p,lt_h                   ; out right
        ld de,0x1C0 - 0x8F
        add hl,de                   ; D0 - 8Fh
        bit 7,h
        jr z,lt_v                   ; no left cut: out above or below
        ld a,l
        cpl
        ld l,a
        ld a,h
        cpl
        ld h,a                      ; 8Eh - D0
        srl h
        rr l
        srl h
        rr l
        srl h
        rr l
        srl h
        rr l
        ld a,h
        or a
        jr nz,lt_h
        ld a,(bob_d4)
        and 0x3F
        ld e,a
        ld a,l
        cp e
        jr nc,lt_h                  ; out left
lt_v:   pop hl
        bit 7,h
        jr z,lt_set
        ld hl,0
        jr lt_set
lt_h:   pop hl
lt_set: ld (uo_d1),hl
        pop af
        ret

; ----- type 21: the big walker ($D2FA) -----

; It pushes RoboCop ($EF18) and falls or stands ($EF72 at y + 38h); its count (-7Eh).w goes on: for 32
; frames it walks (on odd frames a step of t21_step[D2] px, $EF42, and (A3) + 2), for 32 it stands
; facing RoboCop (smi). D2 = (A3) & 0Eh (+ 10h facing right). At (x - 1, y): legs ($46970 + t21_lg[D2],
; A05h) at x + t21_lx[D2], y + 10h; torso ($49B70, + 3688h and 14h right facing right; 704h) at x + 6,
; y + t21_dy[D2 & 0Eh] - 2; every 128 frames (& 79h) a bullet (type 5 leftwards, direction 0Ch, from x
; - 8; type 6, direction 4, from x + 3Ch facing right) 13h down and its muzzle flash ($6CDA0, + 140h
; facing right; 403h) 0Ah above it; head ($49EB8, + 3688h and 18h right facing right; 403h) at x + 0Ch,
; y + t21_dy[D2 & 0Eh] + 0Ah.
t21:    call l3_xy
        ld hl,(t_y)
        ld de,0x38
        add hl,de                   ; D1 = y + 38h
        push hl
        call obj_push               ; ($EF18)
        pop de
        ld (ao_y),de
        ld hl,(t_x)
        call obj_fall               ; ($EF72)
        ld (t_y),de
        ld a,(ix+OS_L0)
        and 0x0E
        ld (t_d2),a                 ; D2
        ld l,(ix+OS_YF)
        ld h,(ix+OS_YF+1)
        inc hl
        ld (ix+OS_YF),l
        ld (ix+OS_YF+1),h           ; (-7Eh).w + 1
        ld a,l
        and 0x20
        jr nz,t21_st
        ld a,(g_frame)
        rra
        jr nc,t21_f                 ; (btst #0,$B01)
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,t21_step
        add hl,de
        ld a,(hl)                   ; D4 (its words are small)
        ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        inc hl
        inc hl
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h           ; (A3) + 2
        call obj_walk               ; ($EF42)
        jr t21_f
t21_st: ld hl,(p_x)
        ld de,(t_x)
        or a
        sbc hl,de
        ld a,h
        rla
        sbc a,a
        ld (ix+OS_FACE),a           ; smi (2,A3): RoboCop left of it
t21_f:  ld a,(ix+OS_FACE)
        or a
        ld a,(t_d2)
        jr nz,t21_l
        add a,0x10
t21_l:  ld (t_d2),a
        ld hl,(t_y)
        ld de,-0x38
        add hl,de
        ld (t_y),hl                 ; D1 - 38h
        ld hl,(t_x)
        dec hl
        ld (t_x),hl                 ; D0 - 1
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,t21_lx
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        ld hl,t21_lg
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0x6970
        ld a,0x04
        call a2_set                 ; $46970 + t21_lg[D2]
        ld hl,(t_y)
        ld de,0x10
        add hl,de
        ld (bob_y),hl
        ld hl,0xA05
        ld (bob_d4),hl
        call bob_part               ; the legs
        ld a,(t_d2)
        and 0x0E
        ld e,a
        ld d,0
        ld hl,t21_dy
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld (t_save),bc              ; (the head's too)
        ld hl,(t_y)
        add hl,bc
        dec hl
        dec hl
        ld (bob_y),hl
        ld hl,(t_x)
        ld de,6
        add hl,de
        ld bc,0x9B70                ; ($49B70)
        ld a,(ix+OS_FACE)
        or a
        jr nz,t21_t
        ld de,0x14
        add hl,de
        ld bc,0x9B70 + 0x3688
t21_t:  ld (bob_x),hl
        ld (bob_a2),bc
        ld a,0x04
        ld (bob_a2+2),a
        ld hl,0x704
        ld (bob_d4),hl
        call bob_part               ; the torso
        ld a,(g_frame)
        and 0x79
        jr nz,t21_h
        ld hl,(t_x)
        ld de,-8
        add hl,de
        ld bc,0xCDA0                ; ($6CDA0)
        ld de,0x0C05                ; (D7 0Ch, D6 5)
        ld a,(ix+OS_FACE)
        or a
        jr nz,t21_fr
        push de
        ld de,0x44
        add hl,de
        pop de
        ld bc,0xCDA0 + 0x140
        ld de,0x0406                ; (D7 4, D6 6)
t21_fr: ld (eb_x),hl
        ld (bob_x),hl
        ld (bob_a2),bc
        ld a,0x06
        ld (bob_a2+2),a
        ld a,d
        ld (eb_dir),a
        ld a,e
        ld (eb_type),a
        ld hl,(t_y)
        ld de,0x13
        add hl,de
        ld (eb_y),hl
        ld de,-0x0A
        add hl,de
        ld (bob_y),hl
        call ebullet_add
        ld hl,0x403
        ld (bob_d4),hl
        call l3_flash               ; the muzzle flash
t21_h:  ld bc,(t_save)
        ld hl,(t_y)
        add hl,bc
        ld de,0x0A
        add hl,de
        ld (bob_y),hl
        ld hl,(t_x)
        ld de,0x0C
        add hl,de
        ld bc,0x9EB8                ; ($49EB8)
        ld a,(ix+OS_FACE)
        or a
        jr nz,t21_hd
        ld de,0x18
        add hl,de
        ld bc,0x9EB8 + 0x3688
t21_hd: ld (bob_x),hl
        ld (bob_a2),bc
        ld a,0x04
        ld (bob_a2+2),a
        ld hl,0x403
        ld (bob_d4),hl
        jp l3_p2                    ; the head (the result: D0)

; $EF18: t_x = D0, HL = D1 (type 21: y + 38h): RoboCop at that y or above it, within 16 px in front
; of the object (D2 = his x + 14h - x facing left, his x - 1Ch - x facing right: 0..15) is pushed 8
; px away (his x - 8 facing left, + 8 facing right).
obj_push:
        ld de,(p_y)
        or a
        sbc hl,de
        ret m
        ld hl,(p_x)
        ld de,0x14
        add hl,de
        ld bc,8
        ld a,(ix+OS_FACE)
        or a
        jr nz,opu_f
        ld bc,-8
        ld de,-0x30
        add hl,de
opu_f:  ld de,(t_x)
        or a
        sbc hl,de
        ret m
        ld de,0x10
        or a
        sbc hl,de
        ret p
        ld hl,(p_x)
        or a
        sbc hl,bc
        ld (p_x),hl
        ret

; ----- type 22: Cain as RoboCop 2 ($D49C) -----

; Hit: its hit look for 6 frames ($16D9). First frame: "CHASE CAIN", and once a life ($16D4) its x into
; obj22_x ($D798); a second one in a life frees itself ($D478). Its x is obj22_x; D0 = x - BAh - his x
; (camera mode 2, type 47's: both its facing and its mode flag (-1Eh) set, D0 = -(D0 + 184h)), >> 5,
; + 4, 0-7: the step mask c22_msk[D0] into obj22_step ($D583; FFh: it stands, $16DA), the facing XOR
; c22_fx[D0]. The fire counter (-40h): 0Bh every 128 frames, and while it is 0 sound 0Eh when the D1
; update_objects hands it is 30h or more (uo_d1). act_20's flag ($16A9): RoboCop and Cain both outside
; x 690h-9D7h (Cain: 9DFh). It falls or stands ($EF72 at y + 43h). On the frames the mask lets through:
; (A3) + 2 when its facing is its mode flag, else - 2; sound 27h at D2 6 and 0Eh; it steps by
; c22_spd[D2] (4 while falling, 0 while standing; leftwards facing left) unless the cell two columns
; ahead is a wall (bit 1). Drawn (D2 + 10h with the mode flag): legs ($3BFC0 + [$D7EE + D2], B04h at x
; + [$D82E + D2], y + 18h; standing: (A3) = D2 & 10h and $3E900; falling: also that and $3EE28, 885h,
; x - 8), then from D1 + [$D7CE + D2] its 48 x 16 ($40278, + 1E0h when frame & 5Ch is 0), 32 x 40 (the
; hit look's frames for $16D9's frames) and 64 x 32 parts (by the fire counter), the last one with its
; hit points 2Ch while that D1 is above 290h (Q1). Then $16B4's bursts, the launch mailbox (l3_mail:
; $E67A-$E67F, every frame) and the burst's bullets (9 rightwards, direction 4; 0Ah leftwards, 0Ch by
; the mode flag) with the muzzle flash on the burst counter's odd values. Never freed (D0 = 0).
t22:    ld a,(ix+OS_FLASH)
        or a
        jr z,c22_a
        ld a,6
        ld (AM + (0x16D9 ^ 1)),a
c22_a:  ld a,(ix+L3_B1D)
        or a
        jr nz,c22_on
        ld a,HUD_MSG_D46C           ; "CHASE CAIN"
        call game_msg
        ld (ix+L3_B1D),0xFF
        ld hl,AM + (0x16D4 ^ 1)
        ld a,(hl)
        or a
        jr z,c22_1st
        ld a,0xFF                   ; ($D478)
        ret
c22_1st:
        ld (hl),0xFF
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (obj22_x),hl
c22_on: ld hl,(obj22_x)
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        ld de,-0xBA
        add hl,de
        ld de,(p_x)
        or a
        sbc hl,de                   ; D0
        ld a,(AM + (0x15C4 ^ 1))
        cp 2
        ld a,0
        jr nz,c22_m
        dec a
c22_m:  ld (ix+OS_FACE),a           ; (seq (2,A3),
        ld (ix+L3_B1E),a            ;  seq (-1Eh,A3))
        or a
        jr z,c22_n
        ld de,0x184
        add hl,de
        ex de,hl
        ld hl,0
        or a
        sbc hl,de
c22_n:  sra h
        rr l
        sra h
        rr l
        sra h
        rr l
        sra h
        rr l
        sra h
        rr l
        inc hl
        inc hl
        inc hl
        inc hl
        bit 7,h
        jr nz,c22_0
        ld a,h
        or a
        jr nz,c22_7
        ld a,l
        cp 7
        jr c,c22_i
c22_7:  ld a,7
        jr c22_i
c22_0:  xor a
c22_i:  ld e,a
        ld d,0
        ld hl,c22_msk
        add hl,de
        ld a,(hl)
        xor 3
        ld (obj22_step),a           ; ($D583, kept XOR 3)
        xor 3
        rla
        sbc a,a
        ld (AM + (0x16DA ^ 1)),a    ; (smi $16DA)
        ld hl,c22_fx
        add hl,de
        ld a,(hl)
        xor (ix+OS_FACE)
        ld (ix+OS_FACE),a
        ld a,(ix+OS_L40)
        or (ix+OS_L40+1)
        jr nz,c22_b
        ld a,(g_frame)
        and 0x7F
        jr nz,c22_d1
        ld (ix+OS_L40),0x0B
        ld (ix+OS_L40+1),0
c22_d1: push ix
        pop hl
        ld de,(0 - OBJ_SLOTS) & 0xFFFF
        add hl,de
        ld a,h
        or l
        jr z,c22_b                  ; (slot 0: read_joystick's D1, negative)
        ld hl,(uo_d1)
        ld de,0x30
        or a
        sbc hl,de
        jp m,c22_b
        ld a,0x0E
        ld (snd_b2d),a
c22_b:  ld hl,AM + (0x16A9 ^ 1)
        ld (hl),0
        ld hl,(p_x)
        ld de,0x690
        or a
        sbc hl,de
        jp m,c22_c
        ld hl,(p_x)
        ld de,0x9D8
        or a
        sbc hl,de
        jp m,c22_f
c22_c:  ld hl,(obj22_x)
        ld de,0x690
        or a
        sbc hl,de
        jp m,c22_s
        ld hl,(obj22_x)
        ld de,0x9E0
        or a
        sbc hl,de
        jp m,c22_f
c22_s:  ld a,0xFF
        ld (AM + (0x16A9 ^ 1)),a
c22_f:  ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld de,0x43
        add hl,de
        ld (ao_y),hl
        ex de,hl
        ld hl,(obj22_x)
        ld (t_x),hl                 ; D0
        call obj_fall               ; ($EF72)
        ld hl,-0x43
        add hl,de
        ld (t_y),hl                 ; D1
        ld a,(ix+OS_L0)
        and 0x0E
        ld (t_d2),a                 ; D2
        ld a,(obj22_step)
        xor 3
        ld e,a
        rla
        sbc a,a
        ld d,a                      ; D4 (moveq #<$D583>)
        ld hl,(g_frame)
        ld a,l
        and e
        ld l,a
        ld a,h
        and d
        or l
        jp nz,c22_x
        ld a,(ix+OS_FACE)
        cp (ix+L3_B1E)
        ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        jr nz,c22_s2
        inc hl
        inc hl
        inc hl
        inc hl
c22_s2: dec hl
        dec hl
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
        ld a,(t_d2)
        cp 6
        jr z,c22_sd
        cp 0x0E
        jr nz,c22_sp
c22_sd: ld a,0x27
        ld (snd_b30),a
c22_sp: ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,c22_spd
        add hl,de
        ld c,(hl)                   ; D4 (its words are small)
        call c22_vy
        jr z,c22_v
        ld c,4
c22_v:  ld a,(AM + (0x16DA ^ 1))
        or a
        jr z,c22_w
        ld c,0
c22_w:  ld b,2                      ; (D3 = 4 bytes: two cells right)
        ld a,(ix+OS_FACE)
        or a
        jr z,c22_d3
        ld b,-2
        ld a,c
        neg
        ld c,a
c22_d3: ld a,(ao_row)               ; (A0: $EF72's cell)
        ld d,a
        ld a,(ao_col)
        add a,b
        ld e,a
        push bc
        call atr_lin
        pop bc
        and 2
        jr nz,c22_x                 ; a wall there: no step
        ld a,c
        ld e,a
        rla
        sbc a,a
        ld d,a
        ld hl,(obj22_x)
        add hl,de
        ld (obj22_x),hl
c22_x:  ld a,(ix+L3_B1E)
        or a
        ld a,(t_d2)
        jr z,c22_g
        add a,0x10
c22_g:  ld (t_d2),a
        ld hl,0xBFC0                ; ($3BFC0)
        ld a,0x03
        ld de,0xB04
        call l3_gfx
        ld hl,(t_x)
        ld (bob_x),hl
        ld a,(t_d2)
        push af                     ; (D2 as pushed: the legs' alone may take D2 & 10h)
        ld a,(AM + (0x16DA ^ 1))
        or a
        jr z,c22_l1
        call c22_vy
        jr nz,c22_l1
        call c22_d2
        ld hl,0xBFC0 + 0x2940       ; ($3E900: it stands)
        ld (bob_a2),hl
c22_l1: call c22_vy
        jr z,c22_l2
        call c22_d2
        ld hl,(bob_a2)
        ld de,0x2E68                ; (+ 2E68h: it falls)
        add hl,de
        ld (bob_a2),hl
        ld hl,0x885
        ld (bob_d4),hl
        ld hl,(bob_x)
        ld de,-8
        add hl,de
        ld (bob_x),hl
c22_l2: ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,c22_tab + (0xD82E - 0xD79A)
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(bob_x)
        add hl,bc
        ld (bob_x),hl
        ld hl,c22_tab + (0xD7EE - 0xD79A)
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,(bob_a2)
        ld a,(bob_a2+2)
        call a2_set
        ld hl,(t_y)
        ld de,0x18
        add hl,de
        ld (bob_y),hl
        call bob_part               ; the legs
        pop af
        ld (t_d2),a
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,c22_tab + (0xD7CE - 0xD79A)
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_y)
        add hl,bc
        ld (t_y),hl                 ; D1: the other parts'
        ld a,(t_d2)
        and 0x10
        rrca
        ld (t_save),a               ; D3 (0 or 8)
        ld e,a
        ld d,0
        ld hl,c22_tab + (0xD80E - 0xD79A)
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld a,(g_frame)
        and 0x5C
        jr nz,c22_m1
        ld hl,0x1E0
        add hl,de
        ex de,hl
c22_m1: ld hl,0x0278
        ld a,0x04
        call a2_set                 ; $40278 + ...
        ld a,(t_save)
        rrca
        ld e,a
        ld d,0
        ld hl,c22_tab + (0xD7B2 - 0xD79A)
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        ld hl,c22_tab + (0xD7BA - 0xD79A)
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_y)
        add hl,bc
        ld (bob_y),hl
        ld hl,0x404
        ld (bob_d4),hl
        call bob_part               ; the 48 x 16 part
        ld a,(t_save)
        rrca
        ld c,a
        ld hl,AM + (0x16D9 ^ 1)
        ld a,(hl)
        or a
        jr z,c22_h0
        dec (hl)
        inc c
        inc c
c22_h0: ld e,c
        ld d,0
        ld hl,c22_tab
        add hl,de
        push hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0x0638
        ld a,0x04
        call a2_set                 ; $40638 + ...
        pop hl
        push hl
        ld de,8
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        pop hl
        ld de,0x10
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_y)
        add hl,bc
        ld (bob_y),hl
        ld hl,0xA03
        ld (bob_d4),hl
        call bob_part               ; the 32 x 40 part
        ld a,(ix+OS_L40)
        ld c,a
        or (ix+OS_L40+1)
        jr z,c22_c0
        ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        dec hl
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h          ; the fire counter - 1
c22_c0: ld a,c
        and 0x0C
        rrca
        ld c,a
        ld a,(t_save)
        add a,c
        ld e,a
        ld d,0
        ld hl,c22_tab + (0xD80E - 0xD79A)
        add hl,de
        push hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0xF378
        ld a,0x03
        call a2_set                 ; $3F378 + ...
        pop hl
        ld de,0x10
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        ld hl,0x805
        ld (bob_d4),hl
        ld hl,(t_y)
        ld de,0x290
        or a
        sbc hl,de
        jp p,c22_k
        ld (ix+OS_HP),0x2C          ; (Q1: unhurt high up)
c22_k:  call bob_part2              ; the 64 x 32 part
        ld hl,(AM + 0x16B4)
        ld a,h
        or l
        jr z,c22_ml
        dec hl
        ld (AM + 0x16B4),hl
        ld a,(g_frame)
        and 0x3F
        jr nz,c22_ml
        ld a,(ix+OS_L40)
        or (ix+OS_L40+1)
        jr nz,c22_ml
        ld (ix+OS_L40+2),0x20
        ld (ix+OS_L40+3),0          ; a burst: (-3Eh).w = 20h
c22_ml: ld a,(t_save)
        rrca
        rrca
        ld e,a
        ld d,0                      ; D3 / 4
        ld hl,c22_tab + (0xD84E - 0xD79A)
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        inc hl
        inc hl                      ; [$D852 + D3 / 4]
        ld a,(AM + 0x0B32)
        and 15
        add a,(hl)
        and 0x1E
        ld (l3_mail),a
        xor a
        ld (l3_mail+1),a            ; ($E67A)
        ld hl,(t_x)
        add hl,bc
        ld de,0x18
        add hl,de
        ld (l3_mail+2),hl           ; ($E67C)
        ld hl,(t_y)
        dec hl
        dec hl
        ld (l3_mail+4),hl           ; ($E67E)
        ld hl,(t_y)
        ld (uo_d1),hl               ; (D1 at its end, but after a muzzle flash)
        ld l,(ix+OS_L40+2)
        ld h,(ix+OS_L40+3)
        ld a,h
        or l
        jp z,c22_e
        ld c,l
        dec hl
        ld (ix+OS_L40+2),l
        ld (ix+OS_L40+3),h
        bit 0,c
        jp z,c22_e
        ld a,(t_save)
        rrca
        rrca
        ld e,a
        ld d,0
        ld hl,c22_tab + (0xD7C2 - 0xD79A)
        add hl,de
        push hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld (eb_x),hl
        ld (t_x),hl
        ld a,(AM + 0x0B32)
        and 7
        ld e,a
        ld d,0
        ld hl,(t_y)
        add hl,de
        ld de,0x0E
        add hl,de
        ld (eb_y),hl
        ld de,-6
        add hl,de
        ld (bob_y),hl
        ld bc,0x0409                ; (D7 4, D6 9)
        ld a,(ix+L3_B1E)
        or a
        jr nz,c22_r
        ld bc,0x0C0A                ; (D7 0Ch, D6 0Ah)
c22_r:  ld a,b
        ld (eb_dir),a
        ld a,c
        ld (eb_type),a
        call ebullet_add
        pop hl
        push hl
        ld de,4
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,(t_x)
        add hl,bc
        ld (bob_x),hl
        pop hl
        ld de,8
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld a,(AM + (0x0B32 ^ 1))    ; (tst.b $B32)
        or a
        jp p,c22_fl
        ld hl,0xA0
        add hl,de
        ex de,hl
c22_fl: ld hl,0x12B8
        ld a,0x04
        call a2_set                 ; $412B8 + ...
        ld hl,0x402
        ld (bob_d4),hl
        call bob_draw               ; the muzzle flash
        call l3_tail
c22_e:  xor a                       ; (D0 = 0)
        ret

; -> Z when the slot's vy (the long at -60h) is 0.
c22_vy: ld a,(ix+OS_L60)
        or (ix+OS_L60+1)
        or (ix+OS_L60+2)
        or (ix+OS_L60+3)
        ret

; D2 & 10h into t_d2 and (A3).w.
c22_d2: ld a,(t_d2)
        and 0x10
        ld (t_d2),a
        ld (ix+OS_L0),a
        ld (ix+OS_L0+1),0
        ret

; ----- type 33: the truck ($E0A4) -----

; Sound 24h on even frames; (A3) + 1; it drives 3 px right; at (A3) 18h with RoboCop at its x or right
; of it, a bullet (type 16h, direction 4) from x + 20h, y + 20h. Drawn: body ($4F00C, C06h), wheels
; ($4F96C and $4FD2C, + 1E0h by bit 1 of (A3); 603h) at y + 19h, x and x + 30h, cab ($4E684, C83h) at x
; + 14h, y - 9 (+ 1 on odd frames), the last part ($4EA6C, + 2D0h by bit 3 of (A3); 604h) at x + 0Ch,
; y + 18h.
t33:    ld a,(g_frame)
        rra
        jr c,t33_a
        ld a,0x24
        ld (snd_b2e),a
t33_a:  ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        inc hl
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
        ld (t_save),hl              ; (D6)
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        inc hl
        inc hl
        inc hl
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        ld (t_x),hl                 ; D0 = x + 3
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld (t_y),hl                 ; D1
        ld hl,(p_x)
        ld de,(t_x)
        or a
        sbc hl,de
        jp m,t33_d
        ld hl,(t_save)
        ld de,0x18
        or a
        sbc hl,de
        jr nz,t33_d
        ld hl,(t_x)
        ld de,0x20
        add hl,de
        ld (eb_x),hl
        ld hl,(t_y)
        add hl,de
        ld (eb_y),hl
        ld a,0x16
        ld (eb_type),a
        ld a,4
        ld (eb_dir),a
        call ebullet_add
t33_d:  ld hl,0xF00C                ; ($4F00C)
        ld a,0x04
        ld de,0xC06
        call l3_gfx
        ld de,0
        ld b,d
        ld c,e
        call l3_at
        call bob_part               ; the body
        ld a,(ix+L3_B1)
        and 2
        ld hl,0xF96C                ; ($4F96C)
        jr z,t33_w1
        ld hl,0xF96C + 0x1E0
t33_w1: ld a,0x04
        ld de,0x603
        call l3_gfx
        ld de,0
        ld bc,0x19
        call l3_at
        call bob_part               ; a wheel
        ld a,(ix+L3_B1)
        and 2
        ld hl,0xFD2C                ; ($4FD2C)
        jr z,t33_w2
        ld hl,0xFD2C + 0x1E0
t33_w2: ld a,0x04
        ld de,0x603
        call l3_gfx
        ld de,0x30
        ld bc,0x19
        call l3_at
        call bob_part               ; the other wheel
        ld hl,0xE684                ; ($4E684)
        ld a,0x04
        ld de,0xC83
        call l3_gfx
        ld a,(g_frame)
        and 1
        add a,-9
        ld c,a
        ld b,0xFF                   ; (-9, -8 on odd frames)
        ld de,0x14
        call l3_at
        call bob_part               ; the cab
        ld a,(ix+L3_B1)
        and 8
        ld hl,0xEA6C                ; ($4EA6C)
        jr z,t33_l
        ld hl,0xEA6C + 0x2D0
t33_l:  ld a,0x04
        ld de,0x604
        call l3_gfx
        ld de,0x0C
        ld bc,0x18
        call l3_at
        jp l3_p2                    ; the last part (the result: D0)

; ----- type 34: the small walker ($E1D6) -----

; Sound 23h every 4th frame; it falls or stands ($EF72 at y + 20h) and walks 2 px ($EF42); D1 = that y
; - 28h (its y stays). With hit points: aimed at RoboCop ($D0A6: D3), D7 = [$E1C6 + D3] picks its
; record A4 = $E1A0 + D7: on frames with ($B02 & 37h) 0 a bullet (type 3, direction (-0Ah,A4)) from x +
; (A4), y + (-14h,A4); the gun ($500EC + (12h,A4), D4 (8,A4)) at x, y + (1Ch,A4) (D7 8, RoboCop to
; its left, reads its x offset from the BLTSIZEs: the original's, kept). Body ($500EC, + A0h without
; hit points; 203h) at y + 18h, legs ($5022C, + A0h by bit 1 of x; 203h) at y + 20h.
t34:    ld a,(g_frame)
        and 3
        jr nz,t34_m
        ld a,0x23
        ld (snd_b2e),a
t34_m:  ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl
        ld e,(ix+OS_Y)
        ld d,(ix+OS_Y+1)
        ex de,hl
        ld bc,0x20
        add hl,bc
        ld (ao_y),hl
        ex de,hl
        call obj_fall               ; ($EF72)
        push de
        ld a,2
        call obj_walk               ; ($EF42)
        pop hl
        ld de,-0x28
        add hl,de
        ld (t_y),hl                 ; D1
        ld a,(ix+OS_HP)
        dec a
        jp m,t34_b
        ld hl,(t_x)
        ld de,(t_y)
        call aim_at                 ; ($D0A6) A = D3
        ld e,a
        ld d,0
        ld hl,t34_tab + (0xE1C6 - 0xE18C)
        add hl,de
        ld e,(hl)                   ; D7
        ld hl,t34_tab + (0xE1A0 - 0xE18C)
        add hl,de
        push hl                     ; A4
        ld a,(AM + 0x0B02)
        and 0x37
        jr nz,t34_g
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,(t_x)
        add hl,de
        ld (eb_x),hl
        pop hl
        push hl
        ld de,-0x14
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,(t_y)
        add hl,de
        ld (eb_y),hl
        pop hl
        push hl
        ld de,-0x0A
        add hl,de
        ld a,(hl)
        ld (eb_dir),a
        ld a,3
        ld (eb_type),a
        call ebullet_add
t34_g:  pop hl
        push hl
        ld de,0x12
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0x00EC
        ld a,0x05
        call a2_set                 ; $500EC + (12h,A4)
        pop hl
        push hl
        ld de,8
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (bob_d4),de
        pop hl
        ld de,0x1C
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld de,0
        call l3_at
        call bob_part               ; the gun
t34_b:  ld a,(ix+OS_HP)
        dec a
        ld hl,0x00EC                ; ($500EC)
        jp p,t34_c
        ld hl,0x00EC + 0xA0
t34_c:  ld a,0x05
        ld de,0x203
        call l3_gfx
        ld de,0
        ld bc,0x18
        call l3_at
        call bob_part               ; the body
        ld a,(t_x)
        and 2
        ld hl,0x022C                ; ($5022C)
        jr z,t34_l
        ld hl,0x022C + 0xA0
t34_l:  ld a,0x05
        ld de,0x203
        call l3_gfx
        ld de,0
        ld bc,0x20
        call l3_at
        jp l3_p2                    ; the legs (the result: D0)

; ----- type 35: the gunner that rises and sinks ($E28C) -----

; Its hit points 3 again every frame (Q2). First frame: y + 40h, (-60h).w 1, its x into (-1Eh).w,
; where it stays. (A3).w + (-60h).w (0: (-60h) 1 again); from 1Ch up, (-60h) -1 at 2Ch or more, and on
; frames with ($B02 & 17h) 0 a bullet (type 3, direction 4) from x + 2Ah, y - 40h + 0Ah with the muzzle
; flash ($6CEE0, 403h) 8 above it. Drawn ($4E080) at y - 40h: (A3) >> 2 - 4 negative, 203h 12h down;
; else (at most 1) by t35_tab (D4, the y offset, the frame).
t35:    ld (ix+OS_HP),3
        ld a,(ix+OS_B3)
        or a
        jr nz,t35_go
        ld (ix+OS_B3),0xFF
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld de,0x40
        add hl,de
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
        ld (ix+OS_L60),1
        ld (ix+OS_L60+1),0
        ld a,(ix+OS_X)
        ld (ix+OS_XF),a
        ld a,(ix+OS_X+1)
        ld (ix+OS_XF+1),a
t35_go: ld l,(ix+OS_XF)
        ld h,(ix+OS_XF+1)
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        ld (t_x),hl                 ; D0
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        ld de,-0x40
        add hl,de
        ld (t_y),hl                 ; D1 = y - 40h
        ld e,(ix+OS_L60)
        ld d,(ix+OS_L60+1)
        ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        add hl,de
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
        ld a,h
        or l
        jr nz,t35_c
        ld (ix+OS_L60),1
        ld (ix+OS_L60+1),0
t35_c:  ld de,0x1C
        or a
        sbc hl,de
        jp m,t35_d
        ld de,0x10
        or a
        sbc hl,de
        jp m,t35_f
        ld (ix+OS_L60),0xFF
        ld (ix+OS_L60+1),0xFF       ; (-60h).w = -1
t35_f:  ld a,(AM + 0x0B02)
        and 0x17
        jr nz,t35_d
        ld hl,(t_x)
        ld de,0x2A
        add hl,de
        ld (eb_x),hl
        ld (bob_x),hl
        ld hl,(t_y)
        ld de,0x0A
        add hl,de
        ld (eb_y),hl
        ld de,-8
        add hl,de
        ld (bob_y),hl
        ld a,3
        ld (eb_type),a
        ld a,4
        ld (eb_dir),a
        call ebullet_add
        ld hl,0xCEE0                ; ($6CEE0)
        ld a,0x06
        ld de,0x403
        call l3_gfx
        call l3_flash               ; the muzzle flash
t35_d:  ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        srl h
        rr l
        srl h
        rr l
        ld de,-4
        add hl,de
        bit 7,h
        jr nz,t35_lo
        ld a,h
        or a
        jr nz,t35_1
        ld a,l
        cp 2
        jr c,t35_k
t35_1:  ld a,1
t35_k:  add a,a
        ld e,a
        ld d,0
        ld hl,t35_tab
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld (bob_d4),bc
        inc hl
        inc hl
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        push bc
        inc hl
        inc hl
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0xE080
        ld a,0x04
        call a2_set                 ; $4E080 + ...
        pop bc
        jr t35_at
t35_lo: ld hl,0xE080                ; ($4E080)
        ld a,0x04
        ld de,0x203
        call l3_gfx
        ld bc,0x12
t35_at: ld de,0
        call l3_at
        jp l3_p2                    ; (the result: D0)

; ----- type 36: the robot on its up-and-down cycle ($E356) -----

; First frame: its x into (-40h).w, where it stays. Its count (1,A3) runs 1-3Ch (60 frames): below
; 1Eh it moves 2 px (down, up while (3,A3) is set; y written), D1 = y + 2 otherwise. Body ($5338C, + 2F8h
; and 8 px right facing right; 983h) at x + 10h. At counts 23h and 2Fh, (A3).b + 2 and its muzzle smoke
; (explosion 7 at x + 2Eh, facing left 6 at x - 0Eh; y + 0Ah unless bit 1 of (A3).b) with a bullet (type
; 3, direction 4, facing left 0Ch) 6 below it, sound 25h. The map word 18h below it not 2D00h (its shaft:
; t36_w), its direction turns. Legs ($5171C, t36_tab by (A3).b & 2, + 6 facing right) at y + 4.
t36:    ld a,(ix+L3_B7D)
        or a
        jr nz,t36_go
        ld (ix+L3_B7D),0xFF
        ld a,(ix+OS_X)
        ld (ix+OS_L40),a
        ld a,(ix+OS_X+1)
        ld (ix+OS_L40+1),a
t36_go: ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        ld (t_x),hl                 ; D0
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        inc hl
        inc hl
        ld (t_y),hl                 ; D1 = y + 2
        inc (ix+L3_B1)
        ld a,(ix+L3_B1)
        ld c,a                      ; D4
        cp 0x3C
        jr nz,t36_a
        ld (ix+L3_B1),0
t36_a:  ld a,c
        cp 0x1E
        jp p,t36_d
        ld a,(ix+OS_B3)
        or a
        jr z,t36_sv
        ld hl,(t_y)
        ld de,-4
        add hl,de
        ld (t_y),hl
t36_sv: ld hl,(t_y)
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
t36_d:  ld hl,0x338C                ; ($5338C)
        ld de,0x10
        ld a,(ix+OS_FACE)
        or a
        jr nz,t36_b
        ld hl,0x338C + 0x2F8
        ld de,8
t36_b:  push de
        ld a,0x05
        ld de,0x983
        call l3_gfx
        pop de
        ld bc,0
        call l3_at
        call bob_part               ; the body
        ld a,(ix+L3_B1)
        cp 0x2F
        jr z,t36_f
        cp 0x23
        jr nz,t36_m
t36_f:  ld a,(ix+L3_B0)
        add a,2
        ld (ix+L3_B0),a
        ld hl,(t_x)
        ld de,0x2E
        add hl,de                   ; D0 + 2Eh
        ex de,hl
        ld hl,(t_y)
        bit 1,a
        jr nz,t36_y
        ld bc,0x0A
        add hl,bc
t36_y:  ex de,hl                    ; HL = x, DE = y
        ld bc,0x0407                ; (D4 4, D5 7)
        ld a,(ix+OS_FACE)
        or a
        jr z,t36_e
        push de
        ld de,-0x3C
        add hl,de
        pop de
        ld bc,0x0C06                ; (D4 0Ch, D5 6)
t36_e:  push hl
        push de
        push bc
        ld b,0
        call expl_add               ; ($F366) the muzzle smoke
        pop bc
        pop de
        pop hl
        ld (eb_x),hl
        ld hl,6
        add hl,de
        ld (eb_y),hl
        ld a,b
        ld (eb_dir),a
        ld a,3
        ld (eb_type),a
        call ebullet_add
        ld a,0x25
        ld (snd_b2f),a
t36_m:  ld hl,(t_y)
        ld de,0x18
        add hl,de
        ld (ao_y),hl
        ex de,hl
        ld hl,(t_x)
        call map_cell               ; ($EF8E)
        call t36_w
        jr z,t36_l
        ld a,(ix+OS_B3)
        cpl
        ld (ix+OS_B3),a             ; (not.b (3,A3))
t36_l:  ld a,(ix+L3_B0)
        and 2
        ld e,a
        ld a,(ix+OS_FACE)
        or a
        jr nz,t36_k
        ld a,e
        add a,6
        ld e,a
t36_k:  ld d,0
        ld hl,t36_tab
        add hl,de
        push hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld (bob_d4),bc              ; [$E446 + D4]
        pop hl
        push hl
        ld bc,0x0C
        add hl,bc
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0x171C
        ld a,0x05
        call a2_set                 ; $5171C + [$E452 + D4]
        pop hl
        ld de,0x18
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)                   ; [$E45E + D4]
        ld bc,4
        call l3_at
        jp l3_p2                    ; the legs (the result: D0)

; -> Z when the map word of the cell map_cell found (ao_row, ao_col) is 2D00h. Level 3's map holds it in
; 22 cells, the shafts of type 36's robots: column 2 rows 25-33, column 75 rows 13-18 and 27-33, which
; no map writer changes (tools/mapcells.py --level 3 checks both).
t36_w:  ld a,(ao_row)
        ld c,a
        ld a,(ao_col)
        cp 2
        jr z,t36w_2
        cp 75
        ret nz
        ld a,c
        sub 13
        cp 6
        jr c,t36w_y
        ld a,c
        sub 27
        cp 7
        jr t36w_c
t36w_2: ld a,c
        sub 25
        cp 9
t36w_c: jr c,t36w_y
        or a                        ; (A not 0 here: NZ)
        ret
t36w_y: xor a
        ret

; ----- type 37: the flying machine ($E470) -----

; One at a time: a new one whose type ran two frames ago (obj37_last, $E46E) frees itself. vy (-60h)
; and vx (-40h) are clamped to -10..10 in the slot, the values read moving it (y + vy >> 2, x + vx >>
; 2); vy + 1, and - 4 above a solid cell 30h below it ((1,A3) FFh). (-3Eh) steers its look 0-4 towards
; RoboCop's 16-px column, vx goes 2 towards his x - 48h (+ 50h while bit 8 of the game frame is set). On frames with & 14h 0,
; every 4th of them a burst shot (type 3, direction 4 from x + 18h, vx - 10h; with (-3Eh) 0 direction
; 0Ch from x + 8, vx + 10h) and its guns' flash; with (1,A3) the rotor's; body ($525CC, 803h) with
; bob_part2 (its D0 into $16BA); then (1,A3)'s third part. D0 = $16BA.
t37:    ld a,(ix+L3_B7E)
        or a
        jr nz,t37_go
        ld hl,(g_frame)
        dec hl
        dec hl
        ld de,(obj37_last)
        or a
        sbc hl,de
        jr nz,t37_st
        ld a,0xFF                   ; ($E46A)
        ret
t37_st: ld (ix+L3_B7E),0xFF
t37_go: ld hl,(g_frame)
        ld (obj37_last),hl
        push ix
        pop hl
        ld de,OS_L60
        add hl,de
        call t37_cl                 ; vy
        sra d
        rr e
        sra d
        rr e
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        add hl,de
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
        ld (t_y),hl                 ; D1
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl                 ; D0
        ld l,(ix+OS_L60)
        ld h,(ix+OS_L60+1)
        inc hl
        ld (ix+OS_L60),l
        ld (ix+OS_L60+1),h          ; vy + 1
        ld hl,(t_y)
        ld de,0x30
        add hl,de
        ld (ao_y),hl
        ex de,hl
        ld hl,(t_x)
        call map_cell               ; ($EF8E)
        sbc a,a
        ld (ix+L3_B1),a             ; (sne (1,A3))
        or a
        jr z,t37_a
        ld l,(ix+OS_L60)
        ld h,(ix+OS_L60+1)
        ld de,-4
        add hl,de
        ld (ix+OS_L60),l
        ld (ix+OS_L60+1),h
t37_a:  ld a,(ix+OS_L40+2)
        ld (t_d2),a                 ; D4 = (-3Eh).w (0, 2, 4)
        push ix
        pop hl
        ld de,OS_L40
        add hl,de
        call t37_cl                 ; vx
        sra d
        rr e
        sra d
        rr e
        ld hl,(t_x)
        add hl,de
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        push hl                     ; (its new x)
        ld a,l
        and 0xF0
        ld l,a
        ex de,hl
        ld hl,(p_x)
        ld a,l
        and 0xF0
        ld l,a
        ex de,hl
        or a
        sbc hl,de
        ld l,(ix+OS_L40+2)
        ld h,(ix+OS_L40+3)
        jp p,t37_r
        inc hl
        inc hl
        ld de,4
        or a
        sbc hl,de
        add hl,de
        jp m,t37_w
        ld hl,4
        jr t37_w
t37_r:  dec hl
        dec hl
        bit 7,h
        jr z,t37_w
        ld hl,0
t37_w:  ld (ix+OS_L40+2),l
        ld (ix+OS_L40+3),h
        pop de
        ld hl,-0x48
        ld a,(g_frame+1)            ; (btst #0,$B00: the frame word's high byte)
        rra
        jr nc,t37_e
        ld hl,0x50
t37_e:  ld bc,(p_x)
        add hl,bc
        or a
        sbc hl,de
        ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        jp m,t37_m2
        inc hl
        inc hl
        inc hl
        inc hl
t37_m2: dec hl
        dec hl
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h
        ld a,(g_frame)
        and 0x14
        jr nz,t37_b
        ld a,(g_frame)
        and 3
        jr nz,t37_p1
        ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        ld de,-0x10
        add hl,de
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h
        ld hl,(t_x)
        ld de,0x18
        add hl,de
        ld b,4
        ld a,(ix+OS_L40+2)
        or (ix+OS_L40+3)
        jr nz,t37_fd
        ld b,0x0C
        ld de,-0x10
        add hl,de
        push hl
        ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        ld de,0x20
        add hl,de
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h
        pop hl
t37_fd: ld (eb_x),hl
        ld a,b
        ld (eb_dir),a
        ld hl,(t_y)
        ld de,0x10
        add hl,de
        ld (eb_y),hl
        ld a,3
        ld (eb_type),a
        call ebullet_add
t37_p1: ld hl,t37_tab + (0xE65A - 0xE642)
        call t37_w3
        jr z,t37_b
        push de
        ld hl,0x0BDC                ; ($50BDC)
        call t37_gfx
        pop de
        ld bc,6
        call l3_at
        call bob_draw
t37_b:  ld a,(ix+L3_B1)
        or a
        jr z,t37_c
        ld hl,t37_tab + (0xE666 - 0xE642)
        call t37_w3
        jr z,t37_c
        ld hl,0x0F9C                ; ($50F9C)
        call t37_gfx
        ld hl,t37_tab + (0xE660 - 0xE642)
        call t37_w3
        ld bc,0x16
        call l3_at
        call bob_draw
t37_c:  ld hl,t37_tab + (0xE648 - 0xE642)
        call t37_w3
        ld hl,0x25CC                ; ($525CC)
        ld a,0x05
        call a2_set
        ld hl,0x803
        ld (bob_d4),hl
        ld de,0
        ld b,d
        ld c,e
        call l3_at
        ld a,(ix+OS_FLASH)
        push af
        call bob_part2              ; the body
        call l3_tail
        pop bc
        jr z,t37_0                  ; drawn: D0 = 0
        ld a,b
        or a
        jr z,t37_c2                 ; not drawn: D0 = $16BA as it is
        ld hl,0xFFFF                ; not drawn, with the hit flash: -1
        jr t37_c1
t37_0:  ld hl,0
t37_c1: ld (AM + 0x16BA),hl         ; (move.w D0,$16BA)
t37_c2: ld a,(ix+L3_B1)
        or a
        jr z,t37_x
        ld hl,t37_tab + (0xE64E - 0xE642)
        call t37_w3
        jr z,t37_x
        ld hl,0x13FC                ; ($513FC)
        call t37_gfx
        ld hl,t37_tab + (0xE654 - 0xE642)
        call t37_w3
        ld bc,0x14
        call l3_at
        call bob_draw
        call l3_tail
t37_x:  ld a,(AM + 0x16BB)          ; (D0 = $16BA)
        ret

; HL = a word of the slot (vy at -60h, vx at -40h): clamped to -10..10 there (the original's clamp
; leaves the value it read in its register) -> DE = the value read.
t37_cl: ld e,(hl)
        inc hl
        ld d,(hl)
        push de
        ex de,hl
        ld bc,10
        bit 7,h
        jr z,t37c_p
        add hl,bc
        jr c,t37c_k
        ld bc,-10
        jr t37c_w
t37c_p: or a
        sbc hl,bc
        jr c,t37c_k
t37c_w: ex de,hl
        ld (hl),b
        dec hl
        ld (hl),c
t37c_k: pop de
        ret

; HL = a table of words by D4 (t_d2) -> DE = its word, Z when 0.
t37_w3: ld a,(t_d2)
        ld e,a
        ld d,0
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld a,d
        or e
        ret

; HL = a part's frame ($5xxxx): A2 = it + [$E642 + D4] + [$E66C + (game frame & 6)], D4 = 402h.
t37_gfx:
        push hl
        ld hl,t37_tab
        call t37_w3
        pop hl
        add hl,de
        push hl
        ld a,(g_frame)
        and 6
        ld e,a
        ld d,0
        ld hl,t37_tab + (0xE66C - 0xE642)
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        pop hl
        add hl,de
        ld (bob_a2),hl
        ld a,0x05
        ld (bob_a2+2),a
        ld hl,0x402
        ld (bob_d4),hl
        ret

; ----- type 38: the homing missile ($E6D6; its flight $E722-$E7B1, level 2's t49's) -----

; Waiting (byte 3 clear) for the launch mailbox (l3_mail's x not 0: Cain fills it every frame): its y
; off the map (y's high byte FFh), (-40h).w + 1, freed at 60h (Q4: its entry's reload brings it back).
; Launched: the mailbox's x, y and direction into x, y and (A3), its x cleared (taken), started, its
; life (-40h) 60h. Then it flies as level 2's drone (level2obj.asm t49): half a step of its heading
; (fly_dx3, fly_dy3), turning towards twice $D0A6's direction to RoboCop from y + 34h; drawn ($4D680 +
; fly_gfx3, 402h); touching RoboCop his energy - 18h (x 1) and gone in an explosion (type 0 at x - 8, y
; - 8), as when its life runs out.
t38:    ld a,(ix+OS_B3)
        or a
        jr nz,t38_f
        ld hl,(l3_mail+2)
        ld a,h
        or l
        jp z,t38_w
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        ld hl,(l3_mail+4)
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
        ld hl,(l3_mail)
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
        ld hl,0
        ld (l3_mail+2),hl
        ld (ix+OS_B3),0xFF
        ld (ix+OS_L40),0x60
        ld (ix+OS_L40+1),0
t38_f:  ld a,(ix+OS_L0)
        and 0x1E
        ld (t_d2),a                 ; D2
        ld e,a
        ld d,0
        ld hl,fly_dx3
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        push ix
        pop hl
        ld de,OS_X
        add hl,de
        call fly_half3
        ld (t_x),de                 ; D0
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,fly_dy3
        add hl,de
        ld c,(hl)
        inc hl
        ld b,(hl)
        push ix
        pop hl
        ld de,OS_Y
        add hl,de
        call fly_half3
        ld (t_y),de                 ; D1
        ld a,(ix+OS_L60)            ; D3: the target
        ld c,a
        ld a,(t_d2)
        cp c
        jr nz,t38_t
        ld hl,(t_y)
        ld de,0x34
        add hl,de
        ex de,hl
        ld hl,(t_x)
        call aim_at                 ; ($D0A6)
        add a,a
        ld (ix+OS_L60),a
        ld (ix+OS_L60+1),0
        jr t38_d
t38_t:  ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        jr c,t38_up
        dec hl
        jr t38_sv
t38_up: inc hl
t38_sv: ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
t38_d:  ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,fly_gfx3
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0xD680                ; ($4D680)
        ld a,0x04
        call a2_set
        ld hl,0x402
        ld (bob_d4),hl
        ld hl,(t_x)
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        call bob_part2
        call l3_tail
        ld a,(ix+OS_TOUCH)
        or a
        jr nz,t38_hit
        ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        dec hl
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h
        ld a,h
        or l
        jr z,t38_boom
        xor a                       ; (D0 = 0)
        ret
t38_hit:                            ; ($E796) its own damage, never multiplied (default 12)
        ld hl,(AM + 0x169A)
        ld de,0 - 0x18
        add hl,de
        ld (AM + 0x169A),hl
t38_boom:                           ; ($E79C)
        ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld de,-8
        add hl,de
        push hl
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        add hl,de
        ld (uo_d1),hl
        ex de,hl
        pop hl
        ld bc,0
        call expl_add
        ld a,0xFF                   ; (D0 = -1)
        ret

; ($E6E4) types 38, 39 and 52 waiting for the mailbox.
t38_w:  ld (ix+L3_B80),0xFF
        ld l,(ix+OS_L40)
        ld h,(ix+OS_L40+1)
        inc hl
        ld (ix+OS_L40),l
        ld (ix+OS_L40+1),h
        ld de,-0x60
        add hl,de
        ld a,h
        or l
        ld a,0
        ret nz
        dec a
        ret

; HL = a 16.16 long, BC = a step: the long + the flight's half step (level2obj.asm fly_half: the
; original's ext.l, swap, asr.l #1) -> DE = its new integer word. Keeps IX.
fly_half3:
        ld a,b
        sra b
        rr c
        ld de,0
        rr d
        rla
        jr nc,fh3_a
        ld e,0xFF
        ld a,d
        or 0x7F
        ld d,a
fh3_a:  push hl
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

; ----- types 39 and 52: the bombs ($E7D2, $E8A2: one routine with their tables) -----

; Waiting as type 38's. Launched: the mailbox's x and y, its life (-5Eh).w 60h, sound 25h ($B2D), the
; mailbox taken, started; D2 = 0 (mailbox direction below 0Fh) or 4: (A3) = D2, vx (-40h).l = the long
; at its table + D2 (4.0, -4.0). Then vx + the long at +8 + D2 (39: -0.25, +0.25; 52: -0.375, +0.375),
; x + vx; it falls 2 px while the cell 10h (52: 3Fh) below it is not solid ($EF8E); drawn ($4D680 + the
; word at +10h + D2, 402h); its life out, gone in an explosion; touching RoboCop, - 18h and gone.
t52:    ld hl,t52_tab
        ld c,0x3F
        jr t39_go
t39:    ld hl,t39_tab
        ld c,0x10
t39_go: ld (t_save),hl
        ld a,c
        ld (t_d2),a
        ld a,(ix+OS_B3)
        or a
        jr nz,t39_f
        ld hl,(l3_mail+2)
        ld a,h
        or l
        jr z,t38_w
        ld (ix+OS_X),l
        ld (ix+OS_X+1),h
        ld hl,(l3_mail+4)
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
        ld (ix+OS_L60+2),0x60
        ld (ix+OS_L60+3),0
        ld a,0x25
        ld (snd_b2d),a
        ld hl,0
        ld (l3_mail+2),hl
        ld (ix+OS_B3),0xFF
        ld hl,(l3_mail)
        ld de,0x0F
        or a
        sbc hl,de
        ld a,0
        jp m,t39_d
        ld a,4
t39_d:  ld (ix+OS_L0),a
        ld (ix+OS_L0+1),0
        ld e,a
        ld d,0
        ld hl,(t_save)
        add hl,de
        ld a,(hl)
        ld (ix+OS_L40),a
        inc hl
        ld a,(hl)
        ld (ix+OS_L40+1),a
        inc hl
        ld a,(hl)
        ld (ix+OS_L40+2),a
        inc hl
        ld a,(hl)
        ld (ix+OS_L40+3),a
t39_f:  ld e,(ix+OS_L0)
        ld d,0
        ld hl,(t_save)
        add hl,de
        push hl
        ld de,0x10
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,0xD680                ; ($4D680)
        ld a,0x04
        call a2_set
        pop hl
        ld de,8
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)                   ; DE:BC: the long
        ld a,(ix+OS_L40+2)
        add a,c
        ld (ix+OS_L40+2),a
        ld a,(ix+OS_L40+3)
        adc a,b
        ld (ix+OS_L40+3),a
        ld a,(ix+OS_L40)
        adc a,e
        ld (ix+OS_L40),a
        ld a,(ix+OS_L40+1)
        adc a,d
        ld (ix+OS_L40+1),a          ; vx + it
        ld a,(ix+OS_XF)
        add a,(ix+OS_L40+2)
        ld (ix+OS_XF),a
        ld a,(ix+OS_XF+1)
        adc a,(ix+OS_L40+3)
        ld (ix+OS_XF+1),a
        ld a,(ix+OS_X)
        adc a,(ix+OS_L40)
        ld (ix+OS_X),a
        ld a,(ix+OS_X+1)
        adc a,(ix+OS_L40+1)
        ld (ix+OS_X+1),a            ; x + vx
        call l3_xy                  ; D0, D1
        ld a,(t_d2)
        ld e,a
        ld d,0
        ld hl,(t_y)
        add hl,de
        ld (ao_y),hl
        ex de,hl
        ld hl,(t_x)
        call map_cell               ; ($EF8E)
        jr c,t39_sl
        ld l,(ix+OS_Y)
        ld h,(ix+OS_Y+1)
        inc hl
        inc hl
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
t39_sl: ld hl,0x402
        ld (bob_d4),hl
        ld hl,(t_x)
        ld (bob_x),hl
        ld hl,(t_y)
        ld (bob_y),hl
        call bob_part2
        call l3_tail
        ld l,(ix+OS_L60+2)
        ld h,(ix+OS_L60+3)
        dec hl
        ld (ix+OS_L60+2),l
        ld (ix+OS_L60+3),h
        ld a,h
        or l
        jp z,t38_boom
        ld a,(ix+OS_TOUCH)
        or a
        jp nz,t38_hit
        xor a                       ; (D0 = 0)
        ret

; ----- types 40, 41 and 42: the wall turrets ($E98C, $EB0A, $E972) -----

; One of each at a time ($16A6, $16A7, $16A8: a second one frees itself at its first frame; Q6: 42
; enters 40's code). x & -16. The flashing panel (tur_pnl) at x - A0h (41: - 70h); D2 = (A3) & 0Ch; with
; RoboCop's x less than 32h (41: 28h) right of it the turret opens (sound 28h, (-1Eh) set; its hit
; flash cleared); open, (A3) + 1 a frame up to D2 8. At D2 8: 40 and 42 add 4 to D2 while obj40_flag
; holds the image's addq.w #4,D2 ($E9F5: 42h; 46h adds to D6, unused) and on every 16th frame toggle it
; and fire the rocket (bullet 11h, direction 0Ch) from x - 10h, y + 24h; 41 fires bullet 3 (direction
; 0Ch) from x, y + 26h. The turret's look D2 x 3 (12 bytes a look) one row below and 10 (41: 7) columns
; right of the panel. Destroyed (hit points 0): its wreck (30h, 41: 24h), 40 and 42 drop energy (pickup
; 1Ch at x, y + 10h, which leaves D1 0: the explosion then at y 0), the explosion (type 0; 41: at x, y +
; 10h), freed. Alive, D0 = 0.
t42:    ld a,(ix+OS_B3)
        or a
        jr nz,t40_go
        ld (ix+OS_B3),0xFF
        ld hl,AM + (0x16A8 ^ 1)
        jr t40_one
t40:    ld a,(ix+OS_B3)
        or a
        jr nz,t40_go
        ld (ix+OS_B3),0xFF
        ld hl,AM + (0x16A6 ^ 1)
t40_one:
        ld a,(hl)
        or a
        jp nz,t40_fr
        ld (hl),0xFF
t40_go: call tur_xy
        ld de,-0xA0
        call tur_pnl
        ld a,(ix+OS_L0)
        and 0x0C
        ld (t_d2),a                 ; D2
        ld de,0x32
        call tur_near
        jr z,t40_lk
        ld a,(t_d2)
        cp 8
        jr z,t40_8
        call tur_step
        jr t40_lk
t40_8:  ld a,(obj40_flag)
        or a
        jr nz,t40_n
        ld a,12
        ld (t_d2),a                 ; (addq.w #4,D2)
t40_n:  ld a,(g_frame)
        and 15
        jr nz,t40_lk
        ld a,(obj40_flag)
        xor 4
        ld (obj40_flag),a           ; (eori.b #4,$E9F5)
        ld hl,(t_x)
        ld de,-0x10
        add hl,de
        ld (eb_x),hl
        ld hl,(t_y)
        ld de,0x24
        add hl,de
        ld (eb_y),hl
        ld a,0x11
        ld (eb_type),a
        ld a,0x0C
        ld (eb_dir),a
        call ebullet_add            ; the rocket
t40_lk: call tur_d2x3
        ld hl,tur40_look
        ld a,(ix+OS_HP)
        or a
        jr z,t40_dd
        call tur_put40
        jp tur_alive
t40_dd: ld e,0x30
        call tur_put40              ; its wreck
        ld hl,(t_y)
        ld de,0x10
        add hl,de
        ld b,h
        ld c,l
        ld hl,(t_x)
        ld de,0x1C
        call pickup_drop            ; ($F98C)
        ld de,0
        jp tur_boom
t40_fr: ld a,0xFF                   ; ($E988)
        ret

t41:    ld a,(ix+OS_B3)
        or a
        jr nz,t41_go
        ld (ix+OS_B3),0xFF
        ld hl,AM + (0x16A7 ^ 1)
        ld a,(hl)
        or a
        jr nz,t40_fr
        ld (hl),0xFF
t41_go: call tur_xy
        ld de,-0x70
        call tur_pnl
        ld a,(ix+OS_L0)
        and 0x0C
        ld (t_d2),a
        ld de,0x28
        call tur_near
        jr z,t41_lk
        ld a,(t_d2)
        cp 8
        jr z,t41_8
        call tur_step
        jr t41_lk
t41_8:  ld a,(g_frame)
        and 15
        jr nz,t41_lk
        ld hl,(t_x)
        ld (eb_x),hl
        ld hl,(t_y)
        ld de,0x26
        add hl,de
        ld (eb_y),hl
        ld a,3
        ld (eb_type),a
        ld a,0x0C
        ld (eb_dir),a
        call ebullet_add
t41_lk: call tur_d2x3
        ld hl,tur41_look
        ld a,(ix+OS_HP)
        or a
        jr z,t41_dd
        call tur_put41
tur_alive:
        ld hl,(t_y)
        ld (uo_d1),hl               ; (D1 = y)
        xor a                       ; (D0 = 0)
        ret
t41_dd: ld e,0x24
        call tur_put41              ; its wreck
        ld hl,(t_y)
        ld de,0x10
        add hl,de
        ex de,hl
tur_boom:                           ; DE = y: the explosion (type 0) at x
        ld (uo_d1),de
        ld hl,(t_x)
        ld bc,0
        call expl_add               ; ($F366)
        ld a,0xFF                   ; (D0 = -1)
        ret

; x & -16 (the slot's), t_x, t_y.
tur_xy: ld a,(ix+OS_X)
        and 0xF0
        ld (ix+OS_X),a
        jp l3_xy

; DE = 32h (40, 42) or 28h (41): with RoboCop's x - x below it and the turret shut ((-1Eh) clear), it
; opens: sound 28h, (-1Eh) set. Its hit flash cleared. -> NZ when open.
tur_near:
        ld hl,(p_x)
        push de
        ld de,(t_x)
        or a
        sbc hl,de
        pop de
        or a
        sbc hl,de
        jp p,tn_c
        ld a,(ix+L3_B1E)
        or a
        jr nz,tn_c
        ld a,0x28
        ld (snd_b2d),a
        ld (ix+L3_B1E),0xFF
tn_c:   ld (ix+OS_FLASH),0
        ld a,(ix+L3_B1E)
        or a
        ret

; (A3).w + 1.
tur_step:
        ld l,(ix+OS_L0)
        ld h,(ix+OS_L0+1)
        inc hl
        ld (ix+OS_L0),l
        ld (ix+OS_L0+1),h
        ret

; -> DE = D2 x 3 (D2 = t_d2, a multiple of 4: the look's offset, 12 bytes a look).
tur_d2x3:
        ld a,(t_d2)
        ld e,a
        add a,a
        add a,e
        ld e,a
        ld d,0
        ret

; HL = a turret's look table, DE = the look's offset: its 2 x 3 words one row below the panel's cell
; and 10 columns right of it ($EA50: A0 + 154h; 41's $EBB8: 7 columns, A0 + 14Eh).
tur_put40:
        ld c,10
        jr tpt_go
tur_put41:
        ld c,7
tpt_go: add hl,de
        ld a,(ao_row)
        inc a
        ld d,a
        ld a,(ao_col)
        add a,c
        ld e,a
        ld c,1                      ; (the port: the turret's block, tur_put's cache entry)
        jr tur_put

; DE = the panel's x offset (-A0h, 41: -70h): the flashing panel's 2 x 3 map words ($EAA6: tur_panel's
; look 18h with no hit points, else 0 or 0Ch by bit 4 of the game frame while its bit 2 is set, 18h
; while it is clear) at map_cell(x + DE, y) -> ao_row, ao_col (the turret's look goes on from that cell).
tur_pnl:
        ld hl,(t_x)
        add hl,de
        push hl
        ld e,0x18
        ld a,(ix+OS_HP)
        or a
        jr z,tp_go
        ld a,(g_frame)
        ld e,0
        bit 4,a
        jr nz,tp_b2
        ld e,0x0C
tp_b2:  bit 2,a
        jr nz,tp_go
        ld e,0x18
tp_go:  ld d,0
        ld hl,tur_panel
        add hl,de
        ex (sp),hl
        ld de,(t_y)
        ld (ao_y),de
        call map_cell               ; ($EF8E)
        pop hl
        ld a,(ao_row)
        ld d,a
        ld a,(ao_col)
        ld e,a
        ld c,0                      ; (the port: the panel's block, tur_put's cache entry)
; HL = 6 map words, D = row, E = column: written two a row from that cell, three rows.
; (The port) C = the block (0 the panel, 1 the turret): with the turret's type (40-42; one of each at
; a time, $16A6-$16A8) one of six map-write cache entries (tc_tab: the look's address, the row, the
; column, mw_gen after its writes). Nothing is written when that entry wrote the same look into the
; same cell in the last tick (or skipped it so: mc_prev's high byte), no map cell changed since (mw_gen:
; tiles.asm map_write's changes) and no write was ever lost (mp_lost, atr_lost 0): the cells hold those
; words, and writing a cell's own word again changes nothing (map_write: no patch, attribute, redraw
; or count). The callers use none of the registers it leaves.
tur_put:
        push de
        push hl
        ld a,(ix+OS_TYPE)
        sub 40
        add a,a
        add a,c                     ; the entry, 0-5
        ld e,a
        ld d,0
        ld hl,tc_bit
        add hl,de
        ld a,(hl)
        ld (tc_bitv),a              ; its bit (mc_prev's and mc_cur's high byte)
        ld hl,tc_tab
        add hl,de
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld (tc_ptr),hl              ; HL = the entry
        ld a,(mc_prev + 1)
        ld c,a
        ld a,(tc_bitv)
        and c
        jr z,tpu_go                 ; (not written last tick)
        ld a,(mp_lost)
        ld c,a
        ld a,(atr_lost)
        or c
        jr nz,tpu_go
        pop bc                      ; BC = the words
        pop de                      ; DE = the cell
        push de
        push bc
        ld a,(hl)
        cp c
        jr nz,tpu_go
        inc hl
        ld a,(hl)
        cp b
        jr nz,tpu_go
        inc hl
        ld a,(hl)
        cp d
        jr nz,tpu_go
        inc hl
        ld a,(hl)
        cp e
        jr nz,tpu_go
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,(mw_gen)
        or a
        sbc hl,de
        jr nz,tpu_go
        pop hl                      ; (no change since: the cells hold the words)
        pop de
        jr tpu_m
tpu_go: pop hl
        pop de
        push hl
        push de
        ld b,3
tpu_r:  push bc
        call tpu_w
        inc e
        call tpu_w
        dec e
        inc d
        pop bc
        djnz tpu_r
        pop de                      ; DE = the cell
        pop bc                      ; BC = the words
        ld hl,(tc_ptr)
        ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ld (hl),d
        inc hl
        ld (hl),e
        inc hl
        ld de,(mw_gen)
        ld (hl),e
        inc hl
        ld (hl),d                   ; (the count after its writes)
tpu_m:  ld a,(tc_bitv)
        ld hl,mc_cur + 1
        or (hl)
        ld (hl),a                   ; (used this tick)
        ret
tc_tab: dw tc_ent0, tc_ent0 + 6, tc_ent0 + 12, tc_ent0 + 18, tc_ent4, tc_ent4 + 6
tc_bit: db 1, 2, 4, 8, 16, 32
tpu_w:  ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        push hl
        ld h,b
        ld l,c
        call map_write_lin          ; (keeps DE)
        pop hl
        ret

; ----- the triggers: types 43, 46, 47 and 48 (each frees its slot at once) -----

; Type 43 ($EC02): no more marker spawns (both marker pointers at markers_off, $C662: two (7, 0, 0)
; entries), $16D7 cleared, the camera's y offset -70h.
t43:    ld hl,mk_tab3 + (0xC662 - 0xC624)
        ld (ac_mkptr),hl
        ld (ac_mktab),hl
        xor a
        ld (AM + (0x16D7 ^ 1)),a
        ld hl,-0x70
        ld (ac_camdy),hl
        dec a
        ret

; Type 46 ($EE22): the spawn delay and the marker mask 0 (never spawned in level 3).
t46:    ld hl,0
        ld (AM + 0x16B8),hl
        xor a
        ld (ac_mkmask),a
        dec a
        ret

; Type 47 ($EE30): the camera mode x & 15 into $15C4 (byte), the camera's offsets from t47_cam.
t47:    ld a,(ix+OS_X)
        and 15
        ld (AM + (0x15C4 ^ 1)),a
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,t47_cam
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (ac_camdx),de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (ac_camdy),de
        ld a,0xFF
        ret

; Type 48 ($EE5E): Cain's bursts for 250 frames ($16B4 FAh).
t48:    ld hl,0xFA
        ld (AM + 0x16B4),hl
        ld a,0xFF
        ret

; ----- type 50: the gunner that stays put ($EEE2) -----

; Every 64 frames a bullet (type 3, direction 4) from x + 18h, y + 10h; drawn ($53D00, 983h).
t50:    call l3_xy
        ld a,(g_frame)
        and 0x3F
        jr nz,t50_d
        ld hl,(t_x)
        ld de,0x18
        add hl,de
        ld (eb_x),hl
        ld hl,(t_y)
        ld de,0x10
        add hl,de
        ld (eb_y),hl
        ld a,3
        ld (eb_type),a
        ld a,4
        ld (eb_dir),a
        call ebullet_add
t50_d:  ld hl,0x3D00                ; ($53D00)
        ld a,0x05
        ld de,0x983
        call l3_gfx
        ld de,0
        ld b,d
        ld c,e
        call l3_at
        jp l3_p2                    ; (the result: D0)

; ----- type 51: the walker ($EE68) -----

; Sound 23h every 8th frame; it falls or stands ($EF72 at y + 30h), walks 3 px ($EF42) and its y becomes
; that point's - 30h (Q: a fall's step is undone but its fraction). On frames with ($B02 & 6Eh) 0 a
; bullet (type 3: direction 4 from x + 30h, facing left 0Ch from x - 10h; y + 20h) whose y acceleration
; (+E0h) is the random word, sign-extended. Drawn ($54390, + 5BEh facing right; C44h).
t51:    ld a,(g_frame)
        and 7
        jr nz,t51_m
        ld a,0x23
        ld (snd_b2e),a
t51_m:  ld l,(ix+OS_X)
        ld h,(ix+OS_X+1)
        ld (t_x),hl
        ld e,(ix+OS_Y)
        ld d,(ix+OS_Y+1)
        ex de,hl
        ld bc,0x30
        add hl,bc
        ld (ao_y),hl
        ex de,hl
        call obj_fall               ; ($EF72)
        push de
        ld a,3
        call obj_walk               ; ($EF42)
        pop hl
        ld de,-0x30
        add hl,de
        ld (t_y),hl
        ld (ix+OS_Y),l
        ld (ix+OS_Y+1),h
        ld a,(AM + 0x0B02)
        and 0x6E
        jr nz,t51_d
        ld hl,(t_x)
        ld de,0x30
        add hl,de
        ld b,4
        ld a,(ix+OS_FACE)
        or a
        jr z,t51_r
        ld de,-0x40
        add hl,de
        ld b,0x0C
t51_r:  ld (eb_x),hl
        ld a,b
        ld (eb_dir),a
        ld hl,(t_y)
        ld de,0x20
        add hl,de
        ld (eb_y),hl
        ld a,3
        ld (eb_type),a
        call ebullet_add
        jr z,t51_d
        ld hl,(eb_slot)
        ld de,0xE0
        add hl,de
        ld de,(AM + 0x0B32)
        ld a,d
        rla
        sbc a,a
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d                   ; +E0h: ext.l of the random word
t51_d:  ld hl,0x4390                ; ($54390)
        ld a,(ix+OS_FACE)
        or a
        jr nz,t51_f
        ld hl,0x4390 + 0x5BE
t51_f:  ld a,0x05
        ld de,0xC44
        call l3_gfx
        ld de,0
        ld b,d
        ld c,e
        call l3_at
        jp l3_p2                    ; (the result: D0)
