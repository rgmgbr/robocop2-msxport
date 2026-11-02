; Game logic, module 3 (continued, BANK_LC3 at 8000h around its call in player.asm game_tick):
; RoboCop's player_move ($AFF8), out of the fixed code. It calls only fixed routines (map
; attributes, the palette flash) and, through player.asm pm_punch, shots.asm pl_punch.

; ----- player_move ($AFF8) -----

pl_move:
        call pl_cellof              ; A0: the cell of the frame's start position
        ld a,(p_state)
        ld (pm_d1),a                ; D1 = state
        and 0x7E
        ld (pm_d5),a                ; D5 = state & 7Eh
        ld a,0xFF
        ld (pm_d2),a                ; D2 = -1: no new state
        ld hl,ac_jmask              ; (the immediate $B02B: 0 while the vehicle steers)
        ld a,(g_joy)
        and (hl)
        ld (pm_d0),a                ; D0 = joystick bits
        ld hl,(p_conf)              ; reversed controls ($1698)
        ld a,h
        or l
        jr z,pm_pend
        dec hl
        ld (p_conf),hl
        ld a,(g_frame)
        and 7
        call z,pl_flash
        ld a,(pm_d0)
        ld c,a
        and 0x0C
        jr z,pm_pend
        ld a,c
        xor 0x0C
        ld (pm_d0),a
pm_pend:
        ld a,(p_pend+1)             ; a state the last frame asked for ($1696)
        bit 7,a
        jr nz,pm_10
        ld a,0xFF
        ld (p_pend+1),a
        ld a,(p_pend)
        ld (pm_d2),a
pm_10:  ld a,(pm_d5)
        cp 0x0A
        jr nz,pm_14
        ld a,(pm_d0)                ; states 10/11: left and right only, no fire
        and 0x0C
        ld (pm_d0),a
        ld hl,g_joy
        res 4,(hl)
pm_14:  ld a,(pm_d5)
        cp 0x0E
        jr nz,pm_8
        ld a,(j_jumpb)              ; (the port: the joystick's trigger B does there what the Amiga's
        or a                        ;  up does, as when crouching: up only aims, and RoboCop hung on a
        jr z,pm_14u                 ;  level-2 trolley with no way down: the user's report, 2026-11-02)
        xor a
        ld (j_nojump),a
        inc a
        ld (pm_d0),a
pm_14u: ld a,(pm_d0)                ; states 14/15: up only
        and 1
        ld (pm_d0),a
pm_8:   ld a,(pm_d5)
        cp 8
        jr nz,pm_6
        ld a,(j_jumpb)              ; (the port: the joystick's trigger B rises as the Amiga's up
        or a                        ;  does, then jumps while held; up only aims there, and B had
        jr z,pm_8u                  ;  left RoboCop crouched, turning and not walking: 2026-10-23)
        ld a,1
        ld (pm_d0),a
pm_8u:  ld a,(pm_d0)                ; crouching: only up goes on
        cp 1
        jp nz,pm_b170
pm_6:   ld a,(pm_d5)
        cp 6
        jp z,pm_afb2
        ld a,(pm_d0)
        bit 2,a
        jr z,pm_right
        ld c,1                      ; left: state 1 (5 in the air)
        ld a,(p_air)
        or a
        jr z,pm_left1
        ld c,5
pm_left1:
        ld a,c
        ld (pm_d2),a
pm_right:
        ld a,(pm_d0)
        bit 3,a
        jr z,pm_step
        ld c,0                      ; right: state 0 (4 in the air)
        ld a,(p_air)
        or a
        jr z,pm_right1
        ld c,4
pm_right1:
        ld a,c
        ld (pm_d2),a
        ; the current state's step, unless the cell beside is a wall (the row above while vy < 0,
        ; i.e. on the ground or going up)
