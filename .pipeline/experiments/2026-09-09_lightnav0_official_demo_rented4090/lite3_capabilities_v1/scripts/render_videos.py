"""Render full wall-time case films, including Chinese text, from local captures."""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from metrics import displacement


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pkg", type=Path, required=True)
    args = parser.parse_args()
    pkg = args.pkg.resolve()
    summary = json.loads((pkg / "analysis/summary.json").read_text())
    suite = summary["suite"]
    fontpath = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    title_font = ImageFont.truetype(fontpath, 26)
    font = ImageFont.truetype(fontpath, 22)
    smaller = ImageFont.truetype(fontpath, 20)
    outputs = []
    for case in suite["cases"]:
        src = pkg / "analysis" / f"{case['id']}_slice.json"
        if not src.exists():
            continue
        data = json.loads(src.read_text())
        result, episode = data["result"], data["episode"]
        cap = Path(data["capture_root"])
        frames = data["frames"]
        t0, t1 = episode["instruction_send_mono_ns"], episode["end_mono_ns"]
        out = pkg / "media" / case["id"]
        out.mkdir(parents=True, exist_ok=False)
        video = out / "run.mp4"
        proc = subprocess.Popen(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", "1280x800", "-r", "20", "-i", "-", "-an", "-c:v", "libx264",
            "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)],
            stdin=subprocess.PIPE)
        index, count, path = -1, 0, []
        start = result["start_pose"]
        stop = data["stop"]
        def project(x, y):
            return 140+(x-4.5)*30, 770-(y-9.8)*30
        for t in range(t0, t1+1, 50_000_000):
            while index+1 < len(frames) and frames[index+1]["capture_mono_ns"] <= t:
                index += 1
            f = frames[index] if index >= 0 else None
            canvas = Image.new("RGB", (1280,800), (16,19,25))
            if f:
                for offset, key in ((0,"front"),(640,"third")):
                    rgb = Image.open(cap/f[key+"_file"]).convert("RGB").resize((640,360))
                    canvas.paste(rgb,(offset,115))
            draw = ImageDraw.Draw(canvas)
            draw.text((18,10), f"{case['order']}/8  {case['id']} | Lite3 + LightNav-0 BF16", font=title_font, fill="white")
            draw.text((18,48), case["instruction"], font=title_font, fill=(190,220,255))
            draw.text((18,85), "LIVE ROBOT CAMERA",font=font,fill="white")
            draw.text((658,85), "LIVE CHASE CAMERA",font=font,fill="white")
            draw.text((18,480), "RECORDED ROUTE (fixed arena axes)",font=font,fill="white")
            draw.rectangle((*project(4.5,17.8),*project(14.5,9.8)),outline=(100,100,110),width=1)
            if case["scene"] == "blocked":
                x,y = suite["obstacle_xy"]
                hx,hy,_ = suite["obstacle_half_extents"]
                draw.rectangle((*project(x-hx,y+hy),*project(x+hx,y-hy)),fill=(170,80,25))
            gx,gy=project(*suite["target_xy"])
            draw.ellipse((gx-5,gy-5,gx+5,gy+5),fill=(40,230,130))
            draw.text((gx+8,gy-10),"trashcan",font=smaller,fill=(40,230,130))
            if case["category"] == "distance":
                distance=case["requested_distance_m"]
                ex,ey=project(start[0]+distance*math.cos(start[2]),start[1]+distance*math.sin(start[2]))
                draw.line((ex,ey-22,ex,ey+22),fill=(255,210,60),width=3)
                draw.text((ex-15,ey+25),f"{distance} m",font=smaller,fill=(255,210,60))
            if f:
                x,y=project(f["pose_x"],f["pose_y"])
                path.append((x,y))
                if len(path)>1:
                    draw.line(path,fill=(50,220,255),width=3)
                draw.ellipse((x-5,y-5,x+5,y+5),fill="white")
                motion=displacement(start,(f["pose_x"],f["pose_y"],f["pose_yaw"]))
                stopped=stop is not None and t>=stop["mono_ns"]
                control="MODEL STOP" if stopped else "NAVIGATING"
                lines=[f"Wall time: {(t-t0)/1e9:.2f} s | {control}",
                    f"Forward: {motion['forward_m']:.3f} m | lateral: {motion['lateral_m']:.3f} m",
                    f"Distance to bin: {math.dist((f['pose_x'],f['pose_y']),suite['target_xy']):.3f} m",
                    f"Obstacle-contact steps (1 ms): {f['backend']['obstacle_contact_steps']}",
                    f"Observed forward/yaw: {f['velocity_linear']:.3f} / {f['velocity_angular']:.3f}",
                    f"Requested forward/yaw: {f['command_linear']:.3f} / {f['command_angular']:.3f}",
                    f"Camera age: {(t-f['capture_mono_ns'])/1e6:.0f} ms"]
                for line_no,text in enumerate(lines):
                    draw.text((658,486+line_no*37),text,font=smaller,fill="white")
            proc.stdin.write(canvas.tobytes())
            count+=1
            if count==1:
                canvas.save(out/"start.png")
        canvas.save(out/"final.png")
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("Video encoder failed")
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(video),"-f","null","-"],check=True)
        meta={"file":str(video),"frames":count,"presentation_seconds":count/20,
              "source_seconds":(t1-t0)/1e9,"sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
              "full_decode_passed":True,"time_basis":"case wall time; held recorded frames only"}
        (out/"metadata.json").write_text(json.dumps(meta,indent=2)+"\n")
        outputs.append(meta)
        print(case["id"],count,"frames",flush=True)
    concat=pkg/"media/concat.txt"
    concat.write_text("".join(f"file '{o['file']}'\n" for o in outputs))
    reel=pkg/"media/all_eight_tests.mp4"
    subprocess.run(["ffmpeg","-v","error","-f","concat","-safe","0","-i",str(concat),
                    "-c","copy","-movflags","+faststart",str(reel)],check=True)
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(reel),"-f","null","-"],check=True)
    (pkg/"media/metadata.json").write_text(json.dumps({"cases":outputs,"reel":str(reel),
        "reel_sha256":hashlib.sha256(reel.read_bytes()).hexdigest(),
        "reel_semantics":"Concatenated independent cases; per-case wall clocks restart; no time compression",
        "full_decode_passed":True},indent=2)+"\n")


if __name__ == "__main__":
    main()
