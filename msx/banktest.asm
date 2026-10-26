; Bank test cartridge for a 2 MiB Konami SCC MegaROM (tools/msxbanktest.py builds the image; no
; game). Written 2026-10-26 to check the 2 MiB ROM on the user's devices before any game data
; goes past 1 MiB (docs/ROM_BUDGET.md 6.1, docs/DISK_VS_ROM.md). On screen (SCREEN 0, the
; BIOS's text):
;   - which bank each of the 256 bank numbers shows in the 8000h window (written at 9000h) and in
;     the A000h window (B000h), and every byte of banks 1-255 through A000h: a cell a bank,
;     . right, 8 or A the window that showed another bank, X both, D a wrong byte;
;   - how many of 4 values stored at 9800h come back with 3Fh, 7Fh, BFh and FFh at 9000h (the
;     SCC's waveform: a ROM gives its own byte);
;   - the bank switches and reads at A000h a frame lets through with 1 to 256 banks in turn (the
;     MSX Pico+ copies 8 KiB pages from its flash into an SRAM cache and holds the Z80 meanwhile:
;     the count falls once the banks no longer fit).
; Bank b holds f(b, o) = b * 3Bh + (o >> 8) * 1Dh + (o & FFh) (low 8 bits) at its offset o, bank 0
; only where this code leaves room. The byte at 0020h names the bank (b = -13 * (byte - 20h));
; the one at 1720h, below the SCC's 9800h, is 9Bh more in every bank.

CHPUT:      equ 0x00A2
POSIT:      equ 0x00C6              ; H = column, L = row (from 1)
INITXT:     equ 0x006C
ERAFNK:     equ 0x00CC
ENASLT:     equ 0x0024
RSLREG:     equ 0x0138
MSXVER:     equ 0x002D
LINL40:     equ 0xF3AE
CSRSW:      equ 0xFCA9
EXPTBL:     equ 0xFCC1
SLTTBL:     equ 0xFCC5
RG9SAV:     equ 0xFFE8
VDP_ST:     equ 0x99                ; S#0: bit 7 the VBLANK flag (cleared when read)
BANK_8000:  equ 0x9000
BANK_A000:  equ 0xB000
SCC_W:      equ 0x9800              ; channel 1's first waveform byte (3Fh at 9000h)
SCC_ON:     equ 0x988F

ST_H:       equ 0xC0                ; C000h: per bank, bit 0 8000h showed another bank, 1 A000h,
                                    ;  2 a wrong byte, 4 and 5 the two tags disagreed (8000h, A000h)
SN8_H:      equ 0xC1                ; C100h: per bank number, the bank 8000h showed
SNA_H:      equ 0xC2                ; C200h: the same at A000h
LST_H:      equ 0xC3                ; C300h: the banks the speed loop takes in turn
RC_CHK:     equ 0xC400              ; the timed loops run from RAM: no cartridge fetch between the
RC_SPD:     equ 0xC480              ;  reads they make (tools/msxbanktest.py checks their sizes)
slotid:     equ 0xC500              ; the cartridge's slot, as ENASLT takes it
n_8:        equ 0xC501              ; word: bank numbers right at 8000h
n_a:        equ 0xC503              ; word: at A000h
n_d:        equ 0xC505              ; word: banks 1-255 with every byte right
scc_n:      equ 0xC507              ; 4 bytes: values back of 4 with 3Fh, 7Fh, BFh, FFh
frames:     equ 0xC50B
bl_n:       equ 0xC50C
sp_res:     equ 0xC50D              ; 9 words: switches a frame for 1, 2, 4 ... 256 banks
rp_res:     equ 0xC51F              ; (results: the speeds' pointers)
rp_pos:     equ 0xC521
rp_lab:     equ 0xC523

        org 0x4000
        db "AB"
        dw start
        ds 12, 0
        db "ROM_KON5"               ; (4010h: the mapper's tag, Konami SCC: the MSX Pico+ starts
        ds 8, 0                     ;  the ROM with it as a sure detection)
        db 0x20                     ; (4020h: bank 0's first tag, f(0, 0020h))

start:  di
        ld sp,0xF380
        call cart_p2                ; this cartridge in page 2 too
        ld hl,rc_chk                ; the timed loops into RAM
        ld de,RC_CHK
        ld bc,rc_chk_end - rc_chk
        ldir
        ld hl,rc_spd
        ld de,RC_SPD
        ld bc,rc_spd_end - rc_spd
        ldir
        ld a,40
        ld (LINL40),a
        call INITXT
        call ERAFNK
        xor a
        ld (CSRSW),a
        call frame
        call tags
        call data
        call scc
        call speed
        call results
        ei
st_end: halt
        jr st_end

; Page 2 to this cartridge's slot (page 1's, as the BIOS started it); slotid keeps it.
cart_p2:
        call RSLREG
        rrca
        rrca
        and 3
        ld c,a
        ld b,0
        ld hl,EXPTBL
        add hl,bc
        ld a,(hl)
        and 0x80
        or c
        ld c,a                      ; C = E000 00PP
        ld hl,SLTTBL
        ld a,c
        and 3
        ld e,a
        ld d,0
        add hl,de
        ld a,(hl)
        and 0x0C                    ; page 1's secondary slot
        or c
        ld (slotid),a
        ld h,0x80
        jp ENASLT

; The texts that do not change; every cell '-' (not tested yet).
frame:  ld hl,0x0101
        ld de,tx_head
        call at_prt
        ld de,tx_id
        call prt
        ld hl,0x0102
        ld de,tx_slot
        call at_prt
        ld a,(slotid)
        and 3
        add a,'0'
        call CHPUT
        ld a,(slotid)
        rlca
        jr nc,fr_ms                 ; (not expanded)
        ld a,'-'
        call CHPUT
        ld a,(slotid)
        rrca
        rrca
        and 3
        add a,'0'
        call CHPUT
fr_ms:  ld a,(MSXVER)
        cp 4
        jr c,fr_mv
        ld a,4
fr_mv:  add a,a
        ld l,a
        ld h,0
        ld de,tx_vers
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        call prt
        ld de,tx_60
        ld a,(RG9SAV)
        and 2
        jr z,fr_hz
        ld de,tx_50
fr_hz:  call prt
        ld hl,0x0103
        ld de,tx_wait
        call at_prt
        ld hl,0x0104
        ld de,tx_cols
        call at_prt
        ld b,0                      ; the rows' labels: their first bank
fr_row: ld a,b
        rlca
        rlca
        rlca
        and 7
        add a,5
        ld l,a
        ld h,1
        call POSIT
        ld a,b
        call hex2
        ld a,b
        add a,32
        ld b,a
        jr nz,fr_row
        ld c,'-'
fr_cel: call cel_at
        inc b
        jr nz,fr_cel
        ret

; Every bank number at 9000h and at B000h: the bank each window shows (st_tab bits 0, 1, 4, 5;
; sn_8, sn_a).
tags:   di
        ld b,0
tg_lp:  ld a,b
        ld (BANK_8000),a
        ld hl,0x8020
        call tag_rd
        ld c,0
        jr z,tg_8c
        ld c,0x11                   ; (wrong: its tags disagree)
tg_8c:  ld h,SN8_H
        ld l,b
        ld (hl),a
        cp b
        jr z,tg_8o
        set 0,c
tg_8o:  ld a,b
        ld (BANK_A000),a
        ld hl,0xA020
        call tag_rd
        jr z,tg_ac
        set 1,c
        set 5,c
tg_ac:  ld h,SNA_H
        ld l,b
        ld (hl),a
        cp b
        jr z,tg_ao
        set 1,c
tg_ao:  ld h,ST_H
        ld l,b
        ld (hl),c
        inc b
        jr nz,tg_lp
        ld a,2                      ; (the windows as at power-on)
        ld (BANK_8000),a
        ld a,3
        ld (BANK_A000),a
        ret

; HL = a window's 0020h: -> A = the bank its tag names, Z when the tag at 1720h agrees.
tag_rd: ld a,(hl)
        ld e,a
        ld a,h
        add a,0x17
        ld h,a
        ld a,(hl)
        sub e
        cp 0x9B
        push af
        ld a,e
        sub 0x20
        ld e,a
        add a,a
        add a,a
        ld d,a                      ; 4x
        add a,a
        add a,d
        add a,e                     ; 13x
        neg
        ld e,a
        pop af
        ld a,e
        ret

; Banks 1-255 through A000h, every byte (rc_chk in RAM); each cell drawn when its bank is done.
data:   ld b,0
dt_lp:  ld h,ST_H
        ld l,b
        ld a,b
        or a
        jr z,dt_cel                 ; (bank 0: this code)
        bit 1,(hl)
        jr nz,dt_cel                ; (A000h showed another bank)
        push hl
        di
        call RC_CHK
        pop hl
        jr z,dt_cel
        set 2,(hl)
dt_cel: ld a,(hl)
        and 7
        ld e,a
        ld d,0
        ld hl,tx_cell
        add hl,de
        ld c,(hl)
        call cel_at
        inc b
        jr nz,dt_lp
        ld a,3
        ld (BANK_A000),a
        ret

; With 3Fh, 7Fh, BFh and FFh at 9000h: 4 values stored at 9800h and loaded back, how many came
; back. Every SCC channel off before and after.
scc:    di
        ld a,0x3F
        ld (BANK_8000),a
        xor a
        ld (SCC_ON),a
        ld hl,scc_bk
        ld de,scc_n
        ld b,4
sc_bk:  push bc
        ld a,(hl)
        ld (BANK_8000),a
        ld c,0
        ld a,0x5A
        call sc_try
        ld a,0xBF
        call sc_try
        ld a,0x24
        call sc_try
        ld a,0x89
        call sc_try
        ld a,c
        ld (de),a
        inc de
        inc hl
        pop bc
        djnz sc_bk
        ld a,0x3F
        ld (BANK_8000),a
        xor a
        ld (SCC_ON),a
        ld a,2
        ld (BANK_8000),a
        ret

; A = a value: stored at 9800h, loaded back a moment later; C + 1 when it came back.
; Keeps DE, HL.
sc_try: ld (SCC_W),a
        ld b,a
        ex (sp),hl
        ex (sp),hl
        ld a,(SCC_W)
        cp b
        ret nz
        inc c
        ret

; For 1, 2, 4 ... 256 banks taken in turn at A000h (spread over the image): the switches and
; reads done in 8 frames, / 8 (sp_res).
speed:  ld hl,sp_step
        ld de,sp_res
        ld b,9
sp_k:   push bc
        push de
        push hl
        ld c,(hl)                   ; (256 / banks; 256 banks: 1)
        ld hl,LST_H * 256
        ld a,2
sp_ls:  ld (hl),a                   ; the list: 2, 2 + step, 2 + 2 * step ...
        add a,c
        inc l
        jr nz,sp_ls
        di
        ld a,8
        ld (frames),a
        ld de,LST_H * 256
        in a,(VDP_ST)               ; (an old flag cleared)
sp_w:   in a,(VDP_ST)
        rlca
        jr nc,sp_w                  ; (from a VBLANK on)
        call RC_SPD
        ld a,3
        ld (BANK_A000),a
        srl b
        rr c
        srl b
        rr c
        srl b
        rr c
        pop hl
        pop de
        ld a,c
        ld (de),a
        inc de
        ld a,b
        ld (de),a
        inc de
        inc hl
        pop bc
        djnz sp_k
        ret

; The counts, the bank numbers that went wrong, the SCC, the speeds, then the verdict.
results:
        ld hl,0
        ld (n_8),hl
        ld (n_a),hl
        ld (n_d),hl
        ld b,0
rs_cnt: ld h,ST_H
        ld l,b
        ld c,(hl)
        bit 0,c
        jr nz,rs_c1
        ld hl,(n_8)
        inc hl
        ld (n_8),hl
rs_c1:  bit 1,c
        jr nz,rs_c2
        ld hl,(n_a)
        inc hl
        ld (n_a),hl
rs_c2:  ld a,b
        or a
        jr z,rs_c3
        ld a,c
        and 6
        jr nz,rs_c3
        ld hl,(n_d)
        inc hl
        ld (n_d),hl
rs_c3:  inc b
        jr nz,rs_cnt
        ld hl,0x010E
        ld de,tx_ok8
        call at_prt
        ld hl,(n_8)
        call dec
        ld de,tx_oka
        call prt
        ld hl,(n_a)
        call dec
        ld de,tx_okd
        call prt
        ld hl,(n_d)
        call dec
        ld hl,0x010F
        ld de,tx_bad8
        call at_prt
        ld c,0x01
        ld e,0x10
        ld d,SN8_H
        call bad_ls
        ld hl,0x0110
        ld de,tx_bada
        call at_prt
        ld c,0x02
        ld e,0x20
        ld d,SNA_H
        call bad_ls
        ld hl,0x0111
        ld de,tx_badd
        call at_prt
        ld b,0
        ld c,8
rd_lp:  ld h,ST_H
        ld l,b
        bit 2,(hl)
        jr z,rd_nx
        ld a,c
        or a
        jr z,rd_nx
        dec c
        ld a,' '
        call CHPUT
        ld a,b
        call hex2
rd_nx:  inc b
        jr nz,rd_lp
        ld a,c
        cp 8
        jr nz,rd_x
        ld de,tx_none
        call prt
rd_x:   ld hl,0x0112
        ld de,tx_scc
        call at_prt
        ld hl,scc_bk
        ld de,scc_n
        ld b,4
rsc_lp: ld a,' '
        call CHPUT
        call CHPUT
        ld a,(hl)
        call hex2
        ld a,':'
        call CHPUT
        ld a,(de)
        add a,'0'
        call CHPUT
        inc hl
        inc de
        djnz rsc_lp
        ld hl,0x0114
        ld de,tx_spd
        call at_prt
        ld hl,sp_res
        ld (rp_res),hl
        ld hl,sp_pos
        ld (rp_pos),hl
        ld hl,sp_lab
        ld (rp_lab),hl
        ld b,9
rsp_lp: push bc
        ld hl,(rp_pos)
        ld a,(hl)
        inc hl
        ld e,(hl)
        inc hl
        ld (rp_pos),hl
        ld h,a
        ld l,e
        ld de,(rp_lab)
        call at_prt
        inc de
        ld (rp_lab),de
        ld hl,(rp_res)
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (rp_res),hl
        ex de,hl
        call dec
        pop bc
        djnz rsp_lp
        ld hl,(n_8)                 ; the verdict: every bank right in both windows, every byte
        ld de,256
        or a
        sbc hl,de
        jr nz,rv_f
        ld hl,(n_a)
        or a
        sbc hl,de
        jr nz,rv_f
        ld hl,(n_d)
        ld de,255
        or a
        sbc hl,de
        jr nz,rv_f
        ld de,tx_pass
        jr rv_p
rv_f:   ld de,tx_fail
rv_p:   ld hl,0x0103
        jp at_prt

; C = the bit of a wrong bank number, E = the bit of disagreeing tags, D = the page of what the
; window showed: " NN>SS" for the first 5 wrong ones (SS ?? when the tags disagreed), or NONE.
bad_ls: ld a,5
        ld (bl_n),a
        ld b,0
bl_lp:  ld h,ST_H
        ld l,b
        ld a,(hl)
        and c
        jr z,bl_nx
        ld a,(bl_n)
        or a
        jr z,bl_nx
        dec a
        ld (bl_n),a
        ld a,' '
        call CHPUT
        ld a,b
        call hex2
        ld a,'>'
        call CHPUT
        ld a,(hl)
        and e
        jr nz,bl_q
        ld h,d
        ld a,(hl)
        call hex2
        jr bl_nx
bl_q:   ld a,'?'
        call CHPUT
        call CHPUT
bl_nx:  inc b
        jr nz,bl_lp
        ld a,(bl_n)
        cp 5
        ret nz
        ld de,tx_none
        jp prt

; B = a bank, C = a character: that bank's cell shows it. Keeps BC, DE.
cel_at: ld a,b
        and 31
        add a,4
        ld h,a
        ld a,b
        rlca
        rlca
        rlca
        and 7
        add a,5
        ld l,a
        call POSIT
        ld a,c
        jp CHPUT

; HL = a column and a row (from 1), DE = a text: the text there.
at_prt: call POSIT
; DE = a text (0 at its end): at the cursor; DE left on its 0.
prt:    ld a,(de)
        or a
        ret z
        call CHPUT
        inc de
        jr prt

; A = a byte: two hex digits at the cursor. Keeps BC, DE, HL.
hex2:   push af
        rrca
        rrca
        rrca
        rrca
        call hx_n
        pop af
hx_n:   and 15
        add a,'0'
        cp '9' + 1
        jr c,hx_o
        add a,7
hx_o:   jp CHPUT

; HL = a number: its digits at the cursor, no leading zeros.
dec:    ld b,0                      ; (B: a digit shown already)
        ld de,10000
        call dc_dig
        ld de,1000
        call dc_dig
        ld de,100
        call dc_dig
        ld de,10
        call dc_dig
        ld a,l
        add a,'0'
        jp CHPUT
dc_dig: ld a,'0' - 1
dc_sub: inc a
        or a
        sbc hl,de
        jr nc,dc_sub
        add hl,de
        cp '0'
        jr nz,dc_nz
        inc b
        dec b
        ret z                       ; (a leading zero)
        jp CHPUT
dc_nz:  ld b,1
        jp CHPUT

; Copied to RC_CHK. B = a bank (1-255): mapped at A000h, every byte checked against f.
; -> Z: all right, NZ: a byte wrong. Keeps B, DE. Relative jumps only (it runs at RC_CHK).
rc_chk: ld a,b
        ld (BANK_A000),a
        add a,a
        add a,a
        ld c,a                      ; 4b
        add a,a
        add a,a
        add a,a
        add a,a                     ; 64b
        sub c
        sub b
        ld c,a                      ; C = page 0's base, b * 3Bh
        ld hl,0xA000
rcc_pg: ld a,(hl)                   ; (8 bytes a turn: byte l of a page is its base + l)
        sub l
        cp c
        jr nz,rcc_x
        inc l
        ld a,(hl)
        sub l
        cp c
        jr nz,rcc_x
        inc l
        ld a,(hl)
        sub l
        cp c
        jr nz,rcc_x
        inc l
        ld a,(hl)
        sub l
        cp c
        jr nz,rcc_x
        inc l
        ld a,(hl)
        sub l
        cp c
        jr nz,rcc_x
        inc l
        ld a,(hl)
        sub l
        cp c
        jr nz,rcc_x
        inc l
        ld a,(hl)
        sub l
        cp c
        jr nz,rcc_x
        inc l
        ld a,(hl)
        sub l
        cp c
        jr nz,rcc_x
        inc l
        jr nz,rcc_pg                ; (Z from the 8th: the page done)
        ld a,c
        add a,0x1D
        ld c,a
        inc h
        ld a,h
        cp 0xC0
        jr nz,rcc_pg
        xor a
rcc_x:  ret
rc_chk_end:

; Copied to RC_SPD. DE = the bank list (256 bytes from a page's start), frames = frames to
; count: from a VBLANK on, a bank from the list at B000h and a read at A020h, over and over.
; -> BC = how many were done.
rc_spd: ld bc,0
        ld hl,0xA020
rcs_lp: ld a,(de)
        inc e
        ld (BANK_A000),a
        ld a,(hl)
        inc bc
        in a,(VDP_ST)
        rlca
        jr nc,rcs_lp
        ld a,(frames)
        dec a
        ld (frames),a
        jr nz,rcs_lp
        ret
rc_spd_end:

tx_head:    db "ROBOCOP2 2 MIB BANK TEST   ID ", 0
        include "banktest_id.inc"   ; (tx_id: tools/msxbanktest.py --id)
tx_slot:    db "SLOT ", 0
tx_vers:    dw tx_v0, tx_v1, tx_v2, tx_v3, tx_v4
tx_v0:      db "  MSX1", 0
tx_v1:      db "  MSX2", 0
tx_v2:      db "  MSX2+", 0
tx_v3:      db "  TURBO R", 0
tx_v4:      db "  MSX?", 0
tx_60:      db "  60 HZ", 0
tx_50:      db "  50 HZ", 0
tx_wait:    db "TESTING, ABOUT 30 SECONDS...", 0
tx_pass:    db "RESULT: PASS                ", 0
tx_fail:    db "RESULT: FAIL                ", 0
tx_cols:    db "   0123456789ABCDEF0123456789ABCDEF", 0
tx_ok8:     db "BANKS OK  8000:", 0
tx_oka:     db "  A000:", 0
tx_okd:     db "  DATA:", 0
tx_bad8:    db "8000 BAD:", 0
tx_bada:    db "A000 BAD:", 0
tx_badd:    db "DATA BAD:", 0
tx_none:    db " NONE", 0
tx_scc:     db "SCC AT 9800", 0
tx_spd:     db "SWITCHES A FRAME, N BANKS IN TURN:", 0
tx_cell:    db ".8AXDXAX"               ; (by st_tab bits 0-2)
sp_step:    db 0, 128, 64, 32, 16, 8, 4, 2, 1
sp_pos:     db 1, 21, 14, 21, 27, 21, 1, 22, 14, 22, 27, 22, 1, 23, 14, 23, 27, 23
sp_lab:     db "  1:", 0
            db "  2:", 0
            db "  4:", 0
            db "  8:", 0
            db " 16:", 0
            db " 32:", 0
            db " 64:", 0
            db "128:", 0
            db "256:", 0
scc_bk:     db 0x3F, 0x7F, 0xBF, 0xFF
