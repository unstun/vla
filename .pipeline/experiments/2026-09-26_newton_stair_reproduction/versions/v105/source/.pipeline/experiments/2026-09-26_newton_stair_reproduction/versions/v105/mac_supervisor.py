"""Use the original bounded supervisor with an explicit temporary run root."""
from pathlib import Path
import importlib.util,os,sys
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]

def verify_prepared_mount(run):
    if not run.exists():return
    allowed={'artifacts','artifacts/external_episode'}
    for path in run.rglob('*'):
        if path.is_symlink() or not path.is_dir() or str(path.relative_to(run)) not in allowed:
            raise FileExistsError('Run already contains data: '+str(path))

def main():
    source=BASE.parent/'2026-09-26_newton_macos_policy/scripts/run_bounded.py'
    text=source.read_text();old='out.mkdir(parents=True, exist_ok=False)'
    assert text.count(old)==1
    index=sys.argv.index('--run-id');run_id=sys.argv[index+1]
    root=Path(os.environ['V105_TEMP_ROOT'])
    assert root.parent==Path('/private/tmp') and root.name.startswith('vla_newton_v105_')
    verify_prepared_mount(root/'runs'/run_id)
    spec=importlib.util.spec_from_file_location('v105_original_supervisor',source)
    module=importlib.util.module_from_spec(spec)
    # Only Docker's pre-created empty tmpfs-parent directories are accepted.
    # Original process group, deadline, child/environment and results stay exact.
    exec(compile(text.replace(old,'out.mkdir(parents=True, exist_ok=True)'),str(source),'exec'),module.__dict__)
    module.BASE=root;module.MAX_DEADLINE_S=1800;module.main()

if __name__=='__main__':main()
