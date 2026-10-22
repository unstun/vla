from common import *
assert not (HERE/'manifest.json').exists()
binding=verify_inputs();write(HERE/'results/input_binding.json',binding)
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','RESULTS.md')}
write(HERE/'manifest.json',dict(version='v273',native='v272',native_manifest_sha256=binding['native']['native_manifest_sha256'],files=files,
    calls=105,original52_ledger_unchanged=True,clean_positive_total=50,clean_illegal_total=3,hard_radius_m=.35,sensor_period_s=.1,physical_attempts=0))
print(json.dumps(dict(manifest_sha256=sha(HERE/'manifest.json'),native_manifest_sha256=binding['native']['native_manifest_sha256'],calls=105)),flush=True)
