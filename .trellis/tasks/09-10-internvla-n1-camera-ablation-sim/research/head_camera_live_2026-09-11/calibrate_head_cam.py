#!/usr/bin/env python3
"""Lite3 head-camera calibration from checkerboard frames (offline, read-only evidence).

Intrinsics : cv2.calibrateCamera on burst frames (moving board).
Extrinsics : solvePnP on frames where the board stands UPRIGHT (its edges aligned with gravity).
             The board axis with the largest image-vertical component is taken as the gravity axis.
             elevation = asin(-d_z) where d = unit 'down' vector in camera coords (OpenCV: +y = image down, +z = forward).
             elevation > 0 means the optical axis points ABOVE horizontal.
Usage:
  calibrate_head_cam.py --intrinsic-dir DIR [--extrinsic FRAME ...] [--pattern auto|CxR] [--square-mm 25]
                        [--out OUTDIR] [--imu-pitch DEG]
"""
import argparse, glob, json, math, os, sys
import cv2, numpy as np
cv2.ocl.setUseOpenCL(False)

CANDIDATES = [(9,6),(8,6),(7,6),(10,7),(11,8),(8,5),(7,5),(6,4),(9,7),(12,8),(7,4),(6,5),(5,4),(10,8),(11,7)]
CRIT = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 60, 1e-4)

def detect(gray, size):
    flags = cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY
    ok, c = cv2.findChessboardCornersSB(gray, size, flags=flags)
    if ok: return c.reshape(-1,2).astype(np.float32)
    ok, c = cv2.findChessboardCorners(gray, size, flags=cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE)
    if ok:
        c = cv2.cornerSubPix(gray, c, (11,11), (-1,-1), CRIT)
        return c.reshape(-1,2).astype(np.float32)
    return None