pm_step:
        ld a,(pm_d1)
        ld e,a
        ld d,0
        ld hl,pl_xstep
        add hl,de
        ld a,(hl)
        or a
        jr z,pm_add
        ld (pm_d4),a
        ld hl,(p_row)
        ld d,l                      ; D = row
        ld e,h                      ; E = column
        ld a,(p_vy+1)
        bit 7,a
        jr z,pm_side
        dec d                       ; the row above
pm_side:
        ld a,(pm_d4)
        bit 7,a
        jr z,pm_east
        dec e
        jr pm_wall
pm_east:
        inc e
pm_wall:
        call atr_rc
        and WALL
        jr nz,pm_b0fe
        ld a,(p_anim)
        and 6
        cp 6
        jr nz,pm_go
        ld a,6
        ld (snd_b30),a              ; footstep
pm_go:  ld a,(pm_d4)
pm_add: ld l,a
        rla
        sbc a,a
        ld h,a
        ld de,(p_x)
        add hl,de
        ld (p_x),hl
pm_b0fe:
        ld a,(j_jumpb)              ; (the port: the joystick's trigger B jumps from walking or
        or a                        ;  standing, whatever direction or fire is held: player.asm
        jr z,pm_nb                  ;  stick_bits)
        ld a,(pm_d1)
        cp 4
        jp c,pm_jb
pm_nb:  ld a,(pm_d0)
        and 0x0C
        jp nz,pm_b170
        ld a,(pm_d0)
        bit 0,a
        jr z,pm_b142
        ld a,(p_floor)              ; up on a floor with bit 2 ($1675) is fire
        bit 2,a
        jr z,pm_up
        ld a,0x10
        ld (g_joy),a
        jr pm_b142
pm_up:  ld a,(p_jwait)              ; just landed: stands a frame more
        or a
        jr z,pm_jump
        dec a
        ld (p_jwait),a
        ld a,2
        ld (pm_d2),a
        jp pm_b170
pm_jump:
        ld a,(p_air)
        or a
        jp nz,pm_b170
        ld a,(pm_d0)
        bit 4,a
        jp nz,pm_b170               ; up + fire: aims up, no jump
        ld a,(j_nojump)             ; (the port: the joystick's up only aims, its trigger B jumps:
        or a                        ;  player.asm stick_bits)
        jp nz,pm_b170
        ld a,(pm_d1)
        and 1
        add a,4
        ld (pm_d2),a                ; jump: state 4/5
        ld a,0xFF
        ld (p_air),a
pm_b142:
        xor a
        ld (p_jwait),a
        ld a,(pm_d0)
        bit 1,a
        jr z,pm_b170
        ld a,(g_joy)
        bit 4,a
        jr z,pm_crouch
        ld a,(pm_d1)                ; down + fire: state 6/7, next frame
        and 1
        add a,6
        ld (pm_d2),a
        ld (p_pend),a
        xor a
        ld (p_pend+1),a
        jr pm_b170
pm_crouch:
        ld a,(pm_d1)
        call st_c0f
        jr z,pm_b170
        ld a,(pm_d1)
        and 1
        add a,8
        ld (pm_d2),a                ; crouch: state 8/9
pm_b170:
        ld a,(pm_d5)
        cp 8
        jr nz,pm_count
        ld a,3
        ld (p_jwait),a
        ld a,(pm_d0)
        cp 1
        jr z,pm_rise
        xor a                       ; crouched: holds step 4, turning with left/right
        ld (p_rev),a
        ld hl,(p_anim)
        ld de,4
        or a
        sbc hl,de
        jp m,pm_count
        ld a,(pm_d0)
        bit 2,a
        jr z,pm_c8
        ld hl,9
        ld (p_state),hl
pm_c8:  ld a,(pm_d0)
        bit 3,a
        jr z,pm_c4
        ld hl,8
        ld (p_state),hl
pm_c4:  ld hl,4
        ld (p_anim),hl
        jr pm_count
