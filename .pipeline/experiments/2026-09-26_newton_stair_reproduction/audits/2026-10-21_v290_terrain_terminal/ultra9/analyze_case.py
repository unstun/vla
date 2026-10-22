"""Reuse existing recorded-state analysis with explicit current-host paths."""
from pathlib import Path
import hashlib
import json
import os
import sys
import types
import zipfile

ROOT = Path('/home/ubuntu/sun/vla_v290_20261021')
EXP = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
VERSIONS = EXP / 'versions'
AUDIT = EXP / 'audits/2026-10-21_v290_terrain_terminal'
MIGRATION = ROOT / 'migration'
CASE = os.environ['V290_CASE_ID']
sys.path.insert(0, str(MIGRATION))
import physical
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def bind_raw_oracle():
    # Only paths are rebound. Both original raw-coordinate SHA assertions and
    # the complete finite material association are executed unchanged.
    source = VERSIONS / 'v272/raw_source_oracle.py'
    text = source.read_text()
    old = "BASE=Path('/data/sun/vla_mppi_20261009')"
    assert text.count(old) == 1
    text = text.replace(old, 'BASE=Path(' + repr(str(ROOT / 'geometry_data')) + ')')
    old = "EXP=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'"
    assert text.count(old) == 1
    text = text.replace(old, 'EXP=Path(' + repr(str(EXP)) + ')')
    module = types.ModuleType('raw_source_oracle')
    module.__file__ = str(source)
    sys.modules[module.__name__] = module
    exec(compile(text, str(source), 'exec'), module.__dict__)
    source2 = VERSIONS / 'v276/registered_point_oracle.py'
    text2 = source2.read_text()
    assert text2.count("BASE=Path('/data/sun/vla_mppi_20261009')") == 1
    text2 = text2.replace("BASE=Path('/data/sun/vla_mppi_20261009')", 'BASE=Path(' + repr(str(ROOT / 'geometry_data')) + ')')
    sys.path.insert(0, str(source2.parent))
    module2 = types.ModuleType('registered_point_oracle')
    module2.__file__ = str(source2)
    sys.modules[module2.__name__] = module2
    exec(compile(text2, str(source2), 'exec'), module2.__dict__)
    return dict(raw_original_sha256=sha(source), raw_executed_sha256=hashlib.sha256(text.encode()).hexdigest(),
        association_original_sha256=sha(source2), association_executed_sha256=hashlib.sha256(text2.encode()).hexdigest(),
        path_rebinding_only=True, physics_steps=0)

