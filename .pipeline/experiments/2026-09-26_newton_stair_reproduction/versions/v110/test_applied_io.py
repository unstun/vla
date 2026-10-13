"""Actual Linux ZeroMQ/reader test; injected host-log delay is explicitly synthetic."""
import copy
import hashlib
import importlib.util
import json
import multiprocessing
from pathlib import Path
import statistics
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=Path('/task/ack-io-probe')

def server(module_path,out,delay_host_log):
    spec=importlib.util.spec_from_file_location('channel_test',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=Path.open
    class SlowLog:
        def __init__(self,file):self.file=file
        def __enter__(self):return self
        def __exit__(self,*args):return self.file.__exit__(*args)
        def write(self,data):return self.file.write(data)
        def flush(self):time.sleep(.15);return self.file.flush()
    def patched(path,*args,**kwargs):
        result=original(path,*args,**kwargs)
        return SlowLog(result) if delay_host_log and path==out/'applied_channel.jsonl' else result
    Path.open=patched
    module.serve(out)

def run(version,stall):
    import zmq
    out=ROOT/(version+('-stall' if stall else '-normal'));out.mkdir(parents=True)
    local=Path('/dev/shm')/('vla-'+out.name);local.mkdir()
    (out/'artifacts').mkdir();(out/'artifacts/external_episode').symlink_to(local)
    (out/'episode_request.json').write_text(json.dumps({'run_epoch_ns':1}))
    module_path=HERE.parent/version/'applied_channel.py'
    process=multiprocessing.Process(target=server,args=(module_path,out,stall));process.start()
    context=zmq.Context();socket=context.socket(zmq.REQ);socket.setsockopt(zmq.LINGER,0)
    socket.setsockopt(zmq.RCVTIMEO,100);socket.setsockopt(zmq.SNDTIMEO,100);socket.connect('tcp://127.0.0.1:46203')
    fixture=json.loads(Path('/task/ack-fixture.json').read_text());latencies=[];timed_out=False;negative=[]
    try:
        time.sleep(.3)
        for i in range(1,101):
            payload=copy.deepcopy(fixture);payload.update(run_id=out.name,run_epoch_ns=1,wall_monotonic_ns=time.monotonic_ns()-1000000)
            payload['state_epoch']['state_sequence']=i
            raw=json.dumps(payload,separators=(',',':')).encode();before=time.monotonic();socket.send(raw)
            try:reply=socket.recv_json()
            except zmq.Again:timed_out=True;break
            latencies.append((time.monotonic()-before)*1000)
            assert reply['ok'] and reply['sha256']==hashlib.sha256(raw).hexdigest() and reply['original_reader_sequence']==i
            time.sleep(.02)
        if not timed_out:
            for kind in ['reordered','stale','wrong_run']:
                bad=copy.deepcopy(payload);bad['wall_monotonic_ns']=time.monotonic_ns()-1000000
                if kind=='stale':bad['wall_monotonic_ns']-=3000000000;bad['state_epoch']['state_sequence']+=1
                if kind=='wrong_run':bad['run_id']='different';bad['state_epoch']['state_sequence']+=1
                socket.send_json(bad);negative.append(not socket.recv_json()['ok'])
            assert all(negative)
    finally:
        socket.close();context.term();process.terminate();process.join(3)
        if process.is_alive():process.kill();process.join()
    audit=local/'applied_channel.jsonl' if version=='v110' else out/'applied_channel.jsonl'
    result={'version':version,'injected_host_flush_delay_ms':150 if stall else 0,'acknowledged':len(latencies),
      'timed_out_at_original_100ms':timed_out,'mean_ack_ms':statistics.mean(latencies) if latencies else None,
      'max_ack_ms':max(latencies) if latencies else None,'negative_rejections':negative,
      'audit_sha256':hashlib.sha256(audit.read_bytes()).hexdigest(),'linux_local_audit':version=='v110'}
    return result

if __name__=='__main__':
    results=[run(v,stall) for v,stall in [('v105',False),('v110',False),('v105',True),('v110',True)]]
    assert results[2]['timed_out_at_original_100ms']
    assert all(not results[i]['timed_out_at_original_100ms'] and results[i]['acknowledged']==100 for i in [0,1,3])
    print(json.dumps({'passed':True,'scope':'actual ZMQ and original state parser; synthetic host-log stall','results':results},indent=2))
