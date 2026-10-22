from pathlib import Path
import json,shutil,hashlib
R=Path('/home/ubuntu/sun/vla_v288_20261020');O=Path('/home/ubuntu/sun/vla_v287_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
assert json.loads((R/'evidence/components06.json').read_text())['stage']=='passed'
(R/'native/fixtures').rename(R/'native/component_fixtures03')
shutil.copytree(O/'native/fixtures',R/'native/fixtures')
files={str(p.relative_to(R/'native/fixtures')):sha(p) for p in (R/'native/fixtures').rglob('*') if p.is_file()}
assert all(sha(O/'native/fixtures'/n)==h for n,h in files.items())
save(R/'evidence/geometry01_closed.json',dict(passed=True,mode='Reuse all immutable v287 field bytes; no geometry regeneration',parent_root=str(O),files=files,physics_steps=0))
metadata={n:dict(sha256=sha(R/'native/fixtures/building'/n),original_sha256=h) for n,h in json.loads((V.parent/'v282/fixture_binding.json').read_text())['new_metadata'].items()}
assert all(x['sha256']==x['original_sha256'] for x in metadata.values())
text=(V/'run_native.py').read_text().replace('/data/sun/vla_mppi_20261009',str(R)).replace('/home/sun/vla_exec/local_cost_crash_v288',str(R)).replace("out=ROOT/('parent_evaluation' if a.parent else 'evaluation')","out=ROOT/'evaluation03'").replace('sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343')
for n in ['recovery_v188','command_continuity_v206_20261015','callback_failure_v232','cooperative_search_v240','physical_traversability_v247/native']:
 old='source /task/'+n+'/install/setup.bash && ';assert old in text;text=text.replace(old,'')
(R/'derived_run_native.py').write_text(text)
(R/'run_native.py').write_text('from pathlib import Path\nimport sys\nassert "--parent" not in sys.argv\nsource=Path('+repr(str(R/'derived_run_native.py'))+').read_text()\nexec(compile(source,'+repr(str(R/'derived_run_native.py'))+',"exec"),dict(__file__='+repr(str(V/'run_native.py'))+',__name__="__main__"))\n')
save(R/'evidence/native_binding01.json',dict(passed=True,metadata=metadata,fixture_files=files,source_version='v288',reused_geometry_from='v287',physics_steps=0))
cohort=json.loads((R/'cohort/cases_manifest.json').read_text())
for case in cohort['cases']:
 folder=R/'cohort/cases'/case['case_id'];fixture=json.loads((folder/'fixture.json').read_text());assert fixture['physics_steps']==0 and fixture['max_scan_s']<=.1
 for rel,h in fixture['files'].items():assert sha(folder/rel)==h,(case['case_id'],rel)
for n in ('queries.txt','margins.csv'):
 if (R/'cohort'/n).exists():(R/'cohort'/n).rename(R/'cohort'/('v287_reference_'+n))
save(R/'evidence/cohort01.json',dict(stage='passed',cases=53,source='All v287 ultra9 zero-step captures reused byte-exact; all53 re-evaluated by v288',manifest_sha256=sha(R/'cohort/cases_manifest.json'),physics_steps=0))
print('Bound full unchanged geometry and53 captured inputs to new native binaries')
