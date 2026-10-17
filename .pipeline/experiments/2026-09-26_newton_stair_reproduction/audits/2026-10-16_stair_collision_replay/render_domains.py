"""Filled, equal-scale native traversability regions, composed on gpu5070ti."""
from pathlib import Path
from functools import lru_cache
import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
SOURCE=ROOT/'output/video_final02'
BG=(243,245,247);INK=(30,43,55);MUTED=(103,117,129)
FREE=(99,183,160);BLOCK=(221,130,137);EMPTY=(219,225,230);ROUTE=(232,155,41)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
@lru_cache(maxsize=32)
def font(size):return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',size)
def text(d,xy,value,size=22,color=INK):d.text(xy,value,font=font(size),fill=color)
def card(d,box):d.rounded_rectangle(box,radius=16,fill='white',outline=(221,226,231),width=1)
def read_csv(path):return np.atleast_1d(np.genfromtxt(path,delimiter=',',names=True))

def panel(image,x,points,passed,body,route,trail,title,subtitle,radius,bounds):
    d=ImageDraw.Draw(image);card(d,(x,130,x+608,807))
    text(d,(x+22,145),title,29);text(d,(x+22,190),subtitle,20,MUTED)
    text(d,(x+22,220),f'绿色通过：{int(passed.sum())} / {len(points)} 格',19,MUTED)
    body_cell=int(np.argmin(np.linalg.norm(points[:,:2]-np.array(body[:2]),axis=1)))
    text(d,(x+335,220),'机身所在格：'+('允许' if passed[body_cell] else '拒绝'),19,(38,124,103) if passed[body_cell] else (181,64,76))
    scale=536/(bounds[1]-bounds[0]);left=x+44;top=252;bottom=top+(bounds[3]-bounds[2])*scale;right=left+536
    def xy(px,py):return left+(px-bounds[0])*scale,bottom-(py-bounds[2])*scale
    d.rectangle((left,top,right,bottom),fill=EMPTY)
    cells={}
    for i,p in enumerate(points):
        u,v=xy(*p[:2]);h=.05*scale
        box=(max(left,u-h),max(top,v-h),min(right,u+h),min(bottom,v+h))
        if box[0]<=box[2] and box[1]<=box[3]:d.rectangle(box,fill=FREE if passed[i] else BLOCK)
        cells[(round(float(p[0])*10),round(float(p[1])*10))]=i
    # Draw actual pass-region edges; do not interpolate across missing cells.
    for key,i in cells.items():
        if not passed[i]:continue
        u,v=xy(*points[i,:2]);h=.05*scale
        for delta,line in [((-1,0),(u-h,v-h,u-h,v+h)),((1,0),(u+h,v-h,u+h,v+h)),((0,-1),(u-h,v+h,u+h,v+h)),((0,1),(u-h,v-h,u+h,v-h))]:
            j=cells.get((key[0]+delta[0],key[1]+delta[1]))
            if j is None or not passed[j]:d.line(line,fill=(38,124,103),width=2)
    def inside(p):return bounds[0]<=p[0]<=bounds[1] and bounds[2]<=p[1]<=bounds[3]
    for a,b in zip(trail,trail[1:]):
        if inside(a) and inside(b):d.line((*xy(*a[:2]),*xy(*b[:2])),fill=(70,84,96),width=2)
    for a,b in zip(route,route[1:]):
        if inside(a) and inside(b):d.line((*xy(*a[:2]),*xy(*b[:2])),fill=(255,244,220),width=7);d.line((*xy(*a[:2]),*xy(*b[:2])),fill=ROUTE,width=4)
    bx,by,bz,yaw=body;u,v=xy(bx,by)
    if radius:
        for sign in [-1,1]:
            cu,cv=xy(bx+sign*.18*math.cos(yaw),by+sign*.18*math.sin(yaw));rr=radius*scale
            d.ellipse((cu-rr,cv-rr,cu+rr,cv+rr),outline=(47,61,74),width=2)
    d.ellipse((u-8,v-8,u+8,v+8),fill=INK,outline='white',width=3)
    au,av=xy(bx+.23*math.cos(yaw),by+.23*math.sin(yaw));d.line((u,v,au,av),fill=INK,width=4)
    for px in [7.,8.]:
        xx,_=xy(px,bounds[2]);text(d,(xx-17,bottom+6),f'{px:.0f} m',15,MUTED)
    for py in [-4.,-3.]:
        _,yy=xy(bounds[0],py);text(d,(x+3,yy-10),f'{py:.0f}',15,MUTED)
    d.line((right-110,bottom-20,right-110+.5*scale,bottom-20),fill=INK,width=3)
    text(d,(right-93,bottom-48),'0.5 m',16,INK)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--preview',action='store_true');a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=False)
    identity=json.loads((ROOT/'domain_input/identity.json').read_text());points=np.load(ROOT/'domain_input/domain_floor.npy')
    frames=json.loads((ROOT/'input/frames.json').read_text());records=json.loads((SOURCE/'frames.json').read_text());bounds=identity['bounds_xy']
    native=[read_csv(ROOT/'output/domain_native'/f'frame_{i}.csv') for i in range(len(frames))]
    original=[read_csv(ROOT/'output/domain_original'/f'frame_{i}.csv') for i in range(len(frames))]
    stats=[]
    for f,n,o in zip(frames,native,original):
        assert len(n)==len(o)==len(points)
        for key in ['id','kind','x','y','z','yaw']:assert np.array_equal(n[key],o[key]),key
        assert np.array_equal(n['x'],points[:,0]) and np.array_equal(n['y'],points[:,1])
        assert np.allclose(n['z'],points[:,2].astype(float)-.03+.30,rtol=0,atol=1e-12)
        assert np.all(n['yaw']==f['body_yaw'])
        stats.append({'frame':f['index'],'time_s':f['time_s'],'cells':len(points),'pct_free':int((points[:,3]<=20).sum()),'original_scan_free':int((o['blocked']==0).sum()),'current_scan_free':int((n['native']==0).sum()),'pct_free_current_reject':int(((points[:,3]<=20)&(n['native']!=0)).sum()),'pct_reject_current_free':int(((points[:,3]>20)&(n['native']==0)).sum())})
    parity=sum(int(r['parity_errors']) for r in csv.DictReader((ROOT/'output/domain_native/frames.csv').open()));assert parity==0
    np.savez_compressed(out/'region_fields.npz',floor=points,pct_allowed=points[:,3]<=20,
        original=np.stack([v['blocked'] for v in original]).astype(np.int8),
        current=np.stack([v['native'] for v in native]).astype(np.int8),
        front_reason=np.stack([v['front_reason'] for v in native]).astype(np.int16),
        rear_reason=np.stack([v['rear_reason'] for v in native]).astype(np.int16),
        query_yaw=np.array([f['body_yaw'] for f in frames]),query_times=np.array([f['time_s'] for f in frames]))
    assert sha(SOURCE/'stairs_collision_comparison.mp4')==json.loads((SOURCE/'verification.json').read_text())['video_sha256']
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],text=True).strip();assert '5070 Ti' in gpu
    selected=[30,400,1445] if a.preview else list(range(len(records)))
    decode=None;encode=None
    if not a.preview:
        decode=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-i',str(SOURCE/'stairs_collision_comparison.mp4'),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
        command=['ffmpeg','-nostdin','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','30','-i','pipe:0','-c:v','h264_nvenc','-preset','p6','-cq','21','-b:v','0','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'stairs_collision_comparison.mp4')]
        log=(out/'encoder.log').open('w');encode=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
    output_records=[]
    for index in selected:
        r=records[index];fi=r['query_frame'];f=frames[fi];t=r['source_time_s'];yaw=f['body_yaw']
        if a.preview:
            b=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-ss',str(index/30),'-i',str(SOURCE/'stairs_collision_comparison.mp4'),'-frames:v','1','-f','image2pipe','-vcodec','png','pipe:1']);old=Image.open(io.BytesIO(b)).convert('RGB')
        else:
            b=decode.stdout.read(1920*1080*3);assert len(b)==1920*1080*3;old=Image.frombytes('RGB',(1920,1080),b)
        image=Image.new('RGB',(1920,1080),BG);d=ImageDraw.Draw(image)
        text(d,(24,17),'PCT 与 SCAN，到底各自允许走哪里？',36)
        text(d,(1490,27),f'记录时间 {t:05.2f} s',25)
        text(d,(24,73),'同一楼层 · 同一坐标 · 同一点云历史',23,MUTED)
        for x,c,label in [(1010,FREE,'允许'),(1140,BLOCK,'拒绝'),(1270,EMPTY,'缺少本层楼面')]:
            d.rectangle((x,80,x+24,100),fill=c);text(d,(x+34,74),label,21,MUTED)
        text(d,(1530,74),'黑点：机器人   橙线：参考路线',19,MUTED)
        route=np.load(ROOT/'input'/f'route_{fi:04d}.npy');bp=np.array(f['body_xyz']);nearest=int(np.argmin(np.linalg.norm(route-bp,axis=1)));route=route[nearest:]
        length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(route,axis=0),axis=1))];route=route[length<=3.5]
        body=(*f['body_xyz'],yaw);trail=[z['body_xyz'] for z in frames[max(0,fi-15):fi+1]]
        panel(image,24,points,points[:,3]<=20,body,route,trail,'① PCT 原生通行区域','原生导航代价 ≤ 20 的楼面格',None,bounds)
        panel(image,656,points,original[fi]['blocked']==0,body,route,trail,'② SCAN 原版通行区域','原版碰撞规则 · 作者尺寸 r = 0.25 m',.25,bounds)
        panel(image,1288,points,native[fi]['native']==0,body,route,trail,'③ SCAN 当前通行区域','当前尺寸 r = 0.35 m · 含新增支撑判定',.35,bounds)
        d=ImageDraw.Draw(image);card(d,(24,825,450,1044));scene=old.crop((24,128,1024,630)).resize((400,201),Image.Resampling.LANCZOS);image.paste(scene,(37,834));d=ImageDraw.Draw(image)
        d.rounded_rectangle((46,840,326,870),radius=7,fill=(248,249,250));text(d,(55,842),'原失败现场的记录姿态',18,MUTED)
        card(d,(474,825,1896,1044))
        if t<48.10519028:
            message='看绿色区域的边界：PCT 与 SCAN 允许的位置，本来就不完全相同。'
            detail='橙色路线来自 PCT；SCAN 还要检查点云、机身范围和脚下支撑。'
        else:
            message='机器人偏到通行带边缘后，当前 SCAN 把所在位置判成无效起点。'
            detail='真实楼面 1.558 m → 支撑表排除这一层 → 找不到当前机身高度对应的地面。'
        text(d,(496,840),message,26);text(d,(496,882),detail,23,MUTED)
        text(d,(496,927),f'SCAN 查询条件：固定本次机身朝向 {math.degrees(yaw):.1f}°；每格机身中心 = 楼面 + 0.30 m。',22)
        text(d,(496,967),'色块表示格中心的位置判定；整条路径的连通性、腿部运动没有在这里重新验证。',21,MUTED)
        text(d,(496,1005),f'三图共享 {len(points)} 个格子，SCAN 包含对 PCT 红色格子的查询；灰色没有被涂成可通行。',19,MUTED)
        d.line((24,1062,1896,1062),fill=(209,217,224),width=4);xx=24+(t-42)/20*1872;d.ellipse((xx-6,1056,xx+6,1068),fill=INK)
        rr=dict(r);rr.update(region_grid_sha256=identity['floor_grid_sha256'],region_query_frame=fi,rgb_sha256=hashlib.sha256(image.tobytes()).hexdigest());output_records.append(rr)
        if a.preview or index in [30,400,1445]:image.save(out/f'preview_{index:04d}.png')
        if encode:encode.stdin.write(image.tobytes())
        if index%180==0:print(json.dumps({'frame':index,'total':len(records),'source_s':t}),flush=True)
    if encode:encode.stdin.close();assert encode.wait(timeout=60)==0;assert decode.wait(timeout=60)==0
    (out/'frames.json').write_text(json.dumps(output_records,indent=2)+'\n')
    result={'gpu':gpu,'encoding':'h264_nvenc','original_scene_renderer':'NVIDIA GeForce RTX 5070 Ti/PCIe/SSE2','source_scene_video_sha256':sha(SOURCE/'stairs_collision_comparison.mp4'),'region_identity':identity,'region_stats':stats,'region_fields_sha256':sha(out/'region_fields.npz'),'native_csv_sha256':{str(p.relative_to(ROOT)):sha(p) for mode in ['domain_native','domain_original'] for p in sorted((ROOT/'output'/mode).glob('frame_*.csv'))},'native_parity_errors':parity,'source_coordinate_identity':True,'frames':len(output_records),'fps':30,'physics_steps':0,'navigation_source_edits':False,'native_binary_sha256':sha(ROOT/'build/collision_probe'),'original_binary_sha256':sha(ROOT/'build_original/original_probe'),'source_hashes':{p.name:sha(p) for p in (ROOT/'source').glob('*') if p.is_file() and p.name in ['domain_inputs.py','run_domains.py','render_domains.py']}}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'frames':len(output_records),'cells':len(points),'parity_errors':parity,'gpu':gpu}),flush=True)

if __name__=='__main__':main()
