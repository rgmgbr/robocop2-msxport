; The tunes after the title: Brainstorm's music and sound effects (PZM, PUZL's copy of the
; player at $18000: tune 1 at every board, effects 3-6 on Amiga channel 3; docs/BRAINSTORM.md,
; tools/msxtune.py) and the shooting range's (FRM, FRNG's copy at $20000: tune 1 once, effects 2-4
; on channel 3; docs/RANGE.md 3.7, tools/msxtune.py --frm) on this machine's chips. BANK_MUSIC at
; A000h around every call (mus_call from the main program: msx/puzl.asm's set-up, tn_pzm;
; msx/frng.asm's, tn_frm; sound.asm fx_tk from the VBLANK interrupt: fx_tkd). Nothing of it is in
; the fixed area but fx_tk's operand. These routines and their
; descriptors (tune.inc) come after the title's code and tables (music.asm, music.inc,
; voice.inc), which keep their places and bytes. Where they lie does not matter to the MSX Pico+
; (with 3Fh at 9000h it also shows the SCC at B800h-BFFFh): nothing here runs or is read while 3Fh
; is there (the SCC's registers through sound.asm's routines; the waveforms from RAM, scc_wv).
;
; A tune's descriptor (tools/mkrom.py tune.inc: pz_desc, fr_desc) gives per chip set its streams (bank,
; address: read through the 8000h window across banks, music.asm mv_rec), its length (no loop: its
; voices silent after it, as the Amiga's channels stop), the OPLL's patch block, its effects'
; table and its SCC waveforms. tn_start plays it from its start, the stop all first ($18004, then
; $18010); the VBLANK interrupt ticks it 50 times a second while the tune or an effect plays:
; sndplay.asm sq_frame's ticks (at 60 Hz every sixth VBLANK skipped) while fx_act is not 0, with
; sndplay.asm voice A's SV_CH set to TN_MARK (sound.asm fx_tk -> fx_tkd: tn_tick).
; - Its tick 0 waits for the stage's next pass (tn_hold: the pass counter $B00 moved). The 68000
;   ticks PZM inside PUZL's pass, after that pass's request ($17794, then $17212), and the stop all
;   and tune 1 end a board's set-up: the first tick plays tune 1's tick 0 with the effect the next
;   pass asks for (5 at boards 1-3: the jingle and the tune start together), at 50 and 60 Hz
;   whichever VBLANKs the passes' and the ticks' dividers skip. FRNG's pass counter is $B00 too:
;   the range's tune 1, started in its set-up, plays its tick 0 after the stage's first pass (FRNG
;   skips its first pass's tick: docs/RANGE.md default 29).
; - The tune: music.asm's voices (mus_v: three melodic, the drums), readers and outputs (mv_rec,
;   mo_fm3, mo_rhy, mo_pv) with mus_on 0 (sound.asm spv_on then turns the SCC's channels 0-3 on);
;   on the SCC tn_sc1, mo_sc1's output with the waveforms from the tune's own table (tn_wv). With
;   an SCC the melody on its channels 0-2 and the drums on PSG voice C, or on the OPLL's rhythm
;   when there is one; the OPLL alone: its channels 0-2 and its rhythm; neither: the PSG version
;   on voices A-C. On a turbo R's R800 no OPLL (opll_w's waits are a Z80's): Brainstorm runs on the
;   Z80.
; - The effect voice (tn_v, the fifth): the effects play over the music as on the Amiga, whose
;   music leaves channel 3 to them. With an SCC on its channel 3 (the music uses 0-2), else on
;   PSG voice C: the PSG version's voice 2 is muted while an effect sounds, then takes C back
;   (its whole state written again: mo_pw), never lost. An effect with no SCC part (FRM's effect
;   2, a noise) has an SCC-mode stream in the PSG format, flagged by bit 7 of its SCC ticks byte
;   (tools/mkrom.py tune_inc): with an SCC it plays on PSG voice B, idle in both SCC modes (the
;   drums on C, which shares the noise period R6, or on the OPLL's rhythm: tn_fxo); an effect of
;   the other format that cuts it silences B first (tn_go). A request (msx/puzl.asm snd_bfx,
;   msx/frng.asm snd_rfx: tn_req)
;   starts at the next tick, before the records: $1822C's rule, refused while the voice is busy
;   (tn_busy) with a higher effect than it (tn_last, cleared by the tune's start as stop all clears
;   $18023). Busy as the 68000's channel 3: until the tick that reads the effect's end (TF_LEN
;   ticks after its first), whose request still finds it busy (PUZL asks at $17794, before that
;   pass's tick at $17212): a lower request is refused after 1 to TF_LEN of its ticks. An effect
;   sounds for its stream's ticks (its trailing silence left out), then its channel goes back.
; - Stopped by snd_stop: mus_quiet (fx_act 0) with an SCC or an OPLL; with the PSG alone mus_stop
;   does not run, but the PSG player's stop (SQ_STOP: sndplay.asm sq_stop) sets voice A's SV_CH,
;   which tn_start set to TN_MARK: fx_tkd then ends the ticks (no write: sq_stop silenced voices
;   A-C).
; - The interrupt rule: the VBLANK runs tn_tick with DE and IX saved (sound.asm snd_bk), AF, BC
;   and HL by the interrupt; IY and the alternate registers are not used here.

TD_SCC:     equ 0                   ; a descriptor: 4 x (bank, address): the SCC's voices 0-2, the
                                    ;   drums on PSG voice C;
TD_FM:      equ 12                  ;   4 x: the OPLL's channels 0-2, its rhythm;
TD_PSG:     equ 24                  ;   3 x: the PSG alone, voices A-C;
TD_TICKS:   equ 33                  ;   2: the tune's length in ticks;
TD_PATCH:   equ 35                  ;   14: the OPLL's custom instrument (00h-07h), the rhythm's
                                    ;   pitches (16h-18h, 26h-28h);
TD_FX:      equ 49                  ;   2: its effects' table, 1: the first effect, 1: how many;
TD_WAVES:   equ 53                  ;   its SCC waveforms (bank, address: 32 bytes each, none across
TD_SIZE:    equ 56                  ;   a bank)
TF_LEN:     equ 0                   ; an effect: its length in ticks (its end's tick: tn_go),
TF_SCC:     equ 1                   ;   its SCC stream (bank, address), its ticks + 1,
TF_PSG:     equ 5                   ;   its PSG stream, its ticks + 1
TF_SIZE:    equ 9
TN_MARK:    equ 0xFE                ; sndplay.asm voice A's SV_CH while a tune of these plays

        if DIAG = 0                 ; (test builds never play the game: no room, no tune)

; msx/frng.asm's set-up (rg_stage, through mus_call): the shooting range's music, FRM tune 1.
tn_frm: ld hl,fr_desc
        ds (fr_fx - fr_desc - TD_SIZE) * 0x4000   ; (tools/mkrom.py's layout: an error if not)
        jr tn_start

; msx/puzl.asm's set-up (bs_setup's end, through mus_call): Brainstorm's music, PZM tune 1.
tn_pzm: ld hl,pz_desc
        ds (pz_fx - pz_desc - TD_SIZE) * 0x4000   ; (tools/mkrom.py's layout: an error if not)

; HL = a tune's descriptor (through mus_call): the stop all, then the tune from its start on this
; machine's chips: its voices set up here, the interrupts off meanwhile (the chips' accesses: the
; PSG's latch, the SCC's bank; up to about 2 ms, the OPLL's patch the most). Its tick 0 is the
; first tick after the stage's next pass (tn_hold, fx_tkd), with the request that pass sends: a
; tick is the VBLANK's, as every tick (its waveform loads are the longest work); the chips stay
; silent until then. The interrupts on: it waits for the next VBLANK first (tick), so that this
; runs far from the HUD split's line interrupt (~13 ms on) and that a stop still queued for the
; PSG player (snd_stop: that VBLANK writes voices A-C silent) cannot silence the new tune (H7);
; without a VBLANK, a second or so at most.
tn_start:
        push hl
        ld hl,tick
        ld e,(hl)
        ld bc,0
tns_q:  ei
        ld a,(hl)
        cp e
        jr nz,tns_go                ; (a VBLANK came)
        dec bc
        ld a,b
        or c
        jr nz,tns_q
tns_go: di
        call mus_quiet              ; ($18004: every voice idle, the chips silent, fx_act 0)
        ld e,0
        ld a,8
        call psg_w                  ; (PSG voices A and B too: the PSG version's)
        ld a,9
        call psg_w
        xor a
        ld (tn_req),a               ; the effect voice idle, the rule's memory cleared ($18023)
        ld (tn_busy),a
        ld (tn_snd),a
        ld (tn_last),a
        pop hl
        push hl
        ld de,TD_TICKS
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc de                      ; (+ 1: tn_tick)
        ld (tn_left),de
        ld de,TD_FX - TD_TICKS - 1
        add hl,de
        ld de,tn_fx
        ld bc,5
        ldir                        ; (its effects' table, the first, how many; its waveforms' bank
        ld e,(hl)                   ;  and address)
        inc hl
        ld d,(hl)
        ld (tn_wad),de
        ld a,(cpu_cur)              ; the chips: mus_mode's, no OPLL on the R800
        or a
        ld a,(mus_mode)
        jr z,tns_m
        and MM_SCC
tns_m:  ld (tn_mode),a
        pop hl
        ld ix,mus_v
        or a
        jr nz,tns_c
        ld de,TD_PSG                ; neither an SCC nor an OPLL: the PSG version on A-C
        add hl,de
        ld c,MVK_PSG
        ld b,3
tns_p:  call mst_one
        djnz tns_p
        jr tns_t
tns_c:  push hl
        ld de,TD_SCC                ; the melody's three voices
        ld c,MVK_SCC
        rra
        jr c,tns_s
        ld de,TD_FM
        ld c,MVK_FM
tns_s:  add hl,de
        ld b,3
tns_v:  call mst_one
        djnz tns_v
        pop hl
        push hl
        ld de,TD_SCC + 9            ; the drums': PSG voice C,
        ld c,MVK_PSG
        ld a,(tn_mode)
        and MM_RHY
        jr z,tns_d
        ld de,TD_FM + 9             ;   or the OPLL's rhythm
        ld c,MVK_RHY
tns_d:  add hl,de
        call mst_one
        pop hl
        ld a,(tn_mode)
        and MM_FM | MM_RHY
        jr z,tns_t
        ld de,TD_PATCH
        add hl,de
        call tn_fm
tns_t:  ld a,(tn_mode)
        rra
        ld a,0x0F                   ; the SCC's channels 0-3 on (3: the effect voice's; their
        call c,scc_on               ; volumes 0 until the first records)
        ld a,(snd_mix)              ; the PSG's tone and noise off until the first records
        or 0x3F
        and 0xBF
        ld (snd_mix),a
        ld e,a
        ld a,7
        call psg_w
        ld a,TN_MARK
        ld (snd_v + SV_CH),a        ; (the PSG player's stop ends this tune too: fx_tkd)
        ld a,2
        ld (fx_act),a               ; (the VBLANK ticks it from its tick 0: sound.asm fx_tk)
        ld a,(pzv_frame)            ; (its tick 0 held until the stage's pass counter, $B00's low
        ld (tn_hpz),a               ;  byte, is no longer this: fx_tkd)
        ld a,1
        ld (tn_hold),a
        ei
        ret

; HL = a patch block: the OPLL's custom instrument (00h-07h); with its rhythm, the rhythm's
; pitches (16h-18h, 26h-28h) and the rhythm mode on, no key struck (music.asm mst_fm's way).
tn_fm:  ld c,0
        ld b,8
        call msf_w
        ld a,(tn_mode)
        and MM_RHY
        ret z
        ld c,0x16
        ld b,3
        call msf_w
        ld c,0x26
        ld b,3
        call msf_w
        ld a,0x0E
        ld e,0x20
        jp opll_w

; sound.asm fx_tk (the VBLANK interrupt: sndplay.asm sq_frame's tick while fx_act is not 0;
; BANK_MUSIC at A000h through fx_bk): the tick of a tune of these while one plays (sndplay.asm
; voice A's SV_CH is TN_MARK: tn_start), its tick 0 held until the stage's next pass (tn_hold: the
; pass counter's low byte no longer tn_hpz, the one tn_start saw; a held tick writes nothing); else
; the in-game effects' tick on the SCC (music.asm fx_tick). fx_act is fx_tick's OR of its voices'
; ticks left, any value: only the mark tells the tune's ticks apart. Without an SCC the in-game
; effects never set fx_act: what is left is a tune's the PSG player's stop ended (snd_stop:
; mus_stop does not run, sq_stop takes the mark away): no more ticks.
fx_tkd: ld a,(snd_v + SV_CH)
        cp TN_MARK
        jr z,fxd_t
        ld a,(mus_mode)
        rra
        jp c,fx_tick
        xor a
        ld (fx_act),a
        ret
fxd_t:  ld hl,tn_hold
        ld a,(hl)
        or a
        jp z,tn_tick
        inc hl                      ; (tn_hpz)
        ld a,(pzv_frame)
        cp (hl)
        ret z                       ; (no pass since tn_start: held)
        dec hl
        ld (hl),0                   ; (this tick is its tick 0: on into tn_tick)

; One tick (from the VBLANK: sndplay.asm sq_frame's tick through fx_tkd; the first after
; tn_start, tick 0, reads every voice's first record): the effect requested first (tn_go), then the
; tune's records while it lasts (at its end every voice silent: the OPLL's at its least volume,
; key off), the effect voice's, then the chips (tn_mode). No more ticks (fx_act 0) when nothing
; plays any more: snd_bfx starts them again. Uses AF, BC, DE, HL, IX; the 8000h window shows
; act_8000's bank after.
tn_tick:
        ld a,(tn_req)
        or a
        call nz,tn_go
        ld hl,(tn_left)
        ld a,h
        or l
        jr z,tna_f                  ; (the tune is over)
        dec hl
        ld (tn_left),hl
        ld a,h
        or l
        ld ix,mus_v
        ld b,4
        jr z,tna_e                  ; (its end)
tna_rd: ld (ix+MV_NEW),0
        ld a,(ix+MV_LEFT)
        or a
        jr z,tna_n
        dec (ix+MV_LEFT)
        jr nz,tna_n
        push bc
        call mv_rec
        pop bc
tna_n:  ld de,MV_SIZE
        add ix,de
        djnz tna_rd
        jr tna_f
tna_e:  ld a,(ix+MV_KIND)           ; the end: a silent record for each voice
        cp MVK_FM
        ld a,0
        jr nz,tna_z
        ld a,15
tna_z:  ld (ix+MV_CTL),a
        ld (ix+MV_LEFT),0
        ld (ix+MV_NEW),1
        ld de,MV_SIZE
        add ix,de
        djnz tna_e
tna_f:  ld hl,tn_busy               ; the effect voice: its busy ticks counted down,
        ld a,(hl)
        or a
        jr z,tna_b
        dec (hl)
tna_b:  ld ix,tn_v
        ld (ix+MV_NEW),0
        ld hl,tn_snd                ;   its records while it sounds
        ld a,(hl)
        or a
        jr z,tna_o
        dec (hl)
        jr z,tna_x
        dec (ix+MV_LEFT)
        call z,mv_rec
        jr tna_o
tna_x:  xor a                       ; (its end: silent)
        ld (ix+MV_CTL),a
        inc a
        ld (ix+MV_NEW),a
        ld a,(tn_mode)
        or a
        jr nz,tna_o
        ld hl,mus_v + 2 * MV_SIZE + MV_NEW
        set 0,(hl)                  ; (the PSG alone: C to voice 2 again, its whole state)
tna_o:  ld a,(act_8000)             ; (the records' banks)
        ld (BANK_8000),a
        ld a,(tn_mode)
        or a
        jr z,tna_p
        rra
        jr nc,tna_q
        ld ix,mus_v                 ; the SCC: voices 0-2 on its channels 0-2,
        ld b,0
tna_s:  call tn_sc1
        ld de,MV_SIZE
        add ix,de
        inc b
        ld a,b
        cp 3
        jr nz,tna_s
        ld ix,tn_v                  ;   the effect voice on its channel 3 (or PSG B: tn_fxo)
        call tn_fxo
tna_q:  ld a,(tn_mode)
        and MM_FM
        call nz,mo_fm3              ; the OPLL's channels 0-2
        ld ix,mus_v + 3 * MV_SIZE
        ld a,(tn_mode)
        and MM_RHY
        jr z,tna_c
        call mo_rhy                 ; the drums on the OPLL's rhythm,
        jr tna_y
tna_c:  call mo_psg                 ;   or on PSG voice C
tna_y:  ld a,(tn_mode)
        rra
        jr c,tna_end
        ld ix,tn_v                  ; the OPLL alone: the effect voice on PSG voice C
        ld a,2
        call mo_pv
        jr tna_end
tna_p:  ld ix,mus_v                 ; the PSG alone: voices 0 and 1 on A and B,
        xor a
        call mo_pv
        ld ix,mus_v + MV_SIZE
        ld a,1
        call mo_pv
        ld ix,mus_v + 2 * MV_SIZE   ;   C: voice 2, or the effect voice while it sounds
        ld a,(tn_snd)
        or a
        jr z,tna_2
        ld ix,tn_v
tna_2:  ld a,2
        call mo_pv
tna_end:
        ld hl,(tn_left)             ; anything still playing?
        ld a,h
        or l
        ld hl,tn_busy
        or (hl)
        ld hl,tn_snd
        or (hl)
        ret nz
        ld (fx_act),a               ; (no: no more ticks)
        ret

; IX = the effect voice (tn_v) with an SCC: its record of this tick, if any (MV_NEW), to SCC
; channel 3, or, when its stream is in the PSG format (MV_KIND MVK_PSG: an effect without an SCC
; part, flagged in its table: tn_go), to PSG voice B (mo_pv), idle in both SCC modes. Uses AF, BC,
; DE, HL; keeps IX.
tn_fxo: ld b,3
        ld a,(ix+MV_KIND)
        or a                        ; (MVK_SCC)
        jr z,tn_sc1
        ld a,1
        jp mo_pv

; IX = a voice on SCC channel B (0-3): its record of this tick, if any (MV_NEW), to the chip as
; music.asm mo_sc1 does (the waveform, the period, the volume, the channels on: sound.asm
; scc_pv), its waveform from the tune's table (tn_wv). Keeps B, IX.
tn_sc1: ld c,(ix+MV_NEW)
        ld a,c
        or a
        ret z
        push bc
        bit 5,c
        call nz,tn_wv
        pop bc
        ld e,(ix+MV_PER)
        ld d,(ix+MV_PER+1)
        ld a,(ix+MV_CTL)
        and 15
        jp scc_pv

; IX = a voice on SCC channel B whose record gave a waveform (MV_AUX): that one of the tune's
; table (tn_wbk, tn_wad: 32 bytes each through the 8000h window; none across a bank) through
; scc_wb into the channel (sound.asm scc_wv: the cartridge's SCC or another slot's; the 8000h
; window shows act_8000's bank after). Uses AF, BC, DE, HL.
tn_wv:  ld l,(ix+MV_AUX)
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,(tn_wad)
        add hl,de
        ld a,(tn_wbk)
        bit 5,h
        jr z,tnw_b
        res 5,h                     ; (past the window: the next bank)
        inc a
tnw_b:  ld (BANK_8000),a
        ld de,scc_wb
        ld c,b
        ld b,0
        push bc
        ld c,32
        ldir
        pop bc
        ld a,c
        rrca
        rrca
        rrca
        ld e,a
        ld d,SCC_WAVE / 256         ; DE = 9800h + 32 x the channel
        jp scc_wv

; A = the effect requested (tn_tick; the request cleared): $1822C's rule, a lower one than the
; last started (tn_last) refused while the voice is busy (tn_busy); else it starts from its
; first record, its stream for this machine's chips (the SCC's, or the PSG's), sounding for its
; stream's ticks. With an SCC, bit 7 of its SCC ticks byte (tools/mkrom.py tune_inc) gives that
; stream in the PSG format, for PSG voice B (tn_fxo); while an effect of the other format still
; sounds, its output is silenced first (FRM: a shot on B cut by a hit sound on SCC 3; Brainstorm's
; effects are all of one format and write what they wrote before). Busy for its length + 1,
; counted down from this tick on (tn_tick tna_f): the
; 68000 clears channel 3's flags ($18126) in the tick that reads the effect's end ($18450-$1845C,
; stored at $18384), its length after its first, and PUZL's request of that pass comes before
; its tick, so it finds the voice busy too.
tn_go:  ld c,a
        xor a
        ld (tn_req),a
        ld a,(tn_fx0)
        ld b,a
        ld a,c
        sub b
        ld hl,tn_fxn
        cp (hl)
        ret nc                      ; (not one of the tune's effects)
        ld b,a                      ; (its index)
        ld a,(tn_busy)
        or a
        jr z,tng_s
        ld a,(tn_last)
        ld e,a
        ld a,c
        cp e
        ret c                       ; (refused)
tng_s:  ld a,c
        ld (tn_last),a
        ld a,b
        add a,a
        add a,a
        add a,a
        add a,b                     ; (TF_SIZE x its index)
        ld e,a
        ld d,0
        ld hl,(tn_fx)
        add hl,de
        ld a,(hl)
        inc a                       ; (TF_LEN + 1: below 256, tools/mkrom.py pzm_check)
        ld (tn_busy),a
        inc hl
        ld c,MVK_SCC
        ld a,(tn_mode)
        rra
        jr nc,tng_p
        push hl                     ; (with an SCC: its ticks + 1, bit 7 the PSG format)
        inc hl
        inc hl
        inc hl
        bit 7,(hl)
        pop hl
        jr z,tng_v
        ld c,MVK_PSG
        jr tng_v
tng_p:  ld de,TF_PSG - TF_SCC
        add hl,de
        ld c,MVK_PSG
tng_v:  ld ix,tn_v
        ld a,(tn_snd)
        or a
        jr z,tng_m                  ; (the voice silent)
        ld a,(ix+MV_KIND)
        cp c
        jr z,tng_m                  ; (the same output: the first record writes it all)
        push bc                     ; the other output silenced first (its record of this tick:
        push hl                     ;  volume 0, tone and noise off)
        xor a
        ld (ix+MV_CTL),a
        inc a
        ld (ix+MV_NEW),a
        call tn_fxo
        pop hl
        pop bc
tng_m:  call mst_one                ; (HL then on its ticks + 1)
        ld a,(tn_mode)
        rra
        ld a,(hl)
        jr nc,tng_t
        and 0x7F                    ; (with an SCC: the format bit off)
tng_t:  ld (tn_snd),a
        ret

; msx/ending.asm's front_ending and hs_name (through mus_call): the ending's music, CMP tune 1 as $11C54
; plays it, with HI1's effects 3 and 4 (the name entry's) in its table (tools/msxtune.py --end,
; docs/ENDING.md; its descriptor in tune_cm.inc, after this code). Its tick 0 is held as any tune's
; (tn_hold): the front end clears it.
tn_cmp: ld hl,cm_desc               ; (its layout checked after tune_cm.inc: msx/rc2.asm)
        jp tn_start

        else                        ; (DIAG builds: no byte here, DIAG=2 fills BANK_MUSIC)
tn_pzm:     equ mus_stop            ; (msx/puzl.asm's set-up: the stop all only)
fx_tkd:     equ fx_tick             ; (sound.asm fx_tk: the in-game effects' tick, as before tune.asm)
tn_frm:     equ mus_stop            ; (msx/frng.asm's set-up: the stop all only)
tn_cmp:     equ mus_stop            ; (msx/ending.asm: the stop all only)
        endif
