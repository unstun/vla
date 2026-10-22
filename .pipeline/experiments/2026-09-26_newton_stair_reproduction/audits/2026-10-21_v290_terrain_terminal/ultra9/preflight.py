from pathlib import Path
p=Path('/home/ubuntu/sun/vla_v290_20261021/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v290/preflight.py')
exec(compile(p.read_text(),str(p),'exec'),dict(__file__=str(p),__name__='v290_single_prefix_preflight'))
