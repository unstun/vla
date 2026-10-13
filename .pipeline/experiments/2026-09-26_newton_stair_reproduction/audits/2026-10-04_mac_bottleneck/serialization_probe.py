"""Replay the exact HTTP JSON encoder and measure same-process Python delays."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import platform
import sys
import threading
import time


def distribution(values):
    values = sorted(values)
    def q(p):
        index = (len(values)-1)*p
        lo = int(index)
        return values[lo] + (values[min(lo+1,len(values)-1)]-values[lo])*(index-lo)
    return {'count':len(values),'mean':sum(values)/len(values),'median':q(.5),
            'p95':q(.95),'p99':q(.99),'maximum':values[-1]}


def probe(data, repeats):
    samples = []
    ticks = []
    running = threading.Event()
    running.set()
    def heartbeat_work():
        while running.is_set():
            ticks.append(time.monotonic())
            time.sleep(1/30)
    worker = threading.Thread(target=heartbeat_work)
    worker.start()
    time.sleep(.1)
    for unused in range(repeats):
        begin = time.monotonic()
        cpu = time.thread_time()
        # This is the unchanged NavigationHttpRuntime Handler._send encoder.
        raw = json.dumps(data, sort_keys=True).encode('utf-8')
        samples.append({'wall_ms':(time.monotonic()-begin)*1000,
                        'cpu_ms':(time.thread_time()-cpu)*1000,'bytes':len(raw)})
        time.sleep(.01)
    time.sleep(.1)
    running.clear()
    worker.join()
    gaps = [(b-a)*1000 for a,b in zip(ticks,ticks[1:])]
    return {'encoding_wall_ms':distribution(r['wall_ms'] for r in samples),
        'encoding_cpu_ms':distribution(r['cpu_ms'] for r in samples),
        'callback_work_gap_ms':distribution(gaps),
        'gaps_above_original_200ms_threshold':sum(g>200 for g in gaps),
        'bytes':samples[0]['bytes'],
        'claim':'Exact serializer and Python thread scheduling seam; no ROS, physics or navigation acceptance.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixtures',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=15)
    args = p.parse_args()
    results = []
    for source in sorted(args.fixtures.glob('trial*.json')):
        data = json.loads(source.read_text())
        full = probe(data,args.repeats)
        small = dict(data)
        small['pct'] = dict(data['pct'],plan_history=[])
        compact = probe(small,args.repeats)
        row = {'fixture':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
               'full_original_state':full,'diagnostic_without_route_history':compact}
        results.append(row)
        print(json.dumps({'fixture':source.name,'full_encode_max_ms':full['encoding_wall_ms']['maximum'],
                         'full_work_gap_max_ms':full['callback_work_gap_ms']['maximum'],
                         'without_history_encode_max_ms':compact['encoding_wall_ms']['maximum']}),flush=True)
        gc.collect()
    proof = {'host':platform.platform(),'machine':platform.machine(),'python':sys.version,
             'repeats':args.repeats,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'results':results,'production_behavior_modified':False}
    args.output.write_text(json.dumps(proof,indent=2)+'\n')
