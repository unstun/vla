"""Bounded raw-frame to MP4 writer; no full PNG sequence unless requested."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from artifacts import atomic_json, digest, video_check


class VideoStream:
    def __init__(self, out, fps, expected_frames, keep_frames=False, max_bytes=512*1024*1024):
        self.out=Path(out);self.fps=fps;self.expected=expected_frames
        self.keep_frames=keep_frames;self.max_bytes=max_bytes;self.count=0
        self.partial=self.out/'newton_stair_recorded.partial.mp4'
        self.final=self.out/'newton_stair_recorded.mp4'
        if self.partial.exists() or self.final.exists():raise FileExistsError('Existing video output')
        self.process=None;self.log=None;self.size=None
        self.samples={0,expected_frames//2,expected_frames-1}
        (self.out/'frame_samples').mkdir()
        if keep_frames:(self.out/'frames').mkdir()
        self.manifest=(self.out/'frames.jsonl').open('x')

    def add(self, frame, metadata):
        if self.count>=self.expected:raise ValueError('Too many frames')
        image=frame.convert('RGB')
        if self.process is None:
            if shutil.disk_usage(self.out).free < 512*1024*1024:raise RuntimeError('Insufficient render disk reserve')
            self.size=image.size
            ffmpeg=shutil.which('ffmpeg')
            if not ffmpeg:raise RuntimeError('FFmpeg is required')
            self.log=(self.out/'ffmpeg.log').open('xb')
            command=[ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pixel_format','rgb24',
                '-video_size',f'{image.width}x{image.height}','-framerate',str(self.fps),'-i','pipe:0',
                '-vf','scale=1280:720','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(self.partial)]
            atomic_json(self.out/'video_encoding.json',dict(command=command,transport='bounded OS pipe, RGB24',max_video_bytes=self.max_bytes,keep_frames=self.keep_frames))
            self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=self.log,stdout=subprocess.DEVNULL)
        if image.size!=self.size:raise ValueError('Frame dimensions changed')
        if self.partial.exists() and self.partial.stat().st_size>self.max_bytes:raise RuntimeError('Video byte limit reached')
        if shutil.disk_usage(self.out).free < 256*1024*1024:raise RuntimeError('Render disk reserve reached')
        raw=image.tobytes()
        row=dict(metadata,frame_index=self.count,rgb24_sha256=hashlib.sha256(raw).hexdigest(),rgb24_shape=[image.height,image.width,3])
        if self.keep_frames or self.count in self.samples:
            directory='frames' if self.keep_frames else 'frame_samples'
            path=self.out/directory/f'{self.count:06d}.png';image.save(path)
            row.update(file=str(path.relative_to(self.out)),sha256=digest(path))
        self.process.stdin.write(raw)
        self.manifest.write(json.dumps(row)+'\n');self.manifest.flush()
        self.count+=1
        return row

    def close(self, success=True):
        error=None
        if self.process:
            try:
                self.process.stdin.close()
                if self.process.wait(timeout=120):error='Encoder failed; see ffmpeg.log'
            except BaseException as exc:
                self.process.kill();self.process.wait();error=repr(exc)
        self.manifest.close()
        if self.log:self.log.close()
        if not success:
            atomic_json(self.out/'video_interrupted.json',dict(frames_written=self.count,expected_frames=self.expected,partial_video=str(self.partial),encoder_error=error))
            return None
        if error or self.count!=self.expected:raise RuntimeError(error or 'Incomplete video')
        proof=video_check(self.partial,self.expected,self.fps)
        self.partial.replace(self.final)
        atomic_json(self.out/'video_verification.json',dict(status='passed',sha256=digest(self.final),stream=proof,frames=self.count,full_decode_passed=True))
        return self.final
