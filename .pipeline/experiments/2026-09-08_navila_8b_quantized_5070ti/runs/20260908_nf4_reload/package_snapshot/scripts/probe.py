"""Bounded upstream NaVILA NF4 inference on recorded RGB; no actuation."""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True)
parser.add_argument('--source', required=True)
parser.add_argument('--fixtures', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--export')
parser.add_argument('--limit', type=int, default=12)
args = parser.parse_args()
sys.path.insert(0, str(Path(args.source).resolve()))
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
import numpy as np
from PIL import Image
import torch
import bitsandbytes as bnb
import transformers
from llava.constants import IMAGE_TOKEN_INDEX
from llava.conversation import conv_templates, SeparatorStyle
from llava.mm_utils import process_images, tokenizer_image_token, KeywordsStoppingCriteria
from llava.model.builder import load_pretrained_model

output = Path(args.output).resolve()
output.mkdir(parents=True, exist_ok=False)
torch.manual_seed(36)
np.random.seed(36)
torch.cuda.reset_peak_memory_stats()
start = time.perf_counter()
tokenizer, model, image_processor, context_len = load_pretrained_model(
    str(Path(args.model).resolve()), 'navila-llama3-8b-8f', load_4bit=True,
    device_map={'': 0}, torch_dtype=torch.float16, attn_implementation='sdpa')
torch.cuda.synchronize()
load_seconds = time.perf_counter() - start
quantized = [(n, m) for n, m in model.named_modules() if isinstance(m, bnb.nn.Linear4bit)]
assert len(quantized) > 0, 'No actual four-bit layers loaded'
assert all(m.weight.device.type == 'cuda' for _, m in quantized)
assert all(m.weight.quant_state is not None for _, m in quantized)
assert all(m.weight.quant_state.quant_type == 'nf4' for _, m in quantized)
devices = sorted(set(str(p.device) for p in model.parameters()))
assert all(d.startswith('cuda') for d in devices), devices
metadata = {'quantization': 'bitsandbytes NF4 double quantization; FP16 compute',
 'paper_awq_reproduction': False, 'gpu': torch.cuda.get_device_name(),
 'torch': torch.__version__, 'cuda': torch.version.cuda,
 'transformers': transformers.__version__, 'bitsandbytes': bnb.__version__,
 'load_seconds': load_seconds, 'linear4bit_count': len(quantized),
 'parameter_devices': devices, 'model': str(Path(args.model).resolve()),
 'context_len_returned_by_upstream': context_len,
 'configured_num_video_frames': model.config.num_video_frames,
 'loaded_allocated_GiB': torch.cuda.memory_allocated()/2**30,
 'loaded_reserved_GiB': torch.cuda.memory_reserved()/2**30,
 'load_peak_allocated_GiB': torch.cuda.max_memory_allocated()/2**30,
 'cases': []}
(output/'metadata.json').write_text(json.dumps(metadata, indent=2))
print(json.dumps({k:v for k,v in metadata.items() if k!='cases'}), flush=True)

# Execute the exact standalone upstream sampling function without importing
# Habitat's training stack. Its source and hash are retained for audit.
trainer = Path(args.source)/'evaluation/vlnce_baselines/navila_trainer.py'
tree = ast.parse(trainer.read_text())
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='sample_and_pad_images')
sampling_source = ast.get_source_segment(trainer.read_text(), node)
(output/'upstream_sampling.py').write_text(sampling_source+'\n')
namespace = {'copy':copy, 'np':np, 'Image':Image}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(trainer), 'exec'), namespace)
sample_frames = namespace['sample_and_pad_images']
fixture_root = Path(args.fixtures)
request = json.loads((fixture_root/'requests.json').read_text())
for index, case in enumerate(request['cases'][:args.limit]):
    case_start = time.perf_counter()
    paths = [fixture_root/p for p in case['images']]
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    images = sample_frames([Image.open(p).convert('RGB') for p in paths],
                           num_frames=model.config.num_video_frames)
    interleaved_images = '<image>\n'*(len(images)-1)
    instruction = case['instruction']
    question = (
        'Imagine you are a robot programmed for navigation tasks. You have been given a video '
        f'of historical observations {interleaved_images}, and current observation <image>\n. Your assigned task is: "{instruction}" '
        'Analyze this series of images to decide your next action, which could be turning left or right by a specific '
        'degree, moving forward a certain distance, or stop if the task is completed.')
    conv = conv_templates['llama_3'].copy()
    conv.append_message(conv.roles[0], question)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt()
    image_tensor = process_images(images, image_processor, model.config).to('cuda', dtype=torch.float16)
    input_ids = tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX,
                                     return_tensors='pt').unsqueeze(0).cuda()
    stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
    stopping = KeywordsStoppingCriteria([stop_str], tokenizer, input_ids)
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    inference_start = time.perf_counter()
    with torch.inference_mode():
        ids = model.generate(input_ids, images=image_tensor, do_sample=False,
             temperature=0.0, max_new_tokens=32, use_cache=True,
             stopping_criteria=[stopping], pad_token_id=tokenizer.eos_token_id)
    torch.cuda.synchronize()
    elapsed = time.perf_counter()-inference_start
    text = tokenizer.batch_decode(ids, skip_special_tokens=True)[0].strip()
    if text.endswith(stop_str):
        text = text[:-len(stop_str)].strip()
    result = {**case, 'index':index, 'input_sha256':hashes,
              'frame_count':len(images), 'prompt':prompt,
              'image_tensor_shape':list(image_tensor.shape),
              'text_token_count':input_ids.shape[-1], 'output_ids':ids.cpu().tolist(),
              'raw_output':text, 'inference_seconds':elapsed,
              'case_wall_seconds':time.perf_counter()-case_start,
              'peak_allocated_GiB':torch.cuda.max_memory_allocated()/2**30,
              'peak_reserved_GiB':torch.cuda.max_memory_reserved()/2**30}
    assert text, 'Empty model response'
    metadata['cases'].append(result)
    (output/f'case_{index:02d}.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
    (output/'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    print(json.dumps({k:v for k,v in result.items() if k!='prompt'}, ensure_ascii=False), flush=True)

if args.export:
    target = Path(args.export).resolve()
    target.mkdir(parents=True, exist_ok=False)
    model.llm.save_pretrained(target/'llm', safe_serialization=True)
    tokenizer.save_pretrained(target/'llm')
    # Vision/projector are intentionally unquantized; preserve original bytes.
    for subdir in ['vision_tower','mm_projector']:
        shutil.copytree(Path(args.model)/subdir, target/subdir)
    shutil.copy2(Path(args.model)/'config.json', target/'config.json')
    records = []
    for path in sorted(target.rglob('*')):
        if path.is_file():
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(8*1024*1024), b''): h.update(block)
            records.append({'path':path.relative_to(target).as_posix(),
                            'size':path.stat().st_size,'sha256':h.hexdigest()})
    (output/'export_manifest.json').write_text(json.dumps({'files':records}, indent=2))
    print('NF4_EXPORT_COMPLETE', flush=True)
metadata['complete'] = True
(output/'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
print('PROBE_COMPLETE', flush=True)
