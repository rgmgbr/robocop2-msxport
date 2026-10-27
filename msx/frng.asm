; The shooting range, the second bonus stage after level 1 (the Amiga's FRNG at $1EA00, which
; $8420 calls: docs/RANGE.md). Bank BANK_FRNG at A000h while it runs, FRONT at 8000h (front.asm
; front_range calls rg_stage); its graphics in the data banks from RANGE_GFX_BANK, its hit data from
; RANGE_HIT_BANK (tools/mkrom.py, tools/msxrange.py).
;
; A stub (docs/RANGE.md section 5, step 5): the bank's place in the ROM, with the converter's
; equates and tables. Nothing calls it yet.

        include "range.inc"         ; the stage's view, VRAM map, positions and layouts (tools/msxrange.py)

rg_stage:
        ret

; ----- data -----

        include "range_tab.inc"     ; FRNG's tables and fr_code's initial image (tools/msxrange.py)
