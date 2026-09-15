"""Freeze a single-episode annotation for the zh_between_two_chairs request.

The instruction is stored with a trailing period sentinel so upstream's
``instruction_text[:-1]`` removes only the period, preserving the original
Chinese text byte-for-byte.

Goal and reference_path are set to the start position for bookkeeping only:
no coordinate ground truth exists for this qualitative instruction-following
task.  Setting goal == start hides the shortest-path/goal markers in the
top-down map without modifying the evaluator (output-only change).
"""
import gzip
import hashlib
import json
import re
from pathlib import Path

REQUEST_DIR = Path(__file__).resolve().parent
EXP = REQUEST_DIR.parents[2]
SPLIT = 'zh_between_two_chairs'

request = json.loads((REQUEST_DIR / 'request.json').read_text())

INSTRUCTION_RAW = request['instruction']
INSTRUCTION_WITH_SENTINEL = INSTRUCTION_RAW + '.'

START_POSITION = request['start_position']
START_ROTATION = request['start_rotation']
SCENE_ID = request['scene_id']

BOOKKEEPING_GOAL = [-0.9091625213623047, 0.20991861820220947, 12.72385311126709]
BOOKKEEPING_REFERENCE_PATH = [list(START_POSITION), BOOKKEEPING_GOAL]
BOOKKEEPING_GEODESIC = 1.1


def tokenize(text):
    return [t for t in re.split(r'([^\w-]+)', text.lower()) if t.strip()]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    vocab = ['<pad>', '<unk>', '<s>', '</s>']
    for t in tokenize(INSTRUCTION_WITH_SENTINEL):
        if t not in vocab:
            vocab.append(t)
    stoi = {w: i for i, w in enumerate(vocab)}

    episode = {
        'episode_id': 1,
        'trajectory_id': 1,
        'scene_id': SCENE_ID,
        'start_position': START_POSITION,
        'start_rotation': START_ROTATION,
        'goals': [{'position': BOOKKEEPING_GOAL, 'radius': 3.0}],
        'info': {'geodesic_distance': BOOKKEEPING_GEODESIC},
        'reference_path': BOOKKEEPING_REFERENCE_PATH,
        'instruction': {
            'instruction_text': INSTRUCTION_WITH_SENTINEL,
            'instruction_tokens': [stoi.get(t, 1) for t in tokenize(INSTRUCTION_WITH_SENTINEL)],
        },
    }

    payload = {'episodes': [episode], 'instruction_vocab': {'word_list': vocab}}
    out = (EXP / 'public_scenes' / 'data' / 'vln_ce' / 'raw_data' / 'public'
           / SPLIT / f'{SPLIT}.json.gz')
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(out, 'wb', mtime=0) as f:
        f.write(json.dumps(payload, sort_keys=True).encode('utf-8'))

    annotation_sha = sha256_file(out)

    consumed = INSTRUCTION_WITH_SENTINEL[:-1]
    assert consumed.encode('utf-8') == INSTRUCTION_RAW.encode('utf-8'), (
        f'Consumed instruction does not match request.instruction:\n'
        f'  consumed: {consumed!r}\n'
        f'  request:  {INSTRUCTION_RAW!r}'
    )

    raw_sha = hashlib.sha256(INSTRUCTION_RAW.encode('utf-8')).hexdigest()
    assert raw_sha == request['instruction_utf8_sha256'], (
        f'instruction SHA-256 mismatch: {raw_sha} != {request["instruction_utf8_sha256"]}'
    )

    provenance = {
        'request_id': request['request_id'],
        'split': SPLIT,
        'annotation_path': str(out.relative_to(EXP)),
        'annotation_sha256': annotation_sha,
        'annotation_bytes': out.stat().st_size,
        'instruction_raw': INSTRUCTION_RAW,
        'instruction_raw_utf8_sha256': raw_sha,
        'instruction_in_annotation': INSTRUCTION_WITH_SENTINEL,
        'sentinel': '.',
        'consumed_after_upstream_slice': consumed,
        'consumed_matches_raw': consumed == INSTRUCTION_RAW,
        'bookkeeping_goal': {
            'position': BOOKKEEPING_GOAL,
            'note': 'set to start_position; no coordinate ground truth for this instruction',
            'metrics_are_meaningful': False,
        },
        'scene_id': SCENE_ID,
        'start_position': START_POSITION,
        'start_rotation': START_ROTATION,
    }
    prov_path = REQUEST_DIR / 'provenance.json'
    prov_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + '\n')

    print(f'annotation: {out.relative_to(EXP)}')
    print(f'annotation sha256: {annotation_sha}')
    print(f'instruction raw: {INSTRUCTION_RAW}')
    print(f'instruction in annotation: {INSTRUCTION_WITH_SENTINEL}')
    print(f'consumed after [:-1]: {consumed}')
    print(f'byte-equal: {consumed == INSTRUCTION_RAW}')
    print('FREEZE_DONE')


if __name__ == '__main__':
    main()
