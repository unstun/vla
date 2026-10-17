"""Run the frozen v206 graph with only its integration identity rebound."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / 'v206/native_graph.py'


def main():
    text = SOURCE.read_text()
    before = 'request.get("integration_version") != "v206"'
    assert text.count(before) == 1
    text = text.replace(before, 'request.get("integration_version") != "v217"')
    text = text.replace('v206 graph requires the v206 integration identity',
                        'v217 graph binding requires the v217 integration identity')
    exec(compile(text, str(SOURCE), 'exec'), {'__file__': str(SOURCE), '__name__': '__main__'})


if __name__ == '__main__':
    main()
