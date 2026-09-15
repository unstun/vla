"""Local-only, bounded audio decoding and pinned SenseVoice CPU inference."""
import hashlib
import json
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
import sherpa_onnx


class SpeechRecognizer:
    def __init__(self, root):
        self.lock = threading.Lock()
        self.status = "loading"
        self.error = None
        self.root = Path(root)
        self.recognizer = None

    def load(self):
        try:
            assets = json.loads((self.root / "manifests/asr_assets.json").read_text())
            for item in assets:
                path = self.root / "models" / item["path"]
                if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                    raise RuntimeError("ASR asset integrity check failed")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(self.root / "models/model.int8.onnx"),
                tokens=str(self.root / "models/tokens.txt"),
                num_threads=4, use_itn=True, language="auto", provider="cpu", debug=False)
            self.status = "ready"
        except Exception as error:
            self.error = str(error)
            self.status = "error"

    def transcribe(self, encoded):
        if self.status != "ready":
            raise ValueError("语音识别尚未就绪，请稍候或使用文字输入。")
        if not 100 <= len(encoded) <= 4 * 1024 * 1024:
            raise ValueError("录音为空或过大，请在 10 秒内说完指令。")
        if not self.lock.acquire(blocking=False):
            raise ValueError("上一段录音仍在识别，请稍候。")
        try:
            started = time.monotonic()
            result = subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
                 "-t", "11", "-ac", "1", "-ar", "16000", "-f", "f32le", "pipe:1"],
                input=encoded, capture_output=True, timeout=15, check=True)
            samples = np.frombuffer(result.stdout, dtype=np.float32)
            duration = len(samples) / 16000
            if not 0.15 <= duration <= 10.5:
                raise ValueError("请录制 0.2 到 10 秒的语音。")
            if not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 0.008:
                raise ValueError("没有听到清晰语音，请靠近麦克风后重试。")
            stream = self.recognizer.create_stream()
            stream.accept_waveform(16000, samples)
            self.recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            if not text:
                raise ValueError("没有识别到文字，请重试。")
            return {"text": text, "audio_seconds": duration,
                    "asr_seconds": time.monotonic() - started, "engine": "SenseVoice / CPU"}
        finally:
            self.lock.release()
