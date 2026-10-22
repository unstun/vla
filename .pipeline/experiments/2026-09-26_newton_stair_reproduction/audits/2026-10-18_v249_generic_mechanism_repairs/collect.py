"""Return compact immutable evidence; retain full arrays and build products remotely."""
from pathlib import Path
import collections,csv,hashlib,json,shutil
BASE=Path('/data/sun/vla_mppi_20261009');HERE=Path(__file__).resolve().parent
OUT=HERE/'results';OUT.mkdir(exist_ok=True);receipt={};retained={}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,relative):
 q=OUT/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 receipt[str(q.relative_to(HERE))]=dict(remote_source=str(p),sha256=sha(p),bytes=p.stat().st_size)
for tag in ('diagnosis01','height_repair01','floor_repair01','floor_repair02','native_floor01','gap_repair01','oriented_gap01','shared_gap01'):
 for case in sorted((BASE/'generic_mechanisms_v249'/tag/'gpmp').glob('*')):
  if not case.is_dir():continue
  for name in ('result.txt','raw_gpmp.csv'):
   p=case/name
   if p.exists():copy(p,Path('gpmp')/tag/case.name/name)
  p=case/'dense_queries.csv'
  if p.exists():
   retained[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
   with p.open() as f:
    reader=csv.DictReader(f);fields=reader.fieldnames;witness=[];counts=collections.Counter()
    for row in reader:
     categories=[]
     if row['slice_height_known']=='0':categories.append('slice_alias_missing')
     if row['continuous_height_known']=='0':categories.append('continuous_missing')
     if row['native_verdict']!='0':categories.append('native_refusal')
     for category in categories:
      if counts[category]<6:witness.append(dict(category=category,**row));counts[category]+=1
   q=OUT/'gpmp'/tag/case.name/'dense_witnesses.csv';q.parent.mkdir(parents=True,exist_ok=True)
   with q.open('w') as f:
    writer=csv.DictWriter(f,fieldnames=['category']+fields);writer.writeheader();writer.writerows(witness)
for tag in ('g07_baseline01','g07_baseline02','g07_gap01','g07_final01'):
 for p in sorted((BASE/'generic_mechanisms_v249'/tag/'frame02').glob('*')):
  if p.is_file():copy(p,Path('g07')/tag/p.name)
for tag,sub in (('late_global_baseline01','results'),('late_pose_recheck01','')):
 for p in sorted((BASE/'generic_mechanisms_v249'/tag/sub).glob('*.csv')):copy(p,Path('late_global')/tag/p.name)
evaluation=BASE/'generic_mechanisms_v251/evaluation'
for name in ('matrix_summary.json','matrix_table.csv','offline_gate.json','selection.json','linked_libraries.txt'):
 copy(evaluation/name,Path('evaluation')/name)
for p in sorted((evaluation/'scored').glob('*/*/*')):
 if p.name in ('summary.json','metrics.txt','stdout.log'):copy(p,Path('evaluation/scored')/p.relative_to(evaluation/'scored'))
for name in ('historical01','historical02','support'):
 for p in (evaluation/name).glob('*'):
  if p.name in ('summary.json','metrics.txt','stdout.log'):copy(p,Path('evaluation')/name/p.name)
copy(BASE/'generic_mechanisms_v251/gap_contract/summary.json',Path('contracts/gap_summary.json'))
for p in BASE.glob('v251_*.log'):
 if p.is_file() and p.stat().st_size<2_000_000:copy(p,Path('logs')/p.name)
for version in ('v249','v250'):
 for p in BASE.glob(version+'_*.log'):
  if p.is_file() and p.stat().st_size<2_000_000:copy(p,Path('logs')/p.name)
(OUT/'return_receipt.json').write_text(json.dumps(dict(returned=receipt,retained_remote=retained,
 physics_steps=0,source_of_truth='Local VLA repository',claim='Offline components and recorded-prefix replay only'),indent=2)+'\n')
print(json.dumps(dict(returned_files=len(receipt),returned_bytes=sum(v['bytes'] for v in receipt.values()),retained_dense_files=len(retained))))
