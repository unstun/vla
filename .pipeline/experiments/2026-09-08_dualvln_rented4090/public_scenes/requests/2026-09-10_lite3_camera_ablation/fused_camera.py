"""Virtual-camera fusion of the two Lite3 mounts (pure numpy; OpenCV optional).

Frames follow Habitat's agent convention: x right, y up, z backward (a camera
looks along -z). A sensor's pose is its position in the agent frame plus a
pitch about its own x axis (positive = up, i.e. Habitat orientation[0]).
Pixels: u right, v down, pinhole with a horizontal field of view; the vertical
field of view follows from the aspect ratio (square pixels).

fuse() builds the image a level virtual pinhole camera would see from the head
camera's optical centre:
  * head camera (same optical centre, pitched up): pure rotation, a fixed
    lookup table sampled bilinearly;
  * D435i colour + z-depth (different optical centre, pitched down): every
    depth pixel is back-projected, moved into the virtual frame, and splatted
    with a z-buffer; small holes are filled from valid neighbours;
  * composition: head pixels where the head sees; a linear feather over the
    last `feather_rows` rows of head coverage into the D435i image; D435i
    elsewhere; black where neither sees.
Returns the uint8 image and a coverage map (0 none, 1 head, 2 d435, 3 blend).
"""
import math
import numpy as np

try:  # optional, faster resampling
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None


class Cam:
    """Pinhole camera in the agent frame."""

    def __init__(self, width, height, hfov_deg, position, pitch_rad):
        self.w, self.h = int(width), int(height)
        self.f = (self.w / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)  # pixels
        self.p = np.asarray(position, dtype=np.float64).reshape(3)
        c, s = math.cos(pitch_rad), math.sin(pitch_rad)
        self.R = np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])  # sensor -> agent (rot about x)

    def vfov_deg(self):
        return math.degrees(2 * math.atan((self.h / 2.0) / self.f))

    def rays(self):
        """Unit-free ray directions in the SENSOR frame for every pixel, shape (h, w, 3)."""
        u = (np.arange(self.w, dtype=np.float64) + 0.5 - self.w / 2.0) / self.f
        v = (np.arange(self.h, dtype=np.float64) + 0.5 - self.h / 2.0) / self.f
        uu, vv = np.meshgrid(u, v)
        return np.stack([uu, -vv, -np.ones_like(uu)], axis=-1)

    def project(self, P):
        """Sensor-frame points (..., 3) -> pixel coords (u, v) and validity (in front, inside)."""
        z = -P[..., 2]
        with np.errstate(divide='ignore', invalid='ignore'):
            u = self.w / 2.0 + P[..., 0] / z * self.f - 0.5
            v = self.h / 2.0 - P[..., 1] / z * self.f - 0.5
        ok = (z > 1e-6) & (u >= 0) & (u <= self.w - 1) & (v >= 0) & (v <= self.h - 1)
        return u, v, ok


