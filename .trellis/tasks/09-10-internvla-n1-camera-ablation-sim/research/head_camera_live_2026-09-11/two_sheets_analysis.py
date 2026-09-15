#!/usr/bin/env python3
"""Two-sheet pitch check: sheet A upright on a box face, sheet B flat on the floor, same frame.
Detects A, masks it, then searches B in the lower image at several upscales. solvePnP both with the fitted intrinsics.
Elevation from A assumes the box face is vertical; elevation from B assumes the floor is level (robot lies on it, IMU level).
The angle between the two board normals measures the box-face lean directly (90 deg = vertical face)."""
import sys, json, math, glob, os, cv2, numpy as np
cv2.ocl.setUseOpenCL(False)
calib, out_dir = sys.argv[1], sys.argv[2]; frames = sys.argv[3:]
C = json.load(open(calib)); K = np.array(C["K"]); dist = np.array(C["dist"]); size = (11,8); sq = 20.0
objp = np.zeros((88,3), np.float32); objp[:,:2] = np.mgrid[0:11,0:8].T.reshape(-1,2)*sq
os.makedirs(out_dir, exist_ok=True)
def sb(g): 
    ok,c = cv2.findChessboardCornersSB(g, size, flags=cv2.CALIB_CB_EXHAUSTIVE|cv2.CALIB_CB_ACCURACY)
    return c.reshape(-1,2).astype(np.float32) if ok else None
def pnp(c):
    ok, rv, tv = cv2.solvePnP(objp, c, K, dist, flags=cv2.SOLVEPNP_IPPE)
    Rm,_ = cv2.Rodrigues(rv); rep = cv2.projectPoints(objp, rv, tv, K, dist)[0].reshape(-1,2)
    return Rm, tv.ravel(), float(np.sqrt(np.mean(np.sum((rep-c)**2,axis=1))))
def elev_from_down(d):
    d = d/np.linalg.norm(d); d = d if d[1] > 0 else -d
    return math.degrees(math.asin(-d[2])), math.degrees(math.atan2(d[0], d[1])), d
results = []
for f in frames:
    g = cv2.imread(f, cv2.IMREAD_GRAYSCALE); h, w = g.shape
    cA = sb(g)
    r = dict(frame=os.path.basename(f))
    if cA is None: r["A"] = None; results.append(r); print(f, "upright board not found"); continue
    RA, tA, repA = pnp(cA)
    vert = RA[:,1] if abs(RA[1,1]) >= abs(RA[1,0]) else RA[:,0]
    elA, rollA, dA = elev_from_down(vert)
    r["A"] = dict(elevation_deg=elA, roll_deg=rollA, reproj_px=repA, dist_m=float(np.linalg.norm(tA))/1000, normal=RA[:,2].tolist(),
                  bbox=[float(cA[:,0].min()),float(cA[:,0].max()),float(cA[:,1].min()),float(cA[:,1].max())])
    # mask A and search B below it
    m = g.copy(); x0,x1,y0,y1 = [int(v) for v in r["A"]["bbox"]]; pad = 25
    cv2.rectangle(m, (max(0,x0-pad), max(0,y0-pad)), (min(w-1,x1+pad), min(h-1,y1+pad)), 128, -1)
    yb = max(0, y1 - 10); crop = m[yb:h, :]
    cB = None
    for s in (2,3,4,5):
        up = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
        c = sb(up)
        if c is None:
            ok, c2 = cv2.findChessboardCorners(up, size, flags=cv2.CALIB_CB_ADAPTIVE_THRESH|cv2.CALIB_CB_NORMALIZE_IMAGE)
            if ok: c = cv2.cornerSubPix(up, c2, (7,7), (-1,-1), (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 40, 1e-3)).reshape(-1,2)
        if c is not None:
            cB = (c/s + np.array([0, yb], np.float32)).astype(np.float32); r["B_scale"] = s; break
    if cB is None:
        r["B"] = None; print(f"{os.path.basename(f)}: A elevation {elA:+.2f} (if box face vertical), dist {r['A']['dist_m']:.2f} m; flat sheet NOT detected")
    else:
        RB, tB, repB = pnp(cB)
        elB, rollB, dB = elev_from_down(RB[:,2])
        ang = math.degrees(math.acos(abs(float(np.dot(RA[:,2], RB[:,2])))))
        # camera height above the floor plane: distance from camera origin to the plane of B along its normal
        pts = (RB @ objp.T + tB.reshape(3,1)).T
        height = float(np.mean(pts @ dB))/1000
        r["B"] = dict(elevation_deg=elB, roll_deg=rollB, reproj_px=repB, normal=RB[:,2].tolist(), camera_height_m=height,
                      bbox=[float(cB[:,0].min()),float(cB[:,0].max()),float(cB[:,1].min()),float(cB[:,1].max())])
        r["angle_between_normals_deg"] = ang
        r["box_face_lean_deg_top_toward_camera_positive"] = elB - elA
        print(f"{os.path.basename(f)}: A(upright) {elA:+.2f} deg | B(flat floor) {elB:+.2f} deg | normals {ang:.2f} deg apart | cam height {height:.3f} m | reproj A {repA:.2f} B {repB:.2f} px | B at {r['B_scale']}x")
        vis = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        cv2.drawChessboardCorners(vis, size, cA.reshape(-1,1,2), True); cv2.drawChessboardCorners(vis, size, cB.reshape(-1,1,2), True)
        cv2.imwrite(os.path.join(out_dir, "both_"+os.path.basename(f)), vis)
    results.append(r)
json.dump(results, open(os.path.join(out_dir, "two_sheets.json"), "w"), indent=1)
