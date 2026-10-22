"""Unchanged installed-package/ABI/link gate inherited from v241."""
from pathlib import Path
FROZEN=Path(__file__).resolve().parent.parent/'v241/preflight.py'
namespace=dict(__file__=str(FROZEN),__name__=__name__)
exec(compile(FROZEN.read_text(),str(FROZEN),'exec'),namespace)
