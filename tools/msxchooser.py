#!/usr/bin/env python3
"""The frame chooser page (build/review/quadros.html): every animation frame at its full look, the
Amiga's beside the MSX's, for the user to remove frames (their list comes back as JSON, which goes
into msx/level1_frames.json, msx/level2_frames.json and msx/level3_frames.json for tools/msxsprites.py).

It reads the converter's outputs (tools/msxsprites.py --pool: POOL.bin, .inc, _l1.json, _l2.json,
_l1_field_vram.bin, _l2_field_vram.bin): the MSX views are the records the ROM holds, decoded
(msxsprites.SpriteData), and the play-field frames their atlas's pixels; the Amiga views come from
the RAM images. Sections:
  - RoboCop: every state's steps (both sides: the left one is the right one mirrored), the hanging
    poses of states 14/15 (level 2's trolleys) included;
  - level 1: its BOB frames (enemies, objects, the hostage) as level 1 shows them;
  - level 2: the frames level 1 never showed: type 1 (joint compositions), types 2, 5, 6, 14,
    16 (its body; its legs are walker1's, shared), 49, the trolley, type 4's new aims and muzzle
    flash; every one kept until the user chooses (msx/level2_frames.json);
  - level 3: its own frames (DATAL3's: Cain, type 21, the truck, types 34-39 and 50-52, the lift's two
    parts; docs/LEVEL3.md 3.5): its sprite frames' records, its play-field frames from its atlas or its
    frame cache (the big animated ones); every one kept until the user chooses (msx/level3_frames.json,
    docs/LEVEL3.md default 14).
A frame that is another's exact mirror shares its card (a removal goes for both). The MSX colours
are the game's (the joint palette, palette C in level 2, through the colour grade).

--sheet OUT.png also writes a contact sheet of level 2's section: per frame the Amiga's look
beside the MSX's (3x), for the review.

usage: msxchooser.py POOL OUT.html [--sheet OUT.png] [--level1-frames msx/level1_frames.json]
                     [--level2-frames msx/level2_frames.json] [--level3-frames msx/level3_frames.json]
       (e.g. msxchooser.py build/msx/sprites build/review/quadros.html)
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import msxsprites as ms  # noqa: E402
import player  # noqa: E402
from msxbright import BRIGHT  # noqa: E402
from planar import write_png  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATES = {0: "Walk", 2: "Stand", 4: "Jump / fall", 6: "Punch (down + fire)", 8: "Crouch", 10: "Level start",
          12: "Firing on a special floor", 14: "Hanging (level 2's trolleys)", 16: "Death"}
L2_OBJECTS = (("type 1 (walking gunman: legs and torso as one composition)", ("obj01_joint",)),
              ("type 2 (the armed suspect: play field; its blink as a sprite silhouette)", ("obj02_update",)),
              ("type 5 (falling debris)", ("obj05_update",)),
              ("type 6 (bouncing tyre)", ("obj06_update",)),
              ("type 14 (gunner that stays put: play field)", ("obj14_update",)),
              ("type 16 (bazooka man: its body in the play field)", ("obj16_update",)),
              ("type 16's legs (walker1, shared with level 1)", ("FUN_0000c948",)),
              ("type 49 (homing missile)", ("obj49_update",)),
              ("the trolley (play field)", ("FUN_00008f02",)),
              ("type 4's aims level 1 never showed", ("obj04_update",)))


def hexrgb(c) -> str:
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


def graded(pal: np.ndarray) -> list[str]:
    return [hexrgb([BRIGHT[int(round(v * 7))] * 255 // 7 for v in c]) for c in pal]


def amiga(pal: np.ndarray) -> list[str]:
    return [hexrgb([round(v * 255) for v in c]) for c in pal]


def trim(img: np.ndarray, clear: int) -> tuple[np.ndarray, int, int]:
    """img without its clear rows and columns -> (img, y, x)."""
    m = img != clear
    if not m.any():
        return img[:1, :1], 0, 0
    ys, xs = np.nonzero(m)
    return img[ys.min():ys.max() + 1, xs.min():xs.max() + 1], int(ys.min()), int(xs.min())


def view(cap: str, img: np.ndarray, pal: str, clear: int, oy: int, ox: int) -> dict:
    t, y, x = trim(img, clear)
    return {"cap": cap, "grid": t.astype(int).tolist(), "pal": pal, "clear": clear, "ox": ox + x, "oy": oy + y}


class Pool:
    """The converter's pool and what each level shows."""

    def __init__(self, prefix: Path):
        self.sd = ms.SpriteData(prefix.with_suffix(".bin"), prefix.with_suffix(".inc"))
        ns = (1, 2, 3) if prefix.with_name(f"{prefix.name}_l3.json").exists() else (1, 2)
        self.levels = {n: json.loads(prefix.with_name(f"{prefix.name}_l{n}.json").read_text()) for n in ns}
        self.atlas = {n: np.frombuffer(prefix.with_name(f"{prefix.name}_l{n}_field_vram.bin").read_bytes(), np.uint8)
                      for n in ns}
        if 3 in ns:                                     # (level 3's frame cache: its big frames)
            import msxframe
            self.looks3 = msxframe.FieldLooks(3, prefix)

    def bob(self, level: int, k: int, one: bool = False) -> tuple[np.ndarray, int, int]:
        return self.sd.look(self.sd.bob_entry(level, k), one)

    def rc(self, n: int) -> tuple[np.ndarray, int, int]:
        return self.sd.look(self.sd.entry(n))

    def field(self, level: int, f: dict) -> np.ndarray:
        """A play-field frame's pixels from its atlas (the dynamic slot's are not there; level 3's frame
        cache's from its ROM)."""
        if level == 3 and f.get("kind") == 1:
            return np.array([list(r) for r in self.looks3.pixels(f["fid"])], np.uint8)
        a = self.atlas[level].reshape(-1, 128)
        rows = a[f["y"]:f["y"] + f["sh"], f["x"] // 2:(f["x"] + f["sw"]) // 2]
        out = np.zeros((f["sh"], f["sw"]), np.uint8)
        out[:, 0::2], out[:, 1::2] = rows >> 4, rows & 15
        return out


def amiga_frame(ram: bytes, f: dict) -> tuple[np.ndarray, int, int]:
    """The Amiga's look of a BOB frame (background indices, -1 clear) and its origin offset; a
    joint composition: its parts drawn as the original draws them."""
    if "joint" not in f:
        return ms.bob_image(ram, f["addr"], f["w"], f["h"]), 0, 0
    ox, oy = f["origin"]
    img = np.full(ms.JOINT_L2["size"], -1, int)
    for addr, w, h, dx, dy in f["joint"]:
        part = ms.bob_image(ram, addr, w, h)
        reg = img[dy - oy:dy - oy + h, dx - ox:dx - ox + w]
        reg[part >= 0] = part[part >= 0]
    return img, oy, ox


def bob_cards(pool: Pool, level: int, ram: bytes, frames: list[dict], pal: str, amiga_pal: str,
              label, near: np.ndarray) -> list[dict]:
    """One card per frame (its mirror's in the same card), Amiga | MSX (| mirror): a sprite frame's
    record, or a play-field frame's pixels (its atlas; the dynamic slot's: the converter's mapping
    'near', as msxsprites.field_frames does)."""
    info = pool.levels[level]
    field = {(f["addr"], f["w"], f["h"]): f for f in info["field"]}
    by_id = {b["id"]: b for b in info["bobs"]}
    mirrored = {}
    for b in frames:
        if b.get("mirror"):
            mirrored.setdefault(b["mirror"][0], b)

    def msx(b: dict, cap: str) -> dict:
        f = field.get((b["addr"], b["w"], b["h"]))
        if f is None:
            img, y0, x0 = pool.bob(level, b["id"])
            return view(cap, img, pal, 0, y0, x0)
        if "dyn" in f or f["src"] != f"{f['addr']:x}:{f['w']}:{f['h']}":    # (a removed one: its own look)
            src = ms.bob_image(ram, f["addr"], f["w"], f["h"])
            return view(cap + " (play field)", np.where(src >= 0, near[np.clip(src, 0, 15)], 0), pal, 0, 0, 0)
        return view(cap + " (play field)", pool.field(level, f), pal, 0, f["oy"], f["ox"])

    cards = []
    for b in frames:
        if b.get("mirror") and b["mirror"][0] in by_id and by_id[b["mirror"][0]] in frames:
            continue                                    # (in its partner's card)
        src, sy, sx = amiga_frame(ram, b)
        views = [view("Amiga", src, amiga_pal, -1, sy, sx), msx(b, "MSX")]
        also = []
        m = mirrored.get(b["id"])
        if m is not None:
            views.append(msx(m, "mirror"))
            also.append(f"bob:{m['addr']:x}:{m['w']}:{m['h']}")
        f = field.get((b["addr"], b["w"], b["h"]))
        card = {"key": f"bob:{b['addr']:x}:{b['w']}:{b['h']}", "label": label(b), "views": views, "also": also,
                "field": f is not None, "note": ""}
        if f is None:
            card.update({"per_line": b["max_line"], "sprites": b["sprites"]})
        elif "sprites" in b:
            card["note"] = "its hit flash (and type 2's blink) shows as a sprite silhouette over the play field"
        cards.append(card)
    return cards


def robocop_groups(pool: Pool, game: player.Game, sppal: str, pal: str, only: tuple | None = None) -> list[dict]:
    """RoboCop: per state pair a group, per step a card (aim 2: horizontal)."""
    recs = game.records()
    groups = []
    for s in sorted(STATES):
        if only and s not in only:
            continue
        items = []
        steps = [i for i, r in enumerate(recs) if r["state"] == s]
        left = [i for i, r in enumerate(recs) if r["state"] == s + 1]
        for j, ri in enumerate(steps):
            amig = np.array(game.compose(recs[ri], player.ARM_AIM))
            hot = (recs[ri]["hot_y"], recs[ri]["hot_x"])
            views = [view("Amiga", amig, "sp", 0, -hot[0], -hot[1])]
            img, y0, x0 = pool.rc(4 * ri + player.ARM_AIM)
            both = s in (10, 12) or not left
            views.append(view("MSX" + (" (both sides)" if both and left else "" if both else " →"), img, pal, 0, y0, x0))
            if not both and j < len(left):
                img, y0, x0 = pool.rc(4 * left[j] + player.ARM_AIM)
                views.append(view("MSX ←", img, pal, 0, y0, x0))
            items.append({"key": f"rc:{s}:{j}", "label": f"step {j + 1}", "views": views, "also": [], "field": False,
                          "note": "", "per_line": None, "sprites": None})
        groups.append({"name": STATES[s], "items": items, "anim": list(range(1, len(items[0]["views"])))})
    return groups


def build(prefix: Path, removed1: dict, removed2: dict, removed3: dict | None = None) -> dict:
    pool = Pool(prefix)
    main = (ROOT / "build/extracted/boot/main_8000.bin").read_bytes()
    perma = (ROOT / "build/extracted/files/PERMA_05.bin").read_bytes()
    ram1 = (ROOT / "build/ram/level1_full.bin").read_bytes()
    ram2 = (ROOT / "build/ram/level2_full.bin").read_bytes()
    bg1, sp = ms.amiga_palettes(main, 0xFFF6)
    bg2, _ = ms.amiga_palettes(main, ms.L2_PAL_ADDR)
    pal1 = ms.msx_palette((ROOT / "build/msx/robocop.pal").read_bytes())
    pal2 = np.array([[int(c) / 7 for c in p] for p in pool.levels[2]["palette"]])
    game = player.Game(main, perma)
    groups = []
    for g in robocop_groups(pool, game, "sp", "msx"):
        groups.append(dict(g, section="RoboCop"))
    l1 = pool.levels[1]
    near1 = ms.nearest(bg1, pal1, 1)
    near2 = ms.nearest(bg2, pal2, 1)
    procs: dict[str, list] = {}
    for b in l1["bobs"]:
        if not b.get("spark"):
            procs.setdefault(f"{b['proc']} ({b['w']}x{b['h']})", []).append(b)
    shown = {(b["addr"], b["w"], b["h"]) for b in l1["bobs"]}
    for f in l1["field"]:                               # (the play-field frames without a sprite version)
        if (f["addr"], f["w"], f["h"]) not in shown and f["src"] == f"{f['addr']:x}:{f['w']}:{f['h']}" or \
                f["proc"] == "obj45_update":
            procs.setdefault(f"the play field: {f['proc']} ({f['w']}x{f['h']})", []).append(dict(f, id=-1))
    for proc, frames in procs.items():
        cards = bob_cards(pool, 1, ram1, [b for b in frames if not b.get("repeat")], "msx", "bg",
                          lambda b: f"{b['addr']:05X}", near1)
        groups.append({"section": "Level 1", "name": proc, "items": cards, "anim": [1]})
    # level 2: the frames level 1 never showed
    l2 = pool.levels[2]
    new = [b for b in l2["bobs"] if "new" in b]
    news = {(b["addr"], b["w"], b["h"]) for b in new}
    for title, plist in L2_OBJECTS:
        frames = [b for b in l2["bobs"] if b["proc"] in plist and ((b["addr"], b["w"], b["h"]) in news
                                                                  or plist == ("FUN_0000c948",))]
        fonly = [f for f in l2["field"] if f["proc"] in plist and (f["addr"], f["w"], f["h"]) not in
                 {(b["addr"], b["w"], b["h"]) for b in frames}]
        frames += [dict(f, id=-1) for f in fonly]
        if not frames:
            continue
        cards = bob_cards(pool, 2, ram2, frames, "msx2", "bg2", lambda b: f"{b['addr']:05X}", near2)
        for c in cards:
            c["key"] = "l2:" + c["key"]
            c["also"] = ["l2:" + k for k in c["also"]]
        groups.append({"section": "Level 2", "name": title, "items": cards, "anim": [1]})
    for g in robocop_groups(pool, game, "sp", "msx2", only=(14,)):
        for c in g["items"]:
            c["note"] = "level 1 never shows it; the same record in both levels (a removal goes for both)"
        groups.append(dict(g, section="Level 2", name="RoboCop hanging (states 14/15)"))
    # level 3: its own frames (DATAL3's), every one kept until the user chooses
    if 3 in pool.levels:
        l3 = pool.levels[3]
        ram3 = (ROOT / "build/ram/level3_full.bin").read_bytes()
        own = lambda b: 0x28000 <= b["addr"] < 0x5540C                  # noqa: E731
        procs3: dict[str, list] = {}
        sprites3 = {(b["addr"], b["w"], b["h"]) for b in l3["bobs"]}
        for b in l3["bobs"]:
            if own(b) and "new" in b and not b.get("repeat"):
                procs3.setdefault(f"{b['proc']} ({b['w']}x{b['h']})", []).append(b)
        for f in l3["field"]:
            if own(f) and (f["addr"], f["w"], f["h"]) not in sprites3 and f["src"] == f"{f['addr']:x}:{f['w']}:{f['h']}":
                procs3.setdefault(f"the play field: {f['proc']} ({f['w']}x{f['h']})", []).append(dict(f, id=-1))
        for proc, frames in procs3.items():
            cards = bob_cards(pool, 3, ram3, frames, "msx2", "bg2", lambda b: f"{b['addr']:05X}", near2)
            for c in cards:
                c["key"] = "l3:" + c["key"]
                c["also"] = ["l3:" + k for k in c["also"]]
            groups.append({"section": "Level 3", "name": proc, "items": cards, "anim": [1]})
    removed = sorted(["rc:" + k for k in removed1.get("rc", {})] + ["bob:" + k for k in removed1.get("bob", {})] +
                     ["l2:bob:" + k for k in removed2.get("bob", {})] +
                     ["l3:bob:" + k for k in (removed3 or {}).get("bob", {})])
    return {"palette": graded(pal1), "palette2": graded(pal2), "sppal": amiga(sp), "bgpal": amiga(bg1),
            "bgpal2": amiga(bg2), "groups": groups, "removed": removed}


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Animation frames</title>
<style>
:root { --bg: #f4f2ee; --panel: #ffffff; --ink: #1d1d1f; --muted: #6b6b70; --line: #dcd8d0;
  --chip: #ece8e0; --sel: #2a5db6; --cut: #b6342a; --warn: #b26a00; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #161618; --panel: #202024; --ink: #ececf0; --muted: #9a9aa3; --line: #34343a;
  --chip: #2b2b31; --sel: #6c9cff; --cut: #e0584c; --warn: #e3a33a; } }
:root[data-theme="dark"] { --bg: #161618; --panel: #202024; --ink: #ececf0; --muted: #9a9aa3;
  --line: #34343a; --chip: #2b2b31; --sel: #6c9cff; --cut: #e0584c; --warn: #e3a33a; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
header { position: sticky; top: 0; z-index: 5; background: var(--panel); border-bottom: 1px solid var(--line);
  padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 10px 22px; align-items: center; }
header h1 { font-size: 17px; margin: 0; }
nav { display: flex; gap: 6px; flex-wrap: wrap; }
nav a { color: var(--ink); text-decoration: none; background: var(--chip); padding: 4px 10px; border-radius: 6px; }
.stats { color: var(--muted); }
button { font: inherit; border: 1px solid var(--line); background: var(--chip); color: var(--ink);
  padding: 5px 10px; border-radius: 6px; cursor: pointer; }
main { padding: 16px; max-width: 1400px; margin: 0 auto; }
.intro { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 16px; }
.intro p { margin: 6px 0; }
h2.section { font-size: 20px; margin: 30px 0 4px; scroll-margin-top: 70px; }
.group { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 12px; margin: 14px 0; }
.ghead { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
.ghead h3 { margin: 0; font-size: 15px; }
.ghead .n { color: var(--muted); }
.preview { display: flex; align-items: flex-end; gap: 12px; color: var(--muted); font-size: 12px; margin-left: auto; }
.preview figure { margin: 0; text-align: center; }
.grid { display: grid; gap: 10px; }
.card { border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: var(--bg); min-width: 0; }
.card.cut { opacity: .38; border-style: dashed; border-color: var(--cut); }
.pics { display: flex; gap: 8px; align-items: flex-end; justify-content: center; flex-wrap: wrap; }
.pics figure { margin: 0; text-align: center; }
figcaption { font-size: 11px; color: var(--muted); }
canvas { image-rendering: pixelated; max-width: 100%; }
.meta { display: flex; justify-content: space-between; gap: 6px; margin-top: 6px; font-size: 12px; flex-wrap: wrap; }
.badge { background: var(--chip); padding: 1px 6px; border-radius: 4px; }
.badge.l6 { color: var(--warn); } .badge.l8 { color: var(--cut); }
.note { font-size: 11px; color: var(--muted); margin-top: 4px; }
textarea { width: 100%; height: 90px; margin-top: 10px; }
</style>
</head>
<body>
<header>
  <h1>Animation frames</h1>
  <nav id="nav"></nav>
  <span class="stats" id="stats"></span>
  <span><button id="copy">Copy choices</button> <button id="save">Download file</button>
    <button id="theme" title="Light / dark">&#9680;</button></span>
</header>
<main>
  <div class="intro">
    <p>Every frame at its <b>full</b> look, as it will be drawn: the Amiga's and the MSX's (every colour, nothing cut;
      the MSX in the game's colours). Tick <b>remove</b> on the frames that may go: the animation then repeats the frame
      before it that stays. Each group's preview plays the frames that stay, at the game's pace and where the game
      draws them.</p>
    <p><b>RoboCop</b>: the left side is the right one mirrored; one choice per step covers both sides and every aim.
      <b>Enemies and objects</b>: a frame that is another's mirror shares its card and goes with it. The play-field
      ones are drawn by the VDP in 16 colours.</p>
    <p><b>Level 2</b> lists the frames level 1 never showed; all of them stay until you choose. The badge gives the
      sprites a frame takes on a line (the MSX shows at most 8 a line) and in all. Your choices stay in this browser;
      at the end click <b>Copy choices</b> and paste them into the conversation.</p>
  </div>
  <div id="root"></div>
  <footer><div id="out-wrap" hidden><textarea id="out" readonly></textarea></div></footer>
</main>
<script id="data" type="application/json">%DATA%</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const KEY = "rc2-frame-review-v3";
const CARD_KEYS = new Set(D.groups.flatMap(g => g.items.map(it => it.key)));
let removed = new Set(D.removed.filter(k => CARD_KEYS.has(k)));
function load(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } }
function persist() { try { localStorage.setItem(KEY, JSON.stringify([...removed])); } catch (e) {} }
const saved = load(KEY);
if (Array.isArray(saved)) removed = new Set(saved.filter(k => CARD_KEYS.has(k)));
const PAL = {sp: D.sppal, bg: D.bgpal, bg2: D.bgpal2, msx: D.palette, msx2: D.palette2};
const RGB = new Map();
function rgb(col) {
  if (!RGB.has(col)) RGB.set(col, [1, 3, 5].map(i => parseInt(col.slice(i, i + 2), 16)));
  return RGB.get(col);
}
const SCALE = 2;
function paint(canvas, w, h, parts) {
  const off = document.createElement("canvas"); off.width = w; off.height = h;
  const oc = off.getContext("2d"), im = oc.createImageData(w, h);
  for (const {v, dx, dy} of parts) {
    const pal = PAL[v.pal];
    v.grid.forEach((row, y) => row.forEach((c, x) => {
      if (c === v.clear) return;
      const X = dx + x, Y = dy + y;
      if (X < 0 || Y < 0 || X >= w || Y >= h) return;
      const [r, g, b] = rgb(pal[c]), i = (Y * w + X) * 4;
      im.data[i] = r; im.data[i + 1] = g; im.data[i + 2] = b; im.data[i + 3] = 255;
    }));
  }
  oc.putImageData(im, 0, 0);
  canvas.width = w * SCALE; canvas.height = h * SCALE;
  const c = canvas.getContext("2d"); c.imageSmoothingEnabled = false;
  c.clearRect(0, 0, canvas.width, canvas.height);
  c.drawImage(off, 0, 0, w * SCALE, h * SCALE);
}
const vw = v => v.grid[0].length, vh = v => v.grid.length;
function keptOf(g) { return g.items.filter(it => !removed.has(it.key)); }
function updateStats() {
  const all = D.groups.reduce((n, g) => n + g.items.length, 0), secs = {};
  for (const g of D.groups) {
    const s = secs[g.section] || (secs[g.section] = [0, 0]);
    s[0] += keptOf(g).length; s[1] += g.items.length;
  }
  document.getElementById("stats").innerHTML = Object.entries(secs).map(([s, [k, t]]) => `${s}: <b>${k}</b>/${t}`)
    .join(" &middot; ") + ` &middot; removed: <b>${removed.size}</b> of ${all}`;
}
const root = document.getElementById("root"), nav = document.getElementById("nav"), previews = [];
let lastSection = null, secN = 0;
for (const g of D.groups) {
  if (g.section !== lastSection) {
    lastSection = g.section;
    const h = document.createElement("h2"); h.className = "section"; h.id = "s" + (++secN); h.textContent = g.section;
    root.append(h);
    const a = document.createElement("a"); a.href = "#" + h.id; a.textContent = g.section; nav.append(a);
  }
  const box = document.createElement("div"); box.className = "group";
  const head = document.createElement("div"); head.className = "ghead";
  const title = document.createElement("h3"); title.textContent = g.name;
  const n = document.createElement("span"); n.className = "n";
  const pv = document.createElement("div"); pv.className = "preview"; pv.append(document.createTextNode("preview"));
  head.append(title, n, pv);
  const grid = document.createElement("div"); grid.className = "grid";
  const cardW = Math.max(...g.items.map(it => it.views.reduce((s, v) => s + Math.max(vw(v) * SCALE, 6.5 * v.cap.length), 0)
    + 8 * (it.views.length - 1))) + 18;
  grid.style.gridTemplateColumns = `repeat(auto-fill, minmax(min(100%, ${Math.max(cardW, 150)}px), 1fr))`;
  box.append(head, grid); root.append(box);
  const countKept = () => { n.textContent = `${keptOf(g).length} of ${g.items.length} frames stay`; };
  for (const it of g.items) {
    const card = document.createElement("div"); card.className = "card";
    const pics = document.createElement("div"); pics.className = "pics";
    for (const v of it.views) {
      const f = document.createElement("figure"), c = document.createElement("canvas");
      f.append(c, Object.assign(document.createElement("figcaption"), {textContent: v.cap}));
      pics.append(f);
      paint(c, vw(v), vh(v), [{v, dx: 0, dy: 0}]);
    }
    const meta = document.createElement("div"); meta.className = "meta";
    const badge = document.createElement("span");
    if (it.field) { badge.className = "badge"; badge.textContent = "play field (VDP)"; }
    else if (it.per_line != null) {
      badge.className = "badge " + (it.per_line >= 8 ? "l8" : it.per_line >= 6 ? "l6" : "");
      badge.textContent = `${it.per_line}/line \\u00b7 ${it.sprites}`; badge.title = "sprites a line \\u00b7 in all";
    }
    meta.append(Object.assign(document.createElement("span"), {textContent: it.label}), badge);
    const rm = document.createElement("label"), cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = removed.has(it.key);
    rm.append(cb, document.createTextNode(it.views.length > 2 || it.also.length ? " remove (both sides)" : " remove"));
    const sync = () => card.classList.toggle("cut", cb.checked);
    cb.addEventListener("change", () => {
      if (cb.checked) removed.add(it.key); else removed.delete(it.key);
      persist(); sync(); countKept(); updateStats();
    });
    sync();
    card.append(pics, meta);
    if (it.note) card.append(Object.assign(document.createElement("div"), {className: "note", textContent: it.note}));
    const bottom = document.createElement("div"); bottom.className = "meta"; bottom.append(rm); card.append(bottom);
    grid.append(card);
  }
  countKept();
  if (g.items.length > 1) {
    for (const vi of g.anim) {
      const vs = g.items.map(it => it.views[Math.min(vi, it.views.length - 1)]);
      const x0 = Math.min(...vs.map(v => v.ox)), y0 = Math.min(...vs.map(v => v.oy));
      const w = Math.max(...vs.map(v => v.ox + vw(v))) - x0, h = Math.max(...vs.map(v => v.oy + vh(v))) - y0;
      const f = document.createElement("figure"), c = document.createElement("canvas");
      f.append(c); pv.append(f);
      previews.push({g, vi, canvas: c, x0, y0, w, h, i: 0});
    }
  } else pv.hidden = true;
}
function tick() {
  for (const p of previews) {
    const kept = keptOf(p.g);
    if (!kept.length) { paint(p.canvas, p.w, p.h, []); continue; }
    const it = kept[p.i++ % kept.length], v = it.views[Math.min(p.vi, it.views.length - 1)];
    paint(p.canvas, p.w, p.h, [{v, dx: v.ox - p.x0, dy: v.oy - p.y0}]);
  }
}
tick(); setInterval(tick, 125); updateStats();
function result() {
  const out = {rc2_frames: 3, level1: [], level2: [], level3: []};
  for (const g of D.groups) for (const it of g.items) if (removed.has(it.key))
    for (const k of [it.key, ...it.also])
      (k.startsWith("l2:") ? out.level2 : k.startsWith("l3:") ? out.level3 : out.level1).push(k.replace(/^l[23]:/, ""));
  out.level1.sort(); out.level2.sort(); out.level3.sort();
  return JSON.stringify(out);
}
document.getElementById("copy").addEventListener("click", async () => {
  const txt = result(), out = document.getElementById("out");
  out.value = txt; document.getElementById("out-wrap").hidden = false;
  const b = document.getElementById("copy");
  try { await navigator.clipboard.writeText(txt); b.textContent = "Copied!"; }
  catch (e) { out.select(); b.textContent = "Select and copy below"; }
  setTimeout(() => b.textContent = "Copy choices", 2500);
});
document.getElementById("save").addEventListener("click", () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([result()], {type: "application/json"}));
  a.download = "rc2_frames.json"; a.click();
});
document.getElementById("theme").addEventListener("click", () => {
  const r = document.documentElement;
  const dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = dark ? "light" : "dark";
});
</script>
</body>
</html>
"""


def sheet(data: dict, path: Path, section: str = "Level 2", scale: int = 3) -> int:
    """Per card of the section: the Amiga's view beside the MSX ones, on a grey ground."""
    pals = {"sp": data["sppal"], "bg": data["bgpal"], "bg2": data["bgpal2"], "msx": data["palette"],
            "msx2": data["palette2"]}
    cards = [c for g in data["groups"] if g["section"] == section for c in g["items"]]
    tiles = []
    for c in cards:
        vs = c["views"]
        w = sum(len(v["grid"][0]) for v in vs) + 4 * (len(vs) - 1)
        h = max(len(v["grid"]) for v in vs)
        tiles.append((vs, w, h))
    per = 6
    cw, ch = max(t[1] for t in tiles) + 6, max(t[2] for t in tiles) + 6
    rows = -(-len(tiles) // per)
    canvas = np.full((rows * ch * scale, per * cw * scale, 3), 72, np.uint8)
    for n, (vs, _, _) in enumerate(tiles):
        oy, ox = (n // per) * ch, (n % per) * cw
        for v in vs:
            g = np.array(v["grid"])
            pal = np.array([[int(p[i:i + 2], 16) for i in (1, 3, 5)] for p in pals[v["pal"]]], np.uint8)
            for y, x in zip(*np.nonzero(g != v["clear"])):
                y0, x0 = (oy + 3 + y) * scale, (ox + 3 + x) * scale
                canvas[y0:y0 + scale, x0:x0 + scale] = pal[g[y, x]]
            ox += g.shape[1] + 4
    write_png(path, canvas.shape[1], canvas.shape[0], [bytes(r.ravel()) for r in canvas])
    return len(tiles)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pool", type=Path, help="tools/msxsprites.py --pool's prefix")
    ap.add_argument("out", type=Path)
    ap.add_argument("--sheet", type=Path, help="a contact sheet of level 2's section (Amiga | MSX)")
    ap.add_argument("--level1-frames", type=Path, default=ROOT / "msx" / "level1_frames.json")
    ap.add_argument("--level2-frames", type=Path, default=ROOT / "msx" / "level2_frames.json")
    ap.add_argument("--level3-frames", type=Path, default=ROOT / "msx" / "level3_frames.json")
    a = ap.parse_args()
    rem = [json.loads(p.read_text()) if p.exists() else {} for p in (a.level1_frames, a.level2_frames, a.level3_frames)]
    data = build(a.pool, *rem)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(PAGE.replace("%DATA%", json.dumps(data, separators=(",", ":"))))
    secs: dict[str, int] = {}
    for g in data["groups"]:
        secs[g["section"]] = secs.get(g["section"], 0) + len(g["items"])
    print(f"{a.out}: " + ", ".join(f"{s} {n} cards" for s, n in secs.items()) +
          f"; level 2: " + "; ".join(f"{g['name'].split(' (')[0]} {len(g['items'])}" for g in data["groups"]
                                     if g["section"] == "Level 2"))
    if a.sheet:
        print(f"{a.sheet}: {sheet(data, a.sheet)} level-2 frames, Amiga | MSX")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
