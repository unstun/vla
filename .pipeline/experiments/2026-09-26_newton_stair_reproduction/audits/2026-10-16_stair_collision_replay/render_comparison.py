"""GPU viewport rendering of archived states and measured collision replay fields."""
from pathlib import Path
import argparse
import bisect
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import subprocess
import sys
import zipfile
from functools import lru_cache
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
BASE=ROOT.parent/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
RUN=ROOT.parent/'trials/v217_linux_full_attempt01/runs/v217_linux_full_attempt01'
os.environ['PYGLET_HEADLESS']='1';os.environ['PYOPENGL_PLATFORM']='egl'
os.environ['WARP_CACHE_PATH']=str(ROOT/'render_cache')
os.environ['NEWTON_CACHE_PATH']=str(ROOT/'render_assets')
sys.path[:0]=[str(BASE/'scripts'),str(BASE/'versions/v51'),str(BASE/'versions/v40/physics'),str(BASE/'versions/v220')]
import render_episode_v51 as appearance
from robot_scene_v40 import StairRobot
from curve_overlay import Overlay
import newton
import warp as wp

BG=(242,244,247);INK=(28,40,54);MUTED=(104,118,133);CYAN=(26,155,174);RED=(208,76,89);GREEN=(61,151,106);AMBER=(229,154,54)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=32)
def font(size):
    names=['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc','/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']
    found=next((p for p in names if Path(p).exists()),None)
    if found is None:
        found=subprocess.check_output(['fc-match','-f','%{file}','sans:lang=zh'],text=True).strip()
    return ImageFont.truetype(found,size)


def load_csv(path):
    return np.genfromtxt(path,delimiter=',',names=True)


def card(draw,box):draw.rounded_rectangle(box,radius=18,fill='white',outline=(220,226,232),width=1)


def map_panel(image,box,data,body,route,title,sub,blocked_field,witnesses=()):
    d=ImageDraw.Draw(image);card(d,box);x0,y0,x1,y1=box
    d.text((x0+20,y0+16),title,font=font(28),fill=INK)
    d.text((x0+20,y0+58),sub,font=font(19),fill=MUTED)
    left,right,top,bottom=x0+27,x1-20,y0+106,y1-49
    bounds=(6.6,8.9,-4.75,-2.65)
    def xy(x,y):return left+(x-bounds[0])/(bounds[1]-bounds[0])*(right-left),bottom-(y-bounds[2])/(bounds[3]-bounds[2])*(bottom-top)
    d.rectangle((left,top,right,bottom),fill=(244,247,249))
    points=data[data['kind']==2]
    # Multiple height-associated samples are drawn at the same XY only within
    # the named local floor range; this is a planar diagnostic projection.
    for row in points:
        x,y=float(row['x']),float(row['y'])
        if not(bounds[0]<=x<=bounds[1] and bounds[2]<=y<=bounds[3]):continue
        u,v=xy(x,y);rx=.047/(bounds[1]-bounds[0])*(right-left);ry=.047/(bounds[3]-bounds[2])*(bottom-top)
        color=RED if row[blocked_field]!=0 else CYAN
        d.rectangle((u-rx,v-ry,u+rx,v+ry),fill=tuple(int(.73*c+.27*255) for c in color))
    for x in np.arange(7,9,.5):
        u,_=xy(x,bounds[2]);d.line((u,top,u,bottom),fill=(213,220,227),width=1)
    for y in np.arange(-4.5,-2.5,.5):
        _,v=xy(bounds[0],y);d.line((left,v,right,v),fill=(213,220,227),width=1)
    pts=[xy(*p[:2]) for p in route if bounds[0]<=p[0]<=bounds[1] and bounds[2]<=p[1]<=bounds[3]]
    if len(pts)>1:d.line(pts,fill=AMBER,width=4)
    bx,by,bz,yaw=body;u,v=xy(bx,by)
    if left<=u<=right and top<=v<=bottom:
        d.ellipse((u-8,v-8,u+8,v+8),fill=INK,outline='white',width=2)
        a,b=xy(bx+.24*math.cos(yaw),by+.24*math.sin(yaw));d.line((u,v,a,b),fill=INK,width=4)
        for sign in [-1,1]:
            cx,cy=xy(bx+sign*.18*math.cos(yaw),by+sign*.18*math.sin(yaw))
            radius=.25 if '原版尺寸' in sub else .35
            rx=radius/(bounds[1]-bounds[0])*(right-left);ry=radius/(bounds[3]-bounds[2])*(bottom-top)
            d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),outline=INK,width=2)
    d.text((x0+22,y1-35),'青：规则通过   红：规则拒绝',font=font(19),fill=MUTED)
    # Spatial witness: the exact neighboring column which rejects the floor fill.
    if '当前' in title:
        du,dv=xy(7.5546853065490724,-3.586811447143555)
        d.rectangle((du-7,dv-7,du+7,dv+7),fill=AMBER,outline=INK,width=2)
        d.line((du,dv,u,v),fill=AMBER,width=3)
        for w in witnesses:
            wu,wv=xy(float(w['witness_x']),float(w['witness_y']))
            d.line((wu-7,wv-7,wu+7,wv+7),fill=(135,70,175),width=4)
            d.line((wu-7,wv+7,wu+7,wv-7),fill=(135,70,175),width=4)


