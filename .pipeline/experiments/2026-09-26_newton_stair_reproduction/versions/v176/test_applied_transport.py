"""Real-socket timeout/replay regressions; synthetic data are not stop evidence."""
import importlib.util,json,socket,sys,tempfile,threading,time,unittest
from pathlib import Path
from applied_channel import AppliedClient,AppliedStore,BASE,zmq
sys.path.insert(0,str(BASE/'runtime_sources/backend_adapter'))
from backend_adapter.applied_evidence import AppliedCommandSnapshot,StopEvidenceWindow


def payload(run,seq=1):
    zero={'vx':0.,'vy':0.,'wz':0.}
    return {'schema_version':1,'run_id':run,'run_epoch_ns':123,'sim_step':1,'sim_time_s':1.,
        'wall_monotonic_ns':time.monotonic_ns(),'command_source_timestamp_ns':1,
        'freshness':{'max_reader_age_s':2.},'applied_command':zero,'admitted_command':zero,
        'raw_command':zero,'command_sequence':1,'command_stale':False,'command_reason':'active',
        'measured':{'horizontal_speed_mps':0.,'yaw_rate_radps':0.,'base_xyz':[0.,0.,1.],
            'base_quat_wxyz':[1.,0.,0.,0.],'command_obs_error':0.},
        'state_epoch':{'state_sequence':seq,'telemetry_sequence':1}}

def raw(p):return json.dumps(p,separators=(',',':'),allow_nan=False).encode()

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.out=Path(self.tmp.name)/'synthetic_transport';self.out.mkdir()
        (self.out/'episode_request.json').write_text('{"run_epoch_ns":123}')
        self.store=AppliedStore(self.out)
    def tearDown(self):self.tmp.cleanup()
    def roundtrip(self,client_type,delay,requests):
        ready=threading.Event();data={};errors=[];replies=[];received=[]
        def server():
            try:
                with zmq.Context() as ctx,ctx.socket(zmq.REP) as rep:
                    rep.setsockopt(zmq.LINGER,0);rep.setsockopt(zmq.RCVTIMEO,1000)
                    data['port']=rep.bind_to_random_port('tcp://127.0.0.1');ready.set()
                    for i in range(requests):
                        message=rep.recv();received.append(message);reply=self.store.accept(message)
                        replies.append(reply)
                        if i==0:time.sleep(delay)
                        rep.send_json(reply)
            except BaseException as e:errors.append(e);ready.set()
        worker=threading.Thread(target=server);worker.start();self.assertTrue(ready.wait(2))
        client=client_type(data['port']);p=payload(self.out.name)
        try:
            response=client.publish(p)
            self.assertEqual(response['sha256'],replies[-1]['sha256'])
            return response,client.last_attempt,replies,received
        finally:
            client.close();worker.join(2);self.assertFalse(worker.is_alive());self.assertFalse(errors,errors)
    def test_clean_real_socket(self):
        r,t,rs,wire=self.roundtrip(AppliedClient,0,1)
        self.assertFalse(r['duplicate']);self.assertEqual(len(t['attempts']),1)
    def test_delayed_commit_reply_recovers_exact_bytes(self):
        r,t,rs,wire=self.roundtrip(AppliedClient,.55,2)
        self.assertEqual([x['duplicate'] for x in rs],[False,True])
        self.assertEqual(wire[0],wire[1]);self.assertEqual(len(t['attempts']),2)
        self.assertEqual((self.store.external/'current_command.json').read_bytes(),wire[0])
    def test_recorded_350ms_delay_old_client_exhausts_new_client_receives(self):
        path=Path(__file__).resolve().parent.parent/'v167/applied_channel.py'
        spec=importlib.util.spec_from_file_location('parent_three_attempt_client',path)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        with self.assertRaises(zmq.Again):self.roundtrip(old.AppliedClient,.35,1)
        self.store=AppliedStore(self.out)
        response,timing,replies,wire=self.roundtrip(AppliedClient,.35,1)
        self.assertFalse(response['duplicate']);self.assertEqual(len(timing['attempts']),1)
        self.assertEqual((self.store.external/'current_command.json').read_bytes(),wire[0])
    def test_original_client_fails_same_delayed_reply(self):
        path=Path(__file__).resolve().parent.parent/'v151/applied_channel.py'
        spec=importlib.util.spec_from_file_location('original_applied_transport',path)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        with self.assertRaises(zmq.Again):self.roundtrip(old.AppliedClient,.14,1)
    def test_exact_duplicate_does_not_rewrite_or_prove_dwell(self):
        p=payload(self.out.name);blob=raw(p);self.store.accept(blob)
        f=self.store.external/'current_command.json';before=f.stat().st_mtime_ns
        self.assertTrue(self.store.accept(blob)['duplicate']);self.assertEqual(before,f.stat().st_mtime_ns)
        window=StopEvidenceWindow();snapshot=AppliedCommandSnapshot.from_mapping(p)
        for _ in range(100):self.assertFalse(window.observe(snapshot,self.out.name,123))
    def test_altered_old_and_foreign_requests_reject(self):
        p=payload(self.out.name,2);self.store.accept(raw(p));p['sim_time_s']=2.
        with self.assertRaises(ValueError):self.store.accept(raw(p))
        for p in [payload(self.out.name,1),payload('foreign',3)]:
            with self.assertRaises(ValueError):self.store.accept(raw(p))
        p=payload(self.out.name,3);p['run_epoch_ns']=124
        with self.assertRaises(ValueError):self.store.accept(raw(p))
    def test_duplicate_rechecks_original_freshness(self):
        p=payload(self.out.name);p['freshness']['max_reader_age_s']=.02;blob=raw(p)
        self.store.accept(blob);time.sleep(.03)
        with self.assertRaises(ValueError):self.store.accept(blob)
        p=payload(self.out.name,2);p['wall_monotonic_ns']+=5_000_000_000
        with self.assertRaises(ValueError):self.store.accept(raw(p))
    def test_tampered_readback_rejects(self):
        blob=raw(payload(self.out.name));self.store.accept(blob)
        (self.store.external/'current_command.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):self.store.accept(blob)
    def test_absent_server_remains_bounded_failure(self):
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        client=AppliedClient(port);start=time.monotonic()
        try:
            with self.assertRaises(zmq.Again):client.publish(payload(self.out.name))
            self.assertEqual(len(client.last_attempt['attempts']),3)
            self.assertTrue(all('timed_out_monotonic_ns' in x for x in client.last_attempt['attempts']))
            self.assertLess(time.monotonic()-start,2.)
        finally:client.close()
if __name__=='__main__':unittest.main()
