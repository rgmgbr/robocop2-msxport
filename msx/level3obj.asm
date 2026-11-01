; Level 3's own object types (bank BANK_L3B, mapped at A000h around each handler by rc2.asm l3b_call,
; which level3.asm's handler table reaches through 6-byte stubs; docs/LEVEL3.md 3.2, 3.3): types 21,
; 22 (Cain), 33-43, 46, 47, 48, 50, 51 and 52, with their tables (at_l3b.inc: tools/amitab.py, bank
; l3b of analysis/amiga_tables.tsv). While a handler runs BANK_L3 is not mapped: it may call the
; fixed code and LC1 (objects.asm, shots.asm, hits.asm at 8000h), never level3.asm's code or
; lvshared_l3.asm's helpers (t_xy, t_face, t_col, t_word: copies of their own here when needed).
; A handler returns D0's high byte in A, as every level bank's (objects.asm obj_call: negative frees
; the slot).
;
; Built by the plan's step A: every type is a stub that frees its slot at once (ld a,FFh / ret: the
; original's moveq #-1,D0 / rts, which tools/bstest/l3stub.py writes into the bench's handlers), so
; the level runs and traces against the stubbed references; step B replaces each stub by its port.

t21:                                ; (the big walker, $D2FA)
t22:                                ; (Cain as RoboCop 2, $D49C)
t33:                                ; (the truck, $E0A4)
t34:                                ; (the small walker, $E1D6)
t35:                                ; (the gunner that rises and sinks, $E28C)
t36:                                ; (the robot, $E356)
t37:                                ; (the flying machine, $E470)
t38:                                ; (the homing missile, $E6D6)
t39:                                ; (the bomb, $E7D2)
t40:                                ; (the wall turret, $E98C)
t41:                                ; (the wall turret, $EB0A)
t42:                                ; (the wall turret, $E972)
t43:                                ; (markers off, $EC02)
t46:                                ; (spawn delay and marker mask 0, $EE22)
t47:                                ; (the camera mode, $EE30)
t48:                                ; (Cain's bursts, $EE5E)
t50:                                ; (the gunner that stays put, $EEE2)
t51:                                ; (the walker, $EE68)
t52:                                ; (the bomb, $E8A2)
        ld a,0xFF                   ; (step A's stub: D0 negative, the slot freed)
        ret
