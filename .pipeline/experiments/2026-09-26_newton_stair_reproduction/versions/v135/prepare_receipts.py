"""Reuse byte-verified x86 native installs; qualify the new map separately."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;TASK=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=TASK/'results/recovery_v135';out.mkdir(exist_ok=False)
for variant,parent in [('baseline','v133'),('candidate','v134')]:
    source=TASK/f'results/recovery_{parent}/candidate_receipt.json'
    receipt=json.loads(source.read_text())
    for name,expected in receipt['files'].items():assert sha(TASK/Path(name).relative_to('/task'))==expected,name
    receipt.update(variant=variant,native_version=parent,reused_native_install=True,
        native_parent_receipt_sha256=sha(source),integration_version='v135')
    if variant=='candidate':
        record=json.loads((HERE/'global_map_input.json').read_text())
        p=TASK/Path(record['file']).relative_to('/task');assert sha(p)==record['map_sha256']
        receipt['files'][record['file']]=record['map_sha256']
        receipt['global_map_input_sha256']=sha(HERE/'global_map_input.json')
    (out/f'{variant}_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('VERIFIED_REUSE_V133_V134_NEW_GLOBAL_MAP')
