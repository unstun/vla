from pathlib import Path
import json,os,subprocess,hashlib
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generic_mechanisms_v251/gap_contract';OUT.mkdir(parents=True,exist_ok=True)
versions='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
shell=f'c++ -std=c++17 -O2 -I{versions}/v251/src/plan_env/include -I{versions} {versions}/v251/contract/gap_parity.cpp -o /output/gap_parity && /output/gap_parity /task/generic_mechanisms_v250/native/fixtures/building/support_gap.txt 10479033888964413526 && c++ -std=c++17 -O2 -I{versions}/v251/src/plan_env/include {versions}/v250/source/contract/gap_geometry_test.cpp -o /output/gap_geometry && /output/gap_geometry'
result=subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=2g','-v',str(BASE)+':/task:ro','-v',str(OUT)+':/output:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(OUT/'stdout.log').write_text(result.stdout);print(result.stdout,flush=True)
if result.returncode:raise SystemExit(result.returncode)
receipt=json.loads(result.stdout.splitlines()[0]);assert receipt['hard_domain_mismatches']==0
receipt.update(passed=True,exhaustive_synthetic_queries=1442401,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
