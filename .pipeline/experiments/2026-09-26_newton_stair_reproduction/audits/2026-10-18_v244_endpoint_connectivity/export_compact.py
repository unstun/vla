"""Return compact complete ledgers and representative derived curves, no raw/cache."""
from pathlib import Path
import csv,hashlib,json,shutil,statistics
BASE=Path('/data/sun/vla_mppi_20261009');RAW=BASE/'endpoint_connectivity_v244';EVAL=RAW/'evaluation';OUT=RAW/'compact_return01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(exist_ok=False);paths=[]
 paths += [p for p in EVAL.iterdir() if p.is_file() and p.suffix in ('.json','.csv','.txt')]
 for p in (EVAL/'scored').rglob('*'):
  if p.is_file() and (p.name in ('summary.json','metrics.txt','stdout.log') or (p.parent.name=='rep01' and p.suffix in ('.csv','.txt'))):paths.append(p)
 paths += list(RAW.glob('*.log'))
 d=RAW/'diagnostic'
 for name in ('graph_summary.json','graph_meta.txt','search.log','analysis.log','passage_summary.json','passage_support_and_atlas.csv','passage_support_only.csv','minimum_bridge.csv','down_control.log','support_grid.log','support_grid02.log','down_control/endpoints.txt','down_control/search.log'):
  if (d/name).is_file():paths.append(d/name)
 copied={}
 for p in sorted(set(paths)):
  rel=p.relative_to(RAW);q=OUT/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);assert sha(p)==sha(q);copied[str(rel)]=dict(bytes=p.stat().st_size,sha256=sha(p))
 matrix=json.loads((EVAL/'protocol_matrix_summary.json').read_text());table=[]
 for c in matrix['by_case']:
  g=c['global_time_s'];local=[v for v in c['local_time_s'] if v is not None]
  table.append(dict(case_id=c['case_id'],calls=c['denominator'],native_passes=c['end_to_end_pass'],first_gpmp_passes=c['first_gpmp_static_pass'],graph_fallback_calls=c['graph_fallback_calls'],global_median_ms=statistics.median(g)*1000,global_max_ms=max(g)*1000,local_median_ms=statistics.median(local)*1000 if local else None,edge_extra_min_m=c['edge_margin_min'],original_pcd_voxel_solid_min_m=c['raw_solid_margin_min'],local_observed_point_min_m=c['observed_point_margin_min']))
 with (OUT/'evaluation/matrix_table_compact.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 final={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in OUT.rglob('*') if p.is_file()}
 size=sum(r['bytes'] for r in final.values());assert size<50*2**20,size
 receipt=dict(host='gpu5070ti',remote_raw_root=str(RAW),remote_export_root=str(OUT),files=final,total_bytes=size,native_version='v244',scored_adapter='v245',calls=60,native_protocol_passes=55,as_scored_extra_row_flag_passes=50,per_call_all_receipts=True,large_derived_curves_retained_remotely_for_reps02_05=True,bulk_excluded=['PCT/PCD/ENV inputs','LiDAR clouds','native binaries and archives','CMakeFiles/build/cache','full support-grid sweep'],regenerate='Frozen v245/run_matrix.py + audit/score_protocol.py; all native calls and hashes retained under remote_raw_root')
 (OUT/'RETURN_MANIFEST.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(files=len(final),bytes=size)))
if __name__=='__main__':main()
