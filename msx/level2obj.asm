; Level 2's own object types (bank BANK_L2, included by level2.asm; docs/LEVEL2.md 3.3): 1, the
; walking gunman ($C736, walk_d6), 2, the armed suspect and its arrest ($C868, $C91A), 5, the drip
; ($D0E2), 6, the rolling tyre ($D1E2, $D1CA-$D1E1) with its death ($C33E), 14, the grenadier
; ($CE0A), 16, the walker with a big gun ($CD7A), and 49, the homing drone ($E6C0, $E728-$E7B1).
;
; Stubs until the plan's step 9: each handler frees its slot at once (A = FFh: D0 negative,
; update_objects $C3E4 frees the slot without a death), so an unported type never shows nor acts;
; the death does nothing.
t1:                                 ; ($C736)
t2:                                 ; ($C868)
t5:                                 ; ($D0E2)
t6:                                 ; ($D1E2)
t14:                                ; ($CE0A)
t16:                                ; ($CD7A)
t49:                                ; ($E6C0)
        ld a,0xFF
        ret
death_c33e:                         ; ($C33E)
        ret
