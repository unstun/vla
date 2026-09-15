"""Test dependency serialization compatibility on a tiny random Llama only."""
import json
from pathlib import Path
import sys
import tempfile
import torch
from transformers import LlamaConfig, LlamaForCausalLM, BitsAndBytesConfig

root=Path(sys.argv[1])
with tempfile.TemporaryDirectory(prefix='tiny_quant_',dir=root) as temporary:
    path=Path(temporary)
    torch.manual_seed(36)
    config=LlamaConfig(hidden_size=128,intermediate_size=256,num_hidden_layers=1,
                       num_attention_heads=4,num_key_value_heads=4,vocab_size=128)
    model=LlamaForCausalLM(config).half()
    model.save_pretrained(path/'original')
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,bnb_4bit_quant_type='nf4')
    model=LlamaForCausalLM.from_pretrained(path/'original',quantization_config=quant,
                torch_dtype=torch.float16,device_map={'':0},attn_implementation='sdpa')
    inputs=torch.tensor([[1,2,3]],device='cuda')
    with torch.inference_mode():before=model(inputs).logits.cpu()
    model.save_pretrained(path/'quantized')
    del model
    torch.cuda.empty_cache()
    model=LlamaForCausalLM.from_pretrained(path/'quantized',quantization_config=quant,
                  torch_dtype=torch.float16,device_map={'':0},attn_implementation='sdpa')
    with torch.inference_mode():after=model(inputs).logits.cpu()
    assert torch.isfinite(after).all()
    error=(before-after).abs().max().item()
    assert error==0,error
    print(json.dumps({'scope':'tiny random Llama dependency check, not NaVILA',
                      'nf4_save_reload_max_logit_error':error,'passed':True}))
