"""Read measured timing for display, without copying or editing run data."""
import json
import re
from artifacts import open_text


def load(source):
    prepared=source/'recording_measurements.json'
    if prepared.is_file():return json.loads(prepared.read_text())
    result=json.loads((source/'result.json').read_text())
    pace=result['realtime_pacing']
    begin=pace['wall_anchor_monotonic_s'];duration=pace['wall_elapsed_s'];end=begin+duration
    starts=overruns=0
    with open_text(source,'scan.log') as stream:
        for line in stream:
            m=re.search(r'nominal_replan frequency_hz=.*start_schedule_s=([\d.]+)',line)
            if m and begin<=float(m[1])<=end:starts+=1
            if 'nominal_replan_result' in line and 'overrun=1' in line:overruns+=1
    controls=0
    with open_text(source,'command_frequencies.jsonl') as stream:
        for line in stream:
            row=json.loads(line)
            controls+=int(row['topic']=='/quad_0/raw_scan_cmd_vel' and begin<=row['wall_monotonic_s']<=end)
    return dict(actual_navigation_rtf=pace['actual_rtf'],local_hz=starts/duration,
                controller_hz=controls/duration,local_overruns=overruns,
                definition='Actual event counts / complete navigation pacing wall window; overrun count from complete original log.')
