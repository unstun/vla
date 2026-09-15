"""Copy identified Lite3 utilities/assets into an independent NavDP experiment."""
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
OLD = EXP.parent / '2026-09-09_lightnav0_official_demo_rented4090'
SOURCE = OLD / 'work/LightNav-0-lite3-capabilities-v1/mujoco_demo/vln_mujoco'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    records = []
    def copy(src, dst):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        records.append({'source': str(src), 'destination': str(dst.relative_to(EXP)), 'sha256': sha(dst)})
    for rel in ['model.py', 'robots/base.py', 'robots/lite3.py']:
        copy(SOURCE / rel, EXP / 'lib' / rel)
    for package in [EXP/'lib', EXP/'lib/robots']:
        (package/'__init__.py').touch()
    for sub in ['assets/lite3', 'policy']:
        for src in (OLD/'lite3_v1'/sub).rglob('*'):
            if src.is_file() and not src.name.startswith('._'):
                copy(src, EXP/sub/src.relative_to(OLD/'lite3_v1'/sub))
    copy(OLD/'lite3_v1/scripts/run_job.py', EXP/'scripts/run_job.py')
    copy(OLD/'work/LightNav-0-lite3-capabilities-v1/LICENSE', EXP/'setup/inherited_scene_loader_LICENSE')
    copy(OLD/'work/LightNav-0-lite3-capabilities-v1/THIRD_PARTY_NOTICES.md', EXP/'setup/inherited_scene_asset_NOTICES.md')
    for name in ['clear', 'blocked']:
        src = OLD/'lite3_capabilities_v1/cases'/f'{name}.xml'
        tree = ET.parse(src)
        # Point goals must occupy free space, not the old semantic-target mesh.
        for body in list(tree.getroot().find('worldbody').findall('body')):
            tree.getroot().find('worldbody').remove(body)
        for item in tree.getroot().iter():
            if item.get('file'):
                source_asset = (src.parent/item.get('file')).resolve()
                dest = EXP/'assets/scene'/source_asset.name
                copy(source_asset, dest)
                item.set('file', '../assets/scene/'+dest.name)
        obstacle = tree.find(".//geom[@name='test_obstacle']")
        if obstacle is not None:
            obstacle.set('pos', '8.25 13.8 0.35')
            obstacle.set('size', '0.30 0.45 0.35')
        (EXP/'cases').mkdir(exist_ok=True)
        ET.indent(tree, space='  ')
        tree.write(EXP/'cases'/f'{name}.xml', encoding='utf-8', xml_declaration=True)
    model = EXP/'models/x-navdp_posttrain.ckpt'
    (EXP/'setup/selected_model.json').write_text(json.dumps({
        'id':'InternRobotics/X-NavDP', 'revision':'7cee38a8d8308874d2b8488783c612f42060ac41',
        'file':model.name, 'bytes':873100357,
        'sha256':'267089a81bbbe7a913debda6603f3f1b66a79520370ce953b2d888d793b89f24',
        'source_commit':'bff5eb8857f50e082243fb455d312409daabc3aa',
        'walking_policy_sha256':'7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',
        'embodiment_index':2, 'embodiment_note':'Original Go2 embedding; unvalidated Lite3 transfer',
    },indent=2)+'\n')
    (EXP/'setup/reused_source_manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps({'copied_files':len(records),'bytes':sum((EXP/r['destination']).stat().st_size for r in records)}))

if __name__ == '__main__':
    main()
