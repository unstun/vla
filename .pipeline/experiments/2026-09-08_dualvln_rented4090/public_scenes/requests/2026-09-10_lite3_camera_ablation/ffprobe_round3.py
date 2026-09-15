import glob, json, subprocess
out = {}
for f in sorted(glob.glob('public_scenes/runs/cam_*/vis_debug/epoch_0/*.mp4') +
                glob.glob('public_scenes/runs/cam_*/vis_0/*/*.mp4')):
    r = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                        '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', f],
                       capture_output=True, text=True)
    out[f] = {'frames': r.stdout.strip(), 'error': r.stderr.strip() or None}
json.dump(out, open('public_scenes/requests/2026-09-10_lite3_camera_ablation/ffprobe_frame_counts.json', 'w'), indent=2)
print(len(out), 'videos probed')
