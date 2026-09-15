"""Bounded caller for the pinned upstream open-loop inference API.

Uses original engine, frame preprocessing, history selection and RVQ decoder.
Capacity inputs are replay frames; this does not execute a simulator/controller.
"""
import argparse
import collections
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import traceback


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["bf16", "fp8_llm_only"], default="bf16")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    stop_sampler = threading.Event()
    import pynvml
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)

    def sample():
        with (out / "gpu_samples.jsonl").open("w", buffering=1) as f:
            while not stop_sampler.is_set():
                m = pynvml.nvmlDeviceGetMemoryInfo(handle)
                u = pynvml.nvmlDeviceGetUtilizationRates(handle)
                f.write(json.dumps(dict(unix=time.time(),used_bytes=m.used,
                                       free_bytes=m.free,total_bytes=m.total,
                                       utilization=u.gpu)) + "\n")
                stop_sampler.wait(0.1)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        import torch
        import numpy as np
        from PIL import Image
        from lightnav.inference.config import InferenceConfig
        from lightnav.inference.engine import build_engine
        from lightnav.inference.vllm_utils import get_vllm_model
        from lightnav.tracking import TrackingAgent, resolve_action_decoder_from_config
        from lightnav.traj_vocab import load_rvq_bundle

        fixtures = json.loads((root / "setup/fixture_manifest.json").read_text())
        for row in fixtures["files"]:
            assert hashlib.sha256((root / row["path"]).read_bytes()).hexdigest() == row["sha256"]
        frames = [np.asarray(Image.open(root / row["path"]).convert("RGB"))
                  for row in fixtures["files"]]
        instruction = "move forward, then go to the trashcan on the right"
        cfg = InferenceConfig(model_path=str(root / "checkpoints/LightNav-0"),
                              backend="vllm_local", max_new_tokens=8,
                              gpu_memory_utilization=0.85, max_num_seqs=1,
                              quantization=None if args.mode == "bf16" else args.mode)
        save(out / "request.json", dict(config=dataclasses.asdict(cfg), instruction=instruction,
             instruction_sha256=hashlib.sha256(instruction.encode()).hexdigest(),
             env={k:os.environ.get(k) for k in ["VLN_KV_CACHE_GIB","VLN_VLLM_ENFORCE_EAGER",
                  "VLLM_ATTENTION_BACKEND","VLLM_DISABLED_KERNELS","VLN_EVAL_TEMPERATURE"]},
             cases=[1,16,64], repeats=3, replay_clock="4 Hz synthetic observation timestamps",
             original_frames=fixtures["original_frames"], padded_frames=8))
        torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        engine, bundle = build_engine(cfg, task_type="vlnce", max_new_tokens=8)
        torch.cuda.synchronize()
        load_s = time.perf_counter() - t0
        model = get_vllm_model(engine.vllm_engine)
        counts = collections.Counter()
        placement = collections.Counter()
        methods = collections.Counter()
        for name, p in model.named_parameters():
            counts[("vision" if name.startswith("visual.") else "llm") + ":" + str(p.dtype)] += p.numel()
            placement[str(p.device)] += p.numel()
        for name, module in model.named_modules():
            method = getattr(module, "quant_method", None)
            if method is not None:
                methods[("vision" if name.startswith("visual.") else "llm") + ":" + type(method).__name__] += 1
        save(out / "model_state.json", dict(load_seconds=load_s, parameter_counts=dict(counts),
             devices=dict(placement), quant_methods=dict(methods),
             resolved={k:getattr(bundle,k) for k in ["video_size","video_fps","pool_enable",
                       "pool_spatial","pool_mode","pool_stage","num_history_frames",
                       "slowfast_tiers","action_method"]},
             allocated_bytes=torch.cuda.memory_allocated(), reserved_bytes=torch.cuda.memory_reserved(),
             load_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
             load_peak_reserved_bytes=torch.cuda.max_memory_reserved()))
        assert all(d.startswith("cuda") for d in placement), placement
        assert bundle.num_history_frames == 64 and list(bundle.video_size) == [256,448]
        if args.mode == "fp8_llm_only":
            assert any(k.startswith("llm:torch.float8") for k in counts), counts
            assert not any(k.startswith("vision:torch.float8") for k in counts), counts
            assert "vision:torch.bfloat16" in counts
        resolved = resolve_action_decoder_from_config(cfg.model_path, "vlnce")
        assert resolved["method"] == "rvq"
        rvq = load_rvq_bundle(Path(resolved["bundle_path"]),int(resolved["horizon"]),
                              num_frames=0,load_cluster_ids=False)
        agent = TrackingAgent(engine,num_history_frames=bundle.num_history_frames,rvq_bundle=rvq)
        results = []
        with (out / "predictions.jsonl").open("w", buffering=1) as f:
            for n in [1,16,64]:
                agent.reset(instruction=instruction)
                for frame in frames[:n]:
                    agent.observe(frame)
                raw_outputs = []
                for repeat in range(3):
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
                    t0 = time.perf_counter()
                    wp, raw, reported_ms = agent.predict_waypoints(instruction,task_type="vlnce_traj")
                    torch.cuda.synchronize()
                    elapsed_ms = 1000 * (time.perf_counter() - t0)
                    row = dict(observed_frames=n,repeat=repeat,raw_text=raw,
                               waypoints=np.asarray(wp).tolist(), upstream_ms=reported_ms,
                               synchronized_call_ms=elapsed_ms,
                               peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                               peak_reserved_bytes=torch.cuda.max_memory_reserved())
                    f.write(json.dumps(row) + "\n")
                    print(json.dumps(row),flush=True)
                    assert raw.strip() and np.asarray(wp).shape == (10,3) and np.isfinite(wp).all()
                    raw_outputs.append(raw)
                    results.append(row)
                assert len(set(raw_outputs)) == 1, "identical-input raw text differed across repeats"
        save(out / "result.json", dict(status="passed",mode=args.mode,predictions=len(results),
             finite_10x3_waypoints=True,identical_input_raw_text_equal=True,
             claim="Open-loop replay inference only; no navigation or simultaneous simulation claim."))
    except BaseException as exc:
        save(out / "failure.json",dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
        raise
    finally:
        stop_sampler.set()
        sampler.join(timeout=5)
        pynvml.nvmlShutdown()


if __name__ == "__main__":
    main()
