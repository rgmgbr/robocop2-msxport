# Level 2 on the MSX: characters and BOBs (area "sprites")

Written 2026-10-27 for the level-2 phase. Repository read at `3c3a735` (branch `range`). Nothing in the
repository was written. No emulator was run.

All paths below are relative to this folder:
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/l2/sprites/`.

Evidence and method:
- **Amiga code.** Read with REA (Ghidra provider, raw-binary m68k, entry 0x0, seeds `analysis/ghidra_seeds.tsv`)
  on `build/ram/level2_full.bin`. The table dumps are in `rea/*.hex`, and `l2cat.py` checks that each one
  equals the RAM image's bytes.
- **Names.** The names found are in `level2_sprites.sym`, in the format of `analysis/*.sym`.
- **Converter.** The project's converter was run from a copy of `tools/` (`tools/`, run with `python -B`),
  with all outputs in `out/`. It reproduces level 1 byte for byte: `out/l1chk/robocop.bin` and
  `robocop_field.bin` equal `build/msx/robocop.bin` and `robocop_field.bin` (`cmp`).

## 1. Summary

1. **What level 2 draws.** 229 distinct frames (address and blit size), listed in `out/l2_frames.json`.
   - 60 are not in level 1's MSX data:
     - 48 sprite frames of level 2's own objects (DATAL2): types 1, 5, 6 and 49;
     - 8 play-field frames of level 2's own objects: types 2, 14 and 16's body;
     - 4 frames of type 4 that level 1 never drew.
   - 169 are level 1's: MADEX, SPERMA and PERMA frames that level 2 also draws.
   - **MADEX holds nothing new.** It is DATAL1's tail byte for byte, so its explosions, smoke, hostage
     and nuke frames are all level 1's.
2. **Sprites or play field.**
   - **Hardware sprites:**
     - type 1, as 16 joint compositions (legs and torso together; see decision D2);
     - types 5, 6 and 49;
     - the walker legs of type 16;
     - everything shared with level 1.
   - **Play field:**
     - type 2 (48 × 56), type 14 (48 × 36) and type 16's body (48 × 24);
     - the trolley `$8F02` (32 × 47, ridden) and the lift;
     - the hostage, the explosions and the smoke.
   - Types 2, 14 and 16 also keep a one-layer sprite silhouette, for their white flash.
3. **ROM, measured with the real converter.**
   - **Sprite pool.** With one global pool, level 2 adds 19.5 KiB:
     - 347 patterns, 245 colour rows, 4,372 B of records and a 612-byte level-2 BOB index;
     - this takes the blob from 23 to 27 banks.
     - RoboCop converts byte-identical (294 of 294 index entries).
   - **A blob of its own** (today's pipeline) would take 23 banks.
   - **Play-field atlas:** 9,722 B, so 2 banks.
   - **Explosions and smoke:** 0 new bytes. Their frames are byte-identical to level 1's (banks 50-51).
4. **Two engine limits, with sensible defaults.**
   - **The atlas.** Level 2 needs 108 atlas lines, but there are 88 above the dynamic slot.
     - Default: move the dynamic slot to page 2 for level 2. The tile cache keeps 224 slots.
     - Alternative: crop the frames to their pixel boxes and stream type 16's body (82 lines).
   - **BOB ids.** Level 2 needs 204 sprite frame ids, but only 200 fit below `FIELD_ID0` (C8h).
     - Default: `FIELD_ID0` D0h.
5. **Two-part characters.** Drawn as two parts, as level 1's walkers are, type 1 has up to 5-6 sprites on a
   line, and 8-9 with its gun flash. Beside RoboCop (5 a line), the VDP would hide some of its sprites.
   - Default: convert type 1 as one composition per step, legs and torso together. That keeps it within
     3 a line by construction, for +1.0 KiB.

## 2. Verified facts (REA on `level2_full.bin`, unless stated)

### Level 2's tables
- **Level header at `$868C`** (`rea/8664.hex`):
  - objects `$A828`, hazards `$95B2`;
  - special objects `$8FE0`, spawns `$97B0`;
  - markers (+24) `$C5EC`;
  - lowest camera `$270`;
  - palette (+36) `$10036`.
- **Spawn list `$97B0`** (`rea/spawn_97b0.hex`, 39 entries up to `$99E0`):

  | Type | Entries |
  |---|---:|
  | 45 | 10 |
  | 5 | 9 |
  | 49 | 6 |
  | 13 | 5 |
  | 12 | 3 |
  | 1 | 2 |
  | 4 | 2 |
  | 2 | 1 |
  | 6 | 1 |
  | 14 | 1 |

- **Marker spawns `$C5EC`** (`rea/c59c.hex`): types 3, 4, 12, 13, 14, 15, 16, 30 and 31.
- **Special objects `$8FE0` → `$9088`-`$910E`** (`rea/8fe0.hex`, `rea/9088.hex`):
  - 5 lifts (`$8DE6`) at x `$AE`, `$21E`, `$9EE`, `$EF` and `$9EF`;
  - 4 trolleys (`$8F02`) at x `$340`, `$510`, `$628` and `$7E0`, each running between two x values of
    its record.

### Palette
- **Level 2's palette `$10036`** differs from level 1's `$FFF6` in background colours 5, 6, 10, 11 and 15
  (`rea/fff6.hex`):

  | Colour | Level 1 | Level 2 |
  |---|---|---|
  | 5 | #024 | #03A |
  | 6 | #012 | #025 |
  | 10 | #B00 | #A00 |
  | 11 | #800 | #700 |
  | 15 | #CCC | #BBB |

  Sprite colours 17-31 are identical in both levels.
- **On level 1's MSX palette** (`build/msx/robocop.pal`), only colour 6 lands on another entry: MSX 13
  (001) in level 1, MSX 11 (012) in level 2 (`pal_cmp.py`).

### MADEX
- **MADEX is DATAL1's tail.** `MADEX_17.bin` (25,340 B at `$45250`) equals `DATAL1_10.bin` from
  `$45250` to `$4B54C` byte for byte.
- In level 1, DATAL1 itself fills that range (`$28000`-`$4B54C`).

### Draw calls and the white flash
- **Every draw call** goes through `draw_bob` `$AB08`, directly or through one of these wrappers:

  | Wrapper | Callers |
  |---|---|
  | `$AC44` | 21 |
  | `$AC56` | 34 |
  | `$AC6E` | 3 |
  | `$AC84` | 1 |

  `xrefs` lists every caller. No draw call exists in `level_tick_1` `$91BC` or `act_0c` `$9EE8`.
- **The white flash.**
  - `$AC44` and `$AC56` draw the white silhouette (minterm `$BFA` patched at `$AC16`) while the object's
    hit flag `+$22` is set. `$AC56` clears the flag after drawing.
  - `$AC6E` always draws the silhouette. Type 2 jumps to it every other 8 frames
    (`$C902`-`$C916`: `jmp ($C912 + ($B00 & 8) / 2)`), so it blinks white for its whole life.

### Level 2's own objects

| Object (handler) | Frames: address, blit size | How it draws (REA) |
|---|---|---|
| Type 1, walking gunman (`$C736`) | Legs `$3E810 + $C7E0[k]`: 16 × 32 × 23 (8 left, 8 mirrored right). Torso `$404D0` (left), `$40674` (right, its mirror): 32 × 21. Gun flash `$6CDA0` / `$6CEE0`: 32 × 16, PERMA. | Legs at (x, y + 21) through `$AC44`. Torso at (x ∓ 2, y + `$C800[step]` (1, 1, 0, 0, …)) through `$AC56`. Flash at (x − 24 or x + 40, y + 8) when (`$B00` & 2Dh) = 0. Fires bullet type 6. Walks with `$EF42` (4 px). |
| Type 2, armed suspect to arrest (`$C868`) | `$3D280` for the first 70 ticks, then `$3D910`: 48 × 56. Gun flash `$6CDA0`. | x fixed at `$180`. Every 64 frames it queues "ARREST ARMED EMEMY." (`$DC76`). Blinks white (above). Fires bullet type 5. Death `$C2D8`: energy −30h, "SUSPECT DESTROYED.", the big explosion. |
| Type 5, falling debris (`$D0E2`) | `$3BFC0 + $D19A[k]` with BLTSIZE `$D17C[k]`, k = 0-10: 9 distinct frames, 5 × 16 × 16 and 4 × 32 × 16 | Falls, splashes, then removes itself. Touching it costs energy −0Ah. |
| Type 6, bouncing tyre (`$D1E2`) | `$3C920 + $D2DA[k]`, 8 entries, 5 distinct (`$3C920`, `$3CB00`, `$3CCE0`, `$3CEC0`, `$3D0A0`): 32 × 24 | Moves right only (x += 3): one side. Death `$C33E` drops a pickup every 4th time. |
| Type 14, gunner that stays put (`$CE0A`) | `$3DFA0` (left), `$3E3D8` (right, its exact mirror): 48 × 36 | Faces RoboCop. When (`$B00` & 2Fh) = 0, twice in 64 frames: muzzle smoke (explosion type 1) and bullet type 4. Death `$C2EE`: explosion `$0408`. |
| Type 16, walking bazooka man (`$CD7A`) | Legs: walker1 `$C948` (SPERMA, shared). Body `$40818` / `$40DB8` (left: standing, then aiming once its count reaches 14h), `$40AE8` / `$41088` (their mirrors): 48 × 24. Gun flash. | Body at (x − 9 (+4 when aiming) (+18 facing right), y + bob + 2 (+2 when aiming)) through `$AC56`. Flash and bullet type 5/6 every 8 counts from 1Eh. |
| Type 49, homing missile (`$E6C0` → body `$E728`, shared with type 38) | `$41358 + $E7B2[dir]`: 16 directions × 16 × 16. Only 415D8 / 41AD8 are mirrors. | Turns toward its aim (speeds `$E680` / `$E6A0`). Touching it costs energy −18h. At its end: explosion type 0. |
| Trolley `$8F02` (special, offset 4) | `$4B95A` (SPERMA): 32 × 47 | Moves ±2 px between its path's x. Drawn at (x + 10h, y − 54h). RoboCop rides it: states 14/15 at `$1696`, platform entry left x, right x + 10h, top y + 14h. |
| Lift `$8DE6` | `$4B68A`: 48 × 24 | As in level 1. |

### Shared objects and the gaps the catalogue had
- **Shared objects level 2 runs:** types 3, 4, 12, 13, 15, 30, 31 and the hostage 45.
- **Their frame tables:**
  - walker1 `$C9A4`-`$CA13`;
  - gunman `$CB12`-`$CB6D`;
  - type 3 / walker2 `$CBAA`-`$CC49`;
  - type 4 `$D046`-`$D0A5`.

  Level 1's bench coverage holds every frame of these tables but four: type 4's torso aims 0
  (`$58312`, 32 × 38), 4 (`$57912`) and 7 (`$58092`, both 32 × 32), and its muzzle flash 4 (`$6C8A0`).
  The level-1 MSX data lacks them too, so level 1 can also lose type 4's torso at those aims.
- **Scan errors in `tools/bobcatalog.py`'s catalogue:**
  - type 4's torso is listed as 8 frames of 16 × 16 at `$57192`… (the real size is in `$D096`:
    `$803` and `$983`);
  - type 15 is listed with `$4ED26` as 16 × 16.

  Both are converted and stored in level 1's data today, but never drawn.
- **What the catalogue misses for level 2:**
  - type 2's first frame `$3D280` (the scan keeps only the last `lea`);
  - type 6's `$3D0A0` (the table walk stops at the first repeated offset);
  - types 5 and 49 entirely (BLTSIZE taken from a table; A2 set in the shared body);
  - it assigns type 16's body to level 2 only by mask score.

### Explosions and bullets
- **Explosions** (`spawn_explosion` `$F366`; tables `$F140`, `$F1C6`, `$F3BC`, `$F3C5`). Level 2's deaths
  and effects spawn:
  - `$0408` (`$C2EE`: types 2, 3 and 14);
  - 4 (`$C31E`: types 1, 4, 12, 13, 15, 16, 30, 31 and the hostage);
  - 0-3 (type 6's death: `$15F2` & 3);
  - 1 (type 14's shot);
  - 0 (type 49's end).

  All of their frames are in level 1's MSX data. Types 5 and 6 of the explosion table would draw DATAL
  addresses (`$3D780`…), which in level 2 hold type 2's frames, but level 2 never spawns them.
- **Enemy bullets** (`ebullet_add` `$F5BC`: D6 = type; frame tables `$F4A4` / `$F500` / `$F55C`, read at
  +4t). Level 2 uses types 1-6 (1-2: type 3's missile; 3: types 4, 15, 30 and 31; 4: type 14; 5: types 2
  and 16; 6: types 1 and 16). All of their frames are in level 1's data.

## 3. Inferences (not verified)

- **Type 49's death path.** A shot that kills a type-49 missile (if its flags allow it) reaches
  `death_expl` `$C35A` with D5 = 0198h. `update_objects` passes the death routine's own descriptor offset
  in D5 (`$C40E`, `$C42A`). That D5 would start an explosion from table bytes `$F454` (E6h) to `$F45D`
  (41h): garbage frames on the Amiga, nothing on the MSX. To be checked on the bench by the logic area.
- **Tiles in view.** "At most 107 distinct tiles in view" comes from `docs/ROM_BUDGET.md` 3.2 and was not
  re-measured here. The VRAM default (D4) relies on it.
- **RoboCop's hanging poses.** States 14 and 15 come into use with the trolley. They are part of
  RoboCop's shared data (all 69 records × 4 aims are converted), but level 1 never shows them, so their
  look has not been reviewed.

## 4. The binding decisions applied

### Per line and in all (`compose_l2.py`, `out/compose_l2.txt`)

Each part's converted record is placed where the original draws it and the sprites are counted per line.
RoboCop reaches 5 a line in 38 of his 144 compositions and uses 11-18 sprites (`RC_CAP` 5). The binding
budget is: enemy ≤ 3 on every line it shares with RoboCop, and RoboCop + spark + enemy ≤ 30.

| Character (MSX) | Most a line | Sprites | Verdict |
|---|---:|---:|---|
| Type 1 as parts (legs, torso) | 5-6 (9-14 lines above 3) | 9-11 | Over: beside RoboCop the VDP hides its last sprites |
| Type 1 as parts + gun flash | 8-9 | 12-14 | Over |
| **Type 1 as joint compositions** | **3** | **7-8** | **Fits (default)**. The gun flash (3) is an effect and gives way |
| Type 2, field + white-flash silhouette | 3 | 8 (one layer) | Fits; + gun flash = 6, and the flash gives way |
| Type 14, field + hit-flash silhouette | 3 | 7 | Fits |
| Type 16: walker1 legs (body in the field) | 3 | 5-6 | Fits; + gun flash 5-6 on 1 line; + hit silhouette 8-9 on 19 lines (give way) |
| Type 5 | 2-3 | 2-3 | Fits |
| Type 6 | 3 | 6 | Fits |
| Type 49 | 2 | 2 | Fits |
| Types 3, 15, 30, 31 (shared, parts as in level 1) | as level 1 | as level 1 | Known overflow of level 1 ("RoboCop 4 + legs 3 + torso 2") |

- **The 32-sprite limit.** RoboCop 18 + spark 2 + type 1 joint 8 = 28 ≤ 30. Muzzle flashes, bullets and
  silhouettes are effects: they are left out first, as the budget does today.

### Defaults chosen, each with its alternative

The user is away; these are the defaults.

- **D1. Palette.**
  - Default: level 1's MSX palette for the sprites, so RoboCop is byte-identical. Shared frames keep
    level 1's conversion; level 2's own frames are read with level 2's Amiga colours.
  - Alternative: read every frame with level 2's colours. That costs 26.2 KiB instead of 18.5-19.5,
    because 32 shared frames change through colour 6.
  - Note: the palette has no saturated blue. Type 1's blue shirt (#03A) becomes 012, a dark navy
    (see the sheets). A per-level background palette (the tiles area's choice) would fix that, but the
    shared BOB frames would then have to be converted again.
- **D2. Type 1.**
  - Default: 16 joint compositions, 48 × 44 (8 steps + 8 mirrors).
  - Alternative: parts, as level 1's walkers do (−1.0 KiB, but 5-6 a line).
  - Cost: on wide strides all three boxes of a line keep one layer, so the dithered trousers show
    solid grey wedges (also visible in the parts version).
- **D3. The play field and flashes.**
  - Types 2, 14 and 16's body go into the play field. Their white flash shows as the sprite silhouette,
    as level 1's gunners do (`FIELD_FLASH` = obj02, obj14, obj16).
  - The trolley is `FIELD_RIDDEN`, like the lift.
  - Alternative for type 16: legs and body as one sprite composition. Its boxes would keep one layer —
    the look the user rejected for the gunners.
- **D4. VRAM for the atlas.**
  - The need: 108 lines for level 2's static frames (shelf packing of `field_frames`: 56 + 28 + 24).
    Today only 88 lines sit above the dynamic slot.
  - Default: in level 2 the dynamic slot (256 × 24) moves to page 2 lines 224-247, and the atlas takes
    page 3 lines 0-111. The tile cache has 224 slots instead of 256 (rows 14-15). Level 1 stays as it is.
  - Alternative (no VRAM change): crop atlas frames to their pixel boxes and stream type 16's 4 bodies
    through the dynamic slot, which gives 82 lines (`pack_trim.py`). But type 16 walks and changes frame
    often, and it would compete with explosions for the slot.
  - Not enough alone:

    | Option | Atlas lines |
    |---|---:|
    | Cropping only | 104 |
    | Cropping + streaming type 2 | 89 |
    | Streaming type 14 without cropping | 108 |
- **D5. BOB ids.**
  - The need: level 2 needs 204 sprite frame ids (206 with parts), the hit spark's four included.
    `FIELD_ID0` is C8h (200), and 35 play-field frames come after it.
  - Default: `FIELD_ID0` D0h for both levels (level 1 still fits: 198 + 40), with `SPR_SPARK` and
    `SPR_BOB_INDEX` per level.
  - Alternative: drop the 8 silhouettes (198 ids). That loses type 2's blinking, a gameplay cue (arrest,
    don't shoot).
- **D6. One global pool.**
  - Level 1's patterns, colour rows and records are reused. Each level has its own BOB index, ids,
    BOBHASH and atlas, and the dynamic frames stay shared.
  - Alternative: a 23-bank blob per level.
- **D7. Frames removed.**
  - Level 1's choices (`msx/level1_frames.json`) apply to the shared data: RoboCop must, since his data
    is identical, and the hostage is the same character.
  - Every new level-2 frame is kept until the user chooses in a level-2 frame chooser.
- **D8. Muzzle flashes and silhouettes are effects.**
  - Enemies' gun flashes (32 × 16) and the play-field silhouettes give way when a line would pass 8.
    They are left out for that picture, and no character piece is ever touched.
- **D9. Types 5 and 49 stay counted by `ENEMY_CAP`, as the code does today.**
  - Then they are never on screen with another enemy, so the line budget holds.
  - Alternative: exempt them, which is more faithful to the original. But they would then have to be
    effects that can vanish: an invisible hazard.
- **D10. Type 4's gaps.**
  - Add type 4's three missing torso aims and flash 4 to the shared pool (≈1 KiB). Level 1 benefits too.

## 5. The pipeline for level 2

### What changes

- **`tools/bobcatalog.py`.**
  - Level 2's REA-verified frames: `mk_l2_inputs.py` holds them. They can become `HARD_REFS`-like
    entries, or a level-2 table.
  - Fix the table walk, which stops at the first repeated offset.
  - Read BLTSIZE from a table, not only from `move.w #imm, D4`.
  - Drop the type 4/15 16 × 16 scan errors.
- **`tools/msxsprites.py`.**
  1. One run for several levels: a global pattern/row/record pool, and per level its BOB index, ids,
     `FIELD_ID0`, `SPR_SPARK`, atlas and field tables.
  2. The `FIELD_*` constants per level. Level 2:
     - `FIELD_PROCS` obj45, obj02, obj14, obj16, `FUN_00008de6`, `FUN_00008f02`;
     - `FIELD_RIDDEN` lift and trolley;
     - `FIELD_FLASH` obj02, obj14, obj16.
  3. Level 2's atlas: 108 lines (`FIELD_H` and the dynamic slot's place per level); the atlas ROM is
     `FIELD_ROM` 2 banks.
  4. Joint compositions: a frame kind built from parts and their offsets, for type 1.
  5. The level's Amiga palette for the level's own frames, with level 1's MSX palette fixed.
- **`tools/msxframe.py`.** It rebuilds the same layouts for the checks, so it follows items 1-4.
- **`tools/recframes.py`.** Takes the level's data paths. Level 2 adds RoboCop's states 14 and 15
  (hanging) to check.
- **`msx/level2_frames.json`.** The user's level-2 removals (empty by default).
- **The frame chooser.**
  - `build/review/quadros.html` has no generator in `tools/` (grep finds none). Its data is
    `{palette, sppal, bgpal, groups[{section, name, anim, items[{key, label, views, also, field,
    per_line, sprites}]}]}`.
  - Add a generator (for example `tools/msxchooser.py`). For level 2 it would add a "Nível 2" section:
    - type 1 (joint), types 2, 5, 6, 14, 16 (body and legs), 49 and the trolley;
    - type 4's three new aims;
    - RoboCop's hanging states 14/15.

### Shared pools, measured
- **RoboCop:** 294 of 294 index entries identical in content.
- **BOB frames:** 146 of 204 (joint) or 206 (parts) are identical to a level-1 record. They need only an
  index entry each.

## 6. Sizes and banks (measured: `run_l2.py`, `pool_l2.py`; `out/pool_*.txt`)

### Sprite pool

| Variant | New patterns | New colour rows | New records | Level-2 index | Total | Banks added |
|---|---:|---:|---:|---:|---:|---|
| Parts, level 1's conversion for shared frames (`out/l2_V_l1`) | 333 (10,656 B) | 235 (3,760 B) | 3,908 B | 618 B | 18.5 KiB | +3 (patterns 13→15, rows 4→5; records fit level 1's last area bank) |
| **Type 1 joint (default, `out/l2_VJ_l1`)** | 347 (11,104 B) | 245 (3,920 B) | 4,372 B | 612 B | **19.5 KiB** | **+4** (patterns 13→15, rows 4→5, area 6→7: 4,984 B against 4,812 B free) |
| Parts, every frame from level 2's colours (`out/l2_V_l2`) | 440 | 336 | 6,744 B | 618 B | 26.2 KiB | +4/+5 |
| A level-2 blob of its own, today's pipeline | — | — | — | — | 184 KiB | 23 |

`ROM_BUDGET` 3.4 estimated level 2's pool data at 17.1 / 20.8 / 22.9 KiB (low, likely, high). The
measurement, 18.5-19.5 KiB, falls in that range.

### Play field

| Item | Size |
|---|---|
| Atlas ROM | 9,722 B = 2 banks (level 1's: 7,373 B, 1 bank). `ROM_BUDGET` planned 2 banks for atlas plus streaming; here all of it is static. |
| Dynamic frames | 0 new bytes: `out/l2_V_l1/robocop_fdyn.bin` equals level 1's (`cmp`) |

### Level 2's sprite area in all
- +4 banks of pool and 2 of atlas.
- Shared banks: the dynamic frames (50-51) and the global pool.

### Placement and the cache budget
- **Placement.** The pools are addressed by id from `SPR_PAT_BANK` / `SPR_COL_BANK` and must be
  contiguous. So the global blob is built once (levels 1 + 2), and the banks after it move. Level 1's
  0.1.x images are unaffected.
- **Pico+ cache** (`docs/PICO_CACHE.md`: ≤ 53 banks a level). Level 2's working set takes about 27
  sprite banks.
- **Saving.** Sort the pools as [shared][level 1 only][level 2 only] to drop about 1 bank from each
  level's working set.

## 7. Previews (Amiga | MSX, 3×; in-game colour grade)

- **`previews/`** (type 1 as parts):
  - `type1_parts.png`;
  - `type2_field.png`, `type2_flash.png` (the sprite version, shown only as the silhouette);
  - `type5.png`, `type6.png`;
  - `type14_field.png`, `type16_field.png`, `type16_legs.png`;
  - `type49.png`, `trolley_field.png`;
  - `type4_new.png`.
- **`previews_joint/type1_joint.png`**: type 1 as joint compositions, left and right.

Notes from looking at them:
- **Faithful:** type 2, 14 and 16's bodies (play field, 16 colours), type 49 and type 5.
- **Type 6:** the tyre loses its inner ring (one OR box a line).
- **Type 1:** the legs show solid grey wedges where the Amiga dithers.

## 8. Files

| File | Content |
|---|---|
| `SPRITES2.md` | This report |
| `level2_sprites.sym` | Names found (REA) |
| `rea/*.hex` | REA byte dumps (checked against the image) |
| `l2cat.py` → `out/l2_frames.json`, `out/l2cat.log` | The catalogue (229 frames: object, role, side, size, pixel box, colours, mirror, renderer, level-1 status) |
| `mk_l2_inputs.py` → `in/catalog_l2.json`, `in/drawn_l2.json` | The converter's level-2 inputs |
| `run_l2.py` | The project's converter with level-2 settings (palette, field, atlas lines, banks, previews) |
| `synth_t1.py` | Type 1's joint compositions |
| `pool_l2.py` | Pool growth against level 1 |
| `compose_l2.py` | Per-line counts |
| `pack_trim.py` | Atlas lines (blit or pixel boxes) |
| `sheets_l2.py` | The contact sheets |
| `pal_cmp.py` | The palette check |
| `out/l1chk/` | Level 1 reproduced byte for byte |
| `out/l2_V_l1/`, `out/l2_VJ_l1/`, `out/l2_V_l2/` | Level 2's converted data (`.bin`, `.inc`, `.json`, `_field.*`, `_bobs.png`) |
| `out/l2_static_*`, `out/l2_dyn14*` | Runs that fail. Their logs show the atlas overflow, and a gap of the converter: a streamed frame cannot have a silhouette. |
