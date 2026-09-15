"""Verify the matched pair, plot measurements and align raw video by sim time."""
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import yaml

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'comparison'


def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def main():
    plan=json.loads((ROOT/'pair_plan.json').read_text())
    records={}
    for case in plan['cases']:
        run=ROOT/'runs'/case['run_id']
        subprocess.run([sys.executable,str(ROOT/'analyze_distance.py'),case['run_id']],
                       check=True,stdout=subprocess.DEVNULL)
        summary=json.loads((run/'distance_analysis.json').read_text())
        assert summary['runtime_complete']
        meta=json.loads((run/'meta.json').read_text())
        assert meta['instruction']==case['instruction'] and meta['inference_seed']==36
        assert not meta['goal_termination_enabled'] and not meta['automatic_backup_enabled']
        config=yaml.safe_load((run/'hospital_demo.yaml').read_text())
        assert config['episode_hospital_demo'].pop('instruction')==case['instruction']
        states=[json.loads(s) for s in (run/'telemetry.jsonl').read_text().splitlines()]
        states=[s for s in states if s.get('distance_probe') is not None]
        assert all(s['instruction']==case['instruction'] for s in states)
        assert all(s['world_to_clip']==states[0]['world_to_clip'] for s in states)
        records[case['language']]={'run':run,'summary':summary,'meta':meta,'config':config,'states':states}
    zh,en=records['zh'],records['en']
    assert zh['config']==en['config']
    assert zh['meta']['source_manifest_sha256']==en['meta']['source_manifest_sha256']
    assert zh['meta']['source_manifest_sha256']==hashlib.sha256((ROOT/'manifests/source.json').read_bytes()).hexdigest()
    assert zh['states'][0]['world_to_clip']==en['states'][0]['world_to_clip']
    assert [s['frame'] for s in zh['states']]==[s['frame'] for s in en['states']]
    times={lang:np.array([s['distance_probe']['elapsed_timeline_seconds'] for s in rec['states']])
           for lang,rec in records.items()}
    assert np.allclose(times['zh'],times['en'],rtol=0,atol=1e-7)
    assert np.allclose(np.diff(times['zh']),.05,rtol=0,atol=1e-7)
    result={'same_non_language_config':True,'same_source_manifest':True,'same_output_camera':True,
            'source_manifest_sha256':zh['meta']['source_manifest_sha256'],
            'aligned_frames':len(times['zh']),'aligned_timeline_span_s':float(times['zh'][-1]),
            'cases':{lang:rec['summary'] for lang,rec in records.items()},
            'time_basis':'20 FPS from the recorded 0.05 s simulator-timeline intervals; not wall-time inference throughput',
            'limit':'one matched pair in one scene; equal seeds do not guarantee identical RGB or asynchronous schedules'}
    from PIL import Image
    fronts={lang:np.asarray(Image.open(OUT/f'front_{lang}.jpg').convert('RGB'),dtype=np.int16) for lang in records}
    assert fronts['zh'].shape==fronts['en'].shape
    result['initial_rgb']={'mean_absolute_difference_255':float(np.abs(fronts['zh']-fronts['en']).mean()),
                           'byte_identical':(OUT/'front_zh.jpg').read_bytes()==(OUT/'front_en.jpg').read_bytes(),
                           'sha256':{lang:hashlib.sha256((OUT/f'front_{lang}.jpg').read_bytes()).hexdigest() for lang in records}}
    save(OUT/'comparison.json',result)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'zh':'#d1495b','en':'#00798c'}
    labels={'zh':'Chinese','en':'English'}
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    for lang,rec in records.items():
        m=[s['distance_probe'] for s in rec['states']]
        t=times[lang]
        axes[0,0].plot(t,[x['forward_m'] for x in m],color=colors[lang],label=labels[lang])
        axes[0,1].plot(t,[x['sampled_path_length_m'] for x in m],color=colors[lang],label=labels[lang])
        axes[1,0].plot(t,[x['actual_planar_speed_m_s'] for x in m],color=colors[lang],label=labels[lang])
        axes[1,1].plot([-x['lateral_m'] for x in m],[x['forward_m'] for x in m],color=colors[lang],label=labels[lang])
        axes[1,1].scatter(-m[-1]['lateral_m'],m[-1]['forward_m'],color=colors[lang],marker='x')
    for ax in [axes[0,0],axes[0,1]]:
        ax.axhline(3,color='gray',ls='--',lw=1)
    axes[1,0].axhline(.05,color='gray',ls=':',lw=1)
    axes[0,0].set(ylabel='Forward displacement (m)',xlabel='Simulator time after instruction (s)')
    axes[0,1].set(ylabel='Cumulative path (m)',xlabel='Simulator time after instruction (s)')
    axes[1,0].set(ylabel='Measured planar speed (m/s)',xlabel='Simulator time after instruction (s)')
    axes[1,1].scatter(0,0,c='black',marker='^',label='Start')
    axes[1,1].scatter(0,3,c='#3e8914',marker='*',s=110,label='3 m reference')
    axes[1,1].set(xlabel='Lateral offset: left < 0 < right (m)',ylabel='Forward displacement (m)')
    axes[1,1].set_aspect('equal',adjustable='datalim')
    for ax in axes.flat:
        ax.grid(alpha=.2);ax.legend(fontsize=9)
    fig.suptitle('Same model and scene: Chinese vs English | Go straight 3 m, then stop')
    fig.tight_layout()
    fig.savefig(OUT/'metric_language_comparison.png',dpi=170)
    fig.savefig(OUT/'metric_language_comparison.pdf')
    plt.close(fig)
    # A generated text legend; raw simulator frames remain unchanged.
    header=plt.figure(figsize=(12.8,.36),dpi=200,facecolor='#20353d')
    header.text(.25,.5,'CHINESE | aligned simulator time',ha='center',va='center',color='white',fontsize=14)
    header.text(.75,.5,'ENGLISH | aligned simulator time',ha='center',va='center',color='white',fontsize=14)
    header.savefig(OUT/'comparison_header.png',dpi=200,facecolor=header.get_facecolor(),bbox_inches=None,pad_inches=0)
    plt.close(header)

    # Extract exact archived output bytes; do not re-render or fabricate motion.
    frames=OUT/'render_frames'
    frames.mkdir(exist_ok=False)
    try:
        for lang,rec in records.items():
            folder=frames/lang;folder.mkdir()
            with tarfile.open(rec['run']/'raw_overlay_frames.tar.gz') as archive:
                for i,s in enumerate(rec['states']):
                    stream=archive.extractfile(f"frames/{s['sequence']:06d}.jpg")
                    if stream is None:raise RuntimeError('Missing recorded frame')
                    (folder/f'{i:06d}.jpg').write_bytes(stream.read())
        filters='[0:v][1:v]hstack=inputs=2[pair];[2:v][pair]vstack=inputs=2[out]'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                        '-framerate','20','-i',str(frames/'zh/%06d.jpg'),
                        '-framerate','20','-i',str(frames/'en/%06d.jpg'),
                        '-loop','1','-framerate','20','-i',str(OUT/'comparison_header.png'),
                        '-filter_complex',filters,'-map','[out]','-frames:v',str(len(times['zh'])),
                        '-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',
                        str(OUT/'chinese_english_3m_comparison.mp4')],check=True,timeout=120)
    finally:
        shutil.rmtree(frames)
    print(json.dumps({'cases':{k:{'forward':v['summary']['final_before_timeout']['forward_m'],
                                 'path':v['summary']['final_before_timeout']['sampled_path_length_m'],
                                 'stop':v['summary']['stopped_near_3m_for_2s']} for k,v in records.items()},
                      'initial_rgb':result['initial_rgb']},ensure_ascii=False))


if __name__=='__main__':
    main()
