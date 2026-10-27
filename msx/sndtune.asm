; The fixed area's entries to the tunes after the title (msx/tune.asm, BANK_MUSIC): Brainstorm's
; music and effects. Last in the fixed area (msx/rc2.asm), so that nothing before them moves.

        if DIAG                     ; (test builds never play the game: tune.asm holds no tune)
snd_tune:
snd_bfx:
        ret
fx_tkd: ld hl,fx_tick
        jp fx_bk
        else

; Brainstorm's music (msx/puzl.asm at a board's set-up, $1743A and $17442): PZM tune 1 from its
; start, the stop all first (tune.asm tn_start; never call snd_stop right before it: a stop the
; PSG player has not taken yet would silence the tune's first records).
snd_tune:
        ld hl,tn_pzm
        jp mus_call

; A = Brainstorm's request ($B04, once a pass, where $17794 starts it): that effect from the next
; tick on (tune.asm tn_go: $1822C's rule); of two requests before a tick the higher one, the one
; the Amiga lets sound. The tick runs again (fx_act: the tune may be over). Uses AF, HL.
snd_bfx:
        ld hl,tn_req
        cp (hl)
        ret c
        ld (hl),a
        ld a,2
        ld (fx_act),a
        ret

; sound.asm fx_tk (in the VBLANK interrupt; fx_act not 0): the tick of a tune of tune.asm while
; one plays (sndplay.asm voice A's SV_CH is TN_MARK: tune.asm tn_start), else the in-game effects'
; on the SCC (music.asm fx_tick, A = fx_act as sq_frame left it). fx_act is fx_tick's OR of its
; voices' ticks left, any value: only the mark tells the tune's ticks apart. Without an SCC the
; in-game effects never set fx_act: what is left is a tune's the PSG player's stop ended (snd_stop:
; mus_stop does not run, sq_stop takes the mark away): no more ticks.
fx_tkd: ld hl,fx_tick
        ld a,(snd_v + SV_CH)
        cp TN_MARK
        jr z,fxt_t
        ld a,(mus_mode)
        rra
        ld a,(fx_act)
        jp c,fx_bk
        xor a
        ld (fx_act),a
        ret
fxt_t:  ld hl,tn_tick
        jp fx_bk
        endif