def draw_diagnosis(image,frame,body_detail,geometry):
    d=ImageDraw.Draw(image);card(d,(24,770,1024,1018));card(d,(1048,770,1896,1018))
    d.text((46,787),'为什么当前位置被拒绝',font=font(29),fill=INK)
    b=body_detail[0];ground=float(b['body_ground']);real=geometry['ground_hits_below_body_m'][-1]
    wrong=int(b['reason'])==110
    title='当前楼面在支撑表里缺失' if wrong else '当前楼面与机身高度匹配'
    d.text((46,833),title,font=font(32),fill=RED if wrong else GREEN)
    d.text((46,885),f'原始楼梯几何：地面 {real:.3f} m',font=font(25),fill=INK)
    d.text((46,928),f'当前支撑判定：地面 {ground:.3f} m',font=font(25),fill=RED if wrong else INK)
    d.text((46,973),f'机身 {frame["body_xyz"][2]:.3f} m  ·  高度误差 {float(b["height_error"]):.3f} m / 允许 0.120 m',font=font(21),fill=MUTED)
    x=907;top,bottom=820,975
    def z(v):return bottom-float(v)/2.1*(bottom-top)
    d.line((x,top,x,bottom),fill=(177,189,201),width=3)
    for value,color,label in [(ground,RED if wrong else GREEN,'判定'),(real,GREEN,'实体'),(frame['body_xyz'][2],INK,'机身')]:
        yy=z(value);d.line((x-25,yy,x+25,yy),fill=color,width=5);d.text((x-90,yy-13),label,font=font(18),fill=color)
    d.text((1070,787),'独立核对：真有障碍，还是模型太保守？',font=font(26),fill=INK)
    d.text((1070,836),'机身实体与原楼梯：'+('没有相交' if geometry['torso_mesh_clear'] else '检测到相交'),font=font(27),fill=GREEN if geometry['torso_mesh_clear'] else RED)
    forces=geometry['foot_forces_n'];stand=geometry['stance_mode']=='FIXED_STAND'
    d.text((1070,882),'四脚支撑：'+' / '.join(f'{x:.0f}' for x in forces)+' N',font=font(24),fill=INK)
    extra='已进入固定站立，仍被支撑高度判定拒绝' if stand and wrong else '行走中的抬脚是正常现象；此处只核对记录'
    if wrong and not stand:extra='邻近落差保护排除了当前楼面，起点因此失效'
    d.text((1070,924),extra,font=font(23),fill=RED if stand and wrong else MUTED)
    blocker=next((x for x in body_detail if int(x['blocking_sources'])>0),None)
    text='紫色 ×：历史非地形记录仍在阻挡' if blocker else '当前机身附近：没有未分类障碍贡献点'
    d.text((1070,969),text,font=font(22),fill=AMBER if blocker else MUTED)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--preview',action='store_true');args=p.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    frames=json.loads((ROOT/'input/frames.json').read_text());ft=[x['time_s'] for x in frames]
    states=json.loads((RUN/'video_states.json').read_text());st=[x['physics_time_s'] for x in states]
    geometry=json.loads((ROOT/'output/geometry_check.json').read_text())['frames']
    details=list(csv.DictReader((ROOT/'output/native_details/details.csv').open()))
    details={i:[x for x in details if int(x['frame'])==i and x['kind']=='0'] for i in range(len(frames))}
    critical_details=[x for x in csv.DictReader((ROOT/'output/critical_native/details.csv').open()) if x['frame']=='0']
    native=[load_csv(ROOT/'output/native'/f'frame_{i}.csv') for i in range(len(frames))]
    original=[load_csv(ROOT/'output/original_author'/f'frame_{i}.csv') for i in range(len(frames))]
    original_current=[load_csv(ROOT/'output/original_current'/f'frame_{i}.csv') for i in range(len(frames))]
    for a,b in zip(native,original):
        for key in ['id','kind','x','y','z','yaw']:assert np.array_equal(a[key],b[key]),key
    source=BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py'
    spec=importlib.util.spec_from_file_location('collision_movie_pct',source);core=importlib.util.module_from_spec(spec);sys.modules[spec.name]=core;spec.loader.exec_module(core)
    m=core.load_pinned_map(BASE/'inputs/new_building.pickle');e=core.load_paired_elevations(BASE/'inputs/new_building_original_precision.npz',m)
    pct=core.selected_ground_points(m,cost_limit=None,paired_elevations=e)
    pct=pct[(pct[:,0]>5.3)&(pct[:,0]<9.8)&(pct[:,1]>-5.8)&(pct[:,1]<-2.0)&(pct[:,2]>1.35)&(pct[:,2]<2.6)]
    colors=np.where((pct[:,3]<=20)[:,None],np.array(GREEN)/255,np.array(RED)/255).astype(np.float32)
    request=json.loads((RUN/'episode_request.json').read_text());scenario=json.loads((RUN/'inputs/stair_scenario.json').read_text())
    robot=StairRobot(startup_mode=request['startup_mode'],stance_hold=True,automatic_contact_capacity=True,model_device='cpu',scenario=scenario)
    appearance.prepare_appearance(robot,None,out)
    v=robot.building_vertices;faces=robot.building_faces;tri=v[faces]
    keep=(tri[:,:,2].max(axis=1)<2.72)&(tri[:,:,0].max(axis=1)>5.2)&(tri[:,:,0].min(axis=1)<10.1)&(tri[:,:,1].max(axis=1)>-6.0)&(tri[:,:,1].min(axis=1)<-1.9)
    robot.model.shape_source[robot.building_shape]=newton.Mesh(v,faces[keep].reshape(-1),compute_inertia=False)
    cutaway={'source_triangles':len(faces),'displayed_triangles':int(keep.sum()),'mask_sha256':hashlib.sha256(keep.tobytes()).hexdigest(),'display_only':True}
    (out/'cutaway.json').write_text(json.dumps(cutaway,indent=2)+'\n')
    overlay=Overlay(RUN,BASE/'versions/v217/results/latency.csv')
    viewer=newton.viewer.ViewerGL(width=1000,height=600,vsync=False,headless=True);viewer.set_model(robot.model)
    viewer.camera.fov=48.;viewer.renderer.sky_upper=viewer.renderer.sky_lower=(.92,.94,.96)
    viewer.renderer.ambient_sky=(.8,.8,.8);viewer.renderer.ambient_ground=(.35,.35,.35);viewer.renderer.spotlight_enabled=False;viewer.renderer.line_width=4.
    try:
        from pyglet import gl
        import ctypes
        glname=ctypes.string_at(gl.glGetString(gl.GL_RENDERER)).decode()
    except Exception as exc:glname='unavailable: '+repr(exc)
    assert 'NVIDIA' in glname or '5070' in glname,glname
    times=[];fps=30
    if args.preview:times=[43.0,48.10519028,60.55]
    else:
        for begin,end,speed in [(42.01,46.8,1.),(46.8,48.10519028,.25),(48.10519028,49.2,.25),(49.2,61.94,1.)]:
            times += [(float(t),speed) for t in np.arange(begin,end,speed/fps)]
            if end==48.10519028:times += [(48.10519028,0.)]*240
            if end==49.2:times += [(49.2,0.)]*150
        times += [(61.94,0.)]*240
    archive=zipfile.ZipFile(RUN/'raw_capture.zip');cloud_cache={};encoder=None;records=[]
    if not args.preview:
        command=['ffmpeg','-nostdin','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r',str(fps),'-i','pipe:0','-c:v','h264_nvenc','-preset','p6','-cq','21','-b:v','0','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'stairs_collision_comparison.mp4')]
        log=(out/'encoder.log').open('w');encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        (out/'encoding.json').write_text(json.dumps(command,indent=2)+'\n')
    try:
        for index,item in enumerate(times):
            t,speed=(item,0.) if args.preview else item
            fi=max(0,bisect.bisect_right(ft,t)-1);f=frames[fi];si=bisect.bisect_right(st,t)-1;row=dict(states[si])
            row.update(source_state_index=si,display_time_s=index/fps,timeline_segment='recorded physics')
            robot.state.body_q.assign(np.asarray(row['body_q'],dtype=np.float32));robot.state.joint_q.assign(np.asarray(row['joint_q'],dtype=np.float32))
            viewer.set_camera((9.4,-5.6,3.3),pitch=-30,yaw=0);viewer.camera.look_at((7.85,-3.65,1.62))
            viewer.begin_frame(t);viewer.log_state(robot.state)
            viewer.log_points('pct_traversability',wp.array(pct[:,:3],dtype=wp.vec3),radii=.013,colors=wp.array(colors,dtype=wp.vec3))
            if f['cloud_file'] not in cloud_cache:
                cloud=np.load(io.BytesIO(archive.read(f['cloud_file'])),allow_pickle=False)['world_points']
                cloud=cloud[(cloud[:,0]>5.4)&(cloud[:,0]<9.7)&(cloud[:,1]>-5.6)&(cloud[:,1]<-2.1)&(cloud[:,2]>1.45)&(cloud[:,2]<2.6)][::3]
                cloud_cache[f['cloud_file']]=cloud
            cloud=cloud_cache[f['cloud_file']]
            viewer.log_points('recorded_cloud',wp.array(cloud,dtype=wp.vec3),radii=.005,colors=wp.array(np.tile([.47,.53,.60],(len(cloud),1)),dtype=wp.vec3))
            curve,cm=overlay.frame(row);route=overlay.route_points
            if route is None:route=np.load(ROOT/'input'/f'route_{fi:04d}.npy')
            keep_route=(route[:,0]>5.4)&(route[:,0]<9.7)&(route[:,1]>-5.6)&(route[:,1]<-2.1)&(route[:,2]>1.45)&(route[:,2]<2.6)
            segments=keep_route[:-1]&keep_route[1:]
            viewer.log_lines('pct_route',wp.array(route[:-1][segments],dtype=wp.vec3),wp.array(route[1:][segments],dtype=wp.vec3),colors=tuple(np.array(AMBER)/255))
            if curve is not None:
                viewer.log_lines('scan_curve',wp.array(curve[:-1],dtype=wp.vec3),wp.array(curve[1:],dtype=wp.vec3),colors=(.05,.85,.95))
            else:viewer.log_lines('scan_curve',None,None,None)
            # This marker is the actual replay-query state, separate from the
            # continuously displayed recorded robot when a query is older.
            body=native[fi][0];mark=np.array([[body['x'],body['y'],body['z']+.13]],dtype=np.float32)
            active_details=critical_details if abs(t-48.10519028)<1e-6 else details[fi]
            blockers=[w for w in active_details if int(w['blocking_sources'])>0]
            viewer.log_points('query_marker',wp.array(mark,dtype=wp.vec3),radii=.055,colors=wp.array([np.array(RED if body['native'] else CYAN)/255],dtype=wp.vec3))
            if blockers:
                hit=np.array([[float(w[k]) for k in ['witness_x','witness_y','witness_z']] for w in blockers],dtype=np.float32)
                viewer.log_points('historical_blocker',wp.array(hit,dtype=wp.vec3),radii=.045,colors=wp.array(np.tile([.53,.27,.69],(len(hit),1)),dtype=wp.vec3))
            else:viewer.log_points('historical_blocker',None)
            witness=np.array([[7.5546853,-3.5868114,1.55803]],dtype=np.float32)
            viewer.log_points('floor_fill_guard_witness',wp.array(witness,dtype=wp.vec3),radii=.065,colors=wp.array([np.array(AMBER)/255],dtype=wp.vec3))
            if f['time_s']>=48.105:
                viewer.log_lines('guard_link',wp.array(witness,dtype=wp.vec3),wp.array([np.array([body['x'],body['y'],1.55803])],dtype=wp.vec3),colors=tuple(np.array(AMBER)/255))
            else:viewer.log_lines('guard_link',None,None,None)
            viewer.end_frame();scene=Image.fromarray(viewer.get_frame(render_ui=False).numpy())
            image=Image.new('RGB',(1920,1080),BG);d=ImageDraw.Draw(image)
            d.text((28,20),'楼梯为什么卡住？',font=font(38),fill=INK)
            d.text((408,30),'同一记录 · 相同点云 / 机身姿态 / 参考路线',font=font(27),fill=MUTED)
            speed_label='定格分析' if speed==0 else f'{speed:g}× 记录时间回放'
            d.text((1390,27),f'{t:05.2f} s  |  {speed_label}',font=font(26),fill=INK)
            d.text((28,88),'PCT 原生代价层 + 记录点云 + 机器人真实记录姿态',font=font(25),fill=INK)
            d.text((1065,88),f'SCAN 位置采样 · 固定机身朝向 / 离地 0.35 m · {f["time_s"]:.2f} s',font=font(21),fill=INK)
            image.paste(scene,(24,128));d=ImageDraw.Draw(image)
            d.rounded_rectangle((42,146,650,187),radius=9,fill=(245,247,249))
            d.text((54,151),'剖视显示：隐藏上层楼板，原始几何未修改',font=font(20),fill=MUTED)
            chapter=('① 相同输入：先看原始代价、点云和参考路线' if t<46.8 else
                     '② 接近边界：机身正在向路线左侧偏移' if t<48.10519028 else
                     '③ 首次卡死：地板还在，支撑表却排除了这一层' if t<49.2 else
                     '④ 后续重试：高度拒绝之外，又叠加历史障碍' if t<58 else
                     '⑤ 已经站住，起点仍被拒绝；前方有路也出不去')
            d.rounded_rectangle((42,642,1006,717),radius=10,fill=(245,247,249))
            d.text((55,650),chapter,font=font(24),fill=INK)
            note='橙色圆点 / 右图方块：触发楼面排除的邻近格'
            if abs(t-48.10519028)<1e-6:note='精确失败查询：规划朝向 60.3° · 前后障碍均通过 · 高度条件拒绝'
            d.text((55,685),note,font=font(19),fill=MUTED)
            d.text((42,738),'绿 / 红：PCT 代价　灰：当前点云　橙：全局路线　青：有效局部轨迹',font=font(20),fill=MUTED)
            b=(*f['body_xyz'],f['body_yaw'])
            # During the second freeze isolate geometry using the unchanged
            # original algorithm with the current envelope, not a new map.
            same_size=abs(t-49.2)<1e-6 and speed==0
            map_panel(image,(1048,128,1463,751),original_current[fi] if same_size else original[fi],b,route,'原版规则 / 当前尺寸' if same_size else '原版 SCAN','当前尺寸 · 地面也参与膨胀' if same_size else '原版尺寸 · 不检查脚下支撑','blocked')
            map_panel(image,(1481,128,1896,751),native[fi],b,route,'当前 Lite3 集成','当前尺寸 · 含新增判定','native',blockers)
            draw_diagnosis(image,f,active_details,geometry[fi])
            if same_size:
                d=ImageDraw.Draw(image);d.rounded_rectangle((42,642,1006,717),radius=10,fill=(245,247,249))
                d.text((55,650),'补充对照：只把原版的碰撞范围扩大，也会堵住',font=font(24),fill=INK)
                d.text((55,685),'当前的地形剔除打开了大片区域；问题集中在新增支撑条件',font=font(20),fill=MUTED)
            d=ImageDraw.Draw(image);d.line((28,1042,1892,1042),fill=(205,214,223),width=5);x=28+(t-42)/(62-42)*1864;d.ellipse((x-7,1035,x+7,1049),fill=INK)
            d.text((28,1052),'42 s',font=font(16),fill=MUTED);d.text((1770,1052),'62 s · 失败现场',font=font(16),fill=MUTED)
            record={'frame':index,'video_s':index/fps,'source_time_s':t,'playback_speed':speed,'source_state_index':si,'recorded_state_time_s':row['physics_time_s'],'query_frame':fi,'query_time_s':f['time_s'],'cloud_stamp_ns':f['last_cloud_stamp_ns'],'curve':cm,'rgb_sha256':hashlib.sha256(image.tobytes()).hexdigest()}
            records.append(record)
            if args.preview or index in (0,len(times)//2,len(times)-1):image.save(out/f'preview_{index:04d}.png')
            if encoder:encoder.stdin.write(image.tobytes())
            if index%90==0:print(json.dumps({'frame':index,'of':len(times),'source_s':t}),flush=True)
        if encoder:
            encoder.stdin.close();assert encoder.wait(timeout=90)==0
    finally:viewer.close()
    (out/'frames.json').write_text(json.dumps(records,indent=2)+'\n')
    result={'render_only_no_physics_steps':True,'physics_steps':0,'frames':len(records),'fps':fps,'graphics_renderer':glname,'source_run':RUN.name,'source_video_states_sha256':digest(RUN/'video_states.json'),'query_identity_sha256':digest(ROOT/'input/identity.json'),'native_source':'frozen installed v219 map, ordered replay','field_scope':'sampled local surface positions at current measured yaw; not a complete reachable set','cutaway':cutaway}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
