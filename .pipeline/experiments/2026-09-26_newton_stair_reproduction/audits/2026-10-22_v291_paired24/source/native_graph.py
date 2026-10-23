"""Original v290 graph with only the selected integration identity accepted."""
from common import *
FROZEN=VERSIONS/'v290/native_graph.py'
source=FROZEN.read_text();old='request.get("integration_version") != "v290"';assert source.count(old)==1
source=source.replace(old,'request.get("integration_version") != '+repr(VARIANT))
if __name__=='__main__':
 scope=dict(__file__=str(FROZEN),__name__='__main__');exec(compile(source,str(FROZEN),'exec'),scope)
