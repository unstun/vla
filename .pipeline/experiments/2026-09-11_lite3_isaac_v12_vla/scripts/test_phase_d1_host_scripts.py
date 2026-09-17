#!/usr/bin/env python3
"""Local tests for the D.1 host scripts: the verified fetch and the D.1b summary gate. No network, no GPU.

    python3 scripts/test_phase_d1_host_scripts.py
"""
import functools
import hashlib
import http.server
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import threading

HERE = pathlib.Path(__file__).resolve().parents[1]
RESULTS = []


def check(name, cond, detail=''):
    RESULTS.append((name, bool(cond)))
    print('{} {}{}'.format('PASS' if cond else 'FAIL', name, ' - ' + str(detail) if detail and not cond else ''))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob_sha1(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def fetch_tests():
    fetch = load(HERE / 'scripts' / 'phase_d1_fetch_scene.py', 'fetch')
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        served = tmp / 'served' / 'kujiale_x'
        (served / 'Meshes').mkdir(parents=True)
        files = {'kujiale_x/kujiale_x.usda': b'#usda 1.0\n', 'kujiale_x/Meshes/a b.usd': b'PXR-USDC' + b'\0' * 100,
                 'kujiale_x/rooms.json': b'[]\n'}
        entries = []
        for rel, data in files.items():
            (tmp / 'served' / rel).write_bytes(data)
            lfs = None if rel.endswith('rooms.json') else hashlib.sha256(data).hexdigest()
            entries.append({'path': rel, 'size': len(data), 'lfs_sha256': lfs, 'git_oid': git_blob_sha1(data)})
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp / 'served'))
        handler.log_message = lambda *a, **k: None
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        manifest = {'repo': 'r', 'revision': 'v', 'scene': 'kujiale_x', 'files': 3,
                    'bytes': sum(e['size'] for e in entries), 'entries': entries,
                    'resolve_url_template': 'http://127.0.0.1:{}/{{path}}'.format(server.server_address[1])}
        mpath = tmp / 'manifest.json'
        mpath.write_text(json.dumps(manifest))
        live = [{'type': 'file', 'path': e['path'], 'size': e['size'], 'oid': e['git_oid'],
                 'lfs': {'oid': e['lfs_sha256'], 'size': e['size']} if e['lfs_sha256'] else None} for e in entries]
        fetch.list_revision = lambda repo, rev, folder: live
        dest = tmp / 'dest'
        rc = fetch.main(['--manifest', str(mpath), '--dest', str(dest), '--workers', '2'])
        check('fetch: downloads and verifies (LFS sha256 and git blob sha1, space in name)',
              rc == 0 and (dest / 'kujiale_x' / 'Meshes' / 'a b.usd').read_bytes() == files['kujiale_x/Meshes/a b.usd'])
        sums = (dest / 'kujiale_x' / 'SHA256SUMS.txt').read_text().splitlines()
        check('fetch: SHA256SUMS lists every file relative to the scene',
              len(sums) == 3 and any(line.endswith('  Meshes/a b.usd') for line in sums), sums)
        record = json.loads((dest / 'kujiale_x_download_record.json').read_text())
        check('fetch: record counts', record['failed'] == 0 and record['bytes_verified'] == manifest['bytes'], record)
        try:
            fetch.main(['--manifest', str(mpath), '--dest', str(dest)])
            refused = False
        except SystemExit:
            refused = True
        check('fetch: refuses to overwrite an existing copy', refused)

        dest2 = tmp / 'dest2'
        fetch.list_revision = lambda repo, rev, folder: live[:2]
        try:
            fetch.main(['--manifest', str(mpath), '--dest', str(dest2)])
            refused = False
        except SystemExit:
            refused = True
        check('fetch: refuses when the live listing differs', refused and not (dest2 / 'kujiale_x').exists())

        fetch.list_revision = lambda repo, rev, folder: live
        (tmp / 'served' / 'kujiale_x' / 'rooms.json').write_bytes(b'[1]\n')   # same size, wrong content
        dest3 = tmp / 'dest3'
        rc = fetch.main(['--manifest', str(mpath), '--dest', str(dest3), '--workers', '1'])
        rec3 = json.loads((dest3 / 'kujiale_x_download_record.json').read_text())
        check('fetch: corrupted file fails and nothing is renamed into place',
              rc == 1 and rec3['failed'] == 1 and not (dest3 / 'kujiale_x').exists()
              and (dest3 / 'kujiale_x.partial').exists(), rec3['failed'])
        (tmp / 'served' / 'kujiale_x' / 'rooms.json').write_bytes(files['kujiale_x/rooms.json'])
        rc = fetch.main(['--manifest', str(mpath), '--dest', str(dest3), '--workers', '1'])
        rec3 = json.loads((dest3 / 'kujiale_x_download_record.json').read_text())
        check('fetch: resume keeps verified files and fetches only the bad one',
              rc == 0 and rec3['kept_from_partial'] == 2 and (dest3 / 'kujiale_x' / 'rooms.json').exists(), rec3)
        server.shutdown()


