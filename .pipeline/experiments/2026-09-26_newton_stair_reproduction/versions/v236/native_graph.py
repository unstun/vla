"""Execute the frozen v232 graph/driver; change only the accepted host version tag."""
from pathlib import Path

FROZEN = Path(__file__).resolve().parent.parent / 'v232/native_graph.py'
source = FROZEN.read_text()
before = 'request.get("integration_version") != "v232"'
assert source.count(before) == 1
source = source.replace(before, 'request.get("integration_version") != "v236"')
namespace = {'__file__': str(FROZEN), '__name__': 'v236_frozen_v232_graph'}
exec(compile(source, str(FROZEN), 'exec'), namespace)

if __name__ == '__main__':
    namespace['main']()
