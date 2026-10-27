; Brainstorm, the bonus stage after level 1 (the Amiga's PUZL at $17100, which $8382 calls:
; docs/BRAINSTORM.md). Bank BANK_PUZL at A000h while it runs, FRONT at 8000h (front.asm
; front_bonus calls bs_stage); its graphics in the data banks from PUZL_GFX_BANK (tools/mkrom.py,
; tools/msxpuzl.py).
;
; For now a stub: the stage ends at once, out of time. The stage itself (its logic, then its
; display) replaces it.

        include "puzl.inc"          ; the stage's places, sheet and VRAM coordinates (tools/msxpuzl.py)

; $17100: the stage -> A = its result ($17100's D0): 0 solved, 1 failed, 2 out of time. It
; leaves through pz_done (rc2.asm: the trace harness's end) with A = the result.
bs_stage:
        ld a,2                      ; (stub: out of time)
        jp pz_done

; ----- data -----

pz_pal1:
        incbin "puzl_1_grade.pal"   ; the stage's 16 colours, through the colour grade (tools/mkrom.py)
pz_cursor:
        incbin "puzl_cursor.spr"    ; the cursor's 9 sprite patterns (tools/msxpuzl.py)
        include "puzl_tab.inc"      ; PUZL's boards, messages and tables (tools/msxpuzl.py)
