"""Decode the complete video and check source-time causality and provenance."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
root=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
out=Path(sys.argv[1]);video=out/'stairs_collision_comparison.mp4'
frames=json.loads((out/'frames.json').read_text())
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_read_frames:format=duration,size','-of','json',str(video)]))
s=probe['streams'][0]
assert (s['width'],s['height'],s['r_frame_rate'],int(s['nb_read_frames']))==(1920,1080,'30/1',len(frames))
for a,b in zip(frames,frames[1:]):assert a['source_time_s']<=b['source_time_s']
for row in frames:
    assert row['recorded_state_time_s']<=row['source_time_s']+1e-8
    assert row['query_time_s']<=row['source_time_s']+1e-8
    assert row['cloud_stamp_ns']*1e-9<=row['query_time_s']+1e-8
decoded=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True)
assert decoded.returncode==0 and not decoded.stderr,decoded.stderr
record={'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'video_bytes':video.stat().st_size,'ffprobe':probe,'complete_decode_exit':decoded.returncode,'complete_decode_errors':decoded.stderr,'source_time_monotonic':True,'causal_recorded_state_and_query':True,'checked_frames':len(frames)}
(out/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