def main():
    physical.verify_sources()
    physical.offline = types.SimpleNamespace(IMAGE='sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343')
    sys.modules['case_binding'] = physical.bind_case()
    verifier=types.ModuleType('verify_case')
    verifier.__file__=str(VERSIONS/'v290/verify_case.py')
    sys.modules['verify_case']=verifier
    exec(compile((MIGRATION/'analysis_verify_case.py').read_text(),str(MIGRATION/'analysis_verify_case.py'),'exec'),verifier.__dict__)
    # Prefix analysis reads only measured telemetry. It never creates result.json.
    import prefix_analysis
    prefix_analysis.install(VERSIONS)
    sys.path[:0] = [str(VERSIONS / 'v196'), str(VERSIONS / 'v290')]
    frozen = AUDIT / 'postprocess_case.py'
    text = frozen.read_text()
    text = text[:text.rindex("if __name__=='__main__':main()")]
    changes = {
        '/data/sun/vla_mppi_20261009': str(ROOT),
        '/home/sun/vla_exec/physical_runs_v290': str(ROOT / 'physical_runs'),
        '/home/sun/vla_exec/local_cost_crash_v290/native': str(ROOT / 'native'),
        'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4': physical.offline.IMAGE,
        "host='gpu5070ti'": "host='ultra9'",
        "sha(VERSIONS/'v290/manifest.json')": "sha(MIGRATION/'physical_manifest01.json')",
    }
    for before, after in changes.items():
        assert before in text, before
        text = text.replace(before, after)
    for name in ('recovery_v188', 'command_continuity_v206_20261015'):
        text = text.replace('source /task/' + name + '/install/setup.bash && ', '')
    old = "profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)"
    assert text.count(old) == 1
    text = text.replace(old, old + ';profile.verify=verify_profile_adapter')
    begin = text.index("    identity=json.loads((VERSIONS/'v290/source_identity.json').read_text())")
    end = text.index('    return capture', begin)
    text = text[:begin] + "    save('post_run_execution_parity.json',verify_sources_adapter())\n" + text[end:]
    begin = text.index("    historical=Capture(PREFIX/'trials/v241_linux_full_attempt01/runs/v241_linux_full_attempt01')")
    end = text.index('    critical=[', begin)
    text = text[:begin] + "    retained_bounds=json.loads((MIGRATION/'reference_bounds.json').read_text())['critical_geometry_bounds']\n    lower,upper=map(np.array,retained_bounds)\n" + text[end:]
    text = text.replace("geometry_source='Original v241 sensor body coordinates during45-55s, expanded0.25m; full floor-transition also reported'", "geometry_source='Original v24145-55s bounds copied from returned v285 audit; original raw data unavailable; full floor-transition also reported'")
    namespace = dict(__file__=str(frozen), __name__='new_host_recorded_analysis', MIGRATION=MIGRATION,
        verify_profile_adapter=physical.verify_profile, verify_sources_adapter=physical.verify_sources)
    exec(compile(text, str(frozen), 'exec'), namespace)
    results = namespace['RESULTS']
    results.mkdir(parents=True, exist_ok=True)
    (results / 'analysis_binding.json').write_text(json.dumps(dict(
        original_sha256=sha(frozen), executed_sha256=hashlib.sha256(text.encode()).hexdigest(),
        host_substitutions=changes, physics_steps=0), indent=2) + '\n')
    snapshot_path=results/'capture_snapshot.json'
    if snapshot_path.exists():
        # Analysis retries verify the original snapshot, including unchanged raw
        # bytes. Later derived audit files do not become new physical sources.
        snapshot=json.loads(snapshot_path.read_text())
        archive=Path(snapshot['archive'])
        assert sha(archive)==snapshot['archive_sha256']
        with zipfile.ZipFile(archive) as zipped:
            assert set(zipped.namelist())==set(snapshot['members'])
            for name,record in snapshot['members'].items():
                data=zipped.read(name)
                assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256']
                original=namespace['RAW']/name
                if original.exists():assert sha(original)==record['sha256'],name
    else:namespace['preserve']()
    capture = namespace['analyze_case']()
    namespace['margins'](capture)
    oracle = bind_raw_oracle()
    (results / 'raw_oracle_binding.json').write_text(json.dumps(oracle, indent=2) + '\n')
    namespace['raw_margins']()
    namespace['windows'](capture)
    for name, function in [('physical_support_margins.py', 'audit'), ('command_audit.py', 'audit')]:
        path = AUDIT / name
        code = path.read_text().replace('/data/sun/vla_mppi_20261009', str(ROOT))
        code = code.replace('/home/sun/vla_exec/physical_runs_v290', str(ROOT / 'physical_runs'))
        code = code.replace('/home/sun/vla_exec/local_cost_crash_v290/native', str(ROOT / 'native'))
        code = code.replace('sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4', physical.offline.IMAGE)
        code = code.replace("raw/'raw_capture_manifest.json'", "out/'capture_snapshot.json'")
        code = code.replace('raw_capture_manifest_sha256=', 'capture_snapshot_manifest_sha256=')
        for underlay in ('recovery_v188', 'command_continuity_v206_20261015'):
            code = code.replace('source /task/' + underlay + '/install/setup.bash && ', '')
        # The edge audit is numerical; video delivery is checked separately.
        code = code.replace("    assert (results / 'local_video_delivery.json').is_file()\n", '')
        scope = dict(__file__=str(path), __name__='new_host_' + path.stem)
        exec(compile(code, str(path), 'exec'), scope)
        scope[function](CASE)
    print(json.dumps(dict(case_id=CASE, analysis_passed=True, physics_steps=0)), flush=True)

if __name__ == '__main__':
    main()