def summary_tests():
    test_mod = load(HERE / 'phase_d' / 'test_stage_audit.py', 'tsa')
    thr_path = HERE / 'phase_d' / 'stage_audit_thresholds_d1b.json'
    thr_sha = hashlib.sha256(thr_path.read_bytes()).hexdigest()
    script = HERE / 'scripts' / 'phase_d1b_stage_audit_summary.py'

    def make_run(tmp, name, own_peak=4800, marker_ok=True, sha=thr_sha, log='', error=None, sample_times=None,
                 cid='aaaaaaaaaaaa', truncate=False):
        run = tmp / name
        (run / 'audit').mkdir(parents=True)
        result = test_mod.fake_result()
        result['thresholds_sha256'] = sha
        result['marks'] = [{'mark': 'app_started', 't_s': 1.0, 'unix_s': 1000.5, 'device_used_mib': 3000},
                           {'mark': 'render_B_done', 't_s': 4.0, 'unix_s': 1003.5, 'device_used_mib': 8000}]
        if error:
            result['error'] = error
        text = json.dumps(result, indent=1) + '\n'
        (run / 'audit' / 'stage_audit_result.json').write_text(text[:len(text) // 2] if truncate else text)
        if marker_ok is not None:
            digest = hashlib.sha256(text.encode()).hexdigest() if marker_ok else '0' * 64
            (run / 'audit' / 'STAGE_AUDIT_COMPLETE').write_text(digest + '\n')
        (run / 'container_id12.txt').write_text(cid + '\n')
        (run / 'compute_apps_before.txt').write_text('1240:2859:bbbbbbbbbbbb;\n')
        lines = ['unix_s,device_used_mib,util_pct,apps']
        times = sample_times or [1000 + i for i in range(5)]
        owns = [0, 1000, own_peak, own_peak - 200, 0]
        for i, t in enumerate(times):
            own = owns[min(i, len(owns) - 1)]
            apps = '1240:2859:bbbbbbbbbbbb;' + ('777:{}:aaaaaaaaaaaa;'.format(own) if own else '')
            if i == 2:
                apps += '888:300:cccccccccccc;'   # a process from neither container: never counted as ours
            lines.append('{:.2f},{},{},{}'.format(t, 2859 + own + 60, 20, apps))
        lines.insert(3, '1001.50,,,')               # one failed nvidia-smi sample, as the sampler now writes it
        (run / 'samples.csv').write_text('\n'.join(lines) + '\n')
        (run / 'sim.log').write_text(log)
        (run / 'exit_code').write_text('0\n')
        return run

    def run_summary(run):
        proc = subprocess.run([sys.executable, str(script), '--run-dir', str(run), '--thresholds', str(thr_path)],
                              capture_output=True, text=True)
        return proc.returncode, json.loads((run / 'summary.json').read_text()), proc.stdout

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        rc, s, out = run_summary(make_run(tmp, 'good', log='[Error] [omni.physx] CollisionAPI applied to an unknown UsdGeomGPrim type\n'))
        check('summary: good run admitted, exit 0', rc == 0 and s['gate']['admit_to_d1c'], out)
        check('summary: own peak by container id, vendor and stray process excluded',
              s['gpu']['isaac_peak_mib'] == 4800 and s['gpu']['vendor_mib_min_max'] == [2859, 2859]
              and s['gpu']['unattributed_mib_max'] == 300, s['gpu'])
        check('summary: log scan counts', s['log_scan']['error_lines']['count'] == 1
              and s['log_scan']['collision_api_unknown_gprim']['count'] == 1, s['log_scan'])
        rc, s, _ = run_summary(make_run(tmp, 'marginal', own_peak=6000))
        check('summary: 6000 MiB marginal still admitted', rc == 0 and s['gate']['checks'][-1]['verdict'] == 'MARGINAL')
        rc, s, _ = run_summary(make_run(tmp, 'oom', own_peak=7000))
        check('summary: 7000 MiB fails, exit 1', rc == 1 and s['gate']['failed'] == ['M1_isaac_gpu_peak'], s['gate']['failed'])
        rc, s, _ = run_summary(make_run(tmp, 'tampered', marker_ok=False))
        check('summary: marker mismatch is a problem, exit 2', rc == 2 and s['problems'], s['problems'])
        rc, s, _ = run_summary(make_run(tmp, 'nomarker', marker_ok=None, error='Traceback\nRuntimeError: boom'))
        check('summary: missing marker with error, exit 2', rc == 2 and s['error_tail'][-1] == 'RuntimeError: boom', s)
        rc, s, _ = run_summary(make_run(tmp, 'otherthr', sha='f' * 64))
        check('summary: run with different thresholds, exit 2', rc == 2 and 'not the frozen' in s['problems'][0], s['problems'])
        rc, s, _ = run_summary(make_run(tmp, 'gap', sample_times=[1000, 1001, 1002, 1009, 1010]))
        check('summary: a 7 s sampler gap inside the audit is a problem, exit 2, and M1 gets no peak',
              rc == 2 and any('gap' in p for p in s['problems']) and s['gate']['checks'][-1]['verdict'] == 'MISSING',
              s['problems'])
        rc, s, _ = run_summary(make_run(tmp, 'late', sample_times=[1000, 1001, 1002]))
        check('summary: sampler that stopped before the last mark, exit 2',
              rc == 2 and any('last mark' in p for p in s['problems']), s['problems'])
        rc, s, _ = run_summary(make_run(tmp, 'nocid', cid=''))
        check('summary: no container id, exit 2', rc == 2 and any('container id' in p for p in s['problems']), s['problems'])
        run = make_run(tmp, 'truncated', truncate=True)
        proc = subprocess.run([sys.executable, str(script), '--run-dir', str(run), '--thresholds', str(thr_path)],
                              capture_output=True, text=True)
        check('summary: a truncated result file is a crash, exit 2, never a gate verdict',
              proc.returncode == 2 and 'SUMMARY_CRASHED' in proc.stdout, proc.stdout[-300:])
        edited = tmp / 'edited_thresholds.json'
        edited.write_text(thr_path.read_text().replace('"wall_limit_s": 1800', '"wall_limit_s": 3600'))
        run = make_run(tmp, 'edited', sha=hashlib.sha256(edited.read_bytes()).hexdigest())
        proc = subprocess.run([sys.executable, str(script), '--run-dir', str(run), '--thresholds', str(edited)],
                              capture_output=True, text=True)
        check('summary: an edited thresholds file (even if the run used it) is not the frozen one, exit 2',
              proc.returncode == 2 and 'is not the frozen' in proc.stdout, proc.stdout[-300:])


if __name__ == '__main__':
    fetch_tests()
    summary_tests()
    failed = [n for n, ok in RESULTS if not ok]
    print('{}/{} checks passed'.format(len(RESULTS) - len(failed), len(RESULTS)))
    sys.exit(1 if failed else 0)
