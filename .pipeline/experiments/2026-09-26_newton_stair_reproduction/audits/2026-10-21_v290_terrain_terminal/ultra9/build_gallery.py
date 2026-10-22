"""Bind the existing offline video player to verified v290 recordings."""
from pathlib import Path
import base64,io,json,re
from PIL import Image
H=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
def main():
    summary=load(H/'physical_summary.json')
    media=load(H/'evidence/local_media_verification01.json')
    startup=load(H/'startup_return/summary.json')
    starts={r['case_id']:r for r in startup['cases']}
    videos={r['case_id']:r for r in media['cases']}
    causes=load(H/'case_diagnoses.json')
    template=H.parents[1]/'2026-10-20_v289_ordered_input_terminal/ultra9/delivered/index.html'
    text=template.read_text().replace('v289','v290')
    rows=[]
    for r in summary['cases']:
        cid=r['case_id'];v=videos[cid];s=starts[cid]
        frame=Path(v['samples'][-1]['file'])
        image=Image.open(frame).convert('RGB');image.thumbnail((352,198))
        buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=78)
        solid=min(r['all_recorded_source_solid_min_m'],s['minimum_source_solid_margin_m'])
        support=min(r['all_recorded_support_gap_min_m'],s['minimum_support_gap_extra_margin_m'])
        geometry=bool(r['all_recorded_physical_envelope_clear'] and s['sampled_factory_envelope_clear'])
        rows.append(dict(id=cid,file=f'v290_{cid}_full_attempt01.mp4',
            poster='data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode(),
            duration=v['duration_s'],path=r['measured_path_m'],solid=solid,support=support,
            arrived=r['goal_and_pd_passed'],geometry=geometry,
            deadline=r['scanner_deadline_failures'],note=causes[cid]))
    payload=json.dumps(rows,ensure_ascii=False).replace('</','<\\/')
    pattern=r'(<script[^>]*id="route-data"[^>]*>).*?(</script>)'
    text,count=re.subn(pattern,lambda m:m[1]+payload+m[2],text,flags=re.S);assert count==1
    combined=sum(r['arrived'] and r['geometry'] for r in rows)
    for label,value in [('到达 + PD',sum(r['arrived'] for r in rows)),('到达 + 几何',combined),('原生崩溃',load(H/'acceptance.json')['native_signal_crash_routes'])]:
        pattern=r'(<dt>'+re.escape(label)+r'</dt><dd>)\d+'
        text,n=re.subn(pattern,lambda m:m[1]+str(value),text);assert n==1
    old="const label = route => !route.arrived ? '未到达 · 已录段几何通过' : route.geometry ? '到达 · 采样几何通过' : '到达 · 固体越界';"
    new="const label = route => route.deadline ? '未到达 · 扫描超时中断' : route.arrived ? (route.geometry ? '到达 · 采样几何通过' : '到达 · 几何越界') : (route.geometry ? '未到达 · 已录段几何通过' : '未到达 · 已录段几何越界');"
    assert text.count(old)==1;text=text.replace(old,new)
    old="document.getElementById('support-margin').textContent = `+${(route.support * 100).toFixed(2)} cm`;"
    new="document.getElementById('support-margin').textContent = `${route.support >= 0 ? '+' : '−'}${Math.abs(route.support * 100).toFixed(2)} cm`; document.getElementById('support-margin').classList.toggle('negative', route.support < 0);"
    assert text.count(old)==1;text=text.replace(old,new)
    text=re.sub(r'(<footer><p>).*?(</p>)',lambda m:m[1]+'“几何”包含工厂起立及后续已录过程的 0.35 m 包络离散采样审计；未到达路线仅检查实际已录段。扫描超时中断与导航失败均保留，不重跑、不补造到达。'+m[2],text,count=1,flags=re.S)
    (H/'delivered/index.html').write_text(text)
    (H/'evidence/gallery_binding.json').write_text(json.dumps(dict(version='v290',videos=len(rows),
        arrived=sum(r['arrived'] for r in rows),combined=combined,local_only=True,external_dependencies=0,
        source='Verified local MP4s and sampled frames; sibling video files, embedded posters'),indent=2)+'\n')
    print('Offline gallery created with ten actual videos')
if __name__=='__main__':main()