pm_rise:
        ld a,0xFF                   ; up: rises (the animation backwards), stands at step 1
        ld (p_rev),a
        ld hl,(p_anim)
        ld a,h
        or a
        jr nz,pm_count
        ld a,l
        cp 1
        jr nz,pm_count
        ld a,2
        ld (pm_d2),a
pm_count:
        ld a,(p_rev)
        or a
        jr z,pm_fwd
        ld hl,(p_anim)
        dec hl
        bit 7,h
        jr z,pm_aset
        ld hl,(p_last)
        jr pm_aset
pm_fwd: ld hl,(p_anim)
        ld de,(p_last)
        or a
        sbc hl,de
        add hl,de
        jr nz,pm_inc
        ld hl,-1
pm_inc: inc hl
pm_aset:
        ld (p_anim),hl
        ; in the air y += vy / 4 and vy += 2 up to 1Fh; on the ground vy = -14h (a jump's start)
        ld a,(p_air)
        or a
        jr z,pm_ground
        ld hl,(p_vy)
        sra h
        rr l
        sra h
        rr l
        ld de,(p_y)
        add hl,de
        ld (p_y),hl
        ld hl,(p_vy)
        ld de,0x1F
        or a
        sbc hl,de
        jp p,pm_floor
        ld hl,(p_vy)
        inc hl
        inc hl
        ld (p_vy),hl
        jr pm_floor
pm_ground:
        ld hl,-0x14
        ld (p_vy),hl
        ; floors: a lift, else the start cell's attributes (bits 0/2); landing needs vy >= 0
pm_floor:
        call pl_lift
        jr c,pm_b24a
        ld hl,(p_row)
        ld d,l                      ; D = row
        ld e,h                      ; E = column
        call atr_rc
        ld de,(p_y)
        and FLOOR
        ld (p_floor),a
        ld hl,p_floor+1
        ld (hl),0
        jr z,pm_b26a
        ld a,(p_vy+1)
        bit 7,a
        call z,pm_land
        ld a,(p_air)
        or a
        jr nz,pm_b24a
        ld a,e
        and 0xF0                    ; on the cell's top
        ld e,a
        ld (p_y),de
        jr pm_b282
pm_b24a:
        ld (p_y),de
        ld a,(p_vy+1)
        bit 7,a
        call z,pm_land
        jr pm_b282
pm_b26a:
        ld a,(p_air)                ; no floor: falls from rest (state 4/5)
        or a
        jr nz,pm_b282
        ld a,(p_state)
        and 1
        add a,4
        ld (pm_d2),a
        ld a,0xFF
        ld (p_air),a
        ld hl,0
        ld (p_vy),hl
        ; walking or standing states with nothing asked for stand; so does a 2
pm_b282:
        ld a,(pm_d1)
        call st_c0f
        jr z,pm_b28e
        ld a,(pm_d2)
        bit 7,a
        jr nz,pm_stand
pm_b28e:
        ld a,(pm_d2)
        cp 2
        jr nz,pm_change
pm_stand:
        ld a,(pm_d1)
        and 1
        add a,2
        ld (pm_d2),a
pm_change:
        ld a,(pm_d2)
        bit 7,a
        jr nz,pm_cam
        ld hl,p_state
        cp (hl)
        jr nz,pm_new
        inc hl
        ld a,(hl)
        or a
        jr z,pm_cam
        ld a,(pm_d2)
pm_new: ld hl,0
        ld (p_anim),hl
        ld l,a
        ld (p_state),hl
        ld e,a                      ; the state's parameters ($B3AE): $15DF, $15E4, hitbox
        ld d,0
        ld hl,pl_stparm
        add hl,de
        add hl,de
        add hl,de
        ld a,(hl)
        ld (p_de),a
        inc hl
        ld a,(hl)
        ld (p_rev),a
        inc hl
        ld a,(hl)
        ld (p_hb),a
        xor a
        ld (p_hb+1),a
        ; camera: x eases by 1/16 towards x - CAM_DX (0..CAM_XMAX), y by 1/8 towards y - CAM_DY,
        ; or towards -60h when that is above 38h (0..the level's lowest)
pm_cam: ld hl,(p_x)
        ld de,(ac_camdx)            ; (the immediates $B2D8 and $B2FC: obj32 changes them)
        or a
        sbc hl,de
        ld de,(gcam_x)
        or a
        sbc hl,de
        sra h
        rr l
        sra h
        rr l
        sra h
        rr l
        sra h
        rr l
        add hl,de
        bit 7,h
        jr z,pm_cx
        ld hl,0
        jr pm_cxs
pm_cx:  ld de,CAM_XMAX
        or a
        sbc hl,de
        add hl,de
        jr c,pm_cxs
        ex de,hl
pm_cxs: ld (gcam_x),hl
        ld hl,(p_y)
        ld de,(ac_camdy)
        add hl,de
        ld de,0x38
        or a
        sbc hl,de
        add hl,de
        jp p,pm_cy
        ld hl,-0x60
pm_cy:  ld de,(gcam_y)
        or a
        sbc hl,de
        sra h
        rr l
        sra h
        rr l
        sra h
        rr l
        add hl,de
        bit 7,h
        jr z,pm_cy1
        ld hl,0
        jr pm_cys
pm_cy1: ld de,(gcam_ymax)
        or a
        sbc hl,de
        add hl,de
        jp m,pm_cys
        ex de,hl
pm_cys: ld (gcam_y),hl
        ; the start of the level ($15CA clear): standing, aim 2, controls locked; from game frame
        ; 1Ch the arm poses 8..25 (sound 303h every few), then $15CA is set
        ld a,(p_started)
        or a
        jr nz,pm_view
        ld hl,4
        ld (p_aim),hl
        ld hl,0
        ld (p_anim),hl
        ld hl,2
        ld (p_de),hl
        ld (p_state),hl
        ld a,0xFF
        ld (g_lock),a
        ld hl,8
        ld (p_arm),hl
        ld hl,(g_frame)
        ld de,0x1C
        or a
        sbc hl,de
        jp m,pm_view
        ld a,(p_startn)
        ld c,a
        and 0x0B
        jr nz,pm_s1
        ld hl,0x0303
        ld (AM + 0x0B2E),hl         ; (move.w #$303,$B2E)
pm_s1:  ld a,c
        dec a
        jr nz,pm_s2
        push bc                     ; the step after the first 303h, when the original plays it
        ld a,SQ_GUN                 ; (player.asm frame_keys, a frame on): the port's sound in its
        call snd_play               ; place, once (tools/msxgun.py; frame_keys drops every 303h)
        pop bc
pm_s2:  ld a,c
        srl a
        add a,8
        ld l,a
        ld h,0
        ld (p_arm),hl
        inc c
        ld a,c
        ld (p_startn),a
        cp 0x25
        jr nz,pm_view
        ld a,0xFF
        ld (p_started),a
        xor a
        ld (p_startn),a
        ld (g_lock),a
        ld hl,0
        ld (p_arm),hl
pm_view:
        jp pl_view

; States 6/7 ($AFB2): at step 8 back to standing; at step 4 the effect of type 8 ahead of him.
pm_afb2:
        ld hl,(p_anim)
        ld a,h
        or a
        jp nz,pm_b170
        ld a,l
        cp 8
        jr nz,pm_a4
        ld a,2
        ld (pm_d2),a
pm_a4:  ld a,l
        cp 4
        jp nz,pm_b170
        ld a,0x14
        ld (snd_b2c),a
        call pm_punch              ; (module 1's: player.asm)
        jp pm_b170

; Landing: on the ground, standing (state 2 asked for), vy 0, a frame before jumping again.
; Keeps DE.
pm_land:
        xor a
        ld (p_air),a
        ld hl,0
        ld (p_anim),hl
        ld (p_vy),hl
        ld a,2
        ld (pm_d2),a
        ld a,1
        ld (p_jwait),a
        ret

; (pm_b0fe) The joystick's trigger B in states 0-3 (player.asm stick_bits).
pm_jb:  ld a,(p_jwait)              ; trigger B: just landed, a frame more first (standing unless
        or a                        ; a direction is held)
        jr z,pm_jba
        dec a
        ld (p_jwait),a
        ld a,(pm_d0)
        and 0x0C
        jp nz,pm_b170
        ld a,2
        ld (pm_d2),a
        jp pm_b170
pm_jba: ld a,(p_air)
        or a
        jp nz,pm_b170
        ld a,(pm_d2)                ; the jump: state 4/5 the way of the direction held (pm_left,
        cp 2                        ; pm_right), else of the state
        jr c,pm_jbw
        ld a,(pm_d1)
pm_jbw: and 1
        add a,4
        ld (pm_d2),a
        ld a,0xFF
        ld (p_air),a
        xor a
        ld (p_jwait),a
        jp pm_b170                  ; (down held too: no crouch)

; A = state -> NZ for those of the walking/standing set (bits of $C0F: 0-3, 10, 11).
st_c0f: cp 4
        jr c,sc_yes
        cp 10
        jr z,sc_yes
        cp 11
        jr z,sc_yes
        xor a
        ret
sc_yes: or 1
        ret

; The lift check ($BD72): on lift 3, 2, 1 or 0 (x in [left, right), y in (top - 15, top], not in
; the air going up) -> Carry, DE = top - 4, x moved by the lift's dx, its flag ($167A + index)
; set. The lifts' table (left, right, top, dx, index: 4 words each) is the special objects'.
; (The port: special.asm sp_update clears every entry's right edge and fills entries 0, 1, ... from
; $168C = 0 on, 2 a filled entry; with $168C below 8 the entries from $168C / 2 on keep right 0 and an
; x not negative is right of them, so the loop starts at the last entry filled, or ends at once with
; none: the loop's own result.)
pl_lift:
        ld hl,(AM + 0x168C)
        ld a,h
        or l
        jr z,pli_0                  ; (no entry filled)
        ld a,h
        or a
        jr nz,pli_go
        ld a,l
        cp 8
        jr nc,pli_go                ; (four or more: every entry)
        ld a,(p_x + 1)
        rla
        jr c,pli_go                 ; (x negative: every entry)
        ld e,l
        ld d,h
        ld ix,lifts - 2
        add ix,de                   ; the last entry filled
        ld a,l
        rrca
        ld b,a                      ; the entries filled
        jr pli_lp
pli_0:  ld a,(p_x + 1)
        rla
        ret nc                      ; (NC: on no lift)
pli_go: ld b,4
        ld ix,lifts + 6
pli_lp: ld a,(p_air)
        or a
        jr z,pli_x
        ld a,(p_vy+1)
        bit 7,a
        jr nz,pli_next
pli_x:  ld hl,(p_x)
        ld e,(ix+0)
        ld d,(ix+1)
        or a
        sbc hl,de
        jp m,pli_next               ; x < left
        ld hl,(p_x)
        ld e,(ix+8)
        ld d,(ix+9)
        or a
        sbc hl,de
        jp p,pli_next               ; x >= right
        ld l,(ix+16)
        ld h,(ix+17)
        ld de,(p_y)
        or a
        sbc hl,de
        jp m,pli_next               ; top < y
        ld de,15
        or a
        sbc hl,de
        jp p,pli_next               ; top - 15 >= y
        ld e,(ix+16)
        ld d,(ix+17)
        dec de
        dec de
        dec de
        dec de
        ld l,(ix+24)
        ld h,(ix+25)
        push de
        ld de,(p_x)
        add hl,de
        ld (p_x),hl
        ld e,(ix+32)
        ld d,(ix+33)
        ld hl,p_onlift
        add hl,de
        ld a,l
        xor 1
        ld l,a                      ; (byte n at p_onlift + (n ^ 1))
        ld (hl),0xFF
        pop de
        scf
        ret
pli_next:
        dec ix
        dec ix
        djnz pli_lp
        or a
        ret

; -> p_row, p_col: the map cell of (x, y): row y >> 4, column (x >> 4) - 7 (A0 = $37FF2 + ...:
; the map at $38000 starts 7 cells to the right of x = 0).
pl_cellof:
        ld hl,(p_y)
        ld a,l
        srl h
        rra
        srl h
        rra
        srl h
        rra
        srl h
        rra
        ld (p_row),a
        ld hl,(p_x)
        ld a,l
        srl h
        rra
        srl h
        rra
        srl h
        rra
        srl h
        rra
        sub 7
        ld (p_col),a
        ret

; ----- rc-edge: may the frame's ticks run? (player.asm rc_safe, for the cadence) -----

; The logic's other moves of his x within a tick, besides his own step (pl_xstep's, RC_VX): rc_bound adds their
; reach to the frame's growth on each side (docs/MSX_ARCHITECTURE.md "RoboCop at the picture's edge").
RC_BELT:    equ 8                   ; level 1's conveyors carry him 4 px a tick (mapobj.asm act_cv; entries 15 and 16
                                    ; of its object list are one belt twice: 8); its barriers' push (act_1c) and the
                                    ; vehicle's ride (sp_vehicle) are 4
RC_PUSH:    equ 8                   ; level 3's type 21 pushes him 8 px a tick (level3obj.asm obj_push): the way it
                                    ; faces, and once it stands away from it (t21_st turns it to face him)
RC_PUSHD:   equ 96                  ; ... a walker whose x is within this of his: its push zones (his x - its x
                                    ; 28..43 facing right, -20..-5 facing left) and the frame's moves (his 3 px a
                                    ; tick, its steps of up to 11 px every other tick: t21_step)
RC_SNAPD:   equ 32                  ; a mount's entry within this of his x: its snap (rc_snap)

; -> C when the view shown is the one the game wants (no lag: at the map's ends he may walk to its
; edge), when RoboCop is not shown, or when his next picture keeps every opaque pixel on the columns
; the VDP shows whatever the frame's ticks do: within k = min(B, RC_K) ticks his place moves at most
; Gr to the right and Gl to the left (rc_grow: his steps, level 1's conveyors, level 3's type-21
; walkers, a mount's snap) and his drawing reaches at most his state's rc_reach columns (gen/rcedge.inc,
; tools/mkrom.py rcedge: from the sprite pool's pixels, the compositions of his state's records and those
; any state starts with, against O_X - p_hotx), against SAT x 0-255 (the V9938's R#18 moves the sprites
; with the picture: spr_xadj) or 8-255 (the V9958's MSK hides 0-7). NC with D = 0 (the cadence's tick
; cap: none: the scroll catches up first) otherwise. B = the ticks due. Keeps BC.
rc_bound:
        ld hl,(v_x)
        ld de,(cam_x)
        or a
        sbc hl,de
        scf
        ret z                       ; (no lag)
        ld ix,obj_tab
        bit 7,(ix+O_FLAGS)
        scf
        ret z                       ; (not shown)
        push bc
        ld a,b                      ; k = min(B, RC_K) ticks
        cp RC_K
        jr c,rcb_k
        ld a,RC_K
rcb_k:  ld b,a
        call rc_grow                ; C = Gr, B = Gl
        jr c,rcb_no                 ; (256 px or more: hold)
        push bc
        ld a,(p_state + 1)
        or a
        jr nz,rcb_ng                ; (a state the table lacks: hold)
        ld a,(p_state)
        cp RC_STATES
        jr nc,rcb_ng
        add a,a
        ld e,a
        ld d,0
        ld hl,rc_reach
        add hl,de
        ld a,(hl)                   ; A = the leftmost column,
        inc hl
        ld b,(hl)                   ; B = the rightmost
        push af
        ld l,(ix+O_X)
        ld h,(ix+O_X+1)
        ld de,(p_hotx)
        or a
        sbc hl,de                   ; his place P
        ld a,(spr_xadj)
        ld e,a
        rla
        sbc a,a
        ld d,a
        add hl,de
        ex de,hl                    ; DE = Q: his place in SAT x
        ld l,b
        ld a,b
        rla
        sbc a,a
        ld h,a
        add hl,de                   ; Q + the rightmost
        ld a,c
        add a,l
        ld l,a
        jr nc,rcb_r
        inc h                       ; + Gr
rcb_r:  ld a,h                      ; (at most 255: H 0, or negative)
        or a
        jr z,rcb_l
        jp p,rcb_nf                 ; (past SAT x 255)
rcb_l:  pop af
        pop bc                      ; B = Gl
        ld l,a
        rla
        sbc a,a
        ld h,a
        add hl,de                   ; Q + the leftmost
        ld e,b
        ld d,0
        or a
        sbc hl,de                   ; - Gl
        ld a,(hud_msk)
        or a
        jr z,rcb_m
        ld de,8
        or a
        sbc hl,de                   ; (the V9958: from SAT x 8)
rcb_m:  bit 7,h
        pop bc
        jr nz,rcb_nd                ; (left of the first column)
        scf
        ret
rcb_nf: pop af
rcb_ng: pop bc                      ; (Gr, Gl)
rcb_no: pop bc
rcb_nd: ld d,0
        or a
        ret

; B = k ticks -> C = Gr, B = Gl, NC: his place's largest move to the right and to the left within them: his step
; a tick (rc_step) and the pushes that way (rc_push), times k, and a mount's snap that way (rc_snap); C when
; either reaches 256 px.
rc_grow:
        call rc_snap                ; D = the snap right, E = left
        push de
        call rc_push                ; D = the pushes a tick right, E = left (keeps BC)
        call rc_step                ; A = the step a tick (keeps BC, DE, HL)
        ld c,a
        add a,e
        call rc_mulk                ; HL = (the step + the pushes left) x k
        push hl
        ld a,c
        add a,d
        call rc_mulk                ; HL = (the step + the pushes right) x k
        pop de                      ; DE = the left one
        pop bc                      ; B = the snap right, C = left
        ld a,b
        call rc_adda                ; HL = Gr
        ex de,hl
        ld a,c
        call rc_adda                ; HL = Gl, DE = Gr
        ld a,h
        or d
        scf
        ret nz                      ; (256 px or more)
        ld b,l
        ld c,e
        or a
        ret

; HL += A.
rc_adda:
        add a,l
        ld l,a
        ret nc
        inc h
        ret

; HL = A x B (B = k: 0 gives 0). Keeps BC, DE.
rc_mulk:
        push bc
        push de
        ld e,a
        ld d,0
        ld hl,0
        inc b
        jr rmul_1
rmul_l: add hl,de
rmul_1: djnz rmul_l
        pop de
        pop bc
        ret

; -> A = his largest step a tick: RC_VX (pl_xstep's), in level 1 + RC_BELT (its conveyors). Keeps BC, DE, HL.
rc_step:
        ld a,(AG + 0x8050)          ; (the level, 0-2: the word's low byte)
        or a
        ld a,RC_VX + RC_BELT
        ret z                       ; (level 1)
        ld a,RC_VX
        ret

; -> D = the pushes his x may take to the right in a tick, E = to the left: in level 3, RC_PUSH for each type-21
; walker (the enemy slots, objects.asm) whose x is within RC_PUSHD of his: to the right when it faces right or
; he is right of it, to the left when it faces left or he is left of it. Keeps BC, IX.
rc_push:
        ld de,0
        ld a,(AG + 0x8050)
        cp 2
        ret nz                      ; (levels 1 and 2)
        push bc
        push ix
        ld ix,OBJ_SLOTS
        ld b,(OBJ_END - OBJ_SLOTS) / 4
rpu_lp: ld a,(ix+OS_TYPE)
        cp 21
        jr nz,rpu_n
        push de
        ld e,(ix+OS_X)
        ld d,(ix+OS_X+1)
        ld hl,(p_x)
        or a
        sbc hl,de                   ; his x - its x
        ld de,RC_PUSHD
        add hl,de                   ; (within RC_PUSHD: 1 .. 2 RC_PUSHD - 1)
        pop de
        ld a,h
        or a
        jr nz,rpu_n
        ld a,l
        or a
        jr z,rpu_n
        cp 2 * RC_PUSHD
        jr nc,rpu_n
        ld c,a                      ; C = his x - its x + RC_PUSHD
        ld a,(ix+OS_FACE)
        or a
        jr z,rpu_r                  ; (facing right)
        ld a,c
        cp RC_PUSHD
        jr c,rpu_l                  ; (facing left, he left of it: to the left only)
rpu_r:  ld a,d
        add a,RC_PUSH
        ld d,a                      ; (to the right)
        ld a,(ix+OS_FACE)
        or a
        jr nz,rpu_l                 ; (facing left: to the left as well)
        ld a,c
        cp RC_PUSHD
        jr nc,rpu_n                 ; (facing right, he right of it: to the right only)
rpu_l:  ld a,e
        add a,RC_PUSH
        ld e,a                      ; (to the left)
rpu_n:  push de
        ld de,4
        add ix,de                   ; (the next slot)
        pop de
        djnz rpu_lp
        pop ix
        pop bc
        ret

; -> D = a mount's snap of his x to the right within the frame, E = to the left (none: 0, 0), for an entry of
; the lifts table (special.asm sp_entry) within RC_SNAPD px of his x: a trolley's (10h wide; level 2,
; sp_trolley: his x becomes its left once he hangs, up to 15 px left, with the landing tick's step of 2 either
; way) he does not hang on yet (state 14/15): 4 and 14h; the vehicle's (36h wide; level 1, sp_vehicle: its
; left + 12h once he rides, up to 18 px right or 35 left) he did not ride at the last tick ($16D8): 14h and 28h.
; A lift's entry (30h wide) moves him in y only. Keeps BC, HL, IX.
rc_snap:
        push hl
        push bc
        push ix
        ld ix,lifts
        ld b,4
rsn_lp: ld l,(ix+8)
        ld h,(ix+9)                 ; its right edge (0: an empty entry)
        ld a,h
        or l
        jr z,rsn_n
        ld e,(ix+0)
        ld d,(ix+1)                 ; DE = its left edge
        or a
        sbc hl,de                   ; its width
        ld a,h
        or a
        jr nz,rsn_n
        ld c,l
        ld a,l
        cp 0x10
        jr z,rsn_t
        cp 0x36
        jr nz,rsn_n                 ; (a lift's)
        ld a,(AM + (0x16D8 ^ 1))
        or a
        jr nz,rsn_n                 ; (the vehicle he rides)
        jr rsn_d
rsn_t:  ld a,(p_state)
        and 0xFE
        cp 14
        jr z,rsn_n                  ; (the trolley he hangs on)
rsn_d:  ld hl,(p_x)
        or a
        sbc hl,de
        ld de,RC_SNAPD
        add hl,de                   ; his x - its left + RC_SNAPD: within reach 0 .. width + 2 RC_SNAPD - 1
        ld a,h
        or a
        jr nz,rsn_n
        ld a,c
        add a,2 * RC_SNAPD - 1
        cp l
        jr c,rsn_n                  ; (beyond)
        ld de,0x0414                ; (the trolley's: 4 right, 14h left)
        ld a,c
        cp 0x10
        jr z,rsn_x
        ld de,0x1428                ; (the vehicle's: 14h right, 28h left)
        jr rsn_x
rsn_n:  inc ix
        inc ix
        djnz rsn_lp
        ld de,0
rsn_x:  pop ix
        pop bc
        pop hl
        ret
