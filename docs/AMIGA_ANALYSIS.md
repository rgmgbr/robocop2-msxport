# Robocop 2 (Amiga) — reverse-engineering ledger

Analysed version: *Robocop 2 (1991)(Ocean)[cr Melnok]*, 2 ADF disks.
Developed by Special FX for Ocean (credits on the `OAS` screen).

| Disk | SHA-1 |
|---|---|
| 1 | `f1bd7bc85c58df4a6f435c9742e37dc8eb8ddbf3` |
| 2 | `faf57c531bbf56017e0fcc55e222ec83ae7a968f` |

Legend: **[verified]** = confirmed by data/code/image; **[inferred]** = consistent
hypothesis not yet confirmed.

## 1. Disk format

- Neither disk has an AmigaDOS file system: sector 880 holds audio samples. All access is
  by sector (512 bytes) through a custom loader. **[verified]**
- Free sectors were filled with `DOS`+counter by the crack. **[verified]**
- `tools/rc2files.py list` maps 100% of the sectors of both disks; the only content outside
  the directory are 3 orphan PP20 copies identical to OAS, PIC4 and PIC7. **[verified]**

## 2. Boot chain (disk 1)

The bootblock (valid checksum) uses `trackdisk.device` (`DoIO`):

| Disk offset | Size | Final address | Content |
|---|---:|---|---|
| `$00400` | `$A600` | `$8000` (via `$48000`) | main code |
| `$CE600` | `$0200` | `$0100` (via `$60000`) | lookup by name + name table |
| `$CE800` | `$0800` | `$0300` (via `$70000`) | trackloader + directory |
| `$D4800` | `$5200` | `$71000` | run with `JSR` before the game (probably the crack intro) **[inferred]** |

Then it enters supervisor mode (vector `$20` trick), stores `$100` in `($C0)` and jumps to
`$8000`. The game calls the loader with `MOVEA.L $C0.W,A2 / JSR (A2)`, `A0` = file name.
**[verified]**

## 3. Loader file system

- Name table at `$14E`: 27 entries of 12 bytes `name[6] | id.w | dest.l`. Bit 7 of the id
  marks PP20 (the loader loads at `dest-8` and decrunches in place). **[verified]**
- Directory at `$91C`: 6-byte entries indexed by `id & $7F`: `(disk-1)<<12 | sector`,
  `length.l`. **[verified]**
- `PUZL` exists on both disks; the lookup switches entries when the 3rd character of the
  name is `Z` and `($8050) == 2`. **[verified]**
- The 14 PP20 files decrunch with exact bit-stream consumption (`tools/pp20.py`).
  **[verified]**
- FRNG and disk 1's PUZL are not PP20: their callers decrunch them after the loader with the
  game's ByteKiller routine `$124A6` (A0 source, A1 destination; `$12528` reads the next long,
  `$12534` a field of bits). Header: stream length, decrunched length, checksum; the stream is read
  backwards one long at a time and the output written backwards. `$124A6` returns without testing
  the checksum (its `rts` at `$12526`). `tools/bytekiller.py` transcribes it from the REA listing:
  FRNG_15 and PUZL_13 give checksum 0 with every long read, and the original run on the bench gives
  the same 170,970 bytes for FRNG. **[verified]**

### Files

| Name | Destination | Final size | Content |
|---|---|---:|---|
| DATAE | `$40000` | 32032 | Data East logo, 320×200×4 + palette **[verified]** |
| OAS | `$18000` | 32032 | Special FX/Ocean credits, 320×200×4 **[verified]** |
| TPIC | `$6FFA0` | 61568 | title, HAM6 320×200 + data + 3 8SVX samples **[verified]** |
| PIC1–7, PIC9 | `$6FFA0` | 42368 | movie stills, HAM6 320×176 **[verified]** |
| PICF | `$6FFA0` | 61568 | final picture, HAM6 320×256 **[verified]** |
| TITM, MU1, CH1, CMP, HI1 | `$18000` | 152520 / 62800 / 24760 / 84031 / 36511 | player code, tunes and 8SVX samples (*Music and sound effects*, section 4) **[verified]** |
| PERMA | `$58850` | 96080 | resident graphics (player, common BOBs, HUD) **[verified for the player]** |
| SPERMA | `$4B68A` | 53700 | resident BOBs with masks **[verified]** |
| RB1 | `$12588` | 10290 | the 8 letters of the title logo, BOBs with masks (48 px wide), flown in by `$106E2` (section 5) **[verified]** |
| DATAL1–3 | `$28000` | 144716 / 105816 / 185356 | level data: tiles, map, BOBs **[verified]** |
| MADEX | `$45250` | 25340 | DATAL1's tail, byte for byte (`DATAL1_10.bin[1D250h:]`): the explosions, smoke, hostage and nuke that levels 1 and 2 share, loaded again before level 2 (*Level 2*, section 4) **[verified]** |
| FRNG | `$1E980` | 93224 | the shooting range (*Gun Calibration*): its code, tables, graphics and FRM (a copy of the music player with its tune and effects), crunched; `$8420` decrunches it with `$124A6` into `$1EA00-$485D9` (170,970 bytes) on both visits (section 5, *The shooting range*) **[verified]** |
| PUZL | `$17080`/`$17100` | 76012 / 113632 | bonus stage *Brainstorm*: its code, boards, graphics and PZM (a copy of the music player with its tunes); disk 1's copy is crunched and decrunched at `$17100` by `$124A6` into the bytes of disk 2's plain copy (section 5, *Brainstorm*) **[verified]** |

Static-screen format: 32 bytes of OCS palette (`$0RGB`) followed by sequential planes
(DATAE/OAS); `PIC*` have a 128-byte header (32 colours + zeros) and the bitmap at `+$80`.
Use `tools/planar.py`. The picture shown is `PIC('1'+D0)` (routine `$11E06`): D0 = 0/3/6
before levels 1/2/3 (PIC1/PIC4/PIC7), 1/5 and 2/4 around the bonus stages, and **8 = game
over (PIC9)**, called from `main_loop` when the lives counter `$8034` goes negative.
**[verified]**

## 4. Game engine (code at `$8000`)

- `$8000`: `BRA` to the initialisation; `$8004–$8028` are 10 public `BRA.W` entries (used
  by overlays). **[verified]**
- `$802C–$8063`: global variables; `$8050` = current level. **[verified]**
- Initialisation at `$11A20`: logos (DATAE, OAS), title (TPIC in HAM6, TITM music), then
  PERMA/SPERMA. **[verified]**
- Main loop at `$80C2`: waits for `($802C) >= 2` (the VBL counter), i.e. **30 game frames/s**
  on the NTSC Amiga this release targets (Data East, US: the DATAE logo; 25 on a PAL
  machine); calls ~17 routines per frame. **[verified loop; the rate follows from the VBL
  counter]**
- Per-level table at `$8664` (40 bytes × 3 levels): pointers patched into the code
  (`$9C18`, `$915E`, `$8B54`), initial camera, palette (`$FFF6` for level 1, `$10036` for
  levels 2–3). **[verified]**
- Game palette: 31 colours copied into copper list `$1049E` (COLOR01–31), fade routine at
  `$F8C4`. **[verified]**

### In-game video

- Copper list `$1049E`: `BPL1MOD=BPL2MOD=$72`, DDF `$38–$C8` (38 bytes per line),
  horizontal DIW `$90–$1B0` (288 px). **[verified]**
- **Interleaved 4-plane** playfield, 152 bytes per line (4 × 38), 16 colours; colours 16–31
  belong to the hardware sprites. **[verified in the BOB routine]**
- Two buffers swapped with `EORI.L #$18E00,$B16` starting at `$6FFA0` (difference `$7200`
  = 152 × 192 lines). **[inferred]**
- In-game copper list `$10332`: bitplanes on from line `$1E` to `$CD` (176 lines of play
  area); from line `$D0` the **status panel**: 5 planes (32 colours, COLOR01..31 set by the
  MOVEs at `$103FA`), 320 px, modulo 0, planes at `$6DA20` + n×`$780` — the last 9600
  bytes of PERMA (file offset `$151D0`); bitplanes off at `$FE` (46 lines shown). It
  holds the energy can, a message/energy box, the nuke counter, two heads (lives), the
  timer and the score (`build/png/panel.png`). **[verified]**
- **Panel elements and their routines** (via REA; assets rendered by `tools/panel.py`;
  the operations are modelled in `tools/hudmodel.py`, which redraws the panel stored in
  PERMA exactly from the start values — a unit test). **[verified]**
  - every routine blits into the panel bitmap; digits and characters write planes 0–2 only,
    so planes 3–4 (the colour bank) stay — the bank is 0 under every digit cell and under the
    text; the can, heads and icons write all 5 planes;
  - energy can, x 0 y 3: `update_energy_can` (`$89BE`, every game frame) moves the shown
    level `$169C` 8 units towards the target `$169A` (0..`$100`, 32 steps); a target of
    `$100` or more draws the full can (`$661D0`, 32×40) at once; otherwise a step from an old
    level L ≥ 2 (L = old shown >> 3) draws an "empty top" (32×8: `$664F0` for L > 23,
    `$66590` for 13–23, `$66630` for ≤ 12) at y = 33 − L and the can's own line 39 − L at
    y = 42 − L. A negative shown level sets the death flag `$16CC`. The energy only drops by
    fixed amounts (−`$A`, −`$C`, −`$10`, −`$18`, −`$20`, −`$30`, −D6, −1; `ST $169A` kills) or is
    set to full (`$100`/`$102`: refill counter `$16AA`, level start); stepping *up* would draw
    the surface two lines lower than stepping down, but the game never does it;
  - message box, x 35–212 y 1–15: `message_queue` (`$FD76`) stores a string pointer in the
    4-slot queue `$FD92` at the write index `$8056` (a busy slot drops the message);
    `message_ticker` (`$FDA2`) runs in the VBL interrupt (`irq_l3_vbl`, `$10324`): one
    character per VBL with `panel_draw_char` (`$10620`: 8×8 font `$65DB0`, 3 planes, at
    x 40 + 8c, y 5; code ' ' → glyph 41, codes ≥ '@' → code − 'A', others → code − `$16`, so
    the strings use lower-case letters for the punctuation glyphs: 'e' = '.'); the string's
    `$FF` terminator is not drawn; then `$805A` = `$50` VBLs of wait and columns 20..0 erased
    with spaces, one per VBL, before the slot is freed and the read index `$8054` moves on (an
    empty slot is skipped in one VBL). Messages: `$C222` "PROTECT THE INNOCENT.", `$DC76`
    "ARREST ARMED EMEMY.", `$C238` "SUSPECT DESTROYED.", `$C24B` "CAIN DESTROYED.", `$D46C`
    "CHASE CAIN.", `$ED11` "EXTRA LIFE.", `$865A` "TIMEOUT.", `$F837`/`$F82C` "PAUSE ON./OFF."
    and the debug `$F841` "NUKE xx HOST xx" (key `$21`);
  - timer, score and weapon ammo: `panel_update_digits` (`$F6B8`, from `frame_keys` `$F76C`
    every game frame) redraws, by the game frame counter `$B00`, the timer's minutes or seconds
    (`$804A`/`$804B`, red glyphs 12–21, x 224/240 and 272/288, y 6: the code passes the odd
    byte offsets `$10F`/`$10D` and the blitter aligns them to words), the ammo's hundreds or
    tens and units (`$8030`/`$8031`, green, x 48/64/80, y 23) and one score byte
    (`$8046`–`$8049`, 7 green digits, x 192–288, y 29) with `$105D2` (16×16, 3 planes,
    `$654B0`; columns 0, 1, 14 and 15 are the same for all ten digits); the dash between
    minutes and seconds is a static red cell at x 256;
  - weapon icon, x 96 y 25: `set_weapon` (`$FD30`) sets the weapon `$805C` (0–3: normal, rapid
    fire, scatter, three-way), its ammo from `$FD52` (000/500/300/400) and its icon from
    `$FD5A` (3, 0, 2, 1) → `panel_draw_icon` (`$896A`, 16×16, offsets `$AF76`, 8 icons);
  - lives, x 128 + 32n y 14: `panel_draw_head` (`$88DE`) draws a 32×34 head (`$666D0`, 6
    graphics: 0 RoboCop's helmet, 1–3 the helmet turning into Murphy's face, 4–5 Murphy's
    face); slot 0 is drawn without its last 4 columns except for its first 4 lines;
    `init_lives` (`$FFD8`) sets `$8034` = 2 and draws head 0 in both slots; an extra life
    (`$ECD8`) adds a life, draws head 0 in slot lives − 1 and queues "EXTRA LIFE."; during the
    death sequence (`main_loop` `$8270`, counter `$16BC` +4 per game frame) slot lives − 1
    shows heads 3, 4, 5 for counter values `$60`–`$8E`. **[inferred: how the lives decrement at
    `$82A0` interleaves with that animation is still to be read]**
- Area at `$7F5E0` swapped with `EORI.L #$1920` and cleared with `BLTSIZE=$9202`
  (2336 bytes): hardware-sprite double buffer. **[inferred]**

### BOBs (routine `$AB08`, `draw_bob`)

- Input: `D0/D1` = world x/y (camera `$B04/$B06` subtracted), `A2` = data, `D4` = BLTSIZE.
  **[verified]**
- Format: `[mask][plane0][plane1][plane2][plane3]`, each `width_bytes × height`,
  `width = ((D4 & 63) − 1) × 2`. Cookie-cut with minterm `$CA` (`D = A ? B : C`), clipped to
  288 × 177. **[verified]**
- The planes may contain bits outside the mask (the artists did not clean them; the
  cookie-cut discards them), so "mask ⊇ planes" is **not** a valid format test. Always read
  the real BLTSIZE from the assembly. **[verified]**
- BOB addresses are **per level**: every handler belongs to one level and that level's
  DATAL holds the graphics at the fixed address. E.g. `$3E450` (16×16, step `$A0`) in level
  1 = flames/smoke of the vehicle routine `$8B9E`; `$3E810` (32×23, step `$1CC`) in level 2
  = walking legs of enemy type 1. **[verified visually]**
- Enemies are **built from parts** (legs, torso, arm/gun from PERMA), each part a BOB.
  **[verified for type 1]**

### Background and maps (routine `$BCCA`) **[verified]**

- The background is **redrawn entirely every frame**: 19 × 12 tiles of 16×16 copied by the
  blitter (`BLTCON0=$09F0`, `BLTSIZE=$1001`) into the back buffer.
- **Tiles**: 16×16, 4 planes interleaved per line = 128 bytes, at the start of the DATAL.
- **Map**: at `$38000` (DATAL + `$10000`), **160 columns** of 16-bit words;
  `graphic = DATAL_base + (word & ~$7F)`, the low 7 bits are attributes.
- Fine scroll: horizontal through BPLCON1 (`15 − (camera_x & 15)`), vertical through the
  line offset `(camera_y & 15) × 152`.
- **Level 1**: map of **160 × 51 tiles (2560 × 816 px)**, **431 unique tiles** (~55 KiB in
  4 bpp), scrolling in both directions; the map ends at `$3BFC0`, exactly where the first
  BOB graphics start.

### Objects (routines `$9C06` and `$C3E4`) **[verified in code]**

- Per-level object lists (`$A562`, `$A828`, `$AA3A`): 12-byte entries `type, ?, ?, ?, x, y`,
  terminated by a negative word; `$9C06` activates the ones entering the camera window
  (some also write patterns into the map).
- 5 active slots at `$BE4` (structure of arrays: x at `−$80`, y at `−$20`, type at `+$20`,
  flags at `+$21`).
- Type descriptors at `$BEB0` (16 bytes; types 1–52): score (BCD), handler, death routine,
  energy, collision width/height. Death adds the score and counts *henchmen obliterated*.

### Player (routine `$B94A`) **[verified]**

- RoboCop is **not a BOB**: every frame `draw_player` composes it into a 64 px × 73 lines ×
  4 planes buffer at `$7E3A0` (planes every `$248`) and copies it into the **8 hardware
  sprites** (4 attached pairs, 16 colours, COLOR16–31; colour 0 transparent), whose data
  pointer is at `$8036`.
- Animation table at `$B4E2`: 17 states × 8 bytes (`steps−1`, list offset, lines); state in
  `$15E2`, frame counter in `$15DC` (record = list + (counter & ~1) × 8). Frame record,
  16 bytes: PERMA offset, BLTSIZE, destination modulo, —, arm x/y (`+8`/`+9`, signed), head
  x/y (`+10` unsigned / `+11` signed), base x in bytes / y (`+12`/`+13`), hotspot x/y
  (`+14`/`+15`, stored +8 in `$15CC`/`$15CE`). A negative head/arm y means "not drawn".
- Composition order: (1) **base part** (legs and torso; 69 records, 34 distinct graphics,
  32×40 to 48×72) copied plainly; (2) **head**, 16×14 masked part, 9 variants at
  `$61BD0`, tables g/x/y at `$B408`/`$B41A`/`$B42C`; (3) **arm with gun**, 32×32 masked
  part, 26 variants at `$62030`, tables at `$B43E`/`$B472`/`$B4A6`; (4) **muzzle flash**,
  16×16 masked, 4 frames at `$65230` (offsets `$B4DA`) while the counter `$16A0` runs, at
  (`$16A2`, `$16A4`). Head and arm variant d = (state & 1) × 4 + aim, aim =
  (`$15DA` & 6) >> 1 (up, diagonal up, horizontal, diagonal down); `$1676` ≠ 0 forces a
  special arm pose (variants 8–25: crouching, torso-held gun…). Masked parts are
  cookie-cut (minterm `$CA`).