def choose_pattern(files, pattern):
    if pattern != "auto":
        c,r = map(int, pattern.lower().split("x")); return (c,r)
    probe = files[:: max(1, len(files)//12)][:12]
    best, best_n = None, 0
    for size in CANDIDATES:
        n = 0
        for f in probe:
            g = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
            if g is not None and detect(g, size) is not None: n += 1
        if n > best_n: best, best_n = size, n
    return best

def fov_deg(K, dist, w, h):
    fx, fy, cx, cy = K[0,0], K[1,1], K[0,2], K[1,2]
    pin = dict(hfov=2*math.degrees(math.atan(w/(2*fx))), vfov=2*math.degrees(math.atan(h/(2*fy))),
               dfov=2*math.degrees(math.atan(math.hypot(w,h)/(2*math.hypot(fx,fy)/math.sqrt(2)))))
    # effective FOV through the distortion model: undistort the image edge midpoints
    pts = np.array([[[0,cy]],[[w,cy]],[[cx,0]],[[cx,h]]], np.float32)
    u = cv2.undistortPoints(pts, K, dist).reshape(-1,2)   # normalised coords
    eff = dict(hfov=math.degrees(math.atan(-u[0,0]) + math.atan(u[1,0])),
               vfov=math.degrees(math.atan(-u[2,1]) + math.atan(u[3,1])),
               up_deg=math.degrees(math.atan(-u[2,1])), down_deg=math.degrees(math.atan(u[3,1])))
    return pin, eff

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--intrinsic-dir", default=None)
    ap.add_argument("--intrinsics-json", default=None, help="reuse K/dist from a previous calibration.json (skips calibrateCamera)")
    ap.add_argument("--extrinsic", nargs="*", default=[])
    ap.add_argument("--pattern", default="auto")
    ap.add_argument("--square-mm", type=float, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--imu-pitch", type=float, default=None, help="torso pitch from /imu/data, deg, + = nose up")
    ap.add_argument("--max-views", type=int, default=40)
    ap.add_argument("--board-flat", action="store_true", help="extrinsic frames show the board lying FLAT on a level floor: gravity = board normal")
    a = ap.parse_args()
    out = a.out or os.path.join(a.intrinsic_dir or os.path.dirname(a.intrinsics_json), "calib_out"); os.makedirs(out, exist_ok=True)
    if a.intrinsics_json:
        prev = json.load(open(a.intrinsics_json)); K = np.array(prev["K"]); dist = np.array(prev["dist"]); w,h = prev["image_size"]
        size = tuple(prev["pattern"]) if a.pattern == "auto" else tuple(map(int, a.pattern.lower().split("x")))
        sq = a.square_mm or prev.get("square_mm") or 1.0
        objp = np.zeros((size[0]*size[1],3), np.float32); objp[:,:2] = np.mgrid[0:size[0],0:size[1]].T.reshape(-1,2) * sq
        pin, eff = fov_deg(K, dist, w, h)
        res = dict(image_size=[w,h], pattern=list(size), square_mm=sq, intrinsics_from=a.intrinsics_json, K=K.tolist(), dist=dist.ravel().tolist(), fov_pinhole_deg=pin, fov_effective_deg=eff)
        print("intrinsics reused from", a.intrinsics_json)
        return finish(a, res, out, size, objp, K, dist, eff)
    files = sorted(glob.glob(os.path.join(a.intrinsic_dir, "*.jpg")) + glob.glob(os.path.join(a.intrinsic_dir, "*.png")))
    if not files: sys.exit("no frames")
    size = choose_pattern(files, a.pattern)
    if size is None: sys.exit("no chessboard found with any candidate size; inspect a frame")
    print(f"pattern inner corners: {size[0]}x{size[1]}")
    sq = a.square_mm or 1.0
    objp = np.zeros((size[0]*size[1],3), np.float32)
    objp[:,:2] = np.mgrid[0:size[0],0:size[1]].T.reshape(-1,2) * sq
    objs, imgs, used, last = [], [], [], None
    w = h = None
    for f in files:
        g = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        if g is None: continue
        h, w = g.shape
        c = detect(g, size)
        if c is None: continue
        if last is not None and np.median(np.linalg.norm(c-last,axis=1)) < 12: continue   # near-duplicate pose
        last = c; objs.append(objp); imgs.append(c); used.append(os.path.basename(f))
    print(f"frames with board: {len(used)} of {len(files)}")
    if len(used) < 6: sys.exit("fewer than 6 usable views; move the board through more of the image")
    if len(used) > a.max_views:
        idx = np.linspace(0, len(used)-1, a.max_views).astype(int)
        objs=[objs[i] for i in idx]; imgs=[imgs[i] for i in idx]; used=[used[i] for i in idx]
    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(objs, imgs, (w,h), None, None)
    per = []
    for o,i,rv,tv in zip(objs,imgs,rvecs,tvecs):
        p,_ = cv2.projectPoints(o, rv, tv, K, dist); per.append(float(np.sqrt(np.mean(np.sum((p.reshape(-1,2)-i)**2,axis=1)))))
    pin, eff = fov_deg(K, dist, w, h)
    res = dict(image_size=[w,h], pattern=list(size), square_mm=a.square_mm, views=len(used), used_frames=used,
               rms_px=float(rms), per_view_rms_px=per, K=K.tolist(), dist=dist.ravel().tolist(),
               fov_pinhole_deg=pin, fov_effective_deg=eff)
    print(json.dumps({k:res[k] for k in ("rms_px","K","dist","fov_pinhole_deg","fov_effective_deg")}, indent=1))
    # coverage image
    cov = np.zeros((h,w,3), np.uint8)
    for c in imgs:
        for x,y in c: cv2.circle(cov,(int(x),int(y)),2,(0,255,0),-1)
    cv2.imwrite(os.path.join(out,"corner_coverage.png"), cov)
    return finish(a, res, out, size, objp, K, dist, eff)

def finish(a, res, out, size, objp, K, dist, eff):
    ext = []
    for f in a.extrinsic:
        g = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        if g is None: continue
        c = detect(g, size)
        if c is None: ext.append(dict(frame=f, detected=False)); continue
        ok, rv, tv = cv2.solvePnP(objp, c, K, dist, flags=cv2.SOLVEPNP_IPPE)
        Rm,_ = cv2.Rodrigues(rv)
        ax_x, ax_y, n = Rm[:,0], Rm[:,1], Rm[:,2]          # board axes in camera coords
        vert = n if a.board_flat else (ax_y if abs(ax_y[1]) >= abs(ax_x[1]) else ax_x)
        d = vert/np.linalg.norm(vert)
        if d[1] < 0: d = -d                                  # 'down' has +y in OpenCV camera coords
        elevation = math.degrees(math.asin(-d[2]))
        roll = math.degrees(math.atan2(d[0], d[1]))
        # camera height above the board corner row nearest the floor: distance along 'down' from camera to lowest corner
        pts_cam = (Rm @ objp.T + tv).T
        lowest = float(np.max(pts_cam @ d))                  # metres if square_mm given (mm units -> /1000)
        e = dict(frame=os.path.basename(f), detected=True, mode=("flat" if a.board_flat else "upright"), elevation_deg=elevation, roll_deg=roll,
                 board_normal_cam=n.tolist(), t_cam=tv.ravel().tolist(),
                 lowest_corner_below_camera=(lowest/1000.0 if a.square_mm else None),
                 reproj_rms_px=float(np.sqrt(np.mean(np.sum((cv2.projectPoints(objp,rv,tv,K,dist)[0].reshape(-1,2)-c)**2,axis=1)))))
        if a.imu_pitch is not None: e["camera_pitch_rel_torso_deg"] = elevation - a.imu_pitch
        ext.append(e)
        vis = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR); cv2.drawChessboardCorners(vis, size, c.reshape(-1,1,2), True)
        cv2.imwrite(os.path.join(out, "ext_"+os.path.basename(f)), vis)
        print(f"extrinsic {os.path.basename(f)}: elevation {elevation:+.2f} deg (+ = up), roll {roll:+.2f} deg, reproj {e['reproj_rms_px']:.2f} px")
    res["extrinsic"] = ext
    if ext and any(x.get("detected") for x in ext):
        el = float(np.mean([x["elevation_deg"] for x in ext if x.get("detected")]))
        vis_down = eff["down_deg"] - el      # degrees below horizontal seen at the bottom edge (through distortion)
        res["derived"] = dict(mean_elevation_deg=el, bottom_edge_below_horizontal_deg=vis_down,
            floor_visible_from_m_at_0p40=(0.40/math.tan(math.radians(vis_down)) if vis_down>0 else None),
            virtual_cam_15down_vfov63p5_needs_deg=46.75, virtual_cam_feasible=(vis_down >= 46.75))
        print(json.dumps(res["derived"], indent=1))
    json.dump(res, open(os.path.join(out,"calibration.json"),"w"), indent=1)
    print("wrote", os.path.join(out,"calibration.json"))

if __name__ == "__main__":
    main()
