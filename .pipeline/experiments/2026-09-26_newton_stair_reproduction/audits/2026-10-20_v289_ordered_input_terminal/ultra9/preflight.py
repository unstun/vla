from pathlib import Path
p=Path('/home/ubuntu/sun/vla_v289_20261020/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v289/preflight.py')
exec(compile(p.read_text(),str(p),'exec'),dict(__file__=str(p),__name__='v289_same_install_preflight'))