- Screen position: x = 5 + `$15D0` − camera_x + hotspot_x, y = `$15D4` − camera_y +
  hotspot_y − 16 (`$15D0`/`$15D4` = player world position). The level-3 handler `$10266`
  turns them into SPRxPOS/CTL with HSTART = x and VSTART = y − 25 (`$102BA`). **[verified]**
- Against the play field: the display window starts at H `$90` (copper `$10332`), the
  bitplanes at line `$1E`, and map pixel X shows at H `$90` + X − camera_x (DDFSTRT `$38`,
  BPLCON1 = 15 − (camera_x & 15), first tile column camera_x >> 4). So the composition's top
  left sits at map (x + `$15CC` − 139, y + `$15CE` − 71). **[verified arithmetic; inferred
  that sprite HSTART and DIW share the same horizontal origin (±1 px)]**
- `tools/player.py` → `build/sprites/robocop.png` (base parts), `robocop_parts.png` (heads,
  arms, flashes) and `robocop_composed.png` (the 69 records × 4 aims as the game composes
  them).

### Player control (`$AFF8`, `$ACEC`, `$BDEC`) **[verified: code and execution bench]**

- `main_loop` order per game frame: `$F878` (palette fades), `$F76C` (keys, panel digits),
  **`$AFF8` player_move**, `$FA7C`, `$9150`, `$9C06` activate_objects, `$BCCA`
  draw_background, `$8B32` special objects (lifts), **`$ACEC` update_player**, **`$B94A`
  draw_player**, `$F3CE`, **`$BDEC` read_joystick**, `$C3E4` update_objects, `$F080`,
  `$F900`, `$89BE` energy can, `$BDCE`; then `$B00` += 1, `$B02` += 3.
- **Input.** `read_joystick` (`$BDEC`) runs once per game frame, late in it, so the logic
  sees the controls one frame later: JOY1DAT & `$303` → table `$BE26` (up 1, down 2, left 4,
  right 8 in `$802E`), fire from CIA-A PRA bit 7 (`$10`); with no joystick input `$802E`
  takes the keyboard byte `$802D`, which the level-2 handler `$101DC` keeps from the key
  codes `$40–$50` through the table `$10254` (cursor keys as the joystick; Space, Backspace,
  Tab, Return, Esc, Del… fire; F1 and right Shift `$20`; bit 7 set on any press). Nothing is
  read while `$804D` is set (start of a level, death).
- **Map attributes** (low 7 bits of the map words): bit 1 wall, bits 0/2 floor (bit 2: up
  there is turned into fire, and fire into states 12/13), bit 3 enemy spawn points (scanned
  by `update_objects` at `$C546` around `$B1A`). The player's cell is A0 = `$37FF2` +
  ((x & `$FFF0`) >> 3) + (y >> 4) × `$140`: the map starts 7 cells to the right of x = 0,
  so map pixel x = player x − 112.
- **The map changes at run time** (bench write watch on `$38000–$3BFC0`): map objects copy
  the words of their current look into the map, a block of (`$110`+1) × (`$112`+1) words
  per object, every time `activate_objects` handles them (`$9C76`, the copy at `$9CF0`;
  a negative look pointer = destroyed, `$F98C`). Level 1: `level_init`'s activation pass
  over the whole map (`$886E`) changes 59 words (platform looks, tiles only); the wall
  right of the start (columns 4–6, rows 46–49, x 176–223) is such an object: RoboCop's
  down + fire punches break it (tiles and attributes 2 → 0), which is the way out of the
  start area. The end of level 1 (`$DF6E`, object type 32) also writes map words from its
  own table. **[verified]**
- **States** (`$15E2`; odd = facing left): 0/1 walk, 2/3 stand, 4/5 jump/fall, 6/7 down +
  fire (asked through `$1696` for the next frame; at step 4 an effect of type 8 ahead of
  him), 8/9 crouch (holds step 4, turns with left/right, rises backwards with up), 10/11
  forced by the palette fade-in (left/right only, no fire), 12/13 fire on a bit-2 floor,
  14/15 up only (tall hitbox), 16 death. x step per state at `$B3F6` (±3 walking and
  jumping); per state at `$B3AE` [−, `$15DF`, `$15E4` (animation backwards), hitbox offset
  from `$B32C`: 3 boxes x, y, w, h = (12, −54, 24, 54), (10, −38, 38, 38), (12, −72, 24, 72)].
- **Movement.** A step is refused when the cell beside the start cell (the row above while
  vy < 0, i.e. standing or rising) has bit 1, whatever the position inside the cell. In the
  air y += vy >> 2 and vy += 2 up to `$1F`; on the ground vy = −`$14` (a jump's start).
  Landing needs vy ≥ 0 and a floor bit in the start cell (y snapped to the cell's top),
  then `$1678` = 1 delays the next jump; with no floor RoboCop falls from vy = 0. The lift
  check `$BD72` comes first: 4 lifts (left, right, top, dx, flag index at `$B3C–$B63`,
  written by the special objects), standing on one when left ≤ x < right and top − 15 < y ≤
  top (not rising): y = top − 4, x += dx, flag `$167A + index` set. `$1698` > 0 reverses
  left/right (and flashes the palette every 8 frames).
- **Animation.** `$15DC` counts up to `$15E8` (= steps − 1 of the state, set by
  `draw_player`) and wraps, or backwards when `$15E4` is set; a new state restarts it.
  The frame record is the counter / 2. State 6 (right punch: steps − 1 = 15, list offset
  `$328`) owns 7 records but reads 8: its last one (steps 14–15) is state 7's first (`$398` =
  `$328` + 7 × 16), the left punch's first drawing, so the right punch faces left for its last
  two game frames (a data slip). **[verified: REA read_bytes `$B4E2`]**
- **Left and right drawings** (measured from the data with `tools/msxsprites.py`'s
  `mirror_place`; a buffer pixel shows at screen x = 13 + `$15D0` − camera_x + the record's hot
  spot x + its buffer x): most left drawings are the exact mirror of the right ones about an
  axis of each animation (at hot spot x + buffer x = walk 20, stand 19.5, jump 15.5, punch
  18.5, first crouch step 17.5); the others
  differ in a few pixels (the arm of the up and up-diagonal aims, the punch's step 6, the
  crouch's last two steps, the up-only pose) and are placed about other axes (crouch steps 1–2:
  19.5 and 23.5, matching the crouch hit box). The left arm table has the diagonals the other
  way round (left aim 1 is the right's aim 3). The frontal poses (states 10–13) are the same
  drawings on both sides. The left punch's last steps and the left crouch's first step share
  one drawing whose right counterparts differ. **[measured]**
- **Camera.** camera_x += (x − `$108` − camera_x) >> 4, within 0..`$8E0`; camera_y += (t −
  camera_y) >> 3 with t = y − `$70`, or −`$60` when that is above `$38`, within 0..`$B08`
  (the level's lowest camera, header +28). `$108` and `$70` are immediates patched by
  `level_init` (`$880E`, `$8816`).
- **Start of a level** (`$15CA` clear): RoboCop stands (state 2, aim 4), `$804D` locks the
  controls and `$1676` = 8; from game frame `$1C` the arm poses 8 + n/2 for n = 0..36
  (`$15CB`), sound `$303` in `$B2E` when n & `$B` = 0, then `$15CA` is set: 65 game frames.
  Meanwhile `$F878` fades the palette in over 31 frames (`$16CD`, `$16CE`) and forces state
  `$A` (`$F89D`, patched by `level_init`; `$B` on the third level).
- **Aim** (`update_player`): with a direction held, `$15DA` = table `$ACDC`[joystick & 15]
  every third frame (`$1679`). The fire: see *RoboCop's fire* below.
- **Level start values** (header at `$8664`, 40 bytes per level): +16/+18 player and camera
  x/y (level 1: 144, 800), +28 `$B08` (640), +30 timer.
- Execution bench (`tools/amigaemu.py game`) traces of the original against the MSX port
  (`tools/tracecmp.py`): identical over 160 and 340 game frames of scripted input (walking
  into walls, jumps, landings, crouching and turning, rising, down + fire, diagonal aims),
  600 frames of fire (shots, hits, flashes, lifts), and 1832 frames of the level-1 coverage
  scenario with teleports and god mode (`--drive`, openMSX `rc2_drive_trace`).

### RoboCop's fire (`$ACEC` after the aim, `$ACBC`, `$AF08`, `$AF90`, `$BE48`) **[verified: code and bench traces]**

- Fire latch `$D78`: one shot per press; weapon 1 (rapid fire) clears it every 4 frames. On a
  floor with bit 2 (but in states 14/15) fire asks for state 12/13 and spawns the punch's hit
  box (type 8) 50 px above him with D7 = whatever `$8B32` left (0, or `6 & $168C`); its
  lifetime is 6 frames from direction 0, fewer from 2/4, none from 6 on.
- No shot in states 6, 7, 12, 13, 16, 17 (`$330C0`). D7 = ((state & 1) × 4 + (aim & 6) / 2) × 2
  (8 → 0); offsets `$AE52`/`$AE62` + 7 by D7, `$AE72`/`$AE92` by state. Weapons 1–3 use ammo
  (`$8030`, 4 BCD digits, `$AC9A`); with none: `set_weapon(0)` and update_player returns at
  once (`bra.w`: the shots do not move that frame). Weapon 2 adds shots at D7 ± 4 (sound 0Bh),
  weapon 3 alternates (`$16D6`) that with D7 ± 2, which leaves D7 two directions back (its
  muzzle flash turns: a bug). Sound 4 (`$B31`); muzzle flash `$6B9A0 + 50h × D7` (402h).
- `set_weapon` (`$FD30`): weapon `$805C`, ammo from `$FD52` (0, 500, 300, 400), panel icon
  from `$FD5A` (3, 0, 2, 1). Weapons: 1 rapid fire, 2 three-way gun, 3 scatter gun.
- 8 shot/effect slots (`$ACBC`: type, direction & 14, x, y at `$15F4`/`$1614`/`$1634`/`$1654`,
  next slot `$1692` & 14), handlers at `$AECA + type`: 4 = shot `$AF08` (16 px per frame by
  `$AEE8`/`$AEF8`; hit test at the old position; an enemy hit is pushed by dx / 4 and the shot
  ends with explosion 1; then the wall test (bit 1) of the cell 8 px left of it ends it with
  explosion 1 (a second one after a hit); its BOB `$6BEA0 + $AF76[D7]`, gone off screen),
  8 = punch box `$AF90`. Player_move `$AFC4` spawns the punch of states 6/7 at step 4
  (`$AFAE`: +48 / −16 px, 48 up, D7 = 0).
- Hit test `$BE48`: 10 collision slots (5 enemies at `$BC4 + 4k` and the 5 map-object slots
  after them), box [x − 8, x + w) × [y − 8, y + h) from the type's record (`$BEAA`/`$BEAC`);
  a hit sets the flash byte (+42h) and takes a hit point (+41h, when ≥ 0; below 0 the +23h
  byte is cleared).
- `bob_part`/`bob_part2` (`$AC44`/`$AC56`) test the flash byte at +22h of the slot (the
  object is drawn white and the byte cleared by its last part); `update_objects` sets the
  high byte of `$16BA` before each handler (`$C42E`).

### Collisions and pickups (`$FA7C`, `$F900`) **[verified: code and bench traces]**

- RoboCop's box = position + the state's hitbox (`$168E`). `$FA7C`, right after
  player_move: (1) the first 6 enemy bullets (of 8) by type tables `$FA35` width (negative:
  never hits), `$FA4C` height, `$FA63` damage — unless `$16BC`'s high byte is set (the death
  sequence past 64 frames, a bug): bullet gone, energy − damage, PAL_SHOT flash and, when the
  bullet was less than 50 px right of him, the hit spark (`$16A0` = 7 at `$16A2`/`$16A4`;
  both get the y value, the x is overwritten: a bug); (2) the first enemy whose box (no −8
  margins) overlaps: touch byte +23h set, PAL_ENEMYHIT flash, energy − 1; (3) pickups 3..0 not
  rising, box (x − 8, y − 8, 15 × 15): the first is taken (message `$FC12`[type] = HUD
  messages 11–20, sound `$FC0B`[type / 4], the vehicle's vy + 6.0 when riding `$16D8`) and its
  effect runs through `$FBE0 + type` (one per frame).
- Enemy bullet types by their callers (REA, the 28 calls of `ebullet_add` `$F5BC` with the D6
  set before each; 2026-10-22): the missile, types 1 and 2 (damage 40h, `$FA63`; 32 × 16,
  animated: frames `$54596`.. and `$50E46`..), comes only from `FUN_cc4a` (`$CD4A`: the kneeling
  of type 3, `$CCFA`) and `obj27_update` (`$D9F8`), D6 = 1 then + 1 facing the other way. The
  others: 3 (types 4, 12, 13, 15, 34-37, 41, 50, 51), 4 (14, 28), 5/6 (1, 2, 16, 21, 24, 26),
  7 and 17h (`FUN_dbea`, type 25's machine), 8 (29), 9/10 (22), 11h (40, never hits: width
  negative), 0Bh-0Eh (the helper `$C398` of the switch at `$C42A`, no damage) and 16h (33).
  **[Corrected 2026-11-01 by a byte read of the three RAM images: `$FA35`[11h] is 08 (an 8 × 8 box)
  and `$FA63`[11h] 40h, so type 40's bullet 11h hits (level 3's rocket, types 40 and 42:
  `docs/LEVEL3.md` 2.6); 12h's width is 9Dh (never hits); 17h lies past the 23-entry tables, its
  width the height table's first byte, 9Dh: never hits.]**
- Pickup effects: 4 scatter gun (weapon 3), 8 rapid fire (1), 12 time − 1 minute (00:00 at
  the bottom), 16 time + 1 minute, 20 reversed controls (100h frames, or off), 24 shield
  (`$16AA` = 100h), 28 energy full (102h), 32 three-way gun (2), 36/40 nuke retrieved (energy
  + 20h, `$16C0` + 1, key code 21h in `$8032` so frame_keys shows the counts).
- `$F900`: 4 pickup slots (type `$D80 + k`, x `$D84`, y / vy longs `$D94` / `$DA4`): y += vy;
  rising above y 4 it bounces; vy + 0.2800h; on a solid cell at y + 15 (`$EF8E`) vy = 0 and it
  is drawn on the cell's top; BOB `$F964`[type] (402h). Type 40's graphics long is the code at
  `$F98C` (garbage).
- `draw_player` counts the hit spark `$16A0` down.

### Special objects (`$8B32`) **[verified: code and bench traces]**

- The level's list (header +8; level 1 `$8FC0`: 6 lifts then the vehicle; records in the code
  area, changed at run time: handler offset, x, y long, path index, path of y values). Each
  runs with D0 = x, D1 = y, the lifts' table entry `$B4C + (6 & $168C)` and the flag
  `$167A + n`. Right/top/dx of the 4 entries are cleared first.
- Lift (`$8DE6`): at its path point it takes the next one (or with RoboCop on it the previous
  for up, the next for down; the index stays within the path), then moves 2 px towards it;
  seen by the camera: sound 0Ah every 4th moving frame, RoboCop on it asks for state 10 (y =
  top − 4 in state 10), table entry (left, right = x + 30h, top, flag index), BOB `$4B68A`
  (48 × 24 at x + 22h, y − 12) unless `level_number` (`$8050`) = 2: the third level's lift is
  two parts, `$5397C` (32 × 29 at x + 20h, y − 52h) and `$53BC0` (32 × 16, 78 px lower)
  (`$8EB0`). In level 1 those addresses hold other SPERMA graphics (the level-3 data is not
  loaded), and the level-1 execution bench never draws them. **[verified: REA, bench]**
- Hostage (`obj45_update` `$ED1E`): legs `$4B31C` (32 × 20 at x + 8, y + 1Bh), then the body,
  one of 8 frames of 48 × 28 from `$498DC` (step `$348`) by game_frame & 1Eh through the table
  at `$EDE2` (0–7 then 7–0: a ping-pong, 2 game frames each) with dy from `$EE02` (frames 0–4:
  +4, frames 5–7: 0). **[verified: REA]**
- Vehicle (`$8B9E`, level 1, x 440h–4DFh): vx `$D7A`, vy long `$D7C`; ridden it carries
  RoboCop (x + 12h, y − 4, `$16D8`), rises, takes the joystick from player_move by patching
  its `moveq #$7F` immediate at `$B02B` to 0, and patches the state RoboCop shows (`$8C98`: 2
  or 3); alone it returns to x 480h. D7 at the end of `$8B32` reaches `update_player`.

### Level hazards (`$9150`, `level_tick_0` `$933A`) **[verified: code and bench traces]**

- The list's address is the header's long at +4 (level 1 `$9538`, 15 electric beams; the RAM
  image's `$915E` immediate holds level 2's `$95B2` until `level_init` patches it). Records
  inside the camera window run `$91B0 + 4 × level`.
- Level 1 beams: 16 frames on / 16 off (`$B00` & 10h). On: RoboCop in [x − 16, x) × [y, y +
  (rows + 2) × 16] loses 10h energy, PAL `$10074` flash, sound 22h (`$B30`); the beam's map
  cells are rewritten every frame (top `$93CA`[random & 6], body `$93D2`[(random + x + 2n) &
  3Eh]); off: E800h and D00h.

### Random word (`$BDCE`) **[verified]**

- Every game frame (last in main_loop): `$B32` rotated left by CIA-A timer A's low byte and
  XORed with timer B. The execution bench returns FFh for these reads (rotate 63, XOR FFFFh);
  the MSX test builds do the same.

### Palette effects (`$F878`, `$F8C4`, `$F80E`) **[verified: code; MSX traces of the fade and flashes]**

- The copper's colours (`$104A4` + 4n: COLOR01-31) have two writers. The fade (`$F878`: `$16CE`
  set = in, `$16CD` up to 1Fh, state 10 forced on every step; clear = out, `$16CD` down to 0)
  recomputes all 31 on every step from the level palette (the immediate at `$F8C6`, `$FFF6`
  for level 1) with each 4-bit component at most (`$16CD` >> 1) & 1Eh: eight steps of four
  frames, 0..Eh (a component F stays E after a fade in).
- A flash (`$F80E`, A0 = 15 colours) sets `$F826` = 4 and writes COLOR17-31, RoboCop's sprite
  colours, at once (`$F816`); `$F878` counts it down and at 0 writes COLOR17-31 from `$10016`
  (`$FFF6` + 32, level 1's), then idles at -1: RoboCop shows the tint for 5 game frames. The
  palettes: `$100B0` an enemy touches him, `$10092` an enemy shot, `$100CE` an electric
  barrier, `$100EC` energy refill, `$10074` a level-1 beam, `$1010A` reversed controls
  (`player_move` `$B030`: every 8th frame while `$1698` runs).
- The panel's colours are separate copper moves (`$103FA`): fades and flashes leave it alone.

### Hit spark (`$16A0`) **[verified: code (xrefs: only `$FA7C` and `draw_player`)]**

- `$FA7C` sets `$16A0` = 7 when an enemy bullet less than 50 px right of RoboCop hits him,
  with `$16A2` = `$16A4` = bullet y + 3Ch − his y clamped to 0..32h (the x written first is
  overwritten by the y).
- `draw_player` (`$BB78`), while `$16A0` ≠ 0: counts it down and cuts a 16 × 16 frame (mask +
  4 planes) from `$65230` + the word at `$B4DA` + (`$16A0` & 0Eh) into RoboCop's buffer at word
  `$16A2` >> 4, line `$16A4` (cookie-cut, so in his sprite colours, in front of him).

### Timer and death **[verified: code; the death sequence: code only]**

- The CIA-B interrupt (`$1015E`), once a second unless paused: `$804B` seconds − 1 (BCD), at
  the bottom `$804A` minutes − 1 and seconds 59; below 0:00 `$804C` is set (time out).
- `en_update` (`$89BE`): the shown energy below 0 sets `$16CC` (dying). main_loop: `$804C`
  with `$16CC` clear shows message `$865A` and sets `$16CC`; while `$16CC`: state 16 asked,
  controls locked, `$16BC` += 4; below 60h explosions around him (table `$81C2`), then the
  head icons (`$88DE`) and the fade out; lives `$8034` − 1 → `level_init` again, or game over.
- Level end (`$16D0`, set by type 32): score + 100h a frame (sound 26h every 4th), `$16C4`
  counts down, fade out, `$8050` + 1, the next level loads.
- Neither the CIA-B interrupt nor main_loop's time-out test (`$816E`-`$8184`) looks at
  `$16D0`: the timer keeps running through type 32's sequence and a time out during it sets
  `$16CC`. main_loop then runs both branches each frame (the level end's at `$8188` first,
  the death's at `$822A`), and the first fade out to finish decides: the death's starts once
  `$16BC` reaches 100h (64 frames after `$16CC`), the level end's once `$16C4` is below 0 (40h
  frames after `$16D0`), so a time out before or early in the count ends the life instead of
  the level **[verified: code, REA]**. Seen in the port (2026-10-25, openMSX FS-A1GT, test8):
  the ten henchmen down, the explosions under way, the timer at 0:00 (replay: 10,963.7 s),
  `$16CC`, a life less and the level from its start; the port's frame.asm matches main_loop
  here, and test builds with a script never see it (their timer stands still).
- **Type 32, the level's end** (`obj32_update` `$DF6E`; level 1: spawn list entry 13 at
  `$96DC`, x 2432, y 736, once, when the camera is at x 2001-2272, y 568-640) **[verified:
  code; bench and MSX traces]**: the camera offsets become 80h / −30h and RoboCop's y at least
  2D0h; on its first frame it stores `$16C2` + 10 and until that many henchmen died it forces
  the spawns (`$16B8` = 0, marker mask `$C53D` = 0). The `cmpi.w #$A,$16C0` (ten nukes) result
  is overwritten by the next MOVE: the nukes are not required. Then energy full, one of the 36
  map words of `$DE68` every 4 frames (explosion 5 on odd frames), explosions, controls locked;
  at (A3) >> 2 = 44h (272 frames) `$16D0` set and `$16C4` = 40h. `main_loop` `$8188` adds 100
  points a frame for 65 frames, fades out, `$8050` + 1 (`$81B8`), then `$80AE` `level_init`:
  `load_level1` `$8582` (statistics, Brainstorm, shooting range, briefing, PIC4, MU1, MADEX and
  DATAL2). Bench: with `$16C2` poked to 10 after type 32's first frame, `$16D0` at game frame
  472, the statistics at 567. Test aid: the bench's and the MSX drive's god mode keep `$16C4`
  at 100h, so the level never ends with it.
- **The cracked wall** (`obj_relocate` `$9FC4`; level 1 object list entry 25 at `$A68E`: type
  5Ch, x 2064, y 256, looks `$A272`: `$A532` cracked, `$A54A` hole, −1; reached by falling
  through trapdoor entry 21 at `$A65E`, type 48h, `act_floor_switch` `$9F84`, into a closed
  room, cols 116-125 × rows 16-19) **[verified: code; bench]**: `activate_objects` runs it every
  frame while the entry is in its window; in states 12/13 (up or fire on a floor with
  attribute bit 2) debris (explosion type 0 via `$F366`) and `$169E` + 1; at 50h (3.2 s)
  RoboCop and the camera (`move.l`) go to `$15D6`/`$15D8`, which then become 90h/50h, state 10h
  is asked, `$16CD` = 0 (black), `$169E` = 0, `$16CE` set (fade in) and the entry is switched
  on (`st 4(A1)`). `level_init` writes `$15D6`/`$15D8` from the level header +20/+22 at
  `$87A4`/`$87A8` (after `clear_game_vars`): level 1 (996, 640), level 2 (192, 112), level 3
  (224, 544). Nothing else is reset. Bench (`--tele 100:2072:320 --joy 110:300:u --god`): the
  relocation at game frame 191, RoboCop at map column 55, row 40 (the hole graphic), the camera
  easing to (760, 528) by frame 224, control back at 224. A death puts every object list entry
  but type 58h back to look 0 / 4 hits (`$16CF`, set at `$8742`, is cleared by
  `clear_game_vars` before `$8852` reads it): door, trapdoor and wall come back.
- **Route of level 1** (map 160 × 51 cells; player column = (x >> 4) − 7, row = y >> 4;
  checked link by link with bench drives, route picture by the agent run of 2026-10-21)
  **[verified: bench; the order inferred from walls and floors]**: A start outside (door
  entry 40) → B lower-left building (lifts L0, L5) → C outdoor gap (the flying vehicle, type 44
  dropping pickups) → D middle building (lifts L2, L3, beams, barriers, trapdoors) → E the
  cracked wall's room → relocation → F upper-left building (lift L1; a jump from the row-12
  platform lands on row 10) → G the corridor between floors 5 and 10 (beams, barriers, crates,
  drums, type 25 the machine) → H the lab building (entered through the row-10 gaps at columns
  142-144 or 148-150; lift L4) → I the lab floor, type 32. Camera limits are global (x 0-8E0h,
  y 0-280h): only types 44 and 32 change its offsets.
