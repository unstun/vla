"""Use original managed retention while keeping bulk outside the repository."""
from pathlib import Path
import os,sys
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
sys.path.insert(0,str(BASE/'versions/v51'))
import managed_run
from mac_supervisor import verify_prepared_mount
# Apply the same predicate at both existing run-directory checks. Native
# ownership, process deadline, exit propagation and closed retention are exact.
source=Path(managed_run.__file__)
text=source.read_text();old='if run.exists():raise FileExistsError(run)'
assert text.count(old)==1
namespace=dict(managed_run.__dict__)
namespace['verify_prepared_mount']=verify_prepared_mount
exec(compile(text.replace(old,'verify_prepared_mount(run)'),str(source),'exec'),namespace)
managed_run.main=namespace['main']
managed_run.a.BASE=Path(os.environ['V75_TEMP_ROOT'])
managed_run.a.AUDIT=managed_run.a.BASE/'artifact_audit'
raise SystemExit(managed_run.main())
