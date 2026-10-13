"""Display-only close camera for recorded v59; preserve frozen source and timing."""
from pathlib import Path
import hashlib,json,os,sys
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
assert str(ROOT)=='/home/sun/vla_exec/vla','Render on execution host only'
parent=BASE/'versions/v51';manifest=json.loads((parent/'manifest.json').read_text())
for name in ('render_heading_v51.py','render_episode_v51.py','video_stream.py','display_measurements.py','artifacts.py'):
    p=parent/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['source_files'][str(p.relative_to(ROOT))]
os.environ.setdefault('WARP_CACHE_PATH',str(BASE/'runtime/render_warp_cache'))
os.environ.setdefault('PYGLET_HEADLESS','true')
sys.path.insert(0,str(parent));sys.path.insert(0,str(BASE/'scripts'))
source=parent/'render_heading_v51.py';text=source.read_text();old='Path("/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction")';new='Path('+repr(str(BASE))+')';assert text.count(old)==1
adapted=text.replace(old,new)
old_camera='TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 1.4, 1.0, 0.6, 0.1, 0.5'
new_camera='TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 0.45, 0.60, 0.25, 0.05, 0.5'
assert adapted.count(old_camera)==1
adapted=adapted.replace(old_camera,new_camera)
out=Path(os.environ['NEWTON_RUN_DIR']);(out/'executed_render_heading_host.py').write_text(adapted)
(out/'host_path_port.json').write_text(json.dumps({'frozen_renderer':'v51','original_heading_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'adapted_heading_sha256':hashlib.sha256(adapted.encode()).hexdigest(),'change':'Only the experiment path and close-camera offsets change; original recorded states, causal wall timeline, frame rate, encoding and controls are unchanged','physics_execution':False},indent=2)+'\n')
exec(compile(adapted,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
video=out/'video.mp4'
if not video.exists():
    videos=list(out.glob('*.mp4'));assert len(videos)==1;video=videos[0]
assert video.stat().st_size<=128*1024**2,'Review video exceeds approved local-return target; leave it remote'