- `level_init` after a death runs `clear_game_vars` (`$FE96`): `$B00-$16EB` cleared, and also
  `$802D`, `$802E` (keyboard and joystick bytes), `$804D` (input lock), `$B02B` = 7Fh (the
  joystick mask), `$B16` = `$6FFA0`. **[verified: code; MSX death trace]**
- Game over (`$82A8`, `$8034` below 0): `show_picture` D0 = 8 (PIC9), 128 VBLs, `$12082`
  (the score as 8 characters (+5Bh) against the last of the **6** high-score entries (13h
  bytes each); when higher: a name is entered (`$12300`, `$1215C`) and the table sorted),
  `$11FD2` (continue offer); fire held: `$FFD8` (two lives) and `level_init` (the same level,
  score kept: a continue); else `$8098`: `$FEDA`, `clear_game_vars`, `$10884`, `$FFC4`,
  `level_init`. Details in section 5. **[verified: code]**

### Enemy types of level 1 **[verified: code; bench traces for 3, 28-31, 45]**

- 3 (`$CB6E`) walker2 with a torso; far from RoboCop it kneels every 16 steps. 12 (`$CEF8`)
  gunner behind cover, its gun by RoboCop's 32-px column, fires when (`$B02` & 2Eh) = 0. 13
  (`$CE72`) standing gunner, fires every 8th frame when in RoboCop's column. 23 (`$DD04`) rail
  crawler: finds a cell with attribute bit 5 near the camera and follows that rail at 4 px per
  frame. 25 (`$DB70`) the machine at the top (only with the camera at y < 20h): fires, drawn
  normal / black / white by frame; RoboCop touching it refills the energy. 26 (`$DAFA`)
  kneeling gunner. 27 (`$D9A4`) walker that stops to fire bursts with recoil and smoke. 32
  (`$DF6E`) the end of level 1 (10 more henchmen, then the destruction sequence `$DE68`).
  44 (`$EC22`) drops random pickups from the sky while RoboCop rides the vehicle.

### Enemy spawning (inside `update_objects`) **[verified]**

- Per-level lists (pointer in `$B0E`): `$9626`, `$97B0`, `$99E2`; 14-byte entries: x (`+0`),
  **type** (`+4`), flags (`+7`, bit 7 = spawn at the screen edge), respawn reload/counter.
- Types per level: level 1 = 4, 12, 23, 25, 26, 28, 32, 44, 45; level 2 = 1, 2, 4, 5, 6, 12,
  13, 14, 45, 49; level 3 = 21, 22, 33, 35, 36, 38–43, 47, 48, 50, 52. Types missing from the
  lists are spawned by other objects (shots, boss parts…).
- Per-level special objects (list in `$8B54`, dispatched by the table at `$8B92`):
  `$8DE6` (lifts, every level), `$8F02` (level 2), `$8B9E` (vehicle, level 1).

### Sprite catalogue **[verified: format; levels from code]**

- `make sprites`: Ghidra assembly exported with the REA CLI (`tools/rea_dump_asm.sh`) →
  `tools/bobcatalog.py` follows A2/D4 up to every call to `draw_bob` and its wrappers
  (`$AC44`, `$AC56`, `$AC6E`, `$AC84`), enumerates frames (adjustments, word tables and, since
  2026-10-21, tables of pointers read with `movea.l (d,PC,Dn),A2`) and assigns the level from code
  (spawn lists, special objects, common PERMA/SPERMA).
- 81 references (4 hard-coded from REA since 2026-10-21, see below); unique frames: 22 common, 39 (level 1), 41 (level 2), 60 (level 3) before the
  pickups' table was read; mostly between 16×16 and 48×56, bosses up to 80×48. 17 references of
  "child" objects still have an inferred level. Sheets in `build/sprites/<level>_<routine>.png`.
- **Pickups** **[verified, REA]**: `$F900` (pickup update) draws each of its four slots
  (`$D80+k` type, `$D84` x, `$D94` y, `$DA4` vy) with D4 = `$402` (16×16) and A2 = the long at
  `$F964 + type` (`movea.l ($F964,PC,D2.w),A2` at `$F958`): type 4 scatter gun `$6D520`, 8 rapid
  fire `$6D5C0`, 12 time −1 min `$6D660`, 16 time +1 min `$6D700`, 20 reversed controls
  `$6D7A0`, 24 shield `$6D840`, 28 energy `$6D8E0`, 32 three-way gun `$6D980`, 36 nuke `$4B4AC`
  (type 0: no pickup; the long after type 36 is code). The flying vehicle's ride drops types
  4-32 (type 44, `obj44_update` `$EC22`, through `pickup_drop` `$F98C`); taking one while riding
  knocks the vehicle down (`$FBCC`). Until the table was read, five of them had no MSX frame
  and were invisible on the MSX while still hitting RoboCop.
