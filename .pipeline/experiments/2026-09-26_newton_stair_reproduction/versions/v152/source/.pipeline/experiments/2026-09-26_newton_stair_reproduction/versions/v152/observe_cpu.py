"""Read only cgroup scheduling evidence during a real navigation trial."""
from pathlib import Path
import argparse,json,time
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
with a.output.open('x') as f:
    for _ in range(9000):
        row={'linux_ns':time.monotonic_ns()}
        for name in ('cpu.stat','cpu.max','cpu.pressure','memory.current','memory.events'):
            path=Path('/sys/fs/cgroup')/name
            if path.exists():row[name]=path.read_text()
        f.write(json.dumps(row)+'\n');f.flush();time.sleep(.1)
