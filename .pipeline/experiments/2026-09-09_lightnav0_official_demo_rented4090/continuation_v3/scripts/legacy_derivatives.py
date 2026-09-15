"""New derivatives for the immutable round-1 runs. Originals are never modified."""
from __future__ import annotations
import json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose_video import (ASHCAN, ASHCAN_2, DOG_BED, SPAWN, Ffmpeg, F24, F26, F28, M24,
                           BG, WHITE, CYAN, GREEN, AMBER, MAGENTA, MINT, BLUE, GREY,
                           project_ground, sha256_file, label)
from PIL import Image, ImageDraw

PKG = Path(sys.argv[1]).resolve()
EXP = PKG.parent
LEGACY_RECORDS = EXP / "records" / "run_20260909_235443"
CONN = {"rep_01": "vln_mujoco_2", "rep_02": "vln_mujoco_3", "rep_03": "vln_mujoco_4"}
out_meta = {}

for rep, conn in CONN.items():
    src = EXP / "runs" / rep
    out = PKG / "media" / f"legacy_{rep}"
    out.mkdir(parents=True, exist_ok=True)
    episode = json.loads((src / "episode.json").read_text())
    index = [json.loads(l) for l in (src / "third_person_frames.jsonl").read_text().splitlines() if l.strip()]
    tp = sorted((src / "third_person").glob("*.jpg"))
    fp = sorted((src / "first_person").glob("*.jpg"))
    polled = len(index)
    survived = len(tp)
    overwritten = polled - survived
    episode_dir = LEGACY_RECORDS / conn / "episode_000"
    actions = json.loads((episode_dir / "actions.json").read_text())

    third = Ffmpeg(out / "third_person_surviving_frames.mp4", 960, 610, fps=5, crf=18)
    for i, path in enumerate(tp):
        canvas = Image.new("RGB", (960, 610), BG)
        canvas.paste(Image.open(path).convert("RGB").resize((960, 540), Image.LANCZOS), (0, 46))
        d = ImageDraw.Draw(canvas)
        d.rectangle((0, 0, 960, 46), fill=(70, 40, 10))
        d.text((8, 10), f"LEGACY {rep} THIRD PERSON - SURVIVING FRAMES ONLY", font=F26, fill=AMBER)
        d.text((8, 576),
               f"frame {i+1}/{survived} of {polled} polled; {overwritten} overwritten by the round-1 "
               f"harness name collision; no exact state replay exists", font=F24, fill=GREY)
        for _ in range(2):
            third.write(canvas)
    third.close()

    overlay = Ffmpeg(out / "first_person_model_overlay.mp4", 960, 610, fps=4, crf=18)
    for entry in actions:
        image = episode_dir / f"image_{entry['step']:06d}.jpg"
        if not image.exists():
            continue
        canvas = Image.new("RGB", (960, 610), BG)
        canvas.paste(Image.open(image).convert("RGB").resize((960, 540), Image.LANCZOS), (0, 46))
        d = ImageDraw.Draw(canvas)
        pointing = entry.get("pointing") or {}
        for key, colour, name in (("apos_px", MINT, "APOS"), ("opos_px", MAGENTA, "OPOS")):
            px = pointing.get(key)
            if px:
                u, v = px[0] * 2, px[1] * 2 + 46
                d.line((u - 16, v, u + 16, v), fill=colour, width=3)
                d.line((u, v - 16, u, v + 16), fill=colour, width=3)
                d.text((u + 14, v + 8), name, font=F24, fill=colour, stroke_width=3, stroke_fill=(0, 0, 0))
        pts = []
        for point in entry.get("waypoints") or []:
            projected = project_ground(point[0], point[1])
            if projected:
                pts.append((projected[0] * 2, projected[1] * 2 + 46))
        if len(pts) > 1:
            d.line(pts, fill=BLUE, width=4)
        d.rectangle((0, 0, 960, 46), fill=(70, 40, 10))
        d.text((8, 10), f"LEGACY {rep} DECISION REVIEW / NOT WALL TIME  seq {entry['seq']}",
               font=F26, fill=AMBER)
        d.text((8, 576), (entry.get("raw_text") or "")[:76], font=M24, fill=WHITE)
        for _ in range(2):
            overlay.write(canvas)
    overlay.close()

    # XY trajectory diagram: no saved state, so no exact overhead replay is claimed.
    snaps = [json.loads(l) for l in (src / "snapshots.jsonl").read_text().splitlines() if l.strip()]
    xy = [(s["simulation"]["pose"]["x"], s["simulation"]["pose"]["y"])
          for s in snaps if isinstance(s, dict) and "simulation" in s]
    W, H = 960, 720
    xmin, xmax, ymin, ymax = 4.6, 15.0, 8.4, 14.6
    def px(x, y):
        return ((x - xmin) / (xmax - xmin) * (W - 80) + 60, H - 70 - (y - ymin) / (ymax - ymin) * (H - 130))
    img = Image.new("RGB", (W, H), (20, 22, 26))
    d = ImageDraw.Draw(img)
    d.rectangle((60, 60, W - 20, H - 70), outline=(70, 76, 84))
    if len(xy) > 1:
        d.line([px(x, y) for x, y in xy], fill=CYAN, width=4)
    for name, point, colour in (("SPAWN", SPAWN, GREY), ("TRASHCAN (target)", ASHCAN, GREEN),
                                ("trashcan #2", ASHCAN_2, (90, 190, 130)), ("dog bed", DOG_BED, AMBER)):
        u, v = px(*point)
        d.ellipse((u - 9, v - 9, u + 9, v + 9), outline=colour, width=3)
        d.text((u + 12, v - 10), name, font=F24, fill=colour)
    end = episode["end_pose"]
    u, v = px(end["x"], end["y"])
    d.ellipse((u - 8, v - 8, u + 8, v + 8), fill=WHITE)
    d.text((14, 14), f"LEGACY {rep} XY TRAJECTORY (from /ws snapshots - NOT an exact state replay)",
           font=F26, fill=AMBER)
    d.text((14, H - 44),
           f"terminal distance to requested trashcan {math.dist((end['x'], end['y']), ASHCAN):.3f} m; "
           f"{overwritten} third-person and first-person frames were lost in round 1", font=F24, fill=GREY)
    img.save(out / "trajectory_xy.png")

    out_meta[rep] = {
        "cohort": "legacy_round_1", "originals_modified": False,
        "polled_frames": polled, "surviving_frames": survived, "overwritten_frames": overwritten,
        "exact_state_replay": False,
        "reason_no_overhead_replay": "round 1 saved no MuJoCo integration state",
        "files": {p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()},
    }
    print(rep, "polled", polled, "survived", survived, "overwritten", overwritten, flush=True)

(PKG / "media" / "legacy_metadata.json").write_text(json.dumps(out_meta, indent=2) + "\n")
