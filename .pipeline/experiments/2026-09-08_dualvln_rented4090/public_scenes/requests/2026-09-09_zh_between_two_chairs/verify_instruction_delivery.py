"""Verify verbatim instruction delivery through the actual prompt-building path.

The evaluator (habitat_vln_evaluator.py:194,438-439) builds the S2 prompt as:
    prompt = "...Your task is to <instruction>. Where should you go..."
    sources[0]["value"].replace('<instruction>.', instruction_text[:-1])

This script loads the annotation, applies the same slice and substitution,
and asserts byte-for-byte UTF-8 equality of the consumed instruction with
the original request.
"""
import gzip
import hashlib
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXP = SCRIPT_DIR.parents[2]

request = json.loads((SCRIPT_DIR / 'request.json').read_text())
EXPECTED_INSTRUCTION = request['instruction']
EXPECTED_SHA = request['instruction_utf8_sha256']

ANN_PATH = (EXP / 'public_scenes' / 'data' / 'vln_ce' / 'raw_data' / 'public'
            / 'zh_between_two_chairs' / 'zh_between_two_chairs.json.gz')

UPSTREAM_PROMPT_TEMPLATE = (
    "You are an autonomous navigation assistant. Your task is to "
    "<instruction>. Where should you go next to stay on track? "
    "Please output the next waypoint's coordinates in the image. "
    "Please output STOP when you have successfully completed the task."
)


def main():
    data = json.loads(gzip.open(ANN_PATH, 'rt').read())
    assert len(data['episodes']) == 1, f'expected 1 episode, got {len(data["episodes"])}'
    ep = data['episodes'][0]
    annotation_text = ep['instruction']['instruction_text']

    sliced = annotation_text[:-1]

    prompt_after = UPSTREAM_PROMPT_TEMPLATE.replace('<instruction>.', sliced)

    consumed_bytes = sliced.encode('utf-8')
    expected_bytes = EXPECTED_INSTRUCTION.encode('utf-8')
    consumed_sha = hashlib.sha256(consumed_bytes).hexdigest()

    results = {
        'annotation_instruction_text': annotation_text,
        'upstream_slice': 'instruction_text[:-1]',
        'consumed_instruction': sliced,
        'expected_instruction': EXPECTED_INSTRUCTION,
        'byte_equal': consumed_bytes == expected_bytes,
        'consumed_utf8_sha256': consumed_sha,
        'expected_utf8_sha256': EXPECTED_SHA,
        'sha_match': consumed_sha == EXPECTED_SHA,
        'template_placeholder_found': '<instruction>.' in UPSTREAM_PROMPT_TEMPLATE,
        'template_placeholder_replaced': '<instruction>.' not in prompt_after,
        'consumed_present_in_prompt': sliced in prompt_after,
        'prompt_after_substitution': prompt_after,
    }

    out = SCRIPT_DIR / 'instruction_verification.json'
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')

    for k, v in results.items():
        if k == 'prompt_after_substitution':
            print(f'  {k}: {v[:120]}...')
        else:
            print(f'  {k}: {v}')

    assert results['byte_equal'], 'FAIL: consumed instruction differs from request'
    assert results['sha_match'], 'FAIL: SHA-256 mismatch'
    assert results['template_placeholder_replaced'], 'FAIL: template placeholder not replaced'
    assert results['consumed_present_in_prompt'], 'FAIL: instruction not found in prompt'

    print('INSTRUCTION_VERIFICATION_PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
