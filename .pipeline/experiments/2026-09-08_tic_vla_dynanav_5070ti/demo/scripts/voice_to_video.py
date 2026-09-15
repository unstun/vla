"""Speak on this Mac, run one remote hospital episode, receive a local MP4."""
import argparse
import datetime
import hashlib
import json
import shlex
import subprocess
import time
import uuid
import wave
from pathlib import Path

from protocol import parse_command, read_instruction_request
from speech import SpeechRecognizer

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/demo"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "gpu5070ti"]


def record():
    import io
    import sounddevice as sd
    device = sd.query_devices(kind="input")
    rate = int(device["default_samplerate"])
    print(f"使用麦克风：{device['name']}")
    input("按回车开始录音（6 秒），例如：走到自动售货机前。")
    for count in (3, 2, 1):
        print(count, flush=True)
        time.sleep(1)
    print("现在请说话…", flush=True)
    samples = sd.rec(6 * rate, samplerate=rate, channels=1, dtype="int16", blocking=True)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(samples.tobytes())
    print("录音结束，正在本机识别。", flush=True)
    return buffer.getvalue()


def retry(command, timeout=45, attempts=4):
    for attempt in range(attempts):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            if attempt + 1 == attempts:
                raise
            print("传输超时，保留已有数据后重试…", flush=True)
            time.sleep(3)
            continue
        if result.returncode == 0:
            return result.stdout
        if attempt+1 == attempts:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        print("连接中断，稍后重试…", flush=True)
        time.sleep(3)


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--audio", type=Path, help="Use an existing recording instead of the microphone")
    source.add_argument("--instruction", help="Send this navigation text directly, without translation")
    parser.add_argument("--synthetic", action="store_true", help="Label test audio as synthesized")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--view", choices=("third_person", "top_down"), default="third_person")
    parser.add_argument("--inference-seed", type=int, help="Optional inference RNG seed for paired trials")
    args = parser.parse_args()
    audio = None
    if args.instruction is not None:
        transcription = {"text": args.instruction, "engine": "direct_text"}
    else:
        audio = args.audio.read_bytes() if args.audio else record()
        recognizer = SpeechRecognizer(ROOT)
        recognizer.load()
        transcription = recognizer.transcribe(audio)
    command = parse_command(transcription["text"])
    if command["action"] != "goal":
        raise ValueError("离线演示请说：走到自动售货机前。停下和继续需要正在运行的交互任务。")
    identity = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6]
    request_dir = ROOT / "requests" / identity
    request_dir.mkdir(parents=True)
    request = {"run_id": identity, "transcription": transcription, "command": command,
               "synthetic_audio": args.synthetic, "input_audio_sha256": hashlib.sha256(audio).hexdigest() if audio else None,
               "audio_source": "none" if audio is None else (str(args.audio.resolve()) if args.audio else "local_microphone"),
               "audio_uploaded": False}
    request["camera_view"] = args.view
    request["instruction_mode"] = "verbatim"
    request["translation_applied"] = False
    request["inference_seed"] = args.inference_seed
    (request_dir / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n")
    runtime_request = request_dir / "runtime_request.json"
    runtime_request.write_text(json.dumps({"instruction": command["instruction"], "instruction_mode": "verbatim",
                                          "inference_seed": args.inference_seed}, ensure_ascii=False, indent=2) + "\n")
    read_instruction_request(runtime_request)
    print(f"直接输入模型：{command['instruction']}\n开始仿真；不传实时画面，结束后下载视频。", flush=True)
    retry(SSH + ["mkdir -p " + shlex.quote(REMOTE + "/requests")])
    retry(["rsync", "-az", "-e", "ssh -o BatchMode=yes -o ConnectTimeout=12", str(runtime_request),
           f"gpu5070ti:{REMOTE}/requests/{identity}.json"])
    print(retry(SSH + ["bash " + shlex.quote(REMOTE + "/scripts/launch_batch.sh") + " " + shlex.quote(identity) + " " + shlex.quote(args.view)]), flush=True)
    started = time.monotonic()
    while time.monotonic()-started < 840:
        time.sleep(10)
        try:
            state = json.loads(retry(SSH + ["cat " + shlex.quote(REMOTE + "/runs/" + identity + ".delivery.json")], attempts=2))
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError):
            print("仿真在服务器独立运行，正在恢复状态连接…", flush=True)
            continue
        if not state["done"]:
            print(f"仿真处理中（已等待 {int(time.monotonic()-started)} 秒）…", flush=True)
            continue
        if not state["success"]:
            raise RuntimeError("仿真未完成：" + state.get("error", "unknown"))
        break
    else:
        raise RuntimeError(f"等待超时；远端有独立运行上限。运行编号：{identity}")
    target = ROOT / "runs" / identity
    target.mkdir(parents=True, exist_ok=True)
    print("仿真结束，下载视频与日志…", flush=True)
    retry(["rsync", "-az", "--partial", "--exclude", "/frames/", "-e", "ssh -o BatchMode=yes -o ConnectTimeout=12",
           f"gpu5070ti:{REMOTE}/runs/{identity}/", str(target) + "/"], timeout=120)
    checks = []
    for item in json.loads((target / "artifact_sha256.json").read_text()):
        if item["path"].startswith("frames/"):
            continue
        path = target / item["path"]
        match = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        checks.append({"path": item["path"], "passed": match})
    if not checks or not all(check["passed"] for check in checks):
        raise RuntimeError("下载文件校验失败，请保留运行编号以便恢复。")
    (target / "local_integrity.json").write_text(json.dumps(checks, indent=2) + "\n")
    video = target / "navigation_with_trajectory.mp4"
    analysis = json.loads((target / "analysis.json").read_text())
    print("导航结果：" + ("达到评测目标范围。" if analysis["episode"]["success"] else "未达到评测目标，录像已保留。"), flush=True)
    request.update(video=str(video), completed=True)
    (request_dir / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n")
    print(f"视频已保存：\n{video}", flush=True)
    if not args.no_open:
        subprocess.run(["open", str(video)], check=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("未完成：", error, flush=True)
        raise SystemExit(1)
