; The sound player (BANK_INPUT at A000h: sound.asm maps it around these calls). Three PSG voices
; play the streams of tools/msxsound.py (sound.inc): records of a duration in ticks (0: the end)
; and the voice's state for it (volume, tone and noise on, the tone period, the noise period),
; 50 ticks a second as the Amiga's player (at 60 Hz every sixth VBLANK is skipped). The title's
; three streams end together, the tune played out (mus_end: the game starts; the Amiga loops it
; until fire). An effect plays on the voice of its Amiga channel (0-2: A-C; 3: an idle
; voice, C first, else the one nearest its record's end) and ends silent; while the Amiga's
; channel 3 plays an effect, a lower effect than the last one started is not played ($1822C).
; The main program only queues requests (sq_put): the VBLANK interrupt starts them (sq_frame),
; so the voices change in one place and the interrupts are never held off for long (the HUD's
; split).

SQ_MUSIC:   equ 0xFE                ; queued requests besides the effects (sound.asm): the title's
SQ_STOP:    equ 0xFF                ;   music, everything silent
SQ_N:       equ 8                   ; the queue's entries (snd_q)

SV_PTR:     equ 0                   ; 2: the next record
SV_LEFT:    equ 2                   ; ticks left of the record in effect (0: idle)
SV_CTL:     equ 3                   ; volume (bits 0-3), tone on (bit 4), noise on (bit 5)
SV_PER:     equ 4                   ; 2: the tone period
SV_NOISE:   equ 6                   ; the noise period
SV_LOOP:    equ 7                   ; 2: not 0: a title stream (its loop point, unused: its
                                    ;   end is the tune's, mus_end); 0: an effect's
SV_CH:      equ 9                   ; the Amiga channel of the effect played (FFh: none)
SV_SIZE:    equ 10

; From the main program (sound.asm, BANK_INPUT mapped through bank_a000, the interrupts on): A =
; an effect, SQ_MUSIC or SQ_STOP into the queue the VBLANK interrupt empties (a full queue drops
; it); SQ_STOP also silences the PSG at once (the VBLANK interrupt may be off for a while: the
; level's start). Uses AF, BC, DE, HL.
sq_put: ld c,a
        cp SQ_STOP
        call z,sq_mute
        ld a,(snd_qt)
        ld e,a
        inc a
        and SQ_N - 1
        ld b,a
        ld a,(snd_qh)
        cp b
        ret z
        ld d,0
        ld hl,snd_q
        add hl,de
        ld (hl),c
        ld a,b
        ld (snd_qt),a               ; (after the entry: the interrupt never reads it half written)
        ret
sq_mute:
        ld b,8                      ; R8-R10 = 0 (the interrupts off: the PSG's address latch)
sqm_lp: di
        ld a,b
        out (PSG_ADDR),a
        xor a
        out (PSG_DATA),a
        ei
        inc b
        ld a,b
        cp 11
        jr nz,sqm_lp
        ret

; At power-on (the interrupts off): the queue empty, the voices idle.
sq_init:
        xor a
        ld (snd_qh),a
        ld (snd_qt),a
        jp sq_stop

; One VBLANK: the requests queued, then (50 a second) a tick.
sq_frame:
        ld a,(snd_qh)
        ld hl,snd_qt
        cp (hl)
        jr z,sqq_x
        ld e,a
        inc a
        and SQ_N - 1
        ld (snd_qh),a
        ld d,0
        ld hl,snd_q
        add hl,de
        ld a,(hl)
        cp SQ_STOP
        jr nz,sqq_m
        call sq_stop
        jr sq_frame
sqq_m:  cp SQ_MUSIC
        jr nz,sqq_e
        call sq_title
        jr sq_frame
sqq_e:  call sq_sfx
        jr sq_frame
sqq_x:  ld a,(RG9SAV)
        and 2
        jr nz,sqf_t                 ; (50 Hz: a tick every VBLANK)
        ld hl,snd_div
        inc (hl)
        ld a,(hl)
        cp 6
        jr c,sqf_t
        ld (hl),0
        ret
sqf_t:  ld a,(mus_mode)             ; (an SCC: the effects play there, these voices stay idle)
        rra
        jr c,sqf_x
        ld ix,snd_v
        ld b,0
sqf_v:  ld a,(ix+SV_LEFT)
        or a
        jr z,sqf_n
        dec (ix+SV_LEFT)
        call z,sq_rec
sqf_n:  ld de,SV_SIZE
        add ix,de
        inc b
        ld a,b
        cp 3
        jr nz,sqf_v
        if INPUT_SCRIPT = 0         ; (builds with a script never show the title: its room)
        ld a,(mus_mode)             ; the title fading out (sound.asm snd_fade) on this player
        or a                        ; (music.asm fades the SCC's and the OPLL's): every FADE_TICKS
        jr nz,sqf_x                 ; ticks 3 dB more (mus_att, sq_out), the voices' volumes again
        ld a,(mus_fade)
        or a
        jr z,sqf_x
        dec a
        jr nz,sqf_s
        ld a,(mus_att)
        cp 15
        jr nc,sqf_r
        inc a
        ld (mus_att),a
        ld ix,snd_v
        ld b,0
sqf_o:  ld a,(ix+SV_LEFT)
        or a
        call nz,sq_out
        ld de,SV_SIZE
        add ix,de
        inc b
        ld a,b
        cp 3
        jr nz,sqf_o
sqf_r:  ld a,FADE_TICKS
sqf_s:  ld (mus_fade),a
        endif
sqf_x:  ld a,(fx_act)               ; (effects playing on the SCC: they tick with these ticks)
        or a
        ret z
        jp fx_tk

; A = an effect (1..SND_SFX_N): it starts.
sq_sfx: or a
        ret z
        cp SND_SFX_N + 1
        ret nc
        ld c,a
        ld a,(mus_mode)             ; an SCC: the effect plays there and its noise on the PSG
        rra                         ; (music.asm fx_start)
        ld a,c
        jp c,fx_go
        ld ix,snd_v                 ; the Amiga's channel 3 busy with an effect?
        ld b,3
sqs_c3: ld a,(ix+SV_CH)
        cp 3
        jr nz,sqs_n3
        ld a,(ix+SV_LEFT)
        or a
        jr z,sqs_n3
        ld a,c
        ld hl,snd_last
        cp (hl)
        ret c                       ; (a lower one than the last: not played)
        jr sqs_ok
sqs_n3: ld de,SV_SIZE
        add ix,de
        djnz sqs_c3
sqs_ok: ld a,c
        ld (snd_last),a
        dec a
        ld l,a
        ld h,0
        ld e,l
        ld d,h
        add hl,hl
        add hl,de
        ld de,snd_sfx
        add hl,de                   ; its entry: the stream, the Amiga channel
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld a,(hl)
        ld c,a
        cp 3
        jr nc,sqs_any
        ld b,a
        jr sqs_set
sqs_any:
        ld ix,snd_v + 2 * SV_SIZE   ; channel 3: an idle voice, else the nearest its end (from C:
        ld hl,0xFF00                ; A plays the shots); H = the best's ticks left, L = its voice
        ld b,2
sqa_lp: ld a,(ix+SV_LEFT)
        cp h
        jr nc,sqa_n
        ld h,a
        ld l,b
sqa_n:  push de
        ld de,0 - SV_SIZE
        add ix,de
        pop de
        dec b
        jp p,sqa_lp
        ld b,l
sqs_set:
        call sq_vix                 ; IX = voice B
        ld (ix+SV_CH),c
        xor a
        ld (ix+SV_LOOP),a
        ld (ix+SV_LOOP+1),a
        ld (ix+SV_PTR),e
        ld (ix+SV_PTR+1),d
        jr sq_rec

; The title's music from its start.
sq_title:
        ld hl,snd_title
        ld b,0
sqt_lp: call sq_vix
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (ix+SV_PTR),e
        ld (ix+SV_PTR+1),d
        push hl
        inc hl
        inc hl
        inc hl
        inc hl
        ld e,(hl)                   ; (its loop pointer, three words on)
        inc hl
        ld d,(hl)
        ld (ix+SV_LOOP),e
        ld (ix+SV_LOOP+1),d
        ld (ix+SV_CH),0xFF
        call sq_rec
        pop hl
        inc b
        ld a,b
        cp 3
        jr nz,sqt_lp
        ret

; Everything silent, the title's fade over (its attenuation off once the voices are: the
; effects share sq_out).
sq_stop:
        ld b,0
sqx_lp: call sq_vix
        ld (ix+SV_CH),0xFF
        call sq_off
        inc b
        ld a,b
        cp 3
        jr nz,sqx_lp
        xor a
        ld (mus_fade),a
        ld (mus_att),a
        ret

; B = a voice -> IX = its record. Keeps BC, DE, HL.
sq_vix: push de
        ld ix,snd_v
        ld de,SV_SIZE
        ld a,b
        or a
sqv_lp: jr z,sqv_x
        add ix,de
        dec a
        jr sqv_lp
sqv_x:  pop de
        ret

; IX = voice B: its next record (at the end silence: the title's voices, SV_LOOP not 0, end
; together, the tune played out: mus_end, front.asm front_fire starts the game), then its
; registers. Keeps B, IX.
sq_rec: ld l,(ix+SV_PTR)
        ld h,(ix+SV_PTR+1)
sqr_rd: ld a,(hl)
        inc hl
        or a
        jr nz,sqr_go
        ld a,(ix+SV_LOOP)
        or (ix+SV_LOOP+1)
        jr z,sq_off
        ld (mus_end),a              ; (not 0)
        jr sq_off
sqr_go: ld (ix+SV_LEFT),a
        ld a,(hl)
        inc hl
        ld (ix+SV_CTL),a
        ld c,a
        bit 6,c
        jr z,sqr_n
        ld a,(hl)
        inc hl
        ld (ix+SV_PER),a
        ld a,(hl)
        inc hl
        ld (ix+SV_PER+1),a
sqr_n:  bit 7,c
        jr z,sqr_s
        ld a,(hl)
        inc hl
        ld (ix+SV_NOISE),a
sqr_s:  ld (ix+SV_PTR),l
        ld (ix+SV_PTR+1),h
        jr sq_out
sq_off: xor a
        ld (ix+SV_LEFT),a
        ld (ix+SV_CTL),a

; IX = voice B: its PSG registers (tone period, volume, the noise period while it uses noise, the
; mixer's bits). Keeps B, IX.
sq_out: ld a,b
        add a,a
        out (PSG_ADDR),a
        ld c,a
        ld a,(ix+SV_PER)
        out (PSG_DATA),a
        ld a,c
        inc a
        out (PSG_ADDR),a
        ld a,(ix+SV_PER+1)
        out (PSG_DATA),a
        ld a,b
        add a,8
        out (PSG_ADDR),a
        if INPUT_SCRIPT = 0
        ld a,(mus_att)              ; (the title's fade: 0 but then)
        ld c,a
        ld a,(ix+SV_CTL)
        and 15
        sub c
        jr nc,sqo_v
        xor a
        else
        ld a,(ix+SV_CTL)
        and 15
        endif
sqo_v:  out (PSG_DATA),a
        ld c,(ix+SV_CTL)
        bit 5,c
        jr z,sqo_m
        ld a,6
        out (PSG_ADDR),a
        ld a,(ix+SV_NOISE)
        out (PSG_DATA),a
sqo_m:  ld a,b                      ; the mixer: tone bit B, noise bit B + 3 (0: on)
        inc a
        ld d,a
        ld a,0x80
sqo_b:  rlca
        dec d
        jr nz,sqo_b
        ld d,a
        add a,a
        add a,a
        add a,a
        ld e,a
        ld a,(snd_mix)
        or d
        or e
        and 0x3F
        or 0x80                     ; (port A input, port B output)
        bit 4,c
        jr z,sqo_t
        xor d
sqo_t:  bit 5,c
        jr z,sqo_w
        xor e
sqo_w:  ld (snd_mix),a
        ld d,a
        ld a,7
        out (PSG_ADDR),a
        ld a,d
        out (PSG_DATA),a
        ret