def _bilinear(img, u, v, ok):
    """Sample img (h, w, c) at float pixel coords; invalid -> 0."""
    if cv2 is not None:
        out = cv2.remap(img, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        out[~ok] = 0
        return out
    h, w = img.shape[:2]
    u0 = np.clip(np.floor(u), 0, w - 2).astype(int); v0 = np.clip(np.floor(v), 0, h - 2).astype(int)
    du = np.clip(u - u0, 0, 1)[..., None]; dv = np.clip(v - v0, 0, 1)[..., None]
    a = img[v0, u0].astype(np.float64); b = img[v0, u0 + 1]; c = img[v0 + 1, u0]; d = img[v0 + 1, u0 + 1]
    out = (a * (1 - du) * (1 - dv) + b * du * (1 - dv) + c * (1 - du) * dv + d * du * dv)
    out[~ok] = 0
    return out.astype(img.dtype)


def head_lut(virt: Cam, head: Cam):
    """Fixed lookup table: virtual pixel -> head pixel (u, v) and validity."""
    d_agent = virt.rays() @ virt.R.T          # (h, w, 3) directions in the agent frame
    d_head = d_agent @ head.R                 # agent -> head sensor frame (R^T applied)
    return head.project(d_head)


def warp_d435(virt: Cam, d435: Cam, rgb, depth_m, depth_valid_max):
    """Forward-warp D435i colour into the virtual view with its z-depth. Returns (img, mask)."""
    z = np.asarray(depth_m, dtype=np.float64).reshape(d435.h, d435.w)
    valid = np.isfinite(z) & (z > 0.05) & (z < depth_valid_max)
    P_s = d435.rays() * z[..., None]                       # sensor-frame points (z-depth along -z)
    P_a = P_s @ d435.R.T + d435.p                          # agent frame
    P_v = (P_a - virt.p) @ virt.R                          # virtual sensor frame
    u, v, ok = virt.project(P_v)
    ok &= valid
    zi = -P_v[..., 2]
    ui = np.rint(u[ok]).astype(int); vi = np.rint(v[ok]).astype(int); zz = zi[ok]
    col = np.asarray(rgb)[..., :3].reshape(-1, 3)[ok.reshape(-1)]
    out = np.zeros((virt.h, virt.w, 3), np.float64)
    zbuf = np.full((virt.h, virt.w), np.inf)
    # z-buffer splat: process far to near so the nearest sample wins
    # z-buffer: keep, per destination pixel, only the nearest sample (np.minimum.at is well defined
    # for repeated indices, unlike fancy-index assignment order)
    np.minimum.at(zbuf, (vi, ui), zz)
    keep = zz <= zbuf[vi, ui] + 1e-9
    out[vi[keep], ui[keep]] = col[keep]
    mask = np.isfinite(zbuf)
    # fill isolated holes inside the covered region from valid 3x3 neighbours (two passes)
    for _ in range(2):
        holes = ~mask
        if not holes.any():
            break
        acc = np.zeros_like(out); cnt = np.zeros((virt.h, virt.w), np.float64)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                sh = np.roll(np.roll(out, dy, axis=0), dx, axis=1)
                sm = np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
                acc += sh * sm[..., None]; cnt += sm
        fill = holes & (cnt >= 5)
        fill[0, :] = fill[-1, :] = False   # np.roll wraps at the borders; never fill from the opposite edge
        fill[:, 0] = fill[:, -1] = False
        out[fill] = acc[fill] / cnt[fill][:, None]
        mask = mask | fill
    return out, mask


def fuse(head_rgb, d435_rgb, d435_depth_m, virt: Cam, head: Cam, d435: Cam,
         feather_rows=8, depth_valid_max=9.9, lut=None):
    """Return (fused uint8 (h, w, 3), coverage uint8 (h, w))."""
    if lut is None:
        lut = head_lut(virt, head)
    hu, hv, hok = lut
    head_img = _bilinear(np.asarray(head_rgb)[..., :3], hu, hv, hok).astype(np.float64)
    d_img, d_mask = warp_d435(virt, d435, d435_rgb, d435_depth_m, depth_valid_max)
    # feather: per column, the last `feather_rows` valid head rows blend into the D435i image
    w_head = hok.astype(np.float64)
    if feather_rows > 0:
        # distance (in rows) from each head-valid pixel to the head coverage boundary below it
        below_invalid = np.zeros_like(hok)
        run = np.zeros(virt.w, dtype=np.float64)
        dist = np.full((virt.h, virt.w), np.inf)
        for r in range(virt.h - 1, -1, -1):
            run = np.where(hok[r], run + 1, 0.0)
            dist[r] = run
        blend = hok & (dist <= feather_rows) & d_mask
        w_head[blend] = dist[blend] / (feather_rows + 1.0)
    w_head[~hok] = 0.0
    w_head[hok & ~d_mask] = 1.0
    out = head_img * w_head[..., None] + d_img * (1.0 - w_head[..., None]) * (d_mask | hok)[..., None]
    out[~hok & ~d_mask] = 0.0
    cov = np.zeros((virt.h, virt.w), np.uint8)
    cov[d_mask] = 2
    cov[hok] = 1
    cov[hok & d_mask & (w_head < 1.0)] = 3
    return np.clip(out + 0.5, 0, 255).astype(np.uint8), cov


def coverage_stats(cov):
    n = cov.size
    return {'head': float((cov == 1).sum() / n), 'd435': float((cov == 2).sum() / n),
            'blend': float((cov == 3).sum() / n), 'none': float((cov == 0).sum() / n)}
