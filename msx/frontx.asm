; FRONT's additions for the game completed and the high scores (docs/ENDING.md), after FRONT's own
; code and tables, so that none of those moves: the calls that reach these replace calls of the same
; size (front_over's front_cont, front_bonus' front_brief, cold_init's snd_detect). The routines
; themselves are in the front end's second bank (ending.asm, BANK_FRONT2 at A000h: front2_call).

; HL = a routine of the front end's second bank (BANK_FRONT2 at A000h around it, FRONT at 8000h; the
; bank that was there comes back). Keeps BC, DE, HL as the routine leaves them.
front2_call:
        ld a,(act_a000)
        push af
        ld a,BANK_FRONT2
        call bank_a000
        call fc_hl
        pop af
        jp bank_a000

; The game completed (level_load_3 $86DE, load-table entries 3 and 7): ending.asm front_ending (WELL
; DONE, the CMP tune, the high-score entry), from a level's end (front_call; then the title: rc2.asm
; ml_ttl) or from front_bonus' end (fb_brief2). The one way in: level 3's end calls it.
fr_ending:
        ld hl,front_ending
        jr front2_call

; front_over's $82C4-$82CA: high_score_entry $12082 (ending.asm hs_entry: the entry when the score
; enters the table), then $11FD2 (front_cont); after an entry the game's display is on already and
; the play area black: the offer without front_cont's set-up (fc_neg, fc_txt).
fo_hsc: ld hl,hs_entry
        call front2_call
        ld a,(hs_ran)
        or a
        jp z,front_cont
        ld hl,(AG + 0x805E)         ; ($11FD2: front_cont's)
        dec hl
        ld (AG + 0x805E),hl
        bit 7,h
        jp nz,fc_neg
        jp fc_txt

; front_bonus' $859E: the next level's briefing (front_brief); after level 2's stages and the
; level-3 briefing ($8050 = 2), until level 3 is in the ROM, the game completed (fr_ending:
; docs/ENDING.md; level 3's end will call it instead). Not in builds with a script (their drives type
; no name; the title follows at once there) nor in PZ_TEST builds (the stages, then the title).
fb_brief2:
        call front_brief
        if INPUT_SCRIPT + PZ_TEST = 0
        ld a,(AG + 0x8050)
        cp 2
        jr z,fr_ending
        endif
        ret

; cold_init's first call after the machine's check: over 1 MiB the guard (rom_guard), the high
; scores' table (ending.asm hs_init: from the power-on until the power goes, as in the Amiga's code),
; then snd_detect as before.
ci_hook:
        if ROM_BANKS > 128
        call rom_guard
        endif
        ld hl,hs_init
        call front2_call
        jp snd_detect

        if ROM_BANKS > 128
; A ROM over 1 MiB (cold_init through ci_hook; the interrupts off): the tag mkrom.py writes at the
; last bank's 1FF0h, read at A000h. A device that holds less wraps, masks or ignores the higher bank
; numbers and shows another bank there: a message, and the machine stays on it (the BIOS still serves
; page 0). So does an SCC+ cartridge whose SCC+ mode an earlier program left on (its registers at
; B800h-BFFFh): a reset clears it, hence the message's last line. (Here since the product is a 2 MiB
; image: in cold.asm it moved FRONT's later code.)
rom_guard:
        ld a,ROM_BANKS - 1
        ld (BANK_A000),a
        ld hl,0xA000 + 0x1FF0
        ld de,rg_tag
        ld b,8
rg_lp:  ld a,(de)
        cp (hl)
        jr nz,rg_bad
        inc de
        inc hl
        djnz rg_lp
        ld a,(act_a000)
        ld (BANK_A000),a
        ret
rg_bad: ei
        call INITXT
        ld hl,rg_msg
        jp nm_lp
rg_tag: db "RC2BANK", ROM_BANKS - 1  ; (tools/mkrom.py guard_tag)
rg_msg: db "ROBOCOP 2 needs a 2 MB Konami"
        db 13, 10
        db "SCC cartridge or MegaRAM."
        db 13, 10
        db "If yours is one, reset the MSX."
        db 0
        endif

        if END_TEST
; (Test build, tools/mkrom.py END_TEST) rc2.asm end_test's part: LV_CARRY's score ($8046), lives
; ($8034) and credits ($805E) over what level 1's set-up left (ng_init), as a game would leave them.
front_etest:
        ld hl,LV_SCORE_H
        ld (AG + 0x8046),hl
        ld hl,LV_SCORE_L
        ld (AG + 0x8048),hl
        ld hl,LV_LIVES
        ld (AG + 0x8034),hl
        ld hl,LV_CREDITS
        ld (AG + 0x805E),hl
        ret
        endif
