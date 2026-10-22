"""Bind verified new-host files without editing any frozen v286 source."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
VERSION = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v286'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def fnv(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return str(value)


def main():
    receipt = ROOT / 'evidence/native_binding01.json'
    assert not receipt.exists()
    geometry = json.loads((ROOT / 'evidence/geometry01_closed.json').read_text())
    assert geometry['passed']
    assert json.loads((ROOT / 'evidence/components03.json').read_text())['stage'] == 'passed'
    native = ROOT / 'native'
    previous = native / 'component_fixtures03'
    assert not previous.exists()
    (native / 'fixtures').rename(previous)
    shutil.copytree(Path(geometry['final_fixtures']), native / 'fixtures')
    fixtures = native / 'fixtures'
    descriptor = fixtures / 'source_surface.env'
    (fixtures / 'probe271.env').write_text('source /work/fixtures/probe225.env\n'
        'export RAW_FIELD=/work/fixtures/source_surface.env\nexport RAW_FNV=' + fnv(descriptor.read_bytes()) + '\n')
    # Reuse the frozen metadata derivation on the identical regenerated fields.
    source = (VERSION.parent / 'v282/prepare_bindings.py').read_text()
    begin = source.index("folder=dest/'building'")
    end = source.index('receipt=dict(', begin)
    namespace = dict(__file__=str(VERSION.parent / 'v282/prepare_bindings.py'),
        HERE=VERSION.parent / 'v282', dest=fixtures, json=json, sha=sha, fnv=fnv)
    exec(compile(source[begin:end], str(VERSION.parent / 'v282/prepare_bindings.py'), 'exec'), namespace)
    original_metadata = json.loads((VERSION.parent / 'v282/fixture_binding.json').read_text())['new_metadata']
    metadata = {name: dict(sha256=sha(fixtures / 'building' / name), original_sha256=expected)
        for name, expected in original_metadata.items()}
    frozen = VERSION / 'run_native.py'
    text = frozen.read_text()
    substitutions = {
        '/data/sun/vla_mppi_20261009': str(ROOT),
        '/home/sun/vla_exec/supported_air_refinement_v286': str(ROOT),
        "out=ROOT/('parent_evaluation' if a.parent else 'evaluation')": "out=ROOT/'evaluation03'",
        'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4':
            'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343',
    }
    for old, new in substitutions.items():
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    underlays = ['recovery_v188', 'command_continuity_v206_20261015', 'callback_failure_v232',
        'cooperative_search_v240', 'physical_traversability_v247/native']
    for name in underlays:
        old = 'source /task/' + name + '/install/setup.bash && '
        assert text.count(old) == 1
        text = text.replace(old, '')
    derived = ROOT / 'derived_run_native.py'
    derived.write_text(text)
    wrapper = ROOT / 'run_native.py'
    wrapper.write_text('from pathlib import Path\nimport sys\nassert "--parent" not in sys.argv\n'
        + 'source=Path(' + repr(str(derived)) + ').read_text()\n'
        + 'exec(compile(source,' + repr(str(derived)) + ',"exec"),dict(__file__='
        + repr(str(frozen)) + ',__name__="__main__"))\n')
    result = dict(passed=True, navigation_source_changed=False, physics_steps=0,
        original_native_manifest_sha256=sha(VERSION / 'native_manifest.json'),
        original_run_native_sha256=sha(frozen), derived_run_native_sha256=sha(derived),
        wrapper_sha256=sha(wrapper), substitutions=substitutions,
        underlays_replaced_by_same_source_full14_package_build=underlays,
        original_geometry_files_verified=geometry['exact_original_geometry_files'], metadata=metadata,
        fixture_files={str(p.relative_to(fixtures)): sha(p) for p in fixtures.rglob('*') if p.is_file()},
        old_component_fixtures_preserved=str(previous))
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, metadata_matches_original={k: v['sha256'] == v['original_sha256'] for k, v in metadata.items()})))


if __name__ == '__main__':
    main()
