"""Explicit one-episode entry; preserves MIP's frozen split and scoring driver."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--episode", type=int, choices=range(100), default=0)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "source/AgentCanvas/coding-agent"))
    import cells
    from driver import run_cell
    from deepseek_adapter import DeepSeekAdapter
    cells.OUTPUT_ROOTS["deepseek"] = root / "runs"
    spec = cells.CellSpec(name="nonstd_deepseek_flash_bare", harness="deepseek",
                          model_key="deepseek-flash", model_id="deepseek-flash",
                          condition="bare", bare=True)
    name = spec.name + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    asyncio.run(run_cell(DeepSeekAdapter(root), spec,
                                 ["http://127.0.0.1:19200"],
                                 episodes_spec=str(args.episode), run_name=name))
    result = json.loads((spec.output_root / name / "summary.json").read_text())
    print(json.dumps(result, indent=2))
    if len(result.get("episodes", [])) != 1 or any(e.get("error") for e in result["episodes"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
