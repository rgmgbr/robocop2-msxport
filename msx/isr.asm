; Interrupts: IM 2 through a 257-byte vector table (any data-bus value leads to IM2_JUMP),
; the line interrupt for the HUD split and VBLANK for the per-frame registers.
;
; Rules for the main program:
; - every port 99h sequence (register write, VRAM address, status read) runs with
;   interrupts disabled, and R#15 is 0 whenever interrupts are enabled;
; - the registers of the next frame are published as a list [seq, len, value, reg|80h, ...,
;   cam_x, cam_y, game frame] (the tail is not sent to the VDP; with the list's pub_spr copy it
;   records what the list shows, for verification)
;   (publish) together with the sprite engine's uploads for it (sprites.asm: pq, run by
;   spr_upload in the split interrupt); the VBLANK after they ran puts the list on screen
;   (vbl_ptr: applied at every VBLANK, seq copied to app_seq) with its SAT;
; - both interrupts write VRAM, so every VRAM stream of the main program sets vram_busy before
;   its address and ends with vram_done (which writes a SAT the interrupt left meanwhile); the
;   uploads then wait for the next frame.
;
; Split timing (openMSX VDP model): the line interrupt fires at the right border of display
; line (R#19 - R#23) & 255, where S#1 FH goes up too; R#1 (blank), R#8 (sprites) and R#18
; take effect at the start of the next line (144 VDP ticks after its sync), while R#2, R#23,
; R#26, R#27 and the palette take effect immediately. HR (S#2 bit 5) is 1 for 312 VDP ticks
; from the right border, computed with the current horizontal adjust (so writing R#18 moves
; the window); with R#18 = 0 it goes down 226 ticks into the next line, past its latch point.
; The One Chip MSX's VDP (ESE-VDP, OCM-PLD: the SX-2) matches R#19 the same way (live, against
; the line + R#23, at the line's last pixel), but its HR is 1 from the end of the line to 17
; ticks into the next one's pixels (236 ticks, R#18 does not move it): 125 ticks later than
; openMSX's. Only an edge of FH tells the lines apart on both.

isr:    push af
        push bc
        push hl
        ld c,VDP_CTRL
        ld a,1
        out (c),a
        ld a,0x8F
        out (c),a
        in b,(c)                    ; S#1: bit 0 = FH (the read acknowledges it)
        bit 0,b
        jr z,isr_r15
        ld a,(split_armed)
        or a
        call nz,isr_split           ; (R#15 still 1: sp_r19 reads S#1)
isr_r15:
        xor a
        out (c),a
        ld a,0x8F
        out (c),a                   ; R#15 = 0
        in a,(c)                    ; S#0: bit 7 = VBLANK (the read acknowledges it)
        or a
        call m,isr_vblank
        pop hl
        pop bc
        pop af
        ei
        reti

IM2_JP0:    equ 0xC3 + (isr & 0xFF) * 256   ; IM2_JUMP's first two bytes: "jp isr" (isr_init)

; HUD split (V = VIEW_LINES): the interrupt fires at the end of line V-5. The routine goes by
; one line match a frame, the end of line V-2 (S#1 FH, R#19 against the line + R#23 at the
; line's last pixel: the same on the V9938, the V9958 and the One Chip MSX's ESE-VDP), and from
; it by delays worked out on this machine (split_cal), never by S#2 HR, whose window differs
; between those chips. It takes that match by its interrupt (split.asm sp_irq: the interrupts on
; in a loop, IM2_JUMP "pop hl / ret" meanwhile), not by polls of S#1: the user's MSX2 Hotbit, a
; real V9938, lost FH in 0-75 % of polls by their phase (2026-10-24, the VDP lab). Its timed
; part runs from RAM (split.asm, at SR_RAM), as do split_cal's waits and its M run: no cartridge
; read comes between the match and the writes timed from it, so that a cartridge's wait states
; cannot move them (the MSX Pico+ holds the Z80 on ROM reads, more in some frames than in
; others, 2026-10-24). After SP_GAP turns (no VDP write right after the read of S#1 that acknowledged
; the interrupt at V-5) it sets R#19 = split_r19 (the play field's R#23 + V - 2) and waits for
; its interrupt; then split_dly turns and the blank, 900-1070 VDP ticks after the match,
; mid-line V-1: past that line's latch of R#1 and well before line V's in every VDP model
; (blueMSX takes R#1 for the next line 186 ticks after a match, openMSX 230, the ESE-VDP 344;
; line V's 1554, 1598 and 1712 after); split_dly1 turns, past the last pixel of line V-1, and
; the sprites off; the page, the scroll and the HUD's colours 1-15 during the blank lines V..V+4
; (sp_regs: 38-40 port accesses, 3.9 lines on the T9769 engines, whose VDP ports take cycles
; more, 3.4-3.5 on a plain Z80); split_dly2 turns and the display on, 840-980 ticks after the
; match of line V+3 on every machine (the measured table: docs/MSX_ARCHITECTURE.md), so the HUD
; shows from line V+5. The jitter is the turn under way when the interrupt comes: 0-14 T-states.
; The blank lines are five (HUD_BLACK): four held the registers and the palette only with the
; display-on just before the HUD's first line (0.1.0's split landed a line late on the FS-A1FX),
; and the design of that morning wrote 10 colours while the HUD showed. Colour 0 is not written:
; the HUD's is the play field's (tools/mkrom.py checks). On the V9958 the border mask is turned
; off (the HUD's left columns are still black there) so that the HUD uses all 256 px. Then, back
; in the ROM (sp_r19), R#19 goes behind (SPLIT_R19), S#1 is read (FH of line V-2, up since the
; wait) and IM2_JUMP gets its jump back: the line interrupt stays enabled, a match the play
; field's R#19 makes against the HUD's R#23 is acknowledged and ignored (isr: split_armed 0). A
; split serviced so late that its R#19 write comes past line V-2's match (never seen: that write
; comes ~310 T-states ahead of the match at 3.58 MHz, ~220 ahead of sp_irq's EI, and the
; interrupt's service varies by up to ~130 T-states in openMSX, vdp.asm vram_write's DI being
; ~150) gets no match that frame: after SP_TURNS turns (~15.7 lines at 3.58 MHz) it writes
; everything at once (sp_late), the HUD that much late that frame. One whose match came between
; that write and sp_irq's EI finds FH up and its interrupt taken at once: timed as usual, 65-79
; T-states late.

; (The split's timed path, its wait for the match, sp_regs and split_cal's waits run from RAM:
; split.asm.)

; The split's end, from RAM (sp_on): R#19 behind, the HUD's work for the frame.
sp_r19:
        if SPLITDIAG
        in a,(c)                    ; (FH of line V-2, up since the split's sync: acknowledged)
        ld b,SC_GAP
dg_gp:  djnz dg_gp
        ld a,(HUD_R23 + 169) & 255
        out (c),a
        ld a,0x93
        out (c),a                   ; SPLITDIAG: R#19 for the end of display line 169
        ld b,0                      ; (polls: on a real V9938 they can miss FH, msx/lab.asm)
dg_fh:  in a,(c)
        rrca
        jr c,dg_got
        djnz dg_fh
dg_got: ld a,b
        neg                         ; the polls from the display-on to that match
        ld hl,dg_min
        cp (hl)
        jr nc,dg_n1
        ld (hl),a
dg_n1:  inc hl
        cp (hl)
        jr c,dg_n2
        ld (hl),a                   ; the fewest and the most this step
dg_n2:  ld hl,dg_cnt
        inc (hl)
        jr nz,dg_x
        ld hl,dg_step
        ld a,(hl)
        inc a
        and 15
        ld (hl),a                   ; a step every 256 frames
        ld hl,0x00FF
        ld (dg_min),hl              ; dg_min 255, dg_max 0
dg_x:
        endif
        ld a,SPLIT_R19
        out (c),a
        ld a,0x93
        out (c),a                   ; R#19 against the HUD's R#23: its match (line V-5) is behind
        in a,(c)                    ; (S#1: FH of line V-2, up since the split's sync, and a match
                                    ;  that came meanwhile, acknowledged)
        xor a
        out (c),a
        ld a,0x8F
        out (c),a                   ; R#15 = 0
        ld hl,IM2_JP0
        ld (IM2_JUMP),hl            ; (the ISR's jump again: sp_irq left "pop hl / ret")
        call isr_fbgo               ; a play-field copy waiting: it starts as the beam leaves
        jp spr_upload               ; sprites off until the next frame: their uploads
sp_late:
        ld a,R1_BLANK               ; (serviced too late for its matches: everything at once)
        out (c),a
        ld a,0x81
        out (c),a
        ld a,R8_SPR_OFF
        out (c),a
        ld a,0x88
        out (c),a
        ld hl,split_list+1
        call sp_regs
        jp sp_on

; The split's delays for this machine (split_dly, split_dly1, split_dly2: turns of 14 T-states),
; worked out with the display off (display_on, every level start; the interrupts off but in
; split.asm's waits for a match, whose interrupts only FH can raise: R#1 = R1_CAL, IE0 off;
; leaves R#15 = 0, IM2_JUMP as it found it, R#1 with the display off). R#23 = 0 meanwhile (the
; VBLANK's list sets the play field's again). Each measure is the least of CAL_TRIES (a match
; missed only makes a count longer). N: the turns from split.asm's return at the match of line
; CAL_LINE to that of line CAL_LINE + 32 (sc_cnt), so n32 = N + SC_GAP + 15 turns in 32 lines
; (the fixed path from the match, 212 + 14 SC_GAP T-states; sc_turns adds the wraps'; its few
; cartridge reads cost a cartridge's waits about a turn in 521). M: the turns left to the match
; of line CAL_LINE + 48 after sp_seq ran from that of line CAL_LINE + 40 exactly as the split runs
; it from its own (split.asm sc_mrun, from RAM: the same return, the same jump and call, sp_seq's
; delays at 0, a blank enabling no interrupt, cal_list and the play field's colours instead of
; the HUD's), so the time from a match to the end of sp_seq is 8 lines - 14 M - 155 - 14 SC_GAP
; T-states, whatever the VDP's port waits and the cartridge's. Then, n = n32 / 32 the turns of a line: split_dly =
; 0.6875 n - 11 puts the blank 0.69 line after the match of line V-2 (169 T-states after it at
; 3.58 MHz, where it is 0: 970-1060 ticks); split_dly1 = n - 14 - split_dly puts the sprites-off
; past the last pixel of line V-1; split_dly2 = M + SC_GAP + 6 - 2.31 n - split_dly - split_dly1
; puts the display-on 0.69 line after the match of line V+3 (5.69 lines after line V-2's). Any
; measure missing (no VDP): 0 / 2 / 11, which suit every machine here at 3.58 MHz.
CAL_LINE:   equ 40                  ; (the first line of split_cal's measures)
CAL_TRIES:  equ 4
split_cal:
        di
        ld hl,(IM2_JUMP)
        push hl                     ; (its jump's first two bytes: the game's, or the lab's)
        ld c,VDP_CTRL
        ld a,R1_CAL
        out (c),a
        ld a,0x81
        out (c),a                   ; R#1: display off, no VBLANK interrupt (from the title the
                                    ;  front end leaves it on: it took split.asm's waits, its F
                                    ;  never read; display_on sets R#1 again after)
        ld a,R0_IE1_ON
        out (c),a
        ld a,0x80
        out (c),a                   ; IE1 on (the interrupts off but in split.asm's waits)
        xor a
        out (c),a
        ld a,0x97
        out (c),a                   ; R#23 = 0
        ld a,1
        out (c),a
        ld a,0x8F
        out (c),a                   ; S#1
        xor a
        ld (split_dly),a
        ld (split_dly1),a           ; (sp_seq timed with no delay)
        ld a,R1_CAL
        ld (sp_v1),a                ; (and a blank that enables no interrupt)
        ld hl,pf_pal + 2
        ld (sp_palp),hl             ; (the play field's colours 1-15: what the VBLANK writes)
        ld hl,0xFFFF
        ld (cal_n),hl
        ld (cal_m),hl
        ld b,CAL_TRIES
scl_n:  push bc
        ld a,CAL_LINE
        call sc_sync                ; the match of line CAL_LINE
        jr nc,scln_x
        ld a,CAL_LINE + 32
        call sc_ack                 ; R#19 for 32 lines on
        call sc_cnt                 ; N: the turns to its match
        jr nc,scln_x
        call sc_turns
        ld de,cal_n
        call sc_min
scln_x: pop bc
        djnz scl_n
        ld b,CAL_TRIES
scl_m:  push bc
        call sc_mrun                ; M: from the match of line CAL_LINE + 40, sp_seq (R#16 writes
        jr nc,sclm_x                ;  and pf_pal here), the turns left to that of CAL_LINE + 48
        call sc_turns
        ld de,cal_m
        call sc_min
sclm_x: pop bc
        djnz scl_m
        ld hl,SR_PAL
        ld (sp_palp),hl             ; (the HUD's colours again)
        ld a,R1_BLANK
        ld (sp_v1),a
        ld hl,(cal_m)
        ld a,h
        and l
        inc a
        jr z,sc_dflt                ; (no M: no VDP)
        ld hl,(cal_n)
        ld a,h
        and l
        inc a
        jr z,sc_dflt                ; (no N)
        ld de,SC_GAP + 15
        add hl,de                   ; n32: the turns of 32 lines
        ld (cal_n),hl
        srl h
        rr l
        srl h
        rr l                        ; n32 / 4 (~130 a multiple of a 3.58 MHz Z80: x 74 below fits
                                    ;  16 bits up to ~6.8 times; split_dly2 saturates from ~4.2)
        push hl
        ld d,h
        ld e,l
        add hl,hl
        push hl                     ; (2)
        add hl,hl
        add hl,hl
        add hl,de                   ; 9
        pop de
        add hl,de                   ; 11
        add hl,hl                   ; 22 (n32 / 4)
        ld a,h                      ; 0.6875 n
        sub 11
        jr nc,scl_s
        xor a
scl_s:   ld (split_dly),a
        ld e,a                      ; split_dly
        ld hl,(cal_n)
        add hl,hl
        add hl,hl
        add hl,hl
        ld a,h                      ; n (n32 / 32: below 256)
        sub 14
        jr c,scl_d1z
        sub e
        jr nc,scl_d1
scl_d1z: xor a
scl_d1:  ld (split_dly1),a
        add a,e
        ld e,a                      ; split_dly + split_dly1
        pop hl                      ; n32 / 4
        add hl,hl
        push hl                     ; (2)
        add hl,hl
        add hl,hl
        push hl                     ; (8)
        add hl,hl
        add hl,hl
        add hl,hl                   ; 64
        pop bc
        add hl,bc                   ; 72
        pop bc
        add hl,bc                   ; 74 (n32 / 4)
        ld a,h                      ; 2.31 n
        ld b,0
        add a,e                     ; + the two delays
        ld c,a
        jr nc,scl_m0
        inc b
scl_m0:  ld hl,(cal_m)
        ld de,SC_GAP + 6
        add hl,de
        or a
        sbc hl,bc                   ; split_dly2 = M + SC_GAP + 6 - 2.31 n - the two delays
        jr c,scl_d2z
        ld a,h
        or a
        ld a,l
        jr z,scl_d2
        ld a,255
        jr scl_d2
scl_d2z: xor a
scl_d2:  ld (split_dly2),a
        jr sc_end
sc_dflt:
        xor a
        ld (split_dly),a            ; (what suits every machine at 3.58 MHz)
        ld a,2
        ld (split_dly1),a
        ld a,11
        ld (split_dly2),a
sc_end: ld c,VDP_CTRL
        in a,(c)                    ; (S#1: the last match acknowledged)
        xor a
        ld (split_armed),a          ; (no split before the VBLANK arms it)
        out (c),a
        ld a,0x8F
        out (c),a                   ; R#15 = 0
        pop hl
        ld (IM2_JUMP),hl            ; (its jump back)
        ei
        ret

; After sc_cnt (split.asm): HL = its turns, 2 more a 256-turn wrap (26 T-states), and the 256 of
; a wrap that ended just as the interrupt came, before sc_cnt counted it (DE = scn_inc, the PC
; the interrupt left: 9 T-states of each wrap's 3610) -> C (vm_cal's vc_run returns through it).
; Uses A.
sc_turns:
        xor a
        sub b
        ld l,a                      ; HL = 256 H + (-B & 255)
        ld a,h
        add a,a
        add a,l
        ld l,a
        jr nc,sct_w
        inc h
sct_w:  ld a,e
        cp scn_inc & 0xFF
        jr nz,sct_c
        ld a,d
        cp scn_inc >> 8
        jr nz,sct_c
        inc h                       ; (that wrap's 256 turns: B is 0)
sct_c:  scf
        ret

; HL less than the word at DE: stored there. Uses A, DE, HL.
sc_min: ex de,hl
        ld a,e
        sub (hl)
        inc hl
        ld a,d
        sbc a,(hl)
        ret nc
        ld (hl),d
        dec hl
        ld (hl),e
        ret

; A play-field copy for the page shown waiting (field.asm fb_cq 1 or 3), its picture published
; (its stamp not fb_tick) with its sprites uploaded (pk_state not 1: both go on screen at the
; same VBLANK), the VDP idle and the main program not giving it a command (cmd_lock): it starts
; now (fb_cq 2 or 4). No copy waiting: a command of theirs for page 3 (ifg_rdy). C = VDP_CTRL
; (kept), AF, B, HL.
isr_fbgo:
        ld a,(fb_cq)
        rra
        jr nc,ifg_rdy
        ld a,(pk_state)
        dec a
        ret z
        ld a,(cmd_lock)
        or a
        ret nz
        ld a,(fb_tick)
        ld hl,fb_cur + 11
        cp (hl)
        ret z
        call ifg_idle
        ret nz                      ; (a command runs)
        ld hl,fb_cmd
        call ifg_send
        ld hl,fb_cq
        inc (hl)                    ; (2, 4: started)
        ld a,(fb_c2)                ; the pair's second part (fb_cmd2) right after it, so that
        dec a                       ; both show from the same frame
        ret nz
        ld b,110                    ; (about 90 lines at 3.58 MHz at most: else fb_wait starts it)
ifg_wt: call ifg_idle
        jr z,ifg_2
        bit 6,a
        jr nz,ifg_vr                ; (S#2 VR: the blank began)
        djnz ifg_wt
        ret
ifg_vr: ld a,b                      ; (only the split's wait gets there: a pair never starts at
        ld (fb_w2),a                ;  the VBLANK, fb_vok) the VBLANK interrupt, which comes at
        ld a,3                      ; once, starts the second part after its list (ifg_fin):
        ld (fb_c2),a                ; waited for here, the list went late by as much (2026-10-24)
        ret
ifg_2:  ld hl,fb_cmd2
        call ifg_send
        ld a,2
        ld (fb_c2),a
        ret

; The pair's second part the split's wait left to the VBLANK (fb_c2 3), the list being in: the
; first part's end, within what is left of that wait (fb_w2), then the second part, at the time
; the split would have started it; else fb_wait does (fb_c2 1). C = VDP_CTRL, AF, B, HL.
ifg_fin:
        ld a,(fb_w2)
        ld b,a
ifn_wt: call ifg_idle
        jr z,ifg_2
        djnz ifn_wt
        ld a,1
        ld (fb_c2),a
        ret

; A command of the play-field BOBs for page 3 ready (field.asm fb_rdy 1: the scratch, the caches,
; off the screen, so any time), the VDP idle and the main program not writing a command
; (cmd_lock): it starts now (fb_rdy 2). C = VDP_CTRL (kept), AF, HL.
ifg_rdy:
        ld a,(fb_rdy)
        dec a
        ret nz
        ld a,(cmd_lock)
        or a
        ret nz
        call ifg_idle
        ret nz
        ld hl,fb_cmd
        call ifg_send
        ld a,2
        ld (fb_rdy),a
        ret

; -> Z when the VDP's command engine is idle (S#2 CE); A bit 6 = S#2 VR (the vertical blank).
; Keeps BC, HL.
ifg_idle:
        ld a,2
        out (c),a
        ld a,0x8F
        out (c),a
        in a,(c)                    ; S#2
        push af
        xor a
        out (c),a
        ld a,0x8F
        out (c),a                   ; R#15 = 0
        pop af
        and 0x41
        bit 0,a
        ret

; HL = 15 bytes -> R#32-R#46 (the command starts). Keeps BC.
ifg_send:
        push bc
        ld a,32
        out (c),a
        ld a,0x80 + 17
        out (c),a                   ; R#17 = 32
        ld bc,15*256 + VDP_IND
        otir
        pop bc
        ret

; VBLANK: registers of the frame being shown next, the play-field palette (pf_pal) and, when
; the list is a new one, the SAT built for it (it must be in VRAM before the first display
; line: written by the main program it often came in the middle of the picture); in the front
; end (front_mode) only the frame count and the sound.
isr_vblank:
        ld a,(front_mode)
        or a
        jp nz,iv_tick
        ld a,(fb_vok)               ; (a play-field copy that keeps ahead of the beam from here,
        or a                        ;  else a command of theirs for page 3: isr_fbgo, ifg_rdy)
        jr z,iv_fbr
        call isr_fbgo
        jr iv_pk
iv_fbr: call ifg_rdy
iv_pk:  ld a,(pk_state)
        cp 1
        jr nz,iv_rdy
        ld a,(split_armed)          ; (no split since the last VBLANK: the display or the line
        or a                        ; interrupt is off) the published frame's uploads now
        call nz,spr_upload
        ld a,(pk_state)
iv_rdy: cp 2
        jr nz,iv_list
        call fb_pend                ; (its play-field BOBs not all composed yet: it waits for them,
        jr z,iv_take                ; FB_HOLD VBLANKs at most, so that they change with the sprites)
        ld hl,fb_hold
        inc (hl)
        ld a,(hl)
        cp FB_HOLD
        jr c,iv_list
iv_take:
        if EXTJOY
        ld hl,fb_visrec             ; (test builds: what the pictures are checked against)
        call field_call
        ld c,VDP_CTRL
        endif
        xor a
        ld (fb_hold),a
        ld (pk_state),a
        ld hl,(pk_list)
        ld (vbl_ptr),hl             ; the published frame from this one on
iv_list:
        ld c,VDP_CTRL               ; (fb_pend changes it)
        ld hl,(vbl_ptr)
        ld a,(app_seq)
        cp (hl)
        ld a,(hl)
        ld (app_seq),a
        push af                     ; (NZ: a new list)
        inc hl
        ld b,(hl)
        inc hl
        ld a,(hl)                   ; (every list starts with R#23, the play field's scroll)
        add a,VIEW_LINES - 2
        ld (split_r19),a            ; the split's R#19: a match at the end of line V-2
        otir
        ld a,1
        out (c),a
        ld a,0x8F
        out (c),a
        in a,(c)                    ; S#1: FH the list's R#23 raised against the split's R#19
        xor a                       ; before its own R#19 went in is acknowledged (no match is
        out (c),a                   ; due in the blank): else the split ran in the blank and the
        ld a,0x8F                   ; next picture showed page 3 in the HUD palette (2026-10-24:
        out (c),a                   ; R#23 240 written at line 214, the vehicle's ride); R#15 = 0
        ld a,1
        out (c),a
        ld a,0x90
        out (c),a                   ; R#16 = colour 1
        ld hl,pf_pal+2
        ld bc,30*256 + VDP_PAL
        otir
        ld a,1
        ld (split_armed),a
        pop af
        call nz,iv_sat              ; (sprites.asm: a new list, its sprite set from now on)
        ld a,(fb_c2)
        cp 3
        ld c,VDP_CTRL
        call z,ifg_fin              ; (a pair's second part the split left: after the list)
iv_late:
        call spr_late               ; more of the sprites' background uploads
iv_tick:
        ld hl,tick
        inc (hl)
        jp snd_frame                ; the music and the sound effects (AF, BC, HL saved; it keeps
                                    ; DE, IX, IY and the alternate registers)

; Builds split_list for the engine in use: A = 2 for the V9958 engine, else the V9938 one.
split_init:
        ld (hud_msk),a              ; 2 (non-zero) = V9958 engine: mask off in the HUD
        ld hl,split_list+1
        ld (hl),R2_PAGE3
        inc hl
        ld (hl),0x82
        inc hl
        or a
        jr nz,si_r23
        ld (hl),a                   ; V9938: R#18 = 0 (the V9958 engine keeps R#18 at 0)
        inc hl
        ld (hl),0x92
        inc hl
si_r23: ld (hl),HUD_R23
        inc hl
        ld (hl),0x97                ; R#23: HUD_VRAM_LINE shown at display line V+5
        inc hl
        ld b,6
        ld a,(hud_msk)
        or a
        jr z,si_len
        ld (hl),R26_PAGE3
        inc hl
        ld (hl),0x9A                ; R#26: page 3, no horizontal scroll
        inc hl
        ld (hl),0
        inc hl
        ld (hl),0x9B                ; R#27 = 0
        ld b,8
si_len: ld a,b
        ld (split_list),a
        ld hl,cal_list              ; (split_cal's list: as many pairs, R#16 = 1 each)
        srl b
si_cal: ld (hl),1
        inc hl
        ld (hl),0x90
        inc hl
        djnz si_cal
        ld hl,SR_PAL
        ld (sp_palp),hl             ; (hud_palette's RAM copy: cold.asm isr_init)
        ld a,R1_BLANK
        ld (sp_v1),a                ; (split.asm sp_seq's blank)
        ret

; Publishes the register list at HL (filled by the engine) for the next VBLANK.
; The list starts with [seq, len]; seq is set here.
publish:
        ld a,(pub_seq)
        inc a
        ld (pub_seq),a
        ld (hl),a
        ld (pk_list),hl
        push hl
        ld hl,pq_buf
        ld (pq_rd),hl               ; (its queue from the start)
        pop hl
        ld a,(pq_buf)               ; no uploads for it: ready at once
        or a
        ld a,1
        jr nz,pb_st
        inc a
pb_st:  ld (pk_state),a             ; (last: the interrupts see a complete frame)
        ret

; Ends a register list being filled (HL past its last pair, the list's address on the stack):
; appends the camera, the game frame ($B00: the tick shown is the one before) and the sprite
; state it shows (not sent to the VDP; for verification) and publishes it.
list_tail:
        ld de,(cam_x)
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld de,(cam_y)
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld de,(g_frame)
        ld (hl),e
        inc hl
        ld (hl),d
        pop hl                      ; the list: what its SAT shows goes to its pub_spr copy
        if EXTJOY                   ; (test builds)
        push hl
        ld de,pub_spr
        ld a,l
        cp vbl_list_a & 0xFF
        jr z,lt_a
        ld de,pub_spr + MAX_OBJ*8
lt_a:   ld hl,pub_cur
        ld bc,MAX_OBJ*8
        ldir
        pop hl
        endif
        jp publish

; Returns HL = the list not in use by the ISR.
next_list:
        ld hl,(vbl_ptr)
        ld a,l
        cp vbl_list_a & 0xFF
        ld hl,vbl_list_a
        ret nz
        ld hl,vbl_list_b
        ret

; Waits until a VBLANK has put the last published list on screen (so the next frame never
; starts on top of one that is still pending), calling idle_work meanwhile; counts frames and
; late frames (more than one VBLANK since the previous call).
wait_frame:
        if LOCKSTEP
        ld a,(last_tick)            ; (test builds: every frame starts LOCKSTEP VBLANKs after the
        add a,LOCKSTEP              ; one before; lk_over counts those that came later)
        ld b,a
wfk_lp: ld a,(tick)
        sub b
        jp p,wfk_go
        push bc
        call idle_work
        pop bc
        jr wfk_lp
wfk_go: jr z,wfk_ok
        ld hl,lk_over
        inc (hl)
wfk_ok: ld a,b
        ld (last_tick),a
        ld a,2
        ld (wf_n),a
        jr wf_ok
        endif
        ld a,(last_tick)
        ld b,a
wf_lp:  ld a,(app_seq)
        ld c,a
        ld a,(pub_seq)
        cp c
        jr nz,wf_idle               ; the last list is not on screen yet
        ld a,(tick)
        cp b
        jr nz,wf_got
wf_idle:
        push bc
        call idle_work
        pop bc
        jr wf_lp
wf_got: ld (last_tick),a
        sub b
        ld (wf_n),a                 ; (the cadence counts them)
        dec a
        jr z,wf_ok
        ld hl,(late)
        inc hl
        ld (late),hl
wf_ok:  ld a,1
        ld (iw_more),a              ; (every frame's first feed_vdp looks at the scroll engine)
        ld hl,(frame)
        inc hl
        ld (frame),hl
        ret