- Draw calls the catalogue still cannot follow (their frames come only from the bench's
  coverage, `--drawn`): `$10750`, `$C992`, `$CBA6` (obj03), `$D178` (obj05), `$D946` (obj29),
  `$E246` (obj34), `$F12A` (`$F080`), `$F292` and `$F2B6` (`$F266`), `$F488` (`$F3CE`, enemy
  bullets); `bobcatalog.py catalog` lists them. Read with REA (agent run, 2026-10-21): their
  parallel tables are BLTSIZE[T + 2i] beside gfx[T + d + 4i]. `$D178` is level 2's, `$E246`
  level 3's, `$10750` the title logo's. Five level-1 groups were in neither the catalogue nor
  the coverage, so the MSX hid them: the muzzle smoke type 3 (`$54096`, `$541D6`, `$54316`,
  `$54456`, 32 × 16, the mirror of type 2: the enemies of types 3 and 27 left of RoboCop) and
  type 2's rare first step `$50946` (`$F12A`); enemy bullet type 1 (`$54596`, `$54816`,
  `$54956`: the rightward shots of types 3 and 27, damage 40h, invisible on 3 of 4 steps) and
  type 7 (`$40660`, 16 × 8, the machine type 25's) (`$F488`); type 25's muzzle flash (`$3F940`,
  `$3FC10`, 48 × 24, `$DC3A` in `$DBEA`). `bobcatalog.py` `HARD_REFS` now lists them.
  Explosion types (`$F366`: D5 low byte 0-8, frames `$F3BC`/`$F3C5`; high byte 0 drawn by
  `$F12A`, 4 by `$F266`): level 1 spawns 0-5 and `$0408`. `$F366` allocates 8 slots from slot
  7 down but `$F080` processes slots 0-5 only (`cmpa.w #$D3A`): the first two explosions after
  each `clear_game_vars` are never drawn and stay (an original bug, kept). `update_objects` also
  spawns from the level's marker table (header +24: level 1 `$C59C`), which adds types 3, 13,
  15, 24, 27, 29, 30 and 31 to level 1.

### Per-level loading (`$86FA`) **[verified]**

| Level | Files | Before the level |
|---|---|---|
| 1 | DATAL1 (+ resident SPERMA/PERMA) | briefing and PIC1 |
| 2 | MADEX at `$45250` + DATAL2 | statistics, 2 bonus stages, the briefing `$110F0`, PIC4 |
| 3 | DATAL3 (overwrites MADEX and SPERMA) | statistics, 2 bonus stages, the briefing `$110B4`, PIC7 |

The level's sound file (`MU1`, with its player code) is loaded at `$18000` by the level start
(`$8614`, then `jmp $18000`); it holds sound effects only (see below).

### Level 2: the Tokugawa brewery **[verified: REA (Ghidra 12.1.4, raw-binary m68k, entry `0x0`, `analysis/ghidra_seeds.tsv`) on `build/ram/level2_full.bin`; data compares; bench runs of the original; inferences marked]**

Sources: the five level-2 area reports and the level-2 plan of 2026-10-27 (REA listings, byte reads,
bench runs); the items marked *REA 10-28* were read again on 2026-10-28. Names:
`analysis/main_8000.sym`, whose level numbers count from 0 as `$8050` does (`spawnlist_level1`,
`special_l1`, `level_tick_1` are level 2's).

- **The image.** `make ram` builds `build/ram/level2_full.bin` (RB1, MU1, DATAL2, MADEX, SPERMA,
  PERMA; sha256 `a039a158…0a88b09`). The main code `$8000-$125FF` is byte-identical in
  `level1_full.bin` and `level2_full.bin` (the first difference is at `$28089`), so the main code's
  names and seeds serve both. Seeds (116 functions, 285 labels): REA creates 115 functions, finds 1
  present and applies the 285 labels, 0 failed (*REA 10-28*). Level 2 needs four `+entry` seeds:
  `$C91A` (type 2's tail, reached only through a pushed return address) and `$D1CA`, `$D1D0`,
  `$D1DE` (type 6's waiting paths, reached by branches Ghidra does not follow). Without `$C91A`,
  REA's xrefs of `$16D0` miss the arrest; with it they are `$8158`, `$8188`, `$C29A`, `$C936`,
  `$DFDA`, `$DFE6` (*REA 10-28*).
- **MADEX is DATAL1's tail** **[verified: data compare, 2026-10-28]**: `MADEX_17.bin` (25,340 bytes)
  equals `DATAL1_10.bin[1D250h:]`. DATAL1 spans `$28000-$4B54B`, so MADEX restores `$45250-$4B54B`:
  the explosions, the smoke, the hostage and the nuke that levels 1 and 2 share. DATAL2 (105,816
  bytes) covers `$28000-$41D57`: the tile sheet `$28000-$37FFF` (512 × 128 bytes), the map
  `$38000-$3BE7F` (160 × 50 words) and level 2's own BOBs `$3BE80-$41D57` (type 5 `$3BFC0`, 6
  `$3C920`, 2 `$3D280`, 14 `$3DFA0`, 1's legs `$3E810`, 16's body `$40818`, 49 `$41358`). Both are
  in the image where the loader puts them. Why MADEX is loaded again **[inferred]**: the shooting
  range's decrunch (`$1EA00-$485D9`, both visits) overwrote that range.
- **The way in** (`load_level1` `$8582`) **[verified: REA listing; bench]**: `clr.b $8580`
  (`datal1_resident`), the statistics `$85D8`, Brainstorm `$8382` (D0 = 2), the range `$8420` (D0 =
  1), `moveq #2,D0` and three `nop`s (a removed 6-byte call **[inferred: the disk-2 prompt]**), the
  level-2 briefing `$110F0` ("TOKUGAWA BREWERY", then "ARREST CAIN") through `text_screen_stop`
  `$10762`, PIC4 (`$11E06`, D0 = 3), `move #$2700,SR`, `load_level_music` `$8614` (MU1: init, no
  tune), MADEX (name `$8579`) at `$45250` and DATAL2 (name `$1012F`) at `$28000`, both PP20; the
  last load is a tail jump into the loader, which returns into `level_init` at `$8764`. The way out
  (`load_level2` `$8524`): the statistics, `moveq #2,D0` and three `nop`s, `clr.b $857F`
  (`sperma_resident`: DATAL3 overwrites SPERMA), Brainstorm (D0 = 4), the range (D0 = 5), the
  level-3 briefing `$110B4`, PIC7 (D0 = 6), MU1, DATAL3.
- **The load table** `$86FA` (8 × `bra.w`, *REA 10-28*): 0 `$8352` `restart_level0`; **1 and 2
  `$86DC`, an `rts`** (`restart_level12`: levels 2 and 3 again after a death or a continue: no
  briefing, no picture, nothing reloaded, so DATAL2's map keeps every cell written since the load;
  `level_init` resets only the object list's entries); 3 and 7 `$86DE`
  (`level_load_3`, the game completed: script `$112C5`, `$11C54` (PICF, CMP), `high_score_entry`,
  `bra $8090`); 4, 5, 6 `load_level0` `$82EC`, `load_level1` `$8582`, `load_level2` `$8524`.
  `level_init` takes entry `$8050` for a restart and `$8050` + 4 for a load (then `$8052` =
  `$8050`).
- **The headers** `$8664` + 40 × `$8050`, copied by `level_init` `$871A` into the code and the
  variables (*REA 10-28*, every field):

| Offset | Goes to | Level 1 `$8664` | **Level 2 `$868C`** | Level 3 `$86B4` |
|---|---|---|---|---|
| +0 | `$9C18` object list | `$A562` | **`$A828`** | `$AA3A` |
| +4 | `$915E` hazard list | `$9538` | **`$95B2`** | `$95EC` |
| +8 | `$8B54` special objects | `$8FC0` | **`$8FE0`** | `$9008` |
| +12 | `$B0E` spawn list | `$9626` | **`$97B0`** | `$99E2` |
| +16, +18 | `$15D0`/`$B04`, `$15D4`/`$B06`: the start (RoboCop and the camera) | (144, 800) | **(352, 784)** | (1184, 784) |
| +20, +22 | `$15D6`, `$15D8`: `obj_relocate`'s target | (996, 640) | **(192, 112)** | (224, 544) |
| +24 | `$C598`, `$C692` marker table | `$C59C` | **`$C5EC`** | `$C624` |
| +28 | `$B08` the camera's lowest y | 640 | **624** (50 rows × 16 − 176) | 624 |
| +30 | `$804A` timer (BCD) | 10:00 | **7:30** | 7:30 |
| +32 | `$16B8` spawn delay | 5Ah | **2Eh** | 3Ch |
| +34 | `$C53D` marker mask (byte) | 7 | **7** | 3 |
| +36 | `$F8C6`, `$F8BC` palette (the fade's source) | `$FFF6` | **`$10036`** | `$10036` |

- **Level 2's lists** (in the main code: the same bytes in every image) **[verified: the reports'
  REA reads; the bench's coverage]**:
  - spawn list `$97B0`: 40 entries of 14 bytes (x, y, type +4, flags +7, reload +8, count +10,
    spawned +12), the end word at `$99E0`: 10 hostages (type 45, flags 40h: once), 2 × type 1 (C0h:
    once, at the screen's edge), 6 × 49 at y 16, 9 × 5 at y 368, one 6 at (416, 448), **the
    suspect, type 2, at (384, 56)** on the roof, one 14 at (320, 77), then 2 × 4, 3 × 12 and 5 × 13
    along the top corridor;
  - object list `$A828`: 44 entries of 12 bytes: 4 mines (map type 30h, activator 0Ch `act_0c`
    `$9EE8`), the relocation object (34h, activator 10h `obj_relocate`, to the header's (192,
    112)), 7 shootable blocks with pickups (`$9C76`), 16 trapdoors (`$9F84`) and 16 crates that
    explode at look 4 (`$9EA4`); together they can change 289 map cells; no conveyor, barrier or
    beam. `act_0c` rewrites the word `$A4A6` of the mine's look every frame (E680h, or 9700h while
    game-frame bit 2 is clear: one cell blinks); RoboCop on a mine explodes it (4 explosions of
    type 0 that do not hurt; no pickup);
  - special objects `$8FE0`: 9 record pointers (records `$9088-$911D`, in the code area: they keep
    moving across deaths): 5 lifts (handler 0, `$8DE6`) and 4 trolleys (handler 4, `special_l1`
    `$8F02`) that shuttle 2 px a frame over vats 0-3; RoboCop hangs under one in states 14/15, and
    its BOB (`$4B95A`, 32 × 47) leaves D7 = BCh for `update_player`;
  - markers `$C5EC`: types 3, 4, 12, 13, 14, 15, 16, 30, 31;
  - hazards `$95B2`: the 7 vats (below).
- **The arrest, level 2's end** **[verified: REA listings and the decompile of `$C91A` (*REA
  10-28*); bench]**. Type 2 (`obj02_update` `$C868`), the armed suspect the briefing calls Cain,
  stays at x 180h on the roof, queues "ARREST ARMED EMEMY." (`$DC76`) every 64th game frame, writes
  `$B2D8` (`player_move`'s camera offset immediate) = 500h every frame, so the camera stays at x 0,
  fires bursts of bullet type 5 from its counter's 46h on, and is drawn white 8 frames in 16
  (`$C90E`). Its tail `obj02_arrest` `$C91A` (pushed by `pea` at `$C90A`) sets its hit points
  (+21h) back to 4 every frame; when RoboCop touches it (+23h): "ARREST SUCESSFUL." (`$DC8A`, the
  original's spelling), effect 21h (`$B2C`), `$16D0` set at `$C936`, `$16C4` = 40h and D0 = −1
  (the slot freed). Then as in level 1 (`main_loop` `$8188`): the bonus count, the fade, `$8050` +
  1 = 2 at `$81B8`, `level_init` and load-table entry 6. There is no boss fight. Five hits in one
  frame would still kill it: `$C2D8` (energy − 30h, "SUSPECT DESTROYED.", the big explosion) and
  no level end until its spawn entry brings it back **[inferred: the respawn]**. "CAIN
  DESTROYED." (`$C24B`) is level 3's: type 22's death `$C25C`, which also sets `$16D0`.
- **`$8060`, the enemies' hit-point table** (*REA 10-28*: written at `$8314`, `$8482`, `$84FC`,
  read at `$C512`, `$C706`): `load_level0` sets SHARP (`$C716`) at `$8314`; the shooting range sets
  POOR on a time out (`$8482`) or the rating's table (`$84FC`). `new_game_vars` `$FFC4` writes
  `$8050` = 0, `$805E` = 0 and the score, never `$8052` or `$8060`. So every game plays level 1 with
  SHARP and level 2 with the range's table, across deaths and continues **[verified: bench, the
  four ratings: type 1 spawns with 2, 3, 3 or 4 hit points]**.
- **`$805E`, the credits** (*REA 10-28*: its only references are `$83FA`, `$FFCC`, `$11FD2`,
  `$11FEE`): + 1 per solved Brainstorm (`$83FA`), 0 at a new game (`clr.w` at `$FFCC`), − 1 by
  `continue_offer` `$11FD2` (`subq.w #1`; still ≥ 0: `load_level_music` and `text_screen` `$11590`,
  "YOU HAVE A GAME CREDIT."). When it went negative, `$11FE8` clears the joystick byte `$802E` and
  **`$11FEE` `clr.b $805E` clears only the high byte: the word reads 00FFh** until the next new
  game; nothing reads it in between (the title follows). Level 1's game over always finds 0 (the
  first Brainstorm comes after level 1), so the offer can first appear in level 2 **[verified:
  bench, level 2 again at row 109 with 2 lives and `$805E` = 0]**.
- **The vats** (`level_tick_1` `$91BC`; *REA 10-28*: the records, the column loop `$9230-$9276`,
  the tables and the copper bytes). `$9150` clears `$15F0` (`clr.w`) and sets the copper byte
  `$10356` to CAh every frame, then runs `$91B0` + 4 × `$8050` for each record in the camera
  window (y in [cam y − 64h, cam y + ACh), x1 ≥ cam x + 73h, x0 < cam x + 1A0h):

| Vat | x | y | Rows | Cells (columns × rows + 2) | First cell (row, column) |
|---|---|---|---|---|---|
| 0 | 848-1024 | 640 | 7 | 12 × 9 = 108 | (40, 45) |
| 1 | 1296-1440 | 640 | 7 | 10 × 9 = 90 | (40, 73) |
| 2 | 1568-1712 | 640 | 7 | 10 × 9 = 90 | (40, 90) |
| 3 | 2016-2256 | 688 | 4 | 16 × 6 = 96 | (43, 118) |
| 4 | 1904-2240 | 288 | 2 | 22 × 4 = 88 | (18, 111) |
| 5 | 1264-1568 | 288 | 2 | 20 × 4 = 80 | (18, 71) |
| 6 | 608-800 | 288 | 2 | 13 × 4 = 52 | (18, 30) |

  - Every frame: effect 1Ah when (random & Fh) = 0; with RoboCop's x in [x0 − 10h, x1 + 10h) and d =
    cam y + 98h − y in [0, 4Dh), `$10356` = CBh − d: the copper's WAIT (`CA01 FFFE` at `$10356`)
    before `MOVE 0020h,DMACON` (`$1035A`, sprite DMA off, then the eight sprites' control words
    cleared), so RoboCop's sprites end at the liquid's surface; from d = 3Ch (line < 90h) RoboCop
    dies (`$169A` high byte and `$16CC` set, effect 10h). The death depends on the camera's y, not
    RoboCop's, and holds in god mode.
  - Odd frames only: for each of the (x1 − x0) / 16 + 1 columns, when the byte `$15F0` is clear
    (`tst.b` at `$9236`) the phase's low byte + 2 (`addq.b` at `$923C`, the phases' only writer);
    d = (phase & 0Eh) + 10h when the next phase word's high byte is set; the column's first cell
    gets `$927A`[d / 2], the next rows alternate `$929A`[d / 2] and `$92BA`[d / 2]; after the
    columns `st $15F0` (`$9272`). So only the first in-window vat's phases advance.
  - The phase words `$92DA` (48 words up to `$9339`, `level_tick_0`'s start; the vats read the first
    23) live in the code area and are never reset. The three tables hold 16 map words each, all
    with attributes 0: **the vats change tiles only, never anything the logic reads**. 604 cells
    in all, at map rows 18-21 and 40-48, none shared with a map object **[verified: the map
    report's data checks]**.
- **`$EF8E`** (`obj_map_cell`, *REA 10-28*): `$EFA4` `cmpi.w #$66,D6` (D6 = row × 2): it looks up
  `map_row_offsets` for rows 0-50 in every level, a constant. Level 2's map has 50 rows, so its row
  50 is DATAL2's BOB data after the map (`$3BE80`): 35 of those 160 words have a nonzero low nibble
  **[verified: data, 2026-10-28]**, attribute bits that `$EF8E`'s callers take for walls and
  floors (in level 1 row 50 is a map row).
- **Type 6's death** `$C33E` (*REA 10-28*): `$15F2` + 1, D5 = `$15F2` & 3; when D5 = 0 (every 4th)
  a pickup at the object through `pickup_drop` (24h, a nuke; 1Ch, energy, at the 16th); then
  `$C35A`, which clears D5 first (`moveq #0,D5`, *REA bytes 10-28*): the explosion is always type 0.
  `pickup_drop` leaves D1's low word 0 (`swap D1`, `clr.w D1`), so after a pickup the explosion
  comes at y 0 **[verified: the MSX port's explosion slots equal the bench's over `barrel`'s 17
  kills, level 2's step 9]**. Its launch gap `$D1DC` is a code-area word: kept across lives, levels
  and games.
- **The homing flight** `$E728` (types 38 and 49, *REA 10-28*): x and y move by half a step of
  `homing_dx`/`homing_dy` with `ext.l`, `swap`, `asr.l #1`, so a negative step carries its sign
  word FFFFh into the low word before the shift and moves a little less than half (-9: FFFB.FFFFh,
  -4 - 1/65536) **[verified: the drone traces of level 2's step 9 differ in 380 of 401 rows with a
  plain half step, 0 with this one]**.
- **What the port's steps found** (2026-10-28 to 2026-10-31; `docs/level2/HANDOFF.md`):
  - **Type 1's leftover registers** **[verified: bench, 16 references and four new drives]**: facing
    left it fires bullet type D6 with direction 10h, and `$EF42` leaves D6 = 2 (an upward missile)
    only on a turn at a wall above its walkway. Both type-1 walkways of level 2 end at edges (entry
    10: x 271-531; entry 11: x 319-931), where D6 is 0, so **the upward missile never occurs in level
    2**: every left-facing shot writes a bullet slot that stays free (`t1left`: 15 such shots).
  - **The shot drone** **[verified: bench, `drone`]**: `$C35A` is entered with D5 = 0198h (its
    descriptor's offset), but clears D5 before `spawn_explosion` (`$F366`): the explosion is a normal
    type 0 and the frames E6h-41h are never read.
  - **The suspect's five-hit kill is out of reach** **[verified: bench, 126 runs]**: with the
    three-way and scatter guns at the roof, firing every 2-4 frames or walking in while firing, at
    most 3 hits land in one frame (one shot's three bullets); `$C2D8` is never reached and walking in
    ends in the arrest. The respawn after such a kill stays **[inferred]**.
  - `act_0c` acts on every frame RoboCop stands in the mine's cell: 5 frames in `mine`, 4 explosion
    requests each **[verified: bench]**.
  - A level-2 start ignores the controls for about 65 frames **[verified: bench]**.
  - Type 6's byte 2 is the draw's D0 low byte: when the tyre is not drawn it holds `$16BA`'s low byte,
    not FFh **[verified: the port's trace against the bench, step 9]**.
  - **The suspect is whole in the Amiga's view**: its BOB covers map x 242-285 (drawn at 241, the
    camera at x 0), inside the 288 px the Amiga shows **[verified: the port's atlas columns and lists,
    step 15]**. An MSX view of 256 px shows only its first columns there.
  - **The copper line after a vat death**: once d = cam y + 98h − y reaches 4Dh (the camera following
    RoboCop down: game frame 56 of `vat`), `$10356` is CAh again and his sprites show whole in front of
    the liquid until the restart **[verified: the bench's `$10356` at each frame's start equal to
    `lt1`'s rule on all 121 rows of `vat`, step 15]**.
  - A briefing screen lasts its script's calls plus the one that reads the end: 394 VBLs for `$110F0`
    (393 calls) and 412 for `$110B4` (411) without fire **[verified: bench VBL count of `$110F0`; the
    port's records, step 18]**.

### Level 3: the Civic Centrum **[verified: REA (Ghidra 12.1.4 through the REA CLI and MCP, raw-binary m68k, entry `0x0`, `analysis/ghidra_seeds.tsv` with level 3's ten `+entry` seeds) on `build/ram/level3_full.bin`; data reads; bench runs of the original (`tools/amigaemu.py game --level 3`, `tools/amigacov.py --level 3`); inferences marked]**

The plan and every table: `docs/LEVEL3.md` section 2 (2026-11-01). The facts in short:
- **The image**: `make ram` builds it with SPERMA under DATAL3 (RB1, MU1, SPERMA, DATAL3, PERMA; sha256
  `700df44d…3515ca`): DATAL3 (185,356 B) covers `$28000-$5540B`, SPERMA's tail `$5540C-$5884D` stays (the
  frames of types 4 and 12 that level 3's markers spawn). The main code is byte-identical to the other
  images. Seeds: REA creates 125 functions, finds 1, applies 303 labels, 0 failed; the ten new
  `+entry` seeds are code reached by `bsr` from type handlers or through branches Ghidra does not
  follow (`$C398`, `$D0A6`, `$D478`, `$EF18`, `$EA50`, `$EAA6`, `$EBB8`, `$9F74`, `$F98C`, `$F12A`).
- **The way in** (`load_level2` `$8524`): the statistics, `sperma_resident` cleared, both stages'
  second visits, the briefing `$110B4`, PIC7, MU1, DATAL3; `level_init` reads the header `$86B4`
  (objects `$AA3A`, hazards `$95EC`, specials `$9008`, spawns `$99E2`, start (1184, 784), relocation
  (224, 544), markers `$C624`, lowest camera 624, 7:30, delay 3Ch, marker mask 3, **palette `$10036`,
  level 2's**) and runs `$88AC`: `$15CA` set (no gun-opening sequence), aim 5, `$15DE` 4, state 6,
  `$F89D` = 0Bh.
- **The level**: 160 × 50 cells, floors on rows 7 (the roof), 20, 25, 30, 35, 40, 49; seven electric
  beams two cells wide (`level_tick_2` `$9436`: 32 frames on, 32 off, − 0Ch a frame); three lifts drawn
  in two parts (`$8ED2`: `$5397C` 32 × 29 and `$53BC0` 32 × 16, because `$8050` = 2); 15 map objects
  (two relocations, ten crates with pickups, three entries of `act_20` `$9F74`, which opens them
  once type 22 sets `$16A9`); wall turrets (types 40-42) that write two 2 × 3 blocks of map words.
- **The objects**: spawn list `$99E2` (39 entries), markers `$C624` with type-0 entries (no spawn) and
  `$C662` (type 43's table of type-0 entries: the markers off from the roof on); new types 21, 22,
  33-43, 46-48, 50-52 (4,222 B of level-3-only code with the deaths `$C25C`, `$C360`, `$C3A8`, the
  debris helper `$C398`, the beams, `act_20` and the two-part lift).
- **Cain as RoboCop 2** (type 22 `$D49C`, 764 B): spawns on the roof (entry 36 at (1280, 56)), "CHASE
  CAIN"; keeps its x in the code (`$D798`) and patches its step mask into `$D583`; hit points set to
  2Ch every frame while its y < 290h; launches through the mailbox `$E67A-$E67E` (its only writer:
  `$D72C`), which types 38, 39 and 52 take; its death `$C25C` throws its parts (debris bullets
  12h-14h), sets `$16D0`, `$16C4` = 40h and queues "CAIN DESTROYED." **[bench: met at game frame 243
  of a roof drive; killed after a poke (coverage only), the level's end 94 frames later]**. Its chase
  ahead of RoboCop and down through the car park **[inferred from the code and two drives]**.
- **The end**: `$8050` = 3, `level_init`'s entry 7, `level_load_3` `$86DE`: the text `$112C5`,
  `$11C54` (PICF, CMP), `high_score_entry`, the title; no statistics, no stage.
- **The frames**: 202 drawn on the bench (136 in DATAL3, 58 of them 48 px wide or more); `bobcatalog.py`
  does not follow their PC-relative tables. **The sound**: effects 0Eh, 22h-25h, 27h, 28h of MU1,
  nothing new.

### Music and sound effects (MU1 player) **[verified: REA listing of `$18000-$18B35` (level-1 image); `tools/rc2music.py --verify` runs that code in Unicorn and matches the model's Paula writes and player RAM on every tick of every tune of the five files (49986 ticks); the paths the data never takes (vibrato, 86h, 81h-83h in patterns, 83h in sequences, stop tune, the effect priority, effects over music) matched the same way on patched images and call scripts]**

- **Files.** TITM (title), MU1 (in-game sound effects), CH1 (a jingle), CMP (game completed)
  and HI1 (high-score entry) are loaded at `$18000` and carry the same player: `$18000-$18B35`
  is identical in the five files except the table operands and the tune count (`cmp.w #n` at
  `$181F2`/`$18270`); `rc2music.py` finds them by instruction signatures and checks the rest
  (SHA-1 with the operands masked). The samples, tables and tune data follow the code.
- **Entries** (7 × `bra.w`): `$18000` → `$18180` init, `$18004` → `$18194` stop all,
  `$18008`/`$1800C` → `$181E8` stop the channels of tune D0, `$18010` → `$1824E` start tune D0
  as music, `$18014` → `$1822C` as a sound effect, `$18018` → `$18316` play one tick. The game
  calls stop all from `$83EC`, `$8720`, `$FE14`, `$10894`, `$11CD0`, `$11FB4`; nothing calls
  `$18008`/`$1800C` (xrefs: `$1800C`'s only one is inside PERMA's graphics). Variables: `$1801C`/`$1801E` AUDxVOL masks of music/effect channels (FFFFh, never changed by
  the player), `$18020` OR of the channel flags (bits 15-14 kept; 0 = nothing to process),
  `$18022` last music started, `$18023` last effect started, `$1817C` DMA bits of this tick's
  key-ons, `$1817E` tick counter (cleared by start, never read).
- **Channel structure** (`$18024 + 56h × ch`): +0 flags (bit 0 grace, 1 arpeggio, 2 vibrato,
  3 slide, 4 envelope running, 5 fixed duration, 6 no transpose, 7 rest, 14 effect, 15 music),
  +2 sequence loop point, +6 sequence pointer, +0Ah pattern loop point, +0Eh pattern pointer,
  +12h repeat count, +13h transpose, +14h/+18h envelope start/pointer, +1Ch-+20h envelope
  rate, counter, ticks left, step, +21h-+23h grace, +24h-+26h slide, +28h-+33h arpeggio,
  +34h-+3Ah vibrato, +3Ch-+48h copy of the instrument record, +4Ah period, +4Ch volume,
  +4Fh/+50h note without/with the grace interval (the arpeggio adds its offsets to +50h),
  +51h fixed duration, +52h ticks to the next read, +54h DMA bit.
- **Layout** (MU1; the other files' addresses are in `build/music/*.json`): period table
  `$18B36-$18B95` (48 equal-tempered words, 1790 … 119; A5 = `$18B66` is index 0 = 447, indices
  −24…23); instrument records `$18B96` + 16n (35 slots; 31 in the other files); a zero word at
  `$18DC6` (`$18D86`) that every one-shot sample loops on; the sample list `$18DDE`
  (`$18D9E`); the 8SVX FORMs; then self-relative word lists (target = word address + word):
  arpeggios `$270CE`, envelopes `$270D6`, tunes `$27156` (8 bytes per tune), patterns `$272A6`;
  then the sequences and patterns.
- **Instrument record** (16 bytes, copied into the channel by command 90h): +0 base note
  (subtracted from the note before the period lookup), +2 sample start, +6 length in words
  (one-shot + repeat), +8 loop start (BODY + one-shot, or the zero word), +12 loop length in
  words (1 for a one-shot), +14 ≠ 0: the note is not transposed. Record 0 is not set by init:
  base 33 and a looped 22-byte waveform at `$18DC8` (`$18D88`; the bytes differ per file, TITM
  has two copies of an 11-sample two-cycle sine), used by MU1 effects 19, 27-33 and 38, CH1's
  jingle and HI1's effects 3 and 4.
- **Init** (`$18180`): `$1896E` walks the sample list (8-byte entries: `offset.l` from the entry
  to a `FORM 8SVX`, base note `.w`, no-transpose `.w`; 0 ends) and fills records 1…n. The IFF
  walker (`$189D2`, `$189F4`, `$18A52`, `$18A9A`) stores the VHDR data address in `$18AE6` and the
  BODY's in `$18B0E` (nested FORMs recursed, other chunks skipped); `$1898E` takes
  oneShotHiSamples and repeatHiSamples (rounded down to even) and the BODY address; the VHDR
  rate, octave count and volume are ignored. An entry that does not point at a FORM is not
  detected: its record repeats the previous sample (CH1 20-26, CMP 23-26, HI1 20-26). Then stop
  all.
- **Tunes and sequences.** Tune n (1…count) = 4 words at tunes + 8(n−1), one per channel,
  self-relative to a sequence; 0 = the channel is not touched. Sequence bytes: 00-7Fh pattern;
  80h end: jump to the loop point, else stop the channel (period 1, volume 0, flags 0); 81h loop
  point here; 82h t transpose (signed) of the next pattern; 83h n play the next pattern n times;
  84h-FFh ignored, without operand. After a pattern and its repeats the transpose returns to 0
  and the count to 1.
- **Patterns**: a note 00-7Fh followed by its duration in ticks (none in fixed mode); commands
  80h-90h through the jump table `$183D8` (`lea 14h(pc)` at `$183C2`: words relative to each
  entry, 91h-9Fh are 0 = ignored); A0h-FFh ignored. Any command byte cancels a pending slide.

  | Byte | Operands | Effect |
  |---|---|---|
  | 80 | — | end of pattern: to the pattern loop point if one was set, else the next sequence entry |
  | 81 | — | pattern loop point (+0Ah; only a new start clears it) |
  | 82, 83, 91-9F | — | nothing (an operand is *not* skipped) |
  | 84 / 85 | d / — | fixed duration d for the following notes and rests (bit 5) / durations per note |
  | 86 | — | +256 ticks on the next duration |
  | 87 | [d] | rest: volume 0, envelope and effects stopped (bit 7) for d ticks; no DMA stop |
  | 88 | i, n | the next note (if it is the next byte) slides into place from i semitones away in n ticks: step = (period(note + i) − period(note)) / n (DIVS, towards 0); the period starts at period(note) + n × step and moves by −step per tick from the note's first tick (bit 3) |
  | 89 / 8A | i, n / — | grace: each note starts i semitones away for n ticks (bit 0) / off |
  | 8B / 8C | d, i, s / — | vibrato: after d ticks, steps of (period(note + i) − period) / 2 / s per tick, turning on the s-th step and then every 2s (a triangle of about ± half the interval, centred one step off) (bit 2) / off — never used |
  | 8D / 8E | t / — | arpeggio table t: speed, length, semitone offsets; one entry every speed ticks from the note's first tick, cycling (bit 1) / off |
  | 8F | e | envelope e (used from the next note) |
  | 90 | n | instrument n (bit 6 from its +14) |

  89h, 8Bh and 8Dh clear bits 0-2 before setting theirs: grace, vibrato and arpeggio exclude
  each other (MU1 27, 28, 29 and 33 give 89h then 8Dh: only the arpeggio sounds); a slide
  takes priority over them on its note.
- **Channel processor** (`$1839A`, each tick for each channel with flags ≠ 0): +52h counts down;
  at 0 the pattern is read up to a note or a rest. A note: + transpose unless bit 6, + the
  grace interval; period = word at A5 + 2 × (sign-extended note − base); the slide or vibrato
  is set up, the arpeggio restarts, the envelope restarts at volume 0, the channel's DMA bit
  goes into `$1817C`, the duration into +52h. Then one effect (the first of slide, grace,
  arpeggio, vibrato), then the envelope.
- **Envelopes** (byte pairs; restarted by each note; the first segment acts on the note's first
  tick): n s with n = 01-7Fh: n ticks of volume + s (signed); n p with n = 80h-FFh: −n ticks
  (as a byte) of ±1 every |p| ticks (− when p < 0); 00 00: end, volume held; 00 r: hold until
  |r| ticks before the note's end (its +52h counter), then go on with r as the next segment's
  count, or end when the note is already shorter. No clamping: AUDxVOL = volume word & mask.
- **Paula output** (`$187E4`, every tick, all four channels): for the key-on channels DMACON
  off, INTREQ cleared, AUDxPER = 1, AUDxDAT = 0, then a wait for their audio interrupt requests
  and 3 raster lines; then per channel AUDxVOL = volume & `$1801C` (`$1801E` with flag bit 14),
  AUDxPER = period, AUDxLC/AUDxLEN = sample start/length on a key-on tick and loop
  start/length otherwise (Paula takes them when the buffer ends: the sample plays once, then
  its loop part or the zero word); DMACON on for the key-on channels.
- **Start** (`$1825C`, both entries): clears `$1817E`, sets CIA-A PRA bit 1 (LED off: the A500
  audio filter off), stops all for n = 0 or n > count; per channel of the tune: volume 0, loop
  points 0, transpose 0, count 1, flags 8000h (music) or 4000h (effect), the sequence read up
  to its first pattern, +52h = 1 (the first note is read by the next play call). Instrument,
  envelope and effect parameters stay from what the channel played before. The effect entry
  `$1822C` does nothing when channel 3 is busy (`$18126` ≠ 0) and n < `$18023`, whichever
  channels the new effect uses. An effect takes over its channels' structures: music there
  stays silent afterwards.
- **Tick rate.** Durations count calls of the play routine. In the game (MU1) and for TITM, CH1
  and HI1 the level-3 VBL handler calls it through the patchable `jsr` at `$1031E` (long
  `$10320`: `$18018`, or `$1032E` = `rts`) on 5 of every 6 VBLs (counter `$10330`): **50
  ticks/s** on the NTSC machine this release targets (41.7 on PAL), the tempo of a PAL machine
  calling it every VBL. CMP is played by the
  game-completed loop `$11C54` (from `$86DE`) on 4 of 5 passes (counter `$11C52`) of a loop that
  waits for raster line C0h, for 1800h passes or until fire: 48 ticks/s on NTSC **[inferred:
  one pass per frame; the skipped pass takes about 420 cycles, a line 455]**. An MSX at 60 Hz
  must skip every sixth VBL like the Amiga.
- **Where each file plays**: TITM is loaded by `$11A20` (`$11B4C`) and its tune 1 started by
  `$10884`, which `$8064` calls after `$11A20` (`$80A2`); MU1 by the level start (`$8614`); CH1
  tune 1 by `$11F60`, a handler of the typed-key sequence matcher `$11EDA`; CMP by `$11C54`; HI1
  tune 1 by `$12300`, its name entry starting effects 4 (`$121F8`) and 3 (`$1228A`). HI1 tune 2
  is not started by any call site of `$18010`/`$18014` **[inferred: from those xrefs only]**.
- **Sound requests.** `frame_keys` (`$F76C`) passes `$B31`, `$B30` … `$B2C` (in that order, each
  cleared) to the effect entry once per game frame. Writers (number, site): `$B2C` 14h
  `$AFC8`; `$B2D` 0Ah lift `$8E72`, 0Ch `$8FAC`/`$A06E`, 0Eh `$9FA8`/`$D540`, 14h `$A138`, 19h
  `$A0F0`, 25h `$E824`/`$E8F4`, 28h `$9F08`/`$E9D0`/`$EB4E`, `$C336`[`$B00` & 7] (15h-19h)
  `$C32E`, `$F37C`[D5] `$F38E`, pickups `$FC0B`[type / 4] (10h, 1Bh-21h) `$FBC6`; `$B2E` 10h
  `$9208`, 12h `$D124`, 19h `$D298`, 1Ah `$91C4`, 23h `$E1DE`/`$EE70`, 24h `$E0AC`, word 0303h
  `$B380` (3 in `$B2E` and `$B2F` at the level start); `$B2F` 13h `$ECCA`, 25h `$E400`, 29h
  vehicle `$8C1C`, `$F5D2`[D6] `$F604`; `$B30` 6 `$B0F2`, 9 `$ED9A`, 22h beams `$937A`/`$9474`,
  27h `$D5A4`, 2Ah `$C314`/`$E092`; `$B31` 4 shot `$ADE0`/`$AE12`, 0Bh extra shots `$AE30`, 26h
  level-end score `$8198`.
- **Contents** (ticks at 50/s; loop = start tick + length, from where the audible output
  repeats): TITM 1 music, 4 channels, 5184-tick loop from 0 (103.7 s). MU1 42 effects of one
  pattern on one channel (42: channels 2 and 3), 2-57 ticks (channel/ticks: 1 2/26, 2 2/27, 3
  1/10, 4 0/13, 5 3/12, 6 1/10, 7 3/28, 8 3/12, 9 2/30, 10 1/6, 11 0/12, 12 1/2, 13 0/15, 14 0/20,
  15 1/17, 16 2/47, 17 1/10, 18 2/9, 19 2/36, 20 0/22, 21-24 3/20, 25 1/18, 26 1/24, 27 2/19, 28
  2/19, 29 2/5, 30 2/22, 31 2/12, 32 2/14, 33 2/14, 34 3/57, 35 2/2, 36 2/3, 37 3/9, 38 1/3, 39
  2/22, 40 1/32, 41 1/5, 42 2+3/48). CH1 1 jingle, 4 channels, 582 ticks, ends. CMP 1 music, 4
  channels, 192 + 4608-tick loop. HI1 1 music, 48 + 1920-tick loop (channel 3 plays only the
  48-tick intro, so it is free for the name-entry effects, which use channel 3); 2 music,
  5760-tick loop from 0; 3 and 4 effects on channel 3, 6 and 14 ticks.
- **Samples** (in the JSON: start, length, loop, VHDR rate, NAME/ANNO, peak/RMS/zero crossings
  and an autocorrelation pitch estimate **[inferred]**): MU1 19 samples, TITM 13, CH1 4, CMP 7,
  HI1 4 (plus record 0's waveform); all one-shot except MU1 "WHITE" (3956 bytes of looped
  noise) and TITM "FILTER-WAH" (12816 + 8756-byte loop). The NAME chunks (Audio Master II)
  give BDRM, SNARE, CLOSEDHAT, TOM, TOM1, TIMPANI, PIZZICATO, BRASS4, ORCH1, FILTER-WAH, ba1,
  CLUB, SNAZ, WHITE, barrel.
- **Data quirks.** A note at table index 24 (one past the table) reads `$18B96`, record 0's base
  note 21h: AUDxPER = 33 (TITM notes 48/base 24 and 60/base 36, HI1 tune 1 note 36/base 12, HI1
  tune 2 through its arpeggio); that is below Paula's DMA limit (~124), so the hardware repeats
  data words — the intent was presumably the semitone above index 23 (≈ 112) **[inferred]**.
  MU1 5 slides for 48 ticks on a 12-tick note (cut). No file uses 81h, 82h or 83h inside
  patterns, 83h in sequences, 86h, 8Bh or 8Ch.
- **Model and output.** `tools/rc2music.py` → `build/music/<NAME>.json`: per tune the channels,
  the end tick or the loop (plus the tick from which the whole player state repeats), the
  sequence loop jumps per channel, the key-ons [tick, channel, instrument, note, table index,
  period], per-channel runs [ticks, AUDxPER, effective volume 0-64, instrument], the sequences
  and a listing of each pattern; per file the instrument records, unique samples, envelopes,
  arpeggios and the period table. `--trace NAME:N` prints one tune tick by tick.
- **PZM: Brainstorm's copy** (PUZL at `$17100`; the player at `$18000`, file offset F00h, to
  PUZL's end) **[verified: REA on the level-1 image with PUZL placed at `$17100` (the 2026-10-26
  sound report); `tools/rc2music.py --verify` on `PUZL_25.bin[F00h:]`: 6 tunes, 9,744 ticks, 0
  differences; disk 1's copy decrunched is byte-identical]**. `$18000-$18B35` is MU1's code but
  for the per-file table operands and the player's own RAM saved with the file (`$18020-$1817F`,
  the IFF walker's `$18AE6`, `$18B0E`, `$189D0`: data, by their xrefs), so `rc2music.py`'s
  "code != MU1's" warning is a false alarm there. Tables: tunes `$23270`, patterns `$232A0`,
  envelopes `$23210`, arpeggios `$23200`; record 0 the same 22-byte two-sine waveform as TITM's.
  Tunes: 1 channels 0-2, 3,000 ticks then every channel stops (melody: instruments 0, 16
  PIZZICATO, 17-19; drums 20 CLUB, 21 PERCUSH2, 22 PERCUSH1, 23 SNAZ); 2 channels 0-2, 1,464
  ticks, never started (PUZL's only `$18010` call takes the tune from the board record's byte 5,
  1 in all 8 records); 3-6 effects on channel 3 (12, 6, 48, 36 ticks; 6 is note 0 against base
  33: AUDxPER 54,191 read from the code word at `$18B24`). PUZL calls init (`$17100`), stop all
  and tune 1 at every board (`$1743A`, `$17442`), the effect in `$B04` once a pass (`$17794`;
  written at `$177BC` 3, `$17844`-`$17894` 4, `$173DC` 5, `$17264` 6) and the tick on 5 of 6
  passes (`$17212`); its level-3 handler replaces the game's VBL hook (patched to an `rts` at
  `$8398`). **[verified: REA and the model, 2026-10-27]** In a pass the effect's start
  (`$171F2` → `$17760`, `$17794`) comes before the tick (`$17212`). The tick (`$18316`) runs
  `$1839A` for each channel whose flags word is set and stores the word back; `$1839A` clears it
  (`$1845C` `moveq #0,D7`) in the tick that reads the sequence's end. So an effect of L ticks
  keeps `$18126` set through L + 1 ticks counted from its first (the model: effect 4's flags
  4019h after its tick 0, 4001h after ticks 1-5, 0 after tick 6), and `$1822C` refuses a lower
  request made 1 to L passes after it (one tick a pass).

## 5. Front end: title, text screens, high scores

Read with REA/Ghidra in `level1_full.bin`. Ghidra follows neither the BRA table `$11746` nor
the particle routines at `$10E46`–`$10EF7` and `$10F40`–`$10FC7`; those were exported with the
REA CLI and extra function seeds (same engine, project seeds plus the targets).
`tools/rc2front.py` decodes the data and models the effects → `build/front/`: `scripts.json`,
`hiscores.json`, `font.json`, `font.png`, `font_strokes.png`, `title.json` and a render of
every screen in `screens/`.

- RoboCop's speech in the title music **[verified: the model's rendering, identified by ear by the
  user, 2026-10-22]**: "YOUR MOVE, CREEP" is TITM sample 11 (16020 bytes at 7004 Hz, "TOM" in its
  8SVX NAME chunk: the names say nothing of the content; sample 6 "ORCH1" is an orchestra hit),
  instrument 24, keyed on channel 2 at tick 2880 (57.6 s at 50 ticks a second) and on channel 0
  at tick 2889, AUDxPER 335 (10685 bytes a second, 1.5 s), volume 64: the same speech left and
  right 9 ticks apart. Its only two key-ons in the tune.

### Sequence **[verified: code]**

- **Boot** (`game_boot` `$11A20`), silent and without waits: each picture stays while the next
  files load. DATAE (4 planes, copper `$12352`) while RB1 and OAS load; OAS while TPIC loads;
  TPIC (HAM6) while TITM, PERMA and SPERMA load; then a blank copper (`$1049E`) and the
  buffers cleared. The expansion-RAM file cache (`$1195E` stores, `$11932` restores; TITM,
  SPERMA, MU1, PIC\*, HI1) is off: only the code that the `BRA.B` at `$8078` skips sets its
  magic `$12343210` in `$803A` **[inferred: a cracked `BNE`]**.
- **`$8098`** (also after every game): `$FEDA` (palette black, buffers cleared, CIA set-up,
  random seed, game copper `$10332` through `$FE14`), `clear_game_vars`, title loop `$10884`,
  `$FFC4` (level 0, `$805E` = 0, score 0, `init_lives`), `level_init`.
- **Title loop** `$10884`, one pass per frame (raster line `$F0`): player init, stop all,
  **tune 1** of the file at `$18000`; both buffers cleared; palette `$109A8`. Fire at any
  moment (`read_joystick` bit 4: joystick or keyboard fire keys) returns and starts a game;
  there is no demo. Nothing reloads TITM: after a game the title plays tune 1 of the resident
  file, MU1 (its effect 1), HI1 or CMP **[verified: code; audible result inferred]**.
  1. Logo fly-in (`$106E2`, 77 frames, double-buffered): *Title logo* below.
  2. Attract script `$11237` on the front buffer, one element per frame, plus the cheat matcher
     `$11EDA` and `$B00` + 1 (cursor blink): credits typed (115 frames), wait 192, diagonal
     wipe 38, the high-score table written by the particle writer (373) and unwritten (373),
     `FF 05`: a 1094-frame cycle, 18 s at 60 Hz (`screens/attract_*.png`).
- **New game**: `level_init` stops the music; `load_level0`: level-1 briefing `$11108` through
  the curtain entry, `$FE14`, PIC1, MU1 (`$8614`: init only, no tune), SPERMA and DATAL1 when
  not resident; `$8060` = `$C716` (*Gun calibration*).
- **Between levels** (`load_level1` `$8582` / `load_level2` `$8524`): statistics, Brainstorm
  (`$8382` D0 = 2 / 4: PIC3 / PIC5), shooting range (`$8420` D0 = 1 / 5: PIC2 / PIC6), briefing
  `$110F0` / `$110B4`, PIC4 / PIC7, MU1, MADEX + DATAL2 / DATAL3.
- **After level 3** (`level_load_3` `$86DE`): script `$112C5`, `$11C54` (PICF and CMP tune 1,
  see *Music*; 1801h passes or fire), `high_score_entry`, `$8090` (stack reset, title).
- **Pictures** (`show_picture` `$11E06`): `$FE14` (music stopped) and `$FEDA`, PIC('1'+D0)
  loaded at `$6FFA0`, shown at once with its own palette, for 251 VBLs or until fire.

### Text screens **[verified: code]**

- Entries: `$10768` (A0 = script; `$FE14`: music stopped, palette black; front buffer
  cleared), `$1079A` (curtain: 16 frames, each clearing a 16-px column from both sides; music
  kept), `$10772` (`$10768` after its `$FE14`), `$10762` (`$10768`, then `$FE14`). Then palette
  `$109A8` at fade level `$1F`, text origin `$109A2` = front buffer + 2 + `$2600`, particles
  cleared, `$B04` = 50.
- Loop `$1084C`: one script element per VBL (`$116CA`); ends when (fire or `$16D1` set) and 50
  VBLs have passed. No fade out: the caller's `$FE14` or `show_picture` blacks the screen.
- Display: game copper `$10332`, 4 interleaved planes (152 bytes per line), buffer lines 0–175
  on display lines `$1E`–`$CD`, 304 px fetched (x 15–302 visible with BPLCON1 = 0); the status
  panel stays below (its `BPLCON0` move `$10494` is never written). The VBL handler applies the
  line offset `$B28` and BPLCON1 `$B0C`, which `main_loop` sets every frame and only
  `clear_game_vars` clears: the screens between levels and after a game over keep the last
  frame's fine scroll **[inferred: not observed]**.
- Palette `$109A8`, COLOR01–15 (components at most E after `$F8C4`): 070 050 020 147 347 AAB
  35A 46A 67A BBB 78A 8AD 58D 79C 9AB; COLOR16–31 read the stroke glyph 'A' that follows.
- Text grid: 8 × 8 cells, column c at bitplane x 16 + 8c, row r (signed) at line 67 + 8r;
  glyphs written into planes 0–2 (colour 1 with a colour-4 shadow).
- Cursor (`$118B4`): lines 6–7 of the next cell, plane 0 `$7F`, plane 1 `$63`. It is erased (a
  space) at the start of every call and drawn after a character, a position, a wait or the
  halt when bit 2 of `$B01` is set. `$B00` moves only in `main_loop` and the title loop: in the
  other screens the cursor is always on or always off. Entered through `$FE14` (the statistics,
  the briefings) it is always off: `$FE14` does not return but falls through at `$FE92` into
  `clear_game_vars` `$FE96`, so `$B00` is 0 **[verified: code; bench, 362 iterations]**.
- The font's glyphs use colours 1 and 4 only: plane 1 is always clear and planes 0 and 2 never
  meet; the shadow (colour 4, `$147`) is drawn into the font data by hand, not a shifted copy
  of the strokes (colour 1, `$070`) **[verified: data]**.

### Script format (`$116CA`, pointer `$10F2C`) **[verified: code]**

| Bytes | Handler | Effect | Calls |
|---|---|---|---|
| `00 x y` | — | cursor to column x (`$16C9`), row y signed (`$16CA` = 8y) | 1 |
| `01`–`7F` | `$118D6` | one character, cursor + 1 | 1 |
| `80`–`FF` 0 | `$1171E` | halt, cursor blinking (the prefix's value is ignored) | — |
| `80`–`FF` 1 | `$11768` | diagonal wipe: call k (0–36) blanks column k − 4 + r of rows r = 0–12 (`$16B2`), then cursor (0, 0) | 38 |
| `80`–`FF` 2 n | `$117A8` | wait | max(1, 4n) |
| `80`–`FF` 3 | `$11864` | particle writer until its 24 particles are idle at the end of the text (`$16C6` = 24) | per text |
| `80`–`FF` 4 p | `$117C6` | particle set-up p / 12 of `$11804`: colour set → `$10F28`, text → `$10F30`, origin → `$10F34`/`$10F36`; particles `$DB4`–`$15C3` and cursor cleared | 1 |
| `80`–`FF` 5 | `$118A2` | script = `$11237` | 1 |
| `80`–`FF` 6 | `$1175E` | halt (`rts`), no cursor | — |
| `80`–`FF` 7 | `$11762` | `$16D1` set (done), halt | — |

- Characters (`$118D6`; the panel's `$10620` is the same): `' '` → glyph 41, codes ≥ `'@'` →
  code − `'A'`, others → code − `$16`. So `'0'`–`'9'` and `'['`–`'d'` are digits, `'e'`–`'l'`
  (and `':'`–`'?'`) are `. , ? " !`, blank, `©`, `%`; `'@'` reads the `$FF` bytes before the
  font (a colour-7 block). Numbers come from `$11DC6`: D2 → BCD at `$11DFA` (`$11D30` holds the
  powers of two `$8000`…1, `$11D52` their BCD values, added for each bit set: 0…32767) → 8
  characters `'['` + digit at A4, leading zeros as spaces (0 shows as one '0').
- Scripts (calls = VBLs without fire; each screen lasts max(calls + 1, 50) VBLs, + 16 for the
  curtain):

| Script | Entered from | Text (`/` = new position) | Calls |
|---|---|---|---|
| `$11237` | title loop | TM AND © ORION PICTURES CORP / ALL RIGHTS RESERVED / WRITTEN BY SPECIAL FX / FOR OCEAN SOFTWARE LTD. / PRESS FIRE TO START; then the high scores (particles 0, 1) | 1093 + 1 |
| `$11108` | `load_level0`, `restart_level0` (lives = 2) | particles 3; NEGOTIATE THE RIVER COMPLEX / COLLECT TEN NUKE CAPSULES / THEN DESTROY THE DRUGS LAB / RESCUE ALL HOSTAGES / FOR AN EXTRA LIFE. | 485 |
| `$110F0` | `load_level1` | particles 4; ARREST CAIN | 393 |
| `$110B4` | `load_level2` | particles 5; BATTLE YOUR WAY TO THE ROOF TO / CONFRONT CAIN. | 411 |
| `$1132F` | `show_level_stats` | LEVEL STATISTICS. / HENCHMEN OBLITERATED n / NUKES COLLECTED n / HOSTAGES RESCUED n (fields `$1135A`, `$11379`, `$11398`) | 361 |
| `$114AA` | `$8382` | BRAINSTORM. / DESTROY ALL RED CHIPS ON THE BOARD / COMPLETE 4 TO REGAIN MEMORY. / AND EARN A GAME CREDIT. | 292 |
| `$1162F` | `$8382` result 0 | WELL DONE MEMORY RESTORED. / GAME CREDIT AWARDED | 143 |
| `$11667` | `$8382` result 1 | MEMORY MALFUNCTION. / ATTEMPT TERMINATED. | 136 |
| `$11698` | `$8382` result 2, `$8420` time out | OUT OF TIME. / ATTEMPT TERMINATED. | 129 |
| `$1142D` | `$8420` | SHOOTING RANGE. / YOU MUST SHOOT ARMED TARGETS / YOUR GUN CALIBRATION WILL BE TESTED / WARNING ACCURACY IS ESSENTIAL. | 304 |
| `$113A5` | `$8420` | GUN CALIBRATION. / CORRECT TARGETS n / DUMMY TARGETS n / YOU ARE RATED AS POOR. FAIR. GOOD. SHARP. (fields `$113CA`, `$113E4`, `$11400`) | 347 |
| `$112C5` | `level_load_3` | particles 7; YOU HAVE DEFEATED ROBOCOP 2, / AND THE SUPPLY OF NUKE HAS BEEN / STAMPED OUT. | 341 |
| `$1151B` | cheat `$11F60` | CHEAT MODE NOW ACTIVE. / USE F9 TO TOP UP ENERGY. / USE F10 TO SKIP MAIN LEVELS. / PRESS FIRE BUTTON TO START | 232 |
| `$11590` | `$11FD2` | YOU HAVE A GAME CREDIT. / PRESS FIRE TO CONTINUE. | 304 |
| `$115C9` | `$1215C` | YOU HAVE A HIGH SCORE. / ENTER NAME ON THE KEYBOARD / USE BACKSPACE TO DELETE / RETURN TO FINISH. | 92 |
| `$116C2` | `disk_prompt` `$11BD2` | particles 6, then `FF 06` (until fire) | 218 |

  `disk_prompt` (D0 → the digit at `$11211`) has no caller in the image **[inferred: the
  crack's loader does not prompt]**; particle text 2 "LEVEL COMPLEATE" is never set up.

### Particle writer (commands 3 and 4) **[verified: code; modelled by `rc2front.py`]**

- 24 particles of 86 bytes at `$DB4`, all updated once per call (`$11870` → `$10FC8`). A free
  one reads the text at `$10F30` (`$10F40`): `0D` new line (x = 0, y + 16), space x + 16,
  `FE i v` byte `$10F38` + i = v (nothing reads it), `FF 00` end (counted in `$16C6`; the
  pointer stays), `FF n` colour set `$10F04` + 6(n − 1); any other byte is glyph code − `'A'`
  at (x, y) (`$10E46`), then x + 16.
- Stroke font `$109C6`: 36 glyphs ('A'–'Z', then `'['`–`'d'` = 0–9), each 16 (x, y) byte
  points on a 14 × 14 grid: a 15-segment polyline. A segment (`$10E84`) moves in 16.16 steps
  halved until both are below one pixel: 2^k frames with 2^k > max(|dx|, |dy|), k ≥ 1. After
  the last point the particle waits 10 frames, then takes the next character.
- Plot (`$11062`): the pixel gets the colour in all 4 planes at bitplane (16 + origin x + px,
  64 + origin y + py), skipped when origin y + py ≥ 160. Per frame: head colour at the current
  point, middle colour 5 points back, final colour 10 points back (history at +`$1E`).
- Colour sets (`$10EF8`, head / final / middle): A 7/4/8 (every set-up but 1), B 8/0/7 (erases
  what A drew), `FF 1`–`6`: 1/2/3, 4/6/5, 7/9/8, 10/12/11, 1/6/8, 0/0/0 (unused).
- Set-ups (`$11804`: colour set, text, origin x, y): 0 high-score table (A; 16, 0), 1 the same
  with B, 2 "LEVEL COMPLEATE" (32, −48), 3 "THE RIVER ROUGE / COMPLEX" (0, −48), 4 "TOKUGAWA
  BREWERY" (16, −24), 5 "CIVIC CENTRUM" (48, −48), 6 "PLEASE INSERT / DISK n / AND PRESS THE /
  FIRE BUTTON" (32, −24), 7 "WELL DONE" (32, −24). Durations: 373, 373, 106, 108, 124, 108,
  217, 106 calls.

### Fonts **[verified]**

- Bitmap `$65DB0` (PERMA): 44 glyphs × 24 bytes (planes 0, 1, 2 × 8 lines, MSB left): 0–25
  A–Z, 26–35 0–9, 36–40 `. , ? " !`, 41 blank, 42 `©`, 43 `%`; strokes in colour 1, shadow
  in colour 4 (`font.png`).
- Stroke `$109C6`: above (`font_strokes.png`).

### Title logo (`$106E2`, `$10720`) **[verified: code; positions computed by `rc2front.py`]**

- RB1 (`$12588`) holds the 8 letters, BOBs with masks, 48 px wide (R, C, 2: 51 lines; the O, B,
  O, O, P: 38 lines, 6 lower). Table `$10682`: x/y offsets, x0 and BLTSIZE, graphics (R
  `$13BCC`, O `$12588`, B `$129FC`, O `$12E70`, C `$141C6`, O `$132E4`, P `$13758`, 2 `$147C0`).
- Countdown t at `$1067A` (16.16, from 136.0): each frame t −= t / 16 (`asr.l #4`; 1.0 when
  that is 0); letter at x0 − ((280 − x0) · t >> 5), y = t + y offset (`draw_bob`: bitplane x =
  x − 128): the letters rise from 136 lines below and slide in from beyond both edges (their
  distance to bitplane x 152 scales with 1 + t / 32), slowing down. The loop ends at
  t = 0, which is not drawn: 77 frames; the last image (t = 1) has the letters at bitplane x 15,
  53, 89, 124, 158, 193, 230, 267 and y 1 (R, C, 2) or 7.
- Each frame clears the rectangles drawn two frames earlier in the back buffer (`draw_bob`'s
  BLTCON0 immediate `$AC16` patched from `$0FCA` to `$0100`) and ORs a "TM" (`$1254E`, 5 lines)
  into plane 2 of the front buffer at byte `$1F50` (x 288–303, lines 52–56). Palette `$109A8`.

### Level statistics and bonus stages **[verified: code]**

- `show_level_stats` (`$85D8`): `$16C2` henchmen obliterated (+1 per enemy killed, `$C422`),
  `$16C0` nukes collected (+1 per nuke pickup, `$FD20`), `$16BE` hostages rescued (+1 at
  `$ECC0`; the 10th gives a life) → `$11DC6` → script `$1132F`. No score is added here (the
  level bonus is the in-game count of `$16D0`, *Timer and death*). The counters lie in
  `$B00`–`$16EB`, which every `level_init` clears (also after a death or a continue): the
  screen counts since the last (re)start. Its 362 calls: 4 positions and 101 characters (one a
  VBL), `FF 02 40` (256 calls: its counter `$16B2` starts at 0, cleared by `clear_game_vars`),
  `FF 07` (`$16D1`, the loop ends); with fire it ends at the first call from the 50th on
  (`clear_game_vars` also cleared the input lock `$804D` that type 32 had set). The bench's
  picture (10 / 0 / 0) matches `rc2front.py`'s pixel for pixel **[verified: bench]**.
- Brainstorm (`$8382`): intro, picture, PUZL (level 1 → 2: the disk-1 copy decrunched by
  `$124A6` from `$17080` to `$17100`; level 2 → 3: disk 2's at `$17100`), `jsr $17100` → D0 =
  0 solved (`$805E` + 1: a continue), 1 failed, 2 out of time; result text from `$840A`. The
  stage itself: *Brainstorm* below.
- Shooting range (`$8420`): intro, picture, FRNG (decrunched from `$1E980` to `$1EA00`; `$1880`
  and `$3FF0` patched at `$1FB34`/`$1FB38`), `jsr $1EA00` → D0 dummy targets, D1 correct
  targets. Time out (`$804C`): `$8060` = `$C72E` and `$11698`. Otherwise rating = max(0, min(3,
  (6 × correct − dummy − 50 − 12 × [timer minutes = 0]) div 14)): POOR, FAIR, GOOD, SHARP
  (`$1140D`), `$8060` = `$C716` + 24 − 8 × rating. The stage itself: *The shooting range* below.
- **Gun calibration = enemy hit points**: a spawned enemy (`$C512`, `$C706`) gets slot byte
  +`$21` (= +41h from `$BC4` in *Hit test*: one off per hit while ≥ 0, so n + 1 hits kill)
  from `$8060`'s table, indexed by its class, the word at `$BEB4` + 16 × type (0–7): SHARP
  `$C716` 0 1 1 2 3 3 4 99, GOOD `$C71E` 1 2 2 3 3 4 4 99, FAIR `$C726` 2 3 3 3 4 4 4 99, POOR
  and time out `$C72E` 3 3 3 4 4 4 5 99. Level 1 uses SHARP.

### Brainstorm (PUZL at `$17100`) **[verified: REA listings of `$8382` and of PUZL's 14 routines; bench runs of the original (`tools/amigaemu.py puzl`); an executable model equal to the original in every field of 17 scenarios, 20,280 passes]**

The port's design and the full spec (pseudo-code of the loop and the step): `docs/BRAINSTORM.md`
2. Names: `analysis/puzl_17100.sym`.

- **The image for REA.** PUZL lies at `$17100-$32CDF` (disk 2's plain `PUZL_25`, 113,632 bytes;
  disk 1's crunched copy at `$17080` decrunches to the same bytes). REA opens the level-1 RAM with
  PUZL over that range: `python3 -I tools/ramimage.py build/extracted build/ram/puzl RB1 MU1
  DATAL1 SPERMA PERMA PUZL_25` → `build/ram/puzl_full.bin` (sha256 `9c76e13f…a9431a`), raw-binary
  m68k, entry `0x0`, with `REA_GHIDRA_SEED_FILE` = `analysis/ghidra_seeds_puzl.tsv` (the main
  code's seeds plus `analysis/puzl_17100.sym`: `tools/ghidra_seeds.py` with the extra sym file;
  REA applies all of them, 0 failed). The two images differ only in `$17100-$32CDF`, so main-code
  answers hold for both; PUZL's seeds never go into `analysis/ghidra_seeds.tsv`, whose level
  images hold MU1 and DATAL1 there.
- **The caller.** `load_level1` `$8582`: statistics `$85D8`, Brainstorm `$8382` (D0 = 2), the
  range `$8420` (D0 = 1), three `nop`s at `$8596` where a 6-byte call was (the disk-2 prompt
  `$11BD2`, removed by the crack **[inferred]**), the level-2 briefing `$110F0`, PIC4, MU1, MADEX,
  DATAL2. `load_level2` `$8524` calls `$8382` with D0 = 4. `$8382` (136 bytes): D0 kept, the intro
  `$114AA` through `$10762`; `show_picture` `$11E06` (PIC3 / PIC5); `$10320` = `$1032E` (the VBL's
  music call becomes an `rts`); `$8036` = `$12558`; the loader `($C0)` with "PUZL" (`$8416`), A1 =
  0; when `$8050` < 2, `$124A6` decrunches `$17080` into `$17100`; `jsr $17100`; PZM's init and stop
  all (`$18000`, `$18004`); D0 × 4: 0 → `$805E` + 1; `jmp $10762` with A0 = `$840A`[D0] (`$1162F`,
  `$11667`, `$11698`). Afterwards the game reads only `$805E` and the score.
- **Memory map.** `$17100-$17193` and `$171B4-$17281` `puzl_main`; `$17194` the cursor frame
  offsets; `$17282` the music divider; `$17284`, `$1728E` the face masks and static shifts by
  `$B0A`; `$17298-$17447` the face, chip and board set-up routines; `$17448-$17737` 8 boards of 94
  bytes; `$17738-$1775F` 3 messages and a pad byte; `$17760-$17971` step, cell, stuck, glyph, LED;
  `$17972` LED thresholds; `$1797C` timer digits; `$179B6` the LED table (+ 38 bytes nothing
  references); `$179FC` button, light, bar; `$17ADE` light/bar rows; `$17AEE` an `rts` the fade
  branches to; `$17AF0` the fade; `$17B5A` the copper interrupt; `$17BEA` 18 zero bytes; `$17BFC`
  the copper list (to `$17D03`); `$17D04-$17D19` an RTE handler that acknowledges EXTER (INTREQ
  `$2000`), referenced by nothing (no xref, its address in no byte of the image); `$17D1A` the
  hardware init; `$17D6A`, `$17DAA` the palettes; `$17DE8` 8 cursor sprite frames of 64 bytes,
  `$17FE8` the "hidden" frame (24 zero bytes, then `$18000`); `$18000` PZM (MU1's player code and
  entries: `$18180` init, `$18194` stop all, `$181E8` stop tune, `$1824E` music, `$1822C` effect,
  `$18316` tick) and its 6 tunes; `$234E0` 32 chip tiles 16 × 16 × 4 planes; `$244E0` / `$25160`
  Murphy's / Ellen's face, 80 × 80 × 4 planes; `$25DE0` 4 static frames (a mask plane, then 4);
  `$29C60` 10 digits 8 × 16; `$29EE0` 2 lights, `$29F20` 2 bars, `$2A020` 2 buttons; `$2A320-$32C9F`
  the screen, 5 planes of 320 × 176, one buffer (plane 5 set only over the TV, `$1711C`).
- **Entry** (`$17100`): PZM init; SR `$2700`; `$17D1A` (`$FE14` through `$8028`, `$B00-$B21` = 0,
  vector `$6C` = `$17B5A`, COP1LC = `$17BFC`, INTENA `$E01C`, `$B19` = 0, `$B20` = FF); setup_timer
  (`$8018` → `$F9DC`) with `$0059`; `$804E` = 0; plane 5 over the TV; the visit by
  `cmpi.w #2,$8050` / `bmi` (`$17156`): the immediates `$173D4` (boards `$17448` / `$175C0`),
  `$17B20` (palette `$17D6A` / `$17DAA`), `$1729A` (face `$244E0` / `$25160`); `$B0A` = −2.
- **The loop.** `$17184`: D0 = `$B0A` + 2; 9 or more → D0 = 0, return; else `$173D2` with D0 / 2.
  `$171BA` waits for `$802C` (`irq_l1` counts the SOFT request the game's copper part `$10356`
  raises at line `$CE`: one pass a frame). A pass (`$171C2`): COLOR00 = 0, `$802C` = 0, `$B12` =
  `$17DE8` + `$17194`[`$B00` & `$1E`], fade, face, LED, timer, step, `$B02` + 3, `$B00` + 1, the music
  tick on 5 passes of 6 (`$17282`), decor, `message_ticker` (`$8020`), `read_joystick` (`$801C`: the
  next pass's step reads it), `panel_update_digits` (`$8004`). End checks (`$17230`): `$B1A` not 0
  and below 99 (signed) → loop; `$B17` or `$B16` (`$17264`): `$B04` = 6, `$B20` = 0, at fade 0 the
  next board or return 1; `$804C` (`$17254`): `$B20` = 0, at fade 0 return 2.
- **The rules.** A move per change of the whole joystick byte `$802E` against `$B1E` (fire
  included), the lowest direction bit first; refused past the edge, onto an IC (type 1) or a
  visited cell (≥ `$10`, a signed byte compare); a pass without a move attempt checks the four
  neighbours (`$178A4`): none free with red chips left → "MALFUNCTION.", `$B16`. The cursor's cell
  is burnt (+ `$10`) and redrawn every pass; a red chip (0) there gives 100 BCD (`$F6A0`), effect 3,
  `$B10` − 1, `$B17` at 0. `cell` (`$178E8`) has no bounds check. The 4th board's last red chip
  (`$B0A` = 6): `$B0A` = 8, "MEMORY RESTORED.", the face clean. A time out (`$804C`, the CIA-B
  handler `$1015E` below 0:00, the 61st tick after a set-up) queues "TIMEOUT." every pass. End
  sequences: after boards 0-2 a 31-pass fade-out with effect 6 every pass; after board 3 or a stuck
  `$B1A` counts to 99 and the result comes 129 passes after the event; a time out returns 80 passes
  after it. Every board: 1:00, tune 1; visit 1 starts at (0, 0) with 22 / 21 / 24 / 28 red chips,
  visit 2 at (5, 3) with 23 / 21 / 24 / 28 (each count = its type-0 cells); a full visit-1 solve
  scores 9,500. No random numbers. **[verified: REA, bench, model]**
- **State.** PUZL reuses `$B00-$B21` (the game's camera and buffers otherwise): `$B00` passes,
  `$B02` + 3 a pass, `$B04` the next pass's effect, `$B06` the board's cells, `$B0A` 2 × board,
  `$B0C`/`$B0E` the cursor, `$B10` red chips left, `$B12` the cursor's sprite frame, `$B16` failed,
  `$B17` done, `$B19` the fade level, `$B1A` the end count, `$B1E` the last joystick byte, `$B20`
  fade in / out; and the globals `$802E`, `$8046-$8049` (score), `$804A-$804C` (timer, time out),
  `$804E` (pause: cleared, never set), `$8050` (the visit), `$805E` (the caller). Three pointers and
  a tune number live in instructions (self-modifying code): `$173D4`, `$17B20`, `$1729A`, `$17441`.
- **Display.** The face shows when (`$B00` & mask) = 0 (masks 7 3 1 0 0 by board: 1 pass in 8, 4,
  2, then always), then a static frame (`$B00` >> shift) & 3 cut over it (shifts 1 1 1 2 0); one
  LED digit a pass; the timer as M:SS; the button, a scanning light and a board bar (rows from
  `$17ADE`); the cursor is hardware sprite 0, its frame `$B12` placed by the copper interrupt from
  `$B0C`/`$B0E`. PUZL's copper list ends with COPJMP2 to the game's `$10356`: the status panel shows
  below, with its digits and messages updated every pass and the energy can still. The fade limits
  every component of COLOR01-31 to (`$B19` >> 1) & `$1E`, 8 steps of 4 passes; at the end of every
  fade-out `$17B14` puts the palette pointer back to `$17D6A`, so a second visit's boards 1-3 fade in
  with the first visit's colours **[verified: bench]**.
- **Sound.** Every set-up: stop all, then tune 1 (3,000 ticks, no loop); effect 4 a move, 3 a red
  chip (refused in practice: effect 4 still holds channel 3 and 3 < 4, `$1822C`'s rule), 5 the start
  of boards 1-3, 6 every pass of a fade-out after boards 0-2; nothing in the end sequences. PZM's
  player is MU1's code (`tools/rc2music.py --verify` on PZM: 9,744 ticks, 0 differences). The text
  screens are silent.
- **Quirks** (kept by the port): the column `message_queue` leaves in D0 in the pass that ends the
  4th board, from which a move in that pass starts (`$8056` & `$C`), reading up to 3 bytes past the
  88 cells; a time out during a fade-out starts the next board with `$B1A` ≥ 99, its input ignored
  until its own time out; "TIMEOUT." queued every pass (the 4-slot queue fills and ticks on during
  the result screen); effect 6 on 31 passes in a row; the palette pointer reset above.
- **[inferred]** (display hardware the bench does not emulate): the cursor covers its cell when
  bitplane x 0 is at H `$80` (DDFSTRT `$34` with BPLCON1 `$FF` left by the panel), and the screen
  shows bitplane x 16-319; in the end sequences the sprite DMA reads 10 lines of PZM's entries
  through the "hidden" frame, a junk sprite on the last cell; a pass never slips a frame on a real
  Amiga; the messages left in the queue print on the panel during the result screen.

### The shooting range (FRNG at `$1EA00`) **[verified: REA listings of `$8420`, `$124A6` and FRNG's routines; bench runs of the original (`$8420`'s whole path, 9 drives); an executable model equal to the original in every compared field of 22 traces, 14,949 passes]**

Sources: the range's area reports of 2026-10-27 (flow, logic, gfx, sound, bench), on the image
below; the port's design, its full spec and what the build measured: `docs/RANGE.md` (sections 2
and 11), as Brainstorm's are in `docs/BRAINSTORM.md`. Names: `analysis/frng_1ea00.sym`.

- **The image for REA.** FRNG_15 (93,224 bytes, loaded at `$1E980`) decrunches into
  `$1EA00-$485D9` (170,970 bytes, sha256 `2ec1d6a4…b6d26f`). REA opens the level-1 RAM with those
  bytes there: `python3 -I tools/ramimage.py build/extracted build/ram/frng RB1 MU1 DATAL1 SPERMA
  PERMA FRNG@1ea00` (`NAME@ADDR`: the file decrunched by `tools/bytekiller.py`, placed at ADDR) →
  `build/ram/frng_full.bin` (sha256 `9470791f…5f3d91a`), raw-binary m68k, entry `0x0`, with
  `REA_GHIDRA_SEED_FILE` = `analysis/ghidra_seeds_frng.tsv` (the main code's seeds plus
  `analysis/frng_1ea00.sym`: `tools/ghidra_seeds.py` with the extra sym file; REA creates 161
  functions, finds 1 present and applies 261 labels, 0 failed). The REA MCP server's environment
  names `analysis/ghidra_seeds.tsv`: FRNG's seeds go through the REA CLI (the same rea-agents 6.7.0
  and Ghidra, `REA_GHIDRA_SEED_FILE` set, `--snapshot` to keep the analysis between calls) or a
  server started with that variable. The image differs from `level1_full.bin` only in
  `$1EA00-$485D9` (MU1's tail and DATAL1 there), so main-code answers hold for both; FRNG's seeds
  never go into `analysis/ghidra_seeds.tsv`. In the game's RAM `$1E980-$1E9FF` then holds the
  crunched file's first 128 bytes; the image keeps level 1's there (nothing reads them).
- **The caller** `$8420` (D0 = 1 from `load_level1` at `$8590`, D0 = 5 from `load_level2` at `$853C`;
  no other caller): the intro `$1142D` through `$10762`; `show_picture` (PIC2 / PIC6: D0 picks only
  the picture); `$10320` = `$1032E`; the loader with "FRNG" (`$841B`) at `$1E980`, then `$124A6`
  into `$1EA00`, on both visits; `clr.b $804C`; `$1FB34` = `$1880` and `$1FB38` = `$3FF0` (the
  values of the DIWSTRT and DIWSTOP moves in FRNG's copper list: the file holds `$0090` and
  `$3FF0`); `jsr $1EA00` → D0 = `$B06` dummy targets, D1 = `$B04` correct targets; then the time
  out or the rating (*Level statistics and bonus stages*). The rating formula matches the original
  `$8498-$8516` run on the bench in 5,043 cases (correct and dummy 0-40, minutes 0-2).
- **Memory map.** Code: `$1EA00` the entry, pass loop and end checks; `$1EB00` the sound delays;
  `$1EB5C` the crosshair; `$1ED5A` a bitmap line; `$1EDBC` the BOB draw with the hit test; `$1EF6A`
  the random word; `$1F0DA` the two slots; `$1F14E` the riser; `$1F32A` the walker;
  `$1F3F6`/`$1F44A` the big target's draw and erase; `$1F46E` a refusal; `$1F472-$1F501` 23 stubs
  (`lea` descriptor, `bra $1F50C`); `$1F50C` the pop-up handler; `$1F808`, `$1F83A`, `$1F940` the
  hit effect; `$1F980` the fade; `$1F9EA` the copper interrupt; `$1FB52` the hardware init;
  `$20000-$2CC61` FRM, the player with its tune and effects. Data: `$1EB30-$1EB5B` the music
  divider, "NO AMMO." and "TIME OUT.", the gun's variables, the restore list; `$1ED96` blit and clip
  masks; `$1EF88-$1F0D7` 42 script entries of 8 bytes; `$1F1C2-$1F215` the riser's tables;
  `$1F246-$1F329` the walkers'; `$1F46C` the big target's clip; `$1F502` 10 position locks;
  `$1F60E-$1F807` 23 descriptors of 22 bytes; `$1F8AA-$1F97D` the effects'; `$1FA8C` the sprite
  table and `$1FA9E-$1FB51` the copper list; `$1FBEA`/`$1FC2A` the palettes of visits 1 and 2;
  `$2CC62-$3E061` the graphics (pop-ups, walkers, riser, dissolves); `$3E062` the clean street, 5
  planes of 320 × 172; `$466C2` the priority plane. Outside the file: the screen `$769B0`, the
  sprite data `$7F330`, the hit test's mask buffer `$7FC50`.
- **Entry** (`$1EA00`): FRM init; set_weapon(0); ammo `$0025`; `$1FB52` (`$FE14` through `$8028`;
  the clean street to the screen; `$B00-$BC4` = 0; vector `$6C` = `$1F9EA`; COP1LC = `$1FA9E`; fade
  in; the palette by `$8050` (`$1FBBE`); setup_ciab_timer 2:00); `$804C` = 0; the crosshair at (240,
  72); tune 1, once; the two hit delays idle.
- **The loop.** `$1EA40` waits for raster line `$C0`: one pass a frame. A pass (`$1EA4A`): COLOR00
  = 0, fade, big erase, effect erase, random word, the slots (then the big target), effect draw,
  crosshair, `$B00` + 1, `$B02` + 3, the music tick on 4 passes of 5 (`$1EB30` starts at 1),
  read_joystick (for the next pass), panel digits, message ticker, sound delays. End checks
  (`$1EAA6`): `$B08` not 0: + 1, below 99 (signed) loop, then fade out, return at fade 0 (130 passes
  after the last shot); else ammo 0: "NO AMMO.", `$B08` = 1; else `$804C`: "TIME OUT." through
  `jmp $8008`, whose `rts` returns to `$847A` in that pass, with no fade-out.
- **The rules.** 25 shots (`$8030`, BCD; `$8010` per shot); fire held shoots every 25 passes
  (`$1EB48` from `$18`), and after a release (or with no ammo) the next press shoots at once. The
  crosshair: X `$B9A` from 240 within `$7C-$198`, Y `$B9E` from 72 within `$10-$9E`, 4 a pass, right
  before left and down before up; the hit pixel is bitplane x X − 111, row Y. Two slots (`$B2E`,
  `$B32`): an empty one spawns script (`$B00` & `$3F`) + 1, less 32 from 40 on (1-39); a refused
  script costs two passes. Pop-ups: 27 scripts through 23 stubs to 22 descriptors, 9 positions, one
  pop-up each. The riser (scripts 23-25, always armed) and the walkers (14-22, 16 kinds by `$B00` &
  `$1E`): one big target at a time (`$BA6`). A shot in pass n is tested by every draw of pass n + 1
  against the target's mask (a pop-up's less the priority plane: only what shows in its opening)
  and scored in pass n + 2; armed or dummy by the hit column from the BOB's word-aligned left edge
  (pop-ups: < the threshold, walkers: ≤). Correct: `$B04` + 1, and 10 passes later effect 3 and 25
  points (BCD); dummy: `$B06` + 1, and 10 passes later effect 4. A hit starts a dissolve unless one
  runs. The timer: 2:00, `$804C` set at the 121st CIA-B second. No random number is read: nothing
  reads `$B0C`. Visit 2 (`$8050` ≥ 2) changes only the palette.
- **State.** FRNG reuses `$B00-$BC5` (the game's camera, buffers and object slots otherwise; the sym
  file names each field) and the globals `$802E`, `$8030`, `$8046-$8049`, `$804A-$804C`, `$8050`,
  `$805C`. FRNG's own bytes hold state too, fresh from the file at every visit: the music divider
  `$1EB30`, the shot flag, fire repeat and recoil box `$1EB46-$1EB4B`, the walker's kind `$1F246`,
  the big clip `$1F46C`, the locks `$1F502` (position 6 locked in the file), the descriptors' +1,
  +`$12` and +`$13`; and four immediates the code rewrites: `$1EE42` (the draw's right clip),
  `$1EE76` (its C source), `$1EEC6` (its first blit's mode), `$1F9B0` (the fade's palette).
- **Display.** 320 × 172 in 5 planes at `$769B0`, one buffer restored from `$3E062`; the status panel
  below (COPJMP2 to `$10356`). The horizontal crosshair is a bitmap row in colour 31; the vertical
  one attached sprite pair 0, a 1-pixel column on rows 0-167; the fire box (32n × 32n, n = 8 → 0)
  has sprite sides (pairs 1 and 2) and bitmap top and bottom. The fade limits each component of
  COLOR01-31 to (`$BC1` >> 1) & `$1E`, one step a pass. Quirks: restoring the old crosshair row
  wipes that row from targets drawn in the same pass; the set-up copies 10 bytes short (row 171, x
  240-319, plane 4); a hit big target is drawn once more under its dissolve; **display quirk 4**
  (found 2026-10-27 by `tools/msxrange.py`'s model of the blits, then read in REA's listing of
  `$1EDBC`): a pop-up's blit 2 (`$1EF1C`: BLTCON0 `$FCA`, D = A·B + ¬A·C over the whole BLTSIZE)
  writes its whole word-aligned box from the clean copy, so it wipes, for that frame, the columns
  where its box meets another position's rectangle holding a pop-up drawn earlier in the same pass.
  Seven descriptors do it: `$1F6A8` and `$1F6D4` (steps 0-5, over position 3, x 126-127), `$1F6EA`
  (steps 0-4, over 1, x 58-63), `$1F716` and `$1F72C` (every step, over 5, x 236-239), `$1F7C6`
  (step 0, over 5, x 240-254: position 6, locked, never shows it), `$1F7F2` (step 0, over 3, x
  144-152). The port does not reproduce display quirks 1, 2 and 4 (zero-glitch rule).
- **Sound.** FRM is MU1's player relocated to `$20000` (entries `$20000-$20018`; its instructions
  equal MU1's but 6 per-file operands; `rc2music.py --verify` on it: 12,600 ticks, 0 differences).
  Tune 1 starts once (channels 0-2, 5,999 ticks, no loop) and nothing in FRNG stops it: the result
  text's `$FE14` does, within microseconds of FRNG's return (`$8474` returns to the rating
  `$847A-$8518`, which has no wait, then `$10762` → `$10768`, whose first act is `$FE14`). FRM ticks
  only from the pass loop (`$1EB30`), so the last tick heard is the last pass's. Effects on channel
  3: 2 a shot, 3 a correct hit (with the + 25), 4 a dummy hit, under `$2022C`'s priority rule; 5 is
  never requested. The text screens are silent.
- **Quirks** (kept by the port): the hit test accepts one row below a BOB, reading bytes earlier
  blits left (T1); position 6 never opens (T2); a split target's border moves with x & 15 (T3); a
  second armed hit within 10 passes loses one + 25 (T4); a time out in the NO AMMO. sequence still
  gives OUT OF TIME. and POOR (T5); the time out returns at once (T6); both slots spawn script 1 in
  pass 0 (T9); a hit on a pop-up in the pass it goes away is never scored (T10).
- **[inferred]** (display hardware the bench does not emulate, and timing): one pass a frame on a
  real Amiga (the bench counts 807-2,796 instructions and 552-8,928 blitter words a pass); the
  vertical line's and the box sides' bitplane x; the box sides hidden above line `$20` (sprite DMA
  from there); all 320 columns shown; the composer's tempo of 50 ticks a second (FRNG ticks 40 a
  second on PAL; at 50 the tune lasts the stage's 2:00); the 3 `nop`s at `$8596`, a disk-2 prompt
  the crack removed; `$1FC6A-$1FFFF` (an earlier build's code, "MUSRNG", "RNGBAK") and
  `$481A2-$485D9` (FFh) unused, as nothing references them.

### Game over, high scores and continues **[verified: code]**

- `main_loop` `$82A8`: PIC9 (251 VBLs or fire), 128 more VBLs, `high_score_entry` `$12082`,
  `$11FD2`; fire held → `init_lives` and `level_init` (same level, score kept), else `$8098`.
- Table `$11FF6` (it is particle text 0 of the attract script; in the code area, so kept in
  RAM only **[inferred]**): `"   TODAYS BEST "`, CR, then **6** entries of 19 bytes from
  `$12006` (`' '`, name of 9, `' '`, score of 7 digits `'['`–`'d'`, CR) and `FF 00` at
  `$12078`. Defaults: IAN 100000, KAREN 90000, COLIN 50000, KEITH 45000, ANDY 9000, PAUL 7500
  (`hiscores.json`).
- `high_score_entry` starts with `st.b $8032` (the key byte FFh, no key), which a continued game's
  `frame_keys` then takes as handled (`$8033`) **[verified: level 2's `cont` reference, `$8032` and
  `$8033` FFh after the continue, equal in the port's trace]**. Then the score `$8046` as 8 digit
  characters at `$1207A`; its low 7 against
  entry 6 (`$12070`), only a greater score goes on: entry 6 = the score and 9 spaces,
  `$12300` (HI1 restored or loaded, copper `$10356` meanwhile; tune 1), `$1215C`, fade out,
  24 bubble passes (18 bytes swapped when the upper score is lower: ties keep the older entry
  above). The `$FE14` of `$1215C`'s text screen stops all before the tune's first tick: only
  the effects are heard **[verified: code; audible result inferred]**.
- Name entry `$1215C`: script `$115C9`, then the field `$12066` (index `$15D0`) drawn by
  `$12218` at bitplane x 128 + 8i, lines 80–87 (no text origin); `'g'` (glyph `?`) marks the
  next position, first under the 2nd character. `$1225C` takes one key per press (latch
  `$15EF`), raw codes `$122C8` → characters `$12296`: A–Z, 0–9 (main row and keypad, stored as
  `'['`–`'d'`), Space; Backspace (`$41`) deletes the last one; Return (`$44`) or `$2B` ends;
  after 9 characters others are ignored. Every key starts effect 3; Return effect 4, the
  palette black and both buffers cleared.
- Continues `$805E`: 0 at a new game, + 1 per solved Brainstorm. `$11FD2`: − 1; if still ≥ 0,
  MU1 init and script `$11590`, and fire during it (or held when it ends) continues; else
  `$802E` cleared and the title. A continue restarts the level with 2 lives; on level 1,
  `restart_level0` shows the briefing and PIC1 again.

### Cheat mode **[verified: code]**

- `$11EDA` (title loop): sequences at `$11F36` (8 bytes each: sequence = progress, length, raw
  key codes; handler; `FFFFFFFF` ends); the only one is S E R I A L I N T E R F A C E, a wrong
  key restarts it. Handler `$11F60`: `$804F` set, CH1 tune 1, script `$1151B` (front buffer
  cleared); the title loop then goes on with that halted script until fire. In play
  (`main_loop` `$8144`): F10 (`$59`) sets `$16D0` (level complete), F9 (`$58`) energy `$102`.

## 6. Texts and content

Strings in the main code describe levels and objectives: *The River Rouge Complex*,
*Tokugawa Brewery*, *Civic Centrum*; collect 10 Nuke capsules and destroy the drugs lab;
rescue hostages; reach the roof and confront Cain. Bonus stages: *Gun Calibration*
(shooting range) and *Brainstorm* (chip puzzle). Items: *scatter gun*, *rapid fire*,
*three way gun*, *time gain/lost*, *reverse control*. There is a cheat mode (F keys for
energy and level skip; section 5).

## 7. Tools

| Tool | Purpose | Dependency |
|---|---|---|
| `tools/rc2files.py` | lists/extracts/decrunches the disk files | stdlib |
| `tools/pp20.py` | PowerPacker decruncher | stdlib |
| `tools/planar.py` | bitplanes (sequential/interleaved, HAM6) → PNG | stdlib |
| `tools/bobs.py` | BOB frames → PNG | stdlib |
| `tools/copper.py` | copper list decoder | stdlib |
| `tools/m68kdis.py` | quick listing (complements Ghidra) | Capstone |
| `tools/ghidra_seeds.py` | REA/Ghidra seeds from the jump tables | stdlib |
| `tools/ramimage.py` | per-level RAM images to open in REA (and Brainstorm's, with `PUZL_25`; the range's, with `FRNG@1ea00`: a file decrunched and placed at an address) | stdlib |
| `tools/bytekiller.py` | ByteKiller decruncher, the game's `$124A6` transcribed (FRNG, disk 1's PUZL) | stdlib |
| `tools/rea_dump_asm.sh` | bulk Ghidra assembly export through the REA CLI | REA |
| `tools/bobcatalog.py` | BOB catalogue and sheets from the exported assembly | stdlib |
| `tools/player.py` | RoboCop frames from the animation table | stdlib |
| `tools/amigaemu.py` | execution bench: `game` runs a level from its RAM image with a joystick script and traces the game variables per game frame (reference for the port's logic); `puzl` runs Brainstorm along the game's path (`$8382`'s loader and decruncher, `jsr $17100`) with a drive's joystick bytes and pokes, and traces PUZL's state per pass | Unicorn |
| `tools/tracecmp.py` | compares a bench trace with the MSX port's (`tools/openmsx_rc2.tcl` rc2_trace) | stdlib |
| `tools/puzlsolve.py` | solves Brainstorm's boards and writes the drive that plays them on the bench (`--quirk1`: a solve that shows quirk 1) | stdlib (Unicorn for the bot's run) |
| `tools/puzlcmp.py` | compares a bench trace of Brainstorm with the MSX port's (`rc2_pz_drive`), pass by pass (`analysis/puzl_ram.tsv`) | stdlib |
| `tools/rc2music.py` | model of the music/sound-effect player: tunes, instruments, samples and per-tick Paula state to `build/music/*.json`; `--verify` against the original code | stdlib (Unicorn for `--verify`) |
| `tools/rc2front.py` | front end from the RAM image: text scripts and particle texts, high-score table, bitmap and stroke fonts, logo fly-in, renders of every screen → `build/front/` | stdlib |

Code analysis: **REA + Ghidra** (project rule, see `CLAUDE.md`). Targets to open in REA:
`build/ram/level1_full.bin` (whole level-1 RAM, entry `$0` with `JMP $8000`) or
`build/ram/level1_8000.bin`. Entries reached only through jump tables are seeded into
Ghidra by `analysis/ghidra_seeds.tsv` (generated by `tools/ghidra_seeds.py` from
`analysis/main_8000.sym`). Brainstorm has an image and seeds of its own: `build/ram/puzl_full.bin`
(`tools/ramimage.py ... PUZL_25`) with `analysis/ghidra_seeds_puzl.tsv` (`tools/ghidra_seeds.py`
with `analysis/puzl_17100.sym` after the main sym file); section 5, *Brainstorm*. So has the
shooting range: `build/ram/frng_full.bin` (`tools/ramimage.py ... FRNG@1ea00`) with
`analysis/ghidra_seeds_frng.tsv` (with `analysis/frng_1ea00.sym`), through the REA CLI; section 5,
*The shooting range*.
