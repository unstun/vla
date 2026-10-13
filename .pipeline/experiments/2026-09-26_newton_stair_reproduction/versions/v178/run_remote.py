"""Render only after all physical repetitions close; preserve every output."""
from pathlib import Path
import json,os,subprocess,sys

H=Path(__file__).resolve().parent;B=H.parents[1];T=Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0,str(B/'versions/v177'))
from resource_gate import admit

def main():
    for attempt in range(1,6):
        tag=f'v177_full_candidate_attempt{attempt:02d}'
        record=T/'results/v177_full_repeats'/tag/'outcome.json'
        assert record.exists() and json.loads(record.read_text())['full_qualification'],tag
    admission=admit()
    subprocess.run([sys.executable,str(H/'prepare_remote.py')],check=True,timeout=120)
    root=T/'video_v178';out=root/'runs/full01';out.mkdir(exist_ok=False)
    env=dict(os.environ,NEWTON_RUN_DIR=str(out),V178_RENDER_ROOT=str(root),
        V178_DISPLAY_CONTRACT=str(root/'display_contract.json'),WARP_CACHE_PATH=str(root/'cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYGLET_HEADLESS='1',PYOPENGL_PLATFORM='egl',
        PYTHONPATH=str(T/'host_python')+':'+str(H)+':'+str(B/'runtime_sources/bridge'))
    command=[sys.executable,str(H/'render_capture.py')]
    (root/'render_request.json').write_text(json.dumps({'command':command,'resource_admission':admission,
        'env':{k:env[k] for k in ['NEWTON_RUN_DIR','V178_RENDER_ROOT','V178_DISPLAY_CONTRACT',
        'WARP_CACHE_PATH','PYTHONPATH','PYGLET_HEADLESS','PYOPENGL_PLATFORM']},'physics_steps_requested':0},indent=2)+'\n')
    with (root/'render.log').open('w') as log:
        subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
    subprocess.run([sys.executable,str(H/'verify_video.py')],env=env,check=True,timeout=180)

if __name__=='__main__':main()
