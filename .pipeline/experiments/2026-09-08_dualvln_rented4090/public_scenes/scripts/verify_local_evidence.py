"""Verify the returned evidence locally: hashes, decodable video, readable frames.

Runs on the local source-of-truth machine. Nothing here talks to the remote host;
it checks the bytes that actually arrived against the manifest taken from the
remote host, then decodes the MP4s and writes the representative frames the
package asks to inspect.
"""
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PS = ROOT / 'public_scenes'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def ffprobe(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
         '-show_entries', 'stream=codec_name,width,height,nb_read_frames,avg_frame_rate',
         '-show_entries', 'format=duration,size', '-of', 'json', str(path)],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def extract(path, out_dir, frames):
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for label, idx in frames.items():
        dst = out_dir / f'{path.stem}__{label}_f{idx:04d}.png'
        subprocess.run(
            ['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', str(path),
             '-vf', f'select=eq(n\\,{idx})', '-vsync', '0', '-frames:v', '1', str(dst)],
            check=True)
        if dst.exists():
            written.append(str(dst.relative_to(ROOT)))
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', default='public_scenes/setup/remote_manifest.txt')
    ap.add_argument('--out', default='public_scenes/setup/local_evidence_verification.json')
    a = ap.parse_args()

    report = {'hash_check': {}, 'videos': [], 'frames_dir': 'public_scenes/decoded_frames'}

    # ---- 1. every returned file against the remote manifest -------------------
    expected = {}
    for line in (ROOT / a.manifest).read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        expected[rel.strip()] = digest
    missing, mismatch, ok = [], [], 0
    for rel, digest in expected.items():
        p = PS / rel
        if not p.exists():
            missing.append(rel)
        elif sha256(p) != digest:
            mismatch.append(rel)
        else:
            ok += 1
    report['hash_check'] = {'files_in_remote_manifest': len(expected), 'verified_identical': ok,
                            'missing_locally': missing, 'hash_mismatch': mismatch}

    # ---- 2. decode every returned MP4 ----------------------------------------
    frames_root = ROOT / report['frames_dir']
    for mp4 in sorted(PS.glob('runs/*/**/*.mp4')):
        probe = ffprobe(mp4)
        st = probe['streams'][0]
        n = int(st['nb_read_frames'])
        picks = collections.OrderedDict([
            ('start', 0),
            ('early_movement', max(0, min(n - 1, n // 5))),
            ('mid', max(0, n // 2)),
            ('late', max(0, min(n - 1, (4 * n) // 5))),
            ('terminal', max(0, n - 1)),
        ])
        rel_run = mp4.relative_to(PS / 'runs').parts[0]
        written = extract(mp4, frames_root / rel_run, picks)
        report['videos'].append({
            'path': str(mp4.relative_to(ROOT)),
            'sha256': sha256(mp4),
            'bytes': int(probe['format']['size']),
            'codec': st['codec_name'],
            'resolution': f"{st['width']}x{st['height']}",
            'frames_decoded': n,
            'avg_frame_rate': st['avg_frame_rate'],
            'duration_s': round(float(probe['format']['duration']), 2),
            'decoded_frames_written': written,
        })

    (ROOT / a.out).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    hc = report['hash_check']
    print(f"hash check: {hc['verified_identical']}/{hc['files_in_remote_manifest']} identical, "
          f"{len(hc['missing_locally'])} missing, {len(hc['hash_mismatch'])} mismatched")
    for v in report['videos']:
        print(f"  {v['path'].split('public_scenes/')[-1]:<62} {v['resolution']:>9} "
              f"{v['frames_decoded']:>5} frames {v['duration_s']:>6.1f}s  {v['codec']}")
    print('LOCAL_VERIFICATION_WRITTEN', a.out)


if __name__ == '__main__':
    main()
