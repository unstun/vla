"""Bind the tested overlay and installed files to the local source identity."""
from pathlib import Path
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
WORK = TASK / 'event_replan_v212'
PARENT = TASK / 'command_continuity_v206_20261015'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
identity = json.loads((HERE / 'source_identity.json').read_text())
for rel, expected in identity['files'].items():
    assert sha(HERE / rel) == expected, rel
old = json.loads((PARENT / 'source_inventory.json').read_text())
inventory = {str(p.relative_to(WORK)): sha(p) for p in (WORK / 'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
owned = {str(p.relative_to(HERE)): sha(p) for p in (HERE / 'src').rglob('*') if p.is_file()}
for rel, expected in inventory.items():
    assert expected == owned.get(rel, old.get(rel)), rel
assert set(inventory) == set(old) | set(owned)
(WORK / 'source_inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
out = HERE / 'verification/remote'
out.mkdir(parents=True, exist_ok=True)
(out / 'test_results').mkdir(exist_ok=True)
suites = {}
for package in ('lite3_nav2_plugins','lite3_nav2_bridge'):
    for path in (WORK / 'build' / package / 'test_results').rglob('*.xml'):
        tree = ET.parse(path)
        cases = tree.findall('.//testcase')
        assert cases and not tree.findall('.//failure') and not tree.findall('.//error') and not tree.findall('.//skipped'), path
        suites[path.name] = len(cases)
        shutil.copyfile(path, out / 'test_results' / path.name)
assert set(suites) == {'test_route_policy.gtest.xml','test_direct_pct.gtest.xml',
    'test_terminal_tree.gtest.xml','test_event_planning.gtest.xml','test_wait_recovery.xunit.xml',
    'test_static_terrain.xunit.xml','test_terrain_profile.xunit.xml','test_mission_bridge.xunit.xml'}
installed = {str(p.relative_to(WORK)): sha(p) for p in (WORK / 'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
receipt = {'passed': True, 'unique_cases':sum(suites.values()), 'suites':suites,
    'source_inventory':inventory, 'installed_files':installed,
    'source_identity_sha256':sha(HERE/'source_identity.json'), 'built_packages':2,
    'underlay':str(PARENT), 'underlay_receipt_sha256':sha(PARENT/'evidence/receipt.json'),
    'changed_source_files':sorted(owned), 'execution_platform':'linux/amd64'}
for destination in (WORK/'evidence/receipt.json', out/'receipt.json'):
    destination.write_text(json.dumps(receipt,indent=2)+'\n')
for name in ('build.log','test.log','test-result.log'):
    shutil.copyfile(WORK/'evidence'/name, out/name)
print(json.dumps({'passed':True, 'unique_cases':sum(suites.values()), 'suites':suites}))
