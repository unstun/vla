"""Same v237 physics/scanner adapter as v241; execution identity only."""
from pathlib import Path
import os
FROZEN=Path(__file__).resolve().parent.parent/'v241/newton_episode.py'
source=FROZEN.read_text().replace("integration='v241', navigation='v240'","integration='v252', navigation='v251'")
source=source.replace("'v241_recorder_adapter.json'","'v252_recorder_adapter.json'").replace("execution='v241'","execution='v252'").replace("navigation='v240'","navigation='v251'")
namespace=dict(__file__=str(FROZEN),__name__=__name__)
exec(compile(source,str(FROZEN),'exec'),namespace)
