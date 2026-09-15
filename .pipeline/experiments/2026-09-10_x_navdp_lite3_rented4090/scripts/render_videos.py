"""Encode recorded panels with their wall-clock intervals and join the four trials."""
import argparse
import json
from pathlib import Path
import subprocess

EXP=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);args=parser.parse_args()
    root=EXP/'runs'/args.run;media=EXP/'media'/args.run;media.mkdir(parents=True,exist_ok=True)
    cases=json.loads((root/'cases.json').read_text());videos=[]
    for case in cases:
        directory=root/case['id']/'frames'
        rows=[json.loads(line) for line in (directory/'frames.jsonl').read_text().splitlines()]
        lines=['ffconcat version 1.0']
        for i,row in enumerate(rows):
            dt=rows[i+1]['mono']-row['mono'] if i+1<len(rows) else .1
            if not dt>0:raise RuntimeError('Nonmonotonic recorded frame time')
            lines.extend([f"file '{directory/row['file']}'",f'duration {dt:.9f}'])
        lines.append(f"file '{directory/rows[-1]['file']}'")
        listing=media/f"{case['id']}.ffconcat";listing.write_text('\n'.join(lines)+'\n')
        video=media/f"{case['id']}.mp4"
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-f','concat',
            '-i',str(listing),'-vf','fps=10,format=yuv420p','-c:v','libx264','-crf','18','-movflags','+faststart',str(video)],check=True)
        subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
        videos.append(video)
    combined=media/'all_trials.mp4';listing=media/'all_trials.ffconcat'
    listing.write_text('\n'.join(f"file '{v}'" for v in videos)+'\n')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',str(listing),
                    '-c','copy','-movflags','+faststart',str(combined)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(combined),'-f','null','-'],check=True)
    print(combined)

if __name__=='__main__':main()
