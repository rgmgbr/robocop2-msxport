; Cold code of the fixed area: routines that run once per level (or at power-on), kept in the
; front end's bank (BANK_FRONT at 8000h through front_call) to leave room in 4000h-7FFFh. They
; call only fixed code and never map the 8000h window themselves.

; The HUD at a level's start (rc2.asm lv_go): a new game's (hud_init) while AG $8050 is 0 (ng_init
; cleared AG: level 1), else the next level's (hud_lvl).
hud_start:
        ld a,(AG + 0x8050)          ; (the word's low byte)
        or a
        jr z,hud_init
; The HUD at the next level's start (hud_start) and after a continue (rc2.asm lv_cont): the level
; start's panel without a new game's reset (docs/LEVEL2.md 3.7). The empty panel and its state again
; (hud_init: what the stages, the text screens and PIC9 left there goes; weapon 0's icon and the
; full can are the panel's), then, with the display off, what the game's values ask drawn at once by
; the game's own HUD work (hud_keep: hud_frame, its jobs and digit cells): the timer, the ammo and
; the score from AG, and the heads of the lives ($8034: slot k keeps head 0 while lives > k, else it
; shows the lost life's last graphic, 5, as frame.asm left it); then the message queue and the
; ticker cleared (no message from the levels before; the idle ticker moved its indices).
hud_lvl:
        call hud_init               ; (no request left: the level's set-up asked set_weapon's icon,
        ld a,(g_tick)               ;  which is the panel's)
        push af
        xor a
        ld (g_tick),a               ; (hud_energy: no step on a frame without a tick)
        ld hl,hud_last
        ld bc,8
        ld a,0xFF
        call fill                   ; (hud_digits looks at every cell again: the panel's digits are
                                    ;  not the values it drew last, which a continue may repeat)
        ld hl,(AG + 0x8034)
        ld de,2
        call hl_head                ; slot 1
        ld de,1
        call hl_head                ; slot 0
        ld b,HL_CALLS
hl_lp:  push bc
        call hud_keep               ; (fixed code: the HUD's banks, then this bank again)
        pop bc
        djnz hl_lp
        pop af
        ld (g_tick),a
        ld hl,msg_queue
        ld b,8 + 4
        xor a
hl_q:   ld (hl),a
        inc hl
        djnz hl_q                   ; queue, indices, column, count (as hud_init)
        jp logic_map                ; (the game's banks for the fixed caller: rc2.asm lv_cont, lv_go)
HL_CALLS:   equ 2 * HUD_HEAD_LINES / HUD_JOB_LINES + 14 + 2  ; the two heads' jobs, the 14 digit
                                    ; cells (one a call), two to spare
; HL = lives, DE = the slot + 1: the lost life's head asked in that slot when HL < DE (signed).
hl_head:
        push hl
        or a
        sbc hl,de
        pop hl
        ret p
        ld a,e
        dec a
        add a,JOB_HEAD0
        ld c,5
        push hl
        call hud_request
        pop hl
        ret

; State of the static HUD (hud.asm) at a new game: timer 09:58, ammo 000, score 0000000, full can,
; two RoboCop heads, the icon of weapon 0, empty message line; then the panel as the game starts
; (vdp.asm hud_upload, the last thing done here: it maps the 8000h window and puts this bank back).
hud_init:
        ld hl,hud_timer
        ld (hl),0x09
        inc hl
        ld (hl),0x58
        ld hl,hud_ammo
        ld b,6
        xor a
hi_z:   ld (hl),a
        inc hl
        djnz hi_z                   ; ammo and score
        ld hl,hi_shown
        ld de,hud_shown
        ld bc,14
        ldir
        ld hl,0x100
        ld (en_target),hl
        ld (en_shown),hl
        ld hl,msg_queue
        ld b,8 + 4
        xor a
hi_q:   ld (hl),a
        inc hl
        djnz hi_q                   ; queue, indices, column, count
        ld hl,hud_chars
        ld b,TEXT_CELLS
        ld a,SPACE
hi_c:   ld (hl),a
        inc hl
        djnz hi_c
        xor a
        ld (heads_g),a
        ld (heads_g+1),a
        ld (job_lines),a
        ld (jobq_n),a
        ld (weapon),a
        ld a,3
        ld (icon_shown),a           ; (weapon 0's icon, see set_weapon $FD30)
        ld a,2
        ld (lives),a
        jp hud_upload               ; (no last game's digits)
hi_shown:
        db 0, 9, 5, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

; At a level's start (sprites.asm sprites_init): nothing shown, every slot and colour row
; unknown.
spr_init:
        ld hl,obj_tab
        ld bc,MAX_OBJ*OBJ_SIZE
        xor a
        call fill
        ld hl,disp
        ld bc,2*MAX_OBJ*LAY_SIZE
        xor a
        call fill                   ; nothing shown, nothing prepared
        ld hl,col_held
        ld bc,SAT_MAX*2
        ld a,0xFF
        call fill                   ; colour rows unknown (sets A and B)
        ld hl,col_held_b
        ld bc,SAT_MAX*2
        ld a,0xFF
        call fill
        ld hl,ent_own
        ld bc,SAT_MAX
        ld a,0xFF
        call fill                   ; every SAT entry free
        ld a,SPARK_OBJ
        ld (ent_own),a
        ld (ent_own+1),a            ; (the spark's two)
        ld hl,pat_held
        ld bc,SPR_SLOTS*2
        ld a,0xFF
        call fill                   ; patterns unknown
        ld hl,slot_ref
        ld bc,SPR_SLOTS
        xor a
        call fill                   ; every slot free
        ld hl,SLOT_PG*256 + SO_OK
        ld bc,2*SPR_SLOTS
        xor a
        call fill                   ; nothing loaded, nothing queued (slot_ok, slot_q)
        ld a,SO_FL - 1
        ld (fl_n),a                 ; nothing to release
        ld (fl_mark),a
        ld hl,pat_slot
        ld bc,PAT_HINTS
        ld a,0xFF
        call fill                   ; and put nowhere
        if EXTJOY
        ld hl,pub_cur
        ld bc,MAX_OBJ*8
        xor a
        call fill
        endif
        ld hl,obj_key
        ld bc,MAX_OBJ*4
        xor a
        call fill                   ; no BOB identity (bob.asm)
        ld hl,pl_st                 ; (the plan's look skips the objects not wanted: their work
        ld bc,MAX_OBJ               ;  and parts' states must start at 0)
        xor a
        call fill
        ld hl,pl_gs
        ld bc,MAX_OBJ
        xor a
        call fill
        ld hl,0
        ld (pl_fl),hl
        ld (pl_flp),hl
        ld a,1
        ld (pg_new),a               ; (the objects with parts: built at the first plan)
        ld hl,bf_last
        ld bc,MAX_OBJ*6
        ld a,0xFF
        call fill                   ; no frame remembered (bob.asm bf_show)
        ld a,SPR_MAX                ; (RoboCop counts whole in the budget)
        ld (rc_hold),a              ; (his largest until his own count is known)
        ld a,(tick)
        ld (rc_hold_t),a
        ld a,1
        ld (bu_dirty),a             ; (the budget runs on the first tick)
        ld (bo_dirty),a
        ld (sat_dirty),a
        xor a
        ld (spr_vblank),a
        ld (sat_due),a
        ld (pk_mux),a               ; (never set since the alternation went; the Tcl checks read it)
        ld (alloc_p),a
        ld (rcp_ok),a               ; (rc_prefetch: nothing brought in ahead)
        ld a,R5_SET_A
        ld (spr_set),a
        ld (spr_dsp),a
        ret

; ----- the cut at a vat's surface (level 2; FRONT for the room it takes) -----

; (sprites.asm sprites_frame, while vat_cut_line < CAh: the 8000h window's bank it found on the
; stack under the return, front_call) The SAT just built (sat_nb) and the colour rows of the set
; being prepared (rows_sync: rs_held, rs_colhi): RoboCop's sprites and the hit spark's (SAT entries
; 0 to RC_RUN + his entries - 1; on the Amiga the spark is drawn into his sprites) end where the
; Amiga's copper turns the sprites off ($10356 = vat_cut_line: he sinks into the liquid), through
; the view's y mapping: the line's map y is the line - 1Eh (the play field's first line) + the game
; camera's y, its screen line that - cam_y. An entry wholly below it is parked; one it crosses gets
; colour 0 (transparent) in its rows from the line down, and its row is marked unknown in that set
; (col_held FFFFh: the set's next list writes it whole again). The enemies are not cut (BOBs on the
; Amiga; docs/LEVEL2.md 3.6, default 30). Then the 8000h window's bank back.
spr_cut:
        ld hl,(gcam_y)
        ld a,(vat_cut_line)
        sub 0x1E - 16
        jr c,spc_x                  ; (0 before a life's first tick, G_VARS cleared: no cut; the
        ld e,a                      ;  vats' lines are 7Fh or more)
        ld d,0
        add hl,de
        ld de,(cam_y)
        sbc hl,de                   ; (no carry before) the line's screen line + 16
        ld a,h
        or a
        jr z,spc_c
        jp p,spc_x                  ; (below the play area: nothing to cut)
        ld l,0                      ; (above it: every entry parked)
spc_c:  ld c,l                      ; C = the line + 16
        ld a,e
        cpl
        add a,18
        ld d,a                      ; D = 17 - cam_y: an entry's SAT y + D = its first line + 16
        exx
        ld hl,(rs_held)             ; HL' = the entry's col_held,
        ld a,(rs_colhi)
        ld d,a
        ld e,0                      ; DE' = its colour row (port 99h form)
        exx
        ld a,(disp + V_ON)
        or a
        jr z,spc_n                  ; (RoboCop shows nothing: the spark's entries only)
        ld a,(disp + V_N)
spc_n:  add a,RC_RUN
        ld b,a
        ld hl,(sat_nb)
spc_lp: ld a,(hl)
        add a,d
        sub c
        jr nc,spc_pk                ; (it starts on the line or below: parked)
        add a,16
        jr nc,spc_nx                ; (it ends above the line: whole)
        jr z,spc_nx
        exx
        ld b,a                      ; B' = its lines from the line down
        ld (hl),0xFF
        inc l
        ld (hl),0xFF                ; its row unknown in this set (each col_held within a
        dec l                       ;  256-byte page)
        push de
        ld a,e
        add a,16
        sub b
        ld e,a                      ; (its first line below the line)
        call spr_wr
        pop de
        xor a
spc_z:  out (VDP_DATA),a            ; (colour 0)
        djnz spc_z
        exx
        jr spc_nx
spc_pk: ld a,(sb_parky)
        ld (hl),a
spc_nx: inc l
        inc l
        inc l
        inc l
        exx
        inc l
        inc l
        ld a,e
        add a,16
        ld e,a
        jr nc,spc_nd
        inc d
spc_nd: exx
        djnz spc_lp
spc_x:  pop hl
        pop af
        push hl
        jp bank_8000

; ----- a level's start (docs/LEVEL2.md 3.1) -----

; A new game's part (rc2.asm ng_go, through front_call; $FFC4, $FFD8, load_level0's $8314): the
; game's globals cleared (level 0, score 0), two lives, the rating's table SHARP; then level 1's
; start (lv_select).
ng_init:
        if R800PING
        call cpu_ping               ; (test build: CPU round trips)
        endif
        ld hl,AG + 0x8000           ; the game's globals ($8000-$80FF): level 0, score 0
        ld bc,256
        xor a
        call fill
        ld a,2
        ld (AG + 0x8034),a          ; two lives ($FFD8; hud_init draws their heads)
        if CHEAT
        ld a,0xFF                   ; (test build, tools/mkrom.py CHEAT=1: the cheat mode on, as the
        ld (AG + (0x804F ^ 1)),a    ;  title's cheat handler $11F60's st.b $804F; frame.asm fe_keys)
        endif
        ld hl,diff_tab
        ld (ac_diff),hl             ; the rating's table: SHARP ($8314: $8060 = $C716; AC_VARS,
                                    ;  which deaths and the next level keep)
        ld c,0                      ; (level 1)
; C = the level (0: level 1): its start up to its objects (rc2.asm lv_go, through front_call; the
; display and the VDP's interrupts off; level_init $871A): its descriptor, palette and view_offy
; (lv_copy); its tiles 0-255 into page 2 and its play-field atlas into page 3 when VRAM holds
; another level's (lv_vram: default 14's alternative, so that level 1's starts stay as they were;
; the title, the stages and vdp_setup put back the tiles of the level lv_cur holds, and nothing
; but vdp_setup and this writes the atlas); the tile cache and the map patches (a turbo R's R800
; from here), the attributes, RoboCop and the camera, its logic bank, its lists into RAM.
lv_select:
        call lvs_vram
        call tiles_init
        call atr_load
        call pl_init
        ld a,(lv_logic)
        ld (lvl_bank),a
        ld a,0xFF
        ld (lv_fresh),a             ; (the level's lists into RAM)
        ret
; (C = the level: lv_copy, and its tiles and atlas into VRAM unless lv_vram says they are there)
lvs_vram:
        ld a,(lv_vram)
        cp c
        push af                     ; (Z: VRAM holds the level's tiles and atlas already)
        ld a,c
        ld (lv_vram),a
        call lv_copy
        pop af
        ret z
        ld e,4
        call tiles_upload
        ld hl,field_upload
        jp field_call               ; (field.asm)

; rc2.asm lv_cont's part in this bank (the continue, docs/LEVEL2.md 3.7, default 50): $FFD8's two
; lives (hud_lvl draws both heads), the level's tiles and atlas into VRAM again (PIC9's G7 overwrote
; page 2: lv_vram FFh, then lv_select's copy and uploads), the tile cache as the uploads leave it
; (tc_reset, which sets the game's CPU: a turbo R's R800 again). The map patches, the attribute RAM
; and the level's lists stay as the game left them (level_init's entry 1 for level 2: the map keeps
; its changes); level_restart restarts the level on them as after a death.
lv_cfront:
        call dsp_off
        ld hl,2
        ld (AG + 0x8034),hl
        ld a,0xFF
        ld (lv_vram),a
        ld a,(AG + 0x8050)
        ld c,a
        call lvs_vram
        jp tc_reset

; C = the level: its descriptor (lv_desc, LV_SIZE bytes a level: gen/levels.inc) into lv_cur, its
; palette into lv_pal and its view_offy into lv_voffy (from FRONT, or from its tables' bank at
; A000h). Also at power-on, before vdp_setup (cold_init).
lv_copy:
        ld hl,lv_desc - LV_SIZE
        ld de,LV_SIZE
        inc c
lvc_m:  add hl,de
        dec c
        jr nz,lvc_m
        ld de,lv_cur
        ld bc,LV_SIZE
        ldir
        ld a,(act_a000)
        push af
        ld a,(lv_tab)
        call bank_a000
        ld hl,(lv_palp)
        ld de,lv_pal
        ld bc,32
        ldir
        ld hl,(lv_voffp)
        ld de,lv_voffy
        ld bc,LV_VOFFN
        ldir
        pop af
        jp bank_a000

; The tile cache and the map patches at the start of a level (tiles.asm; lv_select):
; the level's slots (lv_tcn: 256, or 224 in level 2) hold its first tiles (uploaded by
; vdp_setup or lv_select: page 2), no patch, nothing to redraw.
tiles_init:
        call tc_reset
        ld hl,MP_ROW
        ld bc,256
        ld a,0xFF
        call fill                   ; no patch in any row
        ld h,(MP_A + MPF_NEXT)/256
        call mp_init
        ld h,(MP_B + MPF_NEXT)/256
        call mp_init
        ld hl,rd_bits
        ld bc,40
        xor a
        call fill                   ; (nothing waits to be redrawn)
        xor a
        ld (atr_lost),a
        ld (mp_lost),a
        ld (rd_head),a
        ld (rd_tail),a
        ld (rd_phase),a
        ld (rd_lost),a
        ld (tc_loads),a
        ret

; The tile cache alone (tiles_init's first part; lv_cfront: the continue keeps the map patches): the
; level's slots hold its first tiles, as tiles_upload left page 2.
tc_reset:
        call cpu_game               ; (a turbo R: the game on its R800 from here, docs/TURBO_R.md)
        ld hl,(lv_tcn)
        ex de,hl
        ld hl,0
        or a
        sbc hl,de                   ; HL = the level's slots (TC_SLOTS at most)
        push hl
        srl h
        rr l
        ld b,l
        push bc                     ; (B = the slots / 2)
        ld hl,TC_SLOT
        ld de,1
ti_s:   ld (hl),e                   ; tile t: slot t + 1
        inc hl
        ld (hl),d
        inc hl
        inc de
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        inc de
        djnz ti_s
        ex de,hl
        ld hl,TC_SLOT + 512 * 2
        or a
        sbc hl,de
        ld b,h
        ld c,l
        ex de,hl
        xor a
        call fill                   ; the other tiles (up to 511): not in VRAM
        ld hl,TC_TILE
        ld bc,TC_SLOTS * 2
        ld a,0xFF
        call fill                   ; (the slots the level has not: no tile)
        pop bc
        ld hl,TC_TILE
        ld de,0
ti_t:   ld (hl),e                   ; slot s: tile s
        inc hl
        ld (hl),d
        inc hl
        inc de
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        inc de
        djnz ti_t
        pop bc                      ; (the slots)
        ld hl,TC_REF
        xor a
        call fill
        ld hl,0
        ld (tc_hand),hl
        ret

; H = a map patch pool's MPF_NEXT page: its patches all free, chained 0, 1 .. MP_N - 1 (entry n
; n + 1: entry MP_N - 1 FFh, none after it; entry FFh 0, the first free), none in use (the
; MPF_COL page's entry FFh).
mp_init:
        ld l,0
mpi_f:  ld a,l
        inc a
        ld (hl),a
        inc l
        jr nz,mpi_f
        dec h
        dec l
        ld (hl),0
        ret

; (player.asm)
; Start of level 1 (level_init $871A, clear_game_vars $FE96): the game variables cleared (with
; the keyboard and joystick bytes, the input lock and the joystick mask), RoboCop and the camera
; at the header's position, no state asked for; the cadence for the
; machine's refresh rate (RG9SAV bit 1: 50 Hz) and the view on the camera.
pl_init:
        call snd_stop               ; (level_init $8720)
        ld hl,AM_START
        ld bc,AM_END - AM_START
        xor a
        call fill                   ; (clear_game_vars)
        ld hl,G_VARS
        ld bc,G_VARS_END - G_VARS
        xor a
        call fill
        xor a
        ld (g_keys),a               ; (clear_game_vars: $802D, $802E, $804D)
        ld (g_joy),a
        ld (g_lock),a
        ld (jump_pend),a
        ld (j_nojump),a
        ld (j_jumpb),a
        ld (split_dly),a            ; (split_cal's defaults 0 / 2 / 11 until display_on's
        ld a,2                      ;  split_cal, which runs before any split: the front end shows
        ld (split_dly1),a           ;  none before a level)
        ld a,11
        ld (split_dly2),a
        if SPLITDIAG
        xor a
        ld (dg_step),a
        ld (dg_cnt),a
        ld (dg_max),a
        dec a
        ld (dg_min),a
        endif
        ld a,0x7F
        ld (ac_jmask),a             ; ($B02B)
        xor a
        call pal_fade               ; black until the fade in
        if INPUT_SCRIPT
        ld hl,input_script
        ld (sc_run),hl              ; (the script's first run, from game frame 0)
        endif
        ld hl,(lv_x)
        ld (p_x),hl
        ld (gcam_x),hl
        ld hl,(lv_y)
        ld (p_y),hl
        ld (gcam_y),hl
        ld hl,(lv_ymax)
        ld (gcam_ymax),hl
        ld a,0xFF
        ld (p_pend+1),a             ; (st $1696: its high byte)
        ld (p_fadein),a             ; the palette fades in ($16CE)
        ld a,(RG9SAV)
        and 2
        ld a,5                      ; 60 Hz: every other frame
        jr z,pi_hz
        inc a                       ; 50 Hz: 3 ticks in 5 frames
pi_hz:  ld (g_step),a
        neg
        add a,CAD_TICK
        ld (g_acc),a                ; the first frame ticks
        ld a,1
        ld (wf_n),a
        jp pl_view

; (isr.asm) At power-on (vdp.asm vdp_setup): the IM 2 table and jump, the split's RAM code and
; colours, the interrupts' shared state.
isr_init:
        ld hl,sr_rom
        ld de,SR_RAM
        ld bc,SR_LEN
        ldir                        ; the split's timed path and split_cal's measures (split.asm)
        ld hl,scn_inc
        ld (scn_at),hl              ; (sc_turns: this block's)
        xor a
        ld (sl_off),a               ; (the Z80: the play field's 162 lines)
        ld hl,hud_palette
        ld de,SR_PAL
        ld bc,30
        ldir                        ; the HUD's colours 1-15 the split writes (split.asm)
        ld hl,IM2_TABLE
        ld de,IM2_TABLE+1
        ld bc,256
        ld (hl),IM2_VEC
        ldir
        ld a,0xC3                   ; JP isr
        ld (IM2_JUMP),a
        ld hl,isr
        ld (IM2_JUMP+1),hl
        ld a,IM2_I
        ld i,a
        im 2
        xor a
        ld (split_armed),a
        ld (fb_cq),a                ; (no play-field copy or command waits: field.asm)
        ld (fb_rdy),a
        ld (cmd_lock),a
        ld (fb_vok),a
        ld (fb_qlk),a
        ld (tick),a
        ld (last_tick),a
        ld (pk_state),a             ; (the sprite engine's state the interrupts share)
        ld (pk_mux),a
        ld (pq_buf),a
        ld (bq_head),a
        ld (bq_tail),a
        ld (vram_busy),a
        ld (sat_due),a
        ld (spr_vblank),a
        ld (pub_seq),a              ; the list on screen until the first one is published: one
        ld (app_seq),a              ; that changes nothing (R#15 = 0). At power-on the RAM holds
        ld hl,vbl_list_a            ; anything, and a list read from it once wrote R#14 and an
        ld (vbl_ptr),hl             ; address in the middle of the tiles' upload after the title
        ld (pk_list),hl
        ld (hl),a                   ; (seq 0)
        inc hl
        ld (hl),2
        inc hl
        ld (hl),a
        inc hl
        ld (hl),0x8F
        ld hl,sat_pair0
        ld (sat_cur),hl
        ld (sat_nb),hl
        ld hl,pq_buf
        ld (pq_rd),hl
        ld a,R5_SET_A
        ld (spr_dsp),a
        ret

; (sound.asm) At power-on, with the BIOS in page 0 (cold_init).
; An OPLL: every slot's page 1 is searched for "OPLL" at 401Ch after "APRL" (MSX-MUSIC) or
; "PAC2" (FM-PAC, whose I/O ports are then switched on: bit 0 of 7FF6h in its slot).
; snd_fm = 1 when found. Uses the BIOS (RDSLT, WRSLT); interrupts end up disabled.
snd_detect:
        call cpu_detect             ; (a turbo R's R800 first: in IM 2, checked; the Z80 runs on)
        xor a
        ld (snd_fm),a
        ld c,0                      ; primary slot
sdt_p:  ld hl,EXPTBL
        ld e,c
        ld d,0
        add hl,de
        ld a,(hl)
        and 0x80
        or c
        ld b,a                      ; slot id (expanded: secondary 0 first)
sdt_s:  push bc
        ld a,b
        call sdt_try
        pop bc
        ret z                       ; found
        bit 7,b
        jr z,sdt_np                 ; not expanded: the next primary slot
        ld a,b
        add a,4
        ld b,a
        and 0x0C
        jr nz,sdt_s                 ; secondary 1-3
sdt_np: inc c
        ld a,c
        cp 4
        jr c,sdt_p
        or 1                        ; (NZ: none)
        ret

; A = slot id: Z when its page 1 holds an OPLL BIOS (then snd_fm = 1, the FM-PAC's ports on).
sdt_try:
        ld (snd_slot),a
        ld hl,0x401C
        ld de,sdt_opll
        ld b,4
        call sdt_cmp
        ret nz
        ld l,0x18                   ; (H = 40h: 4018h; no ld hl,4018h in the image, see sdt_opll)
        ld de,sdt_aprl
        ld b,4
        call sdt_cmp
        jr z,sdt_yes
        ld l,0x18
        ld de,sdt_pac2
        ld b,4
        call sdt_cmp
        ret nz
        ld a,(snd_slot)             ; an FM-PAC: its I/O ports on
        ld hl,0x7FF6
        ld e,1
        call WRSLT
sdt_yes:
        ld a,1
        ld (snd_fm),a
        xor a                       ; (Z)
        ret

; HL = address in the slot snd_slot, DE = text, B = length: Z when they match.
sdt_cmp:
        push bc
        push de
        push hl
        ld a,(snd_slot)
        call RDSLT
        cpl                         ; (the texts are stored complemented)
        pop hl
        pop de
        pop bc
        ex de,hl
        cp (hl)
        ex de,hl
        ret nz
        inc hl
        inc de
        djnz sdt_cmp
        ret

; The texts complemented, so that "OPLL" is nowhere in the image: the MSX Pico+ firmware starts
; a Konami SCC ROM holding "OPLL" and an ld hl,4018h or ld de,4018h as an FM-PAC game, its
; mapper without the SCC (seen in its v2.12 code; tools/mkrom.py checks the image).
sdt_opll:   db 0xFF - 'O', 0xFF - 'P', 0xFF - 'L', 0xFF - 'L'
sdt_aprl:   db 0xFF - 'A', 0xFF - 'P', 0xFF - 'R', 0xFF - 'L'
sdt_pac2:   db 0xFF - 'P', 0xFF - 'A', 0xFF - 'C', 0xFF - '2'

; ----- the start, at power-on -----

; From rc2.asm init (jumped to through front_call, the interrupts off, the cartridge in pages 1 and
; 2): the machine checked, the sound chips, the VDP, page 0's RAM, the code area's variables, then
; the title and level 1 (rc2.asm ng_go). (The fixed area's room: docs/LEVEL2.md 3.2. Every routine
; it calls leaves BANK_FRONT at 8000h: act_8000's bank, or FRONT's own code.)
cold_init:
        ld a,(MSXVER)
        if DIAG
        ld (dg_msxv),a
        endif
        or a
        jr z,ci_nm2                 ; (an MSX1)
        ld a,(MODE)
        and 6
        cp 4
        jr nc,ci_ok                 ; (less than 128 KiB of VRAM: the tiles, the HUD and the
ci_nm2: jp no_msx2                  ;  sprite tables need pages 2-3: a message, and the machine
ci_ok:                              ;  stays on it)
        if DIAG
        di
        ld b,'1'
        call dg_probe
        endif
        call ci_hook                ; (frontx.asm: over 1 MiB the guard, the high scores' table) and
                                    ;  snd_detect: an OPLL (with the BIOS: before page 0 becomes RAM)
        di
        if DIAG
        ld b,'2'
        call dg_probe
        endif
        ld c,0
        call lv_copy                ; level 1's descriptor (vdp_setup's uploads read lv_cur), palette
        call vdp_setup              ; SCREEN 5, VDP ID, IM 2, palette, tiles, HUD, sprite tables
        xor a
        ld (lv_vram),a              ; (VRAM: level 1's tiles and atlas)
        if DIAG
        di
        ld b,'3'
        call dg_probe
        endif
        call ram_page0              ; page 0: RAM from now on (no more BIOS calls)
        jp c,no_ram
        if DIAG
        ld b,'4'
        call dg_probe
        endif
        call snd_init               ; the PSG (and the OPLL) silent
        if DIAG
        di
        ld b,'5'
        call dg_probe
        endif
        ld hl,mus_init
        call mus_call               ; an SCC: the title music's chips (music.asm)
        ld hl,vm_cal
        call mus_call               ; the speech's rate on this machine (music.asm)
        if DIAG
        ld hl,dg_main
        call mus_call               ; (test build: what this machine showed, then test tones; no game)
        endif
        ld hl,sq_init
        call snd_bank               ; the player idle, its queue empty (the interrupts still off)
        ld hl,AC_VARS               ; the variables of the Amiga's code area at the power-on
        ld bc,AC_VARS_END - AC_VARS ; (they live on across levels and games: the code is never
        xor a                       ; loaded again: ac_mkstep $C44A...)
        call fill
        ld a,2                      ; (the code's values: $8C98, $F826, $F07E; pl_init sets
        ld (ac_ridest),a            ; $B02B's)
        ld hl,0xFFFF
        ld (ac_flash),hl
        ld a,l
        ld (ac_ediv),a
        ld hl,0
        ld (tick_n),hl              ; (the test scripts' game frames)
        xor a
        ld (front_mode),a
        if PZ_TEST + LV_TEST + END_TEST
        ld a,1
        ld (pz_first),a             ; (test build: Brainstorm first, level 2 or the game's end,
        else                        ;  without the title: rc2.asm pz_test, lv_test, end_test)
        call title                  ; (rc2.asm: front.asm fr_title, or nothing in a script's build)
        endif
        jp ng_go

; (vdp.asm) At power-on (cold_init): SCREEN 5, 212 lines, VDP ID, IM 2, level 1's palette
; (lv_copy's), tiles (pages 2-3), HUD and sprite tables. Returns with the display off and no VDP
; interrupt enabled.
vdp_setup:
        ld a,5
        call CHGMOD
        di
        ld a,0x02                   ; display off, no VBLANK interrupt, 16x16 sprites
        out (VDP_CTRL),a
        ld a,0x81
        out (VDP_CTRL),a
        ld a,R0_IE1_OFF
        out (VDP_CTRL),a
        ld a,0x80
        out (VDP_CTRL),a
        call isr_init               ; no VDP interrupt source is enabled yet
        ld a,1
        ld b,15
        call wrreg
        in a,(VDP_CTRL)             ; S#1: ID in bits 5..1
        rrca
        and 0x1F
        ld (vdp_id),a
        xor a
        ld b,15
        call wrreg
        xor a
        ld b,7
        call wrreg                  ; border colour = 0
        ld a,R8_SPR_OFF
        ld b,8
        call wrreg
        ld a,(RG9SAV)
        or 0x80
        ld b,9
        call wrreg                  ; 212 lines (keeps the 50/60 Hz setting)
        xor a
        ld b,16
        call wrreg
        ld hl,lv_pal
        ld bc,32*256 + VDP_PAL
        otir
        ld e,8
        call tiles_upload
        ld hl,field_upload
        call field_call             ; the play-field BOBs' atlas over the last tile slots
        call hud_upload
        ; sprite tables: both SATs end at sprite 0 (Y = 216)
        ld e,1
        ld hl,(SPR_COL_A + 0x200) & 0xFFFF
        call vram_write
        ld a,216
        out (VDP_DATA),a
        ld e,1
        ld hl,(SPR_COL_B + 0x200) & 0xFFFF
        call vram_write
        ld a,216
        out (VDP_DATA),a
        call vram_done
        ld a,R5_SET_A
        ld (spr_set),a
        ld b,5
        call wrreg
        ld a,R11_SPR
        ld b,11
        call wrreg
        ld a,R6_PAT
        ld b,6
        call wrreg
        ; fixed parameters of the tile HMMM
        ld hl,16
        ld (cmdbuf+8),hl
        ld (cmdbuf+10),hl
        xor a
        ld (cmdbuf+12),a
        ld (cmdbuf+13),a
        ld a,0xD0
        ld (cmdbuf+14),a
        ret

; No RAM in page 0 (cold_init, the main RAM is not in page 3's slot): a red screen.
no_ram: xor a
        ld b,16
        call wrreg                  ; palette entry 0
        ld a,0x70
        out (VDP_PAL),a
        xor a
        out (VDP_PAL),a             ; red
        xor a
        ld b,7
        call wrreg                  ; border colour 0
        ld a,0x02
        ld b,1
        call wrreg                  ; display off, no interrupt
        di
        halt

; MSX turbo R (docs/TURBO_R.md 3.2), at the power-on (cold_init): the BIOS
; in page 0 with its work area intact, the interrupts off. A cartridge started before this one may
; have left the R800 running: the Z80 again first, whatever follows. Then a round trip to the
; R800, which goes into IM 2 for good (it booted in IM 1 and CHGCPU carries I but not the mode,
; while the IM 1 handler's BIOS work area is gone once the game runs) and measures itself against
; the turbo R's timer (cd_ram, from RAM: SR_RAM is free until vdp_setup's isr_init). cpu_tr = 1
; when the measures are an R800's: 512 djnz turns in under 120 counts (~63 on an R800 from RAM,
; 512 on a 3.58 MHz Z80, ~171 at 10.74), and port 98h held by the S1990 (16 reads at least 16
; counts longer than 16 of port A8h). The Z80 runs on in every case (cpu_cur 0).
cpu_detect:
        xor a
        ld (cpu_tr),a
        ld (cpu_cur),a
        if SPLITDIAG + DEMO_HUD
        ret                         ; (test builds: the Z80 block's units, or no room: the Z80 only)
        endif
        ld a,(MSXVER)
        cp 3
        ret c                       ; (not a turbo R)
        ld a,(CHGCPU)
        cp 0xC3
        ret nz                      ; (no CPU switch in this BIOS)
        call GETCPU
        or a
        ld a,0x80
        call nz,CHGCPU              ; (the R800 left on: the Z80 again, the LED off)
        di
        ld hl,cd_ram
        ld de,SR_RAM
        ld bc,cd_end - cd_ram
        ldir
        ld c,VDP_CTRL
        ld a,(RG1SAV)
        and 0xDF
        out (c),a
        ld a,0x81
        out (c),a                   ; R#1 without the VBLANK interrupt,
        ld a,(RG0SAV)
        and 0xEF
        out (c),a
        ld a,0x80
        out (c),a                   ; R#0 without the line interrupt,
        ld a,1
        out (c),a
        ld a,0x8F
        out (c),a
        in a,(c)                    ; (FH dropped)
        xor a
        out (c),a
        ld a,0x8F
        out (c),a
        in a,(c)                    ; (F dropped): CHGCPU ends with EI, no interrupt then
        ld a,1
        call CHGCPU                 ; to the R800, ROM mode, the LED as it was
        di
        ld a,IM2_I
        ld i,a
        im 2                        ; (the R800 from here: kept while it is parked)
        call SR_RAM                 ; its measures
        xor a
        call CHGCPU                 ; to the Z80 (the R800 parks under CHGCPU's DI)
        di
        im 1                        ; (the BIOS's mode until isr_init: a CHGCPU that came back on
        ld c,VDP_CTRL               ;  this same CPU, no R800, had left IM 2 here)
        ld a,(RG1SAV)
        out (c),a
        ld a,0x81
        out (c),a
        ld a,(RG0SAV)
        out (c),a
        ld a,0x80
        out (c),a                   ; R#1 and R#0 as the BIOS had them
        ld hl,(cpu_chk)
        ld de,120
        or a
        sbc hl,de
        ret nc                      ; (512 turns took 120 counts or more: not an R800)
        ld a,(cpu_chk + 3)
        add a,16
        ret c
        ld b,a
        ld a,(cpu_chk + 2)
        cp b
        ret c                       ; (port 98h not held: not the S1990's R800)
        ld a,1
        ld (cpu_tr),a
        ret

; The game's CPU (docs/TURBO_R.md 3.3): A = 81h the R800 (its LED on) or 80h the Z80 (the LED off);
; nothing when cpu_tr = 0. With the VDP's interrupt sources off and none pending (CHGCPU ends with
; EI) and page 0 on the main ROM for the call (slot 0, whose secondary register the game never
; writes: 0-0). The Z80 would freeze inside CHGCPU on a PAUSE flip-flop left set during R800 play,
; so a switch to it first waits for the key again (the picture kept, the pause LED lit); the same
; wait serves front_bonus' end, on the Z80 with its hardware pause off (front.asm). The CPU
; that resumes gets IM 2 (the R800 has it from cpu_detect: a second guard); cpu_cur = the CPU
; running. Returns with the interrupts off, R#1 = display off without interrupts, IE1 off.
cpu_set:
        ld e,a
        ld a,(cpu_tr)
        or a
        ret z
        bit 0,e
        jr nz,cs_go                 ; (to the R800)
cs_pz:  in a,(TR_PAUSE)
        rrca
        jr nc,cs_pl
        ld a,(CASPRV)
        or 1
        out (TR_PAUSE),a            ; (paused: its LED on until the key is pressed again)
        jr cs_pz
cs_pl:  ld a,(CASPRV)
        and 0xFE
        ld (CASPRV),a
        out (TR_PAUSE),a            ; (its LED off)
cs_go:  di
        ld c,VDP_CTRL
        ld a,0x02
        out (c),a
        ld a,0x81
        out (c),a                   ; R#1: display off, no VBLANK interrupt
        ld a,R0_IE1_OFF
        out (c),a
        ld a,0x80
        out (c),a                   ; R#0: no line interrupt
        ld a,1
        out (c),a
        ld a,0x8F
        out (c),a
        in a,(c)                    ; (S#1: FH dropped)
        xor a
        out (c),a
        ld a,0x8F
        out (c),a
        in a,(c)                    ; (S#0: F dropped)
        in a,(PPI_SLOT)
        ld d,a                      ; (CHGCPU keeps every register)
        and 0xFC
        out (PPI_SLOT),a            ; page 0: the main ROM (slot 0-0)
        ld a,e
        call CHGCPU
cs_back:
        di                          ; (the other CPU from here: CHGCPU ended with EI, no source on)
        ld a,IM2_I
        ld i,a
        im 2
        call GETCPU
        ld e,a
        ld a,d
        out (PPI_SLOT),a            ; page 0: the game's RAM again
        ld a,e
        or a
        jr z,cs_c
        ld a,1
cs_c:   ld (cpu_cur),a
        ld (sl_off),a               ; (the R800: the play field a line shorter, docs/TURBO_R.md 4.1)
        or a
        ld hl,sr_rom
        ld bc,SR_LEN
        ld de,scn_inc
        jr z,cs_blk
        in a,(TR_PAUSE)
        and 1
        ld (key_tp),a               ; (the PAUSE flip-flop as it is: key_scan follows its changes)
        xor a
        ld (sp8_cnt),a              ; (the split's timeouts from 0)
        ld hl,sr8_rom
        ld bc,SR8_LEN
        ld de,scn8_inc
cs_blk: ld (scn_at),de
        ld de,SR_RAM
        ldir                        ; this CPU's timed block (split.asm or split8.asm)
        ret

; (rc2.asm) The game's CPU: the R800 from ng_go, the Z80 again before the title.
cpu_game:
        ld a,0x81
        jp cpu_set
cpu_title:
        ld a,0x80
        jp cpu_set

        if R800PING
; (Test build) At each new game: 100 round trips Z80 -> R800 -> Z80, page 0's sum before and after
; them in cpu_png (ng_init).
cpu_ping:
        ld hl,0
        ld (cpu_png),hl
        call cpp_sum
        ld (cpu_png + 2),hl
        ld b,100
cpp_lp: push bc
        ld a,0x81
        call cpu_set
        ld a,0x80
        call cpu_set
        ld hl,(cpu_png)
        inc hl
        ld (cpu_png),hl
        pop bc
        djnz cpp_lp
        call cpp_sum
        ld (cpu_png + 4),hl
        ret
cpp_sum:
        ld hl,0
        ld de,0
        ld bc,0x4000
cps_lp: ld a,(de)
        add a,l
        ld l,a
        jr nc,cps_nc
        inc h
cps_nc: inc de
        dec bc
        ld a,b
        or c
        jr nz,cps_lp
        ret
        endif

; cpu_detect's measures, run by the R800 from SR_RAM (relative jumps only), the interrupts off:
; cpu_chk = timer counts of 512 djnz turns (2 bytes), of 16 reads of port 98h, of 16 of port A8h.
cd_ram:
        xor a
        out (TR_TIMER),a            ; the timer from 0
        ld c,2
        ld b,a
cdr_t:  djnz cdr_t
        dec c
        jr nz,cdr_t
        in a,(TR_TIMER)
        ld l,a
        in a,(TR_TIMER + 1)
        ld h,a
        ld (cpu_chk),hl
        xor a
        out (TR_TIMER),a
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(VDP_DATA)
        in a,(TR_TIMER)
        ld (cpu_chk + 2),a
        xor a
        out (TR_TIMER),a
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(0xA8)
        in a,(TR_TIMER)
        ld (cpu_chk + 3),a
        ret
cd_end:

; An MSX1, or an MSX2 with less than 128 KiB of VRAM (cold_init): the game
; cannot run there; a message in SCREEN 0 (the BIOS still serves page 0) and the machine stays
; on it.
no_msx2:
        ei
        call INITXT
        ld hl,no2_msg
nm_lp:  ld a,(hl)
        or a
        jr z,nm_x
        call CHPUT
        inc hl
        jr nm_lp
nm_x:   jr nm_x
no2_msg:
        db "ROBOCOP 2 needs an MSX2"
        db 13, 10
        db "with 128 KB of VRAM."
        db 0


; (tiles.asm) At power-on (cold_init).
; Page 0 (0000h-3FFFh) switched to the main RAM (the slot of page 3) once the BIOS is not
; needed any more: the game never calls it after its start and IM 2 does not use page 0.
; Carry on return when there is no RAM there.
ram_page0:
        di
        in a,(0xA8)
        ld b,a                      ; B = primary slot register
        rlca
        rlca
        and 3
        ld c,a                      ; C = page 3's primary slot
        ld e,a
        ld d,0
        ld hl,EXPTBL
        add hl,de
        bit 7,(hl)
        jr z,rp_prim
        ld a,(0xFFFF)
        cpl                         ; its secondary slot register
        ld d,a
        and 0xFC
        ld e,a
        ld a,d
        rlca
        rlca
        and 3                       ; page 3's secondary slot
        or e
        ld (0xFFFF),a
rp_prim:
        ld a,b
        and 0xFC
        or c
        out (0xA8),a
        ld hl,0x0000                ; is it RAM?
        ld a,0x5A
        ld (hl),a
        cp (hl)
        jr nz,rp_none
        cpl
        ld (hl),a
        cp (hl)
        jr nz,rp_none
        ld hl,0x3FFF
        ld (hl),a
        cp (hl)
        jr nz,rp_none
        ei
        or a
        jp tr_fixram                ; (a turbo R: the fixed area from its RAM; returns NC)
rp_none:
        ei
        scf
        ret

; MSX turbo R (docs/TURBO_R.md 6), at power-on after ram_page0 (cold_init):
; the fixed area (4000h-7FFFh, banks 0-1) copied into the internal RAM's segment 4 and shown in page
; 1 from then on, so that both CPUs run it from RAM (the R800 fetches the cartridge at ~4-5 cycles a
; byte, its RAM at ~1). The mapper's registers set as the game uses them (FCh = 3: page 0, the game's
; RAM; FFh = 0: page 3; FDh = 4: page 1), whatever a loader left. Page 1 takes page 3's slot, the
; RAM's (slot 3-0 on a turbo R, expanded). Nothing writes 4000h-7FFFh afterwards: the mapper's
; registers there (5000h, 7000h) never are, banks 0-1 being fixed.
tr_fixram:
        ld a,(cpu_tr)
        or a
        ret z
        di
        ld a,3
        out (0xFC),a
        xor a
        out (0xFF),a
        ld a,4
        out (0xFD),a                ; (page 1's segment once its slot is the RAM's)
        out (0xFC),a                ; page 0 on segment 4 for the copy
        ld hl,0x4000
        ld de,0x0000
        ld bc,0x4000
        ldir                        ; the cartridge's banks 0-1
        ld a,3
        out (0xFC),a                ; page 0: the game's RAM again
        in a,(0xA8)
        ld b,a
        rlca
        rlca
        and 3
        rlca
        rlca
        ld c,a                      ; page 3's primary slot, at page 1's bits
        ld a,(0xFFFF)
        cpl                         ; (page 3's secondary slot register)
        ld d,a
        and 0xF3
        ld e,a
        ld a,d
        rlca
        rlca
        rlca
        rlca
        and 0x0C                    ; page 3's subslot at page 1's bits
        or e
        ld (0xFFFF),a               ; (slot 3's page 1: the RAM's subslot)
        ld a,b
        and 0xF3
        or c
        out (0xA8),a                ; page 1: the RAM copy from here on
        ei
        ret

; (sound.asm) At power-on (cold_init).
; Everything silent: the PSG's volumes 0 and its mixer (PSG_MIX); with an OPLL, its 9 channels
; keyed off at volume 15 (the quietest) and its rhythm off.
snd_init:
        di
        ld a,7
        ld e,PSG_MIX
        call psg_w
        ld a,PSG_MIX
        ld (snd_mix),a              ; (vm_cal's vm_play restores R7 from it before sq_init runs)
        ld a,8
        ld e,0
        call psg_w
        ld a,9
        call psg_w
        ld a,10
        call psg_w
        ei
        ld a,(snd_fm)
        or a
        ret z
        ld a,0x0E
        ld e,0
        call opll_w                 ; rhythm off
        ld b,9
        ld c,0
sin_ch: ld a,0x20
        add a,c
        ld e,0
        call opll_w                 ; key off, block 0, F-number 0
        ld a,0x30
        add a,c
        ld e,0x0F
        call opll_w                 ; instrument 0, volume 15
        inc c
        djnz sin_ch
        ret

; (tiles.asm) At the level's start (lv_select): the packed map attributes (bank lv_atr, through
; the A000h window: 80 bytes per row, 4-bit codes, then the codes' 16 values) into page-0 RAM -
; rows 0-47 at ATR_RAM0, the others (lv_atrn bytes) at ATR_RAM1 (atr_rows: each row's address) -
; and the values into atr_lut. atr_rc reads them there: no bank switching for the game logic's
; many attribute reads.
atr_load:
        ld a,(act_a000)
        push af
        ld a,(lv_atr)
        call bank_a000
        ld hl,0xA000
        ld de,ATR_RAM0
        ld bc,48*80
        ldir
        ld de,ATR_RAM1
        ld bc,(lv_atrn)
        ldir
        ld de,atr_lut
        ld bc,16
        ldir
        pop af
        jp bank_a000

; (vdp.asm) E = banks of 8 KiB: the tiles from the ROM (through the A000h window) -> VRAM from
; 10000h (8 at the start: 10000h-1FFFFh, the HUD and the sprite tables follow; 4 after a SCREEN 8
; picture: G7 interleaves its bytes over both halves of VRAM, so a picture overwrites
; 10000h-16A00h).
tiles_upload:
        ld a,(act_a000)
        push af
        push de
        ld e,1
        ld hl,0
        call vram_write
        pop de
        ld a,(lv_tiles)             ; (the level's: lv_cur)
        ld d,a
ut_bank:
        ld a,d
        call bank_a000
        ld hl,0xA000
        ld b,32
        push de
        call vram_blocks
        pop de
        inc d
        dec e
        jr nz,ut_bank
        call vram_done
        pop af
        jp bank_a000

; (vdp.asm) The HUD's empty panel (HUD_IMG_BANK through the A000h window): page 3 from line
; HUD_VRAM_LINE (after the tiles, which cover pages 2-3); also at each new game (hud_init: the
; last game's digits and message go).
hud_upload:
        ld a,(act_a000)
        push af
        ld e,1
        ld hl,VRAM_HUD & 0xFFFF
        call vram_write
        ld a,HUD_IMG_BANK
        call bank_a000
        ld hl,0xA000
        ld b,HUD_LINES/2            ; 128 bytes per line: 256 per pair of lines
        call vram_blocks
        if HUD_LINES & 1
        ld bc,128*256 + VDP_DATA
        otir                        ; the odd last line
        endif
        call vram_done
        pop af
        jp bank_a000
