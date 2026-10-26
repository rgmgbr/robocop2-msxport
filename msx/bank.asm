; Bank switching for the Konami SCC style MegaROM / MegaRAM (write inside the page itself).
; Not the only code that knows the medium: music.asm, sound.asm and sprites.asm write 9000h/B000h
; themselves, and five places read both 8 KiB windows at once, so a memory-mapper version (one
; 16 KiB page) needs more than new routines here (docs/DISK_VS_ROM.md).
; The mapper's registers cannot be read: act_8000 / act_a000 keep the bank each window shows, so
; code that maps a window for a moment can put back what it found (the game's logic runs from
; the 8000h and A000h windows, logic_map).
bank_8000:                          ; A = bank for the 8000h-9FFFh window
        ld (act_8000),a
        ld (BANK_8000),a
        ret
bank_a000:                          ; A = bank for the A000h-BFFFh window
        ld (act_a000),a
        ld (BANK_A000),a
        ret

; The game logic's banks: module 1 (objects.asm) at 8000h, the level's own at A000h (module 2,
; mapobj.asm, is mapped at 8000h around its calls). Keeps HL, DE, BC.
logic_map:
        ld a,BANK_LC1
        call bank_8000
        ld a,(lvl_bank)
        jr bank_a000
