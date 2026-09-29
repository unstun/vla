"""Exercise the real clock-client receive loop with recorded and faulted replies."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,sys,tempfile,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
SOURCE=Path(sys.argv.pop(1)) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else BASE/'scripts/clock_sync.py'
spec=importlib.util.spec_from_file_location('clock_under_test',SOURCE);clock=importlib.util.module_from_spec(spec);sys.modules[spec.name]=clock;spec.loader.exec_module(clock)
ID='6c1be163154841f58b01a8a22f52bdb8'
def sample(i,*,accepted=True,rtt=1000000,delta=0,identity=ID,error=None,reset=False):
 sent=1000000000+i*5000000;offset=123400000
 return dict(seq=i+1,sent=sent,received=sent+rtt,remote=sent+rtt//2-offset+delta,accepted=accepted,responder=identity,error=error,reset=reset)
def exercise(rows):
 index=0;now=rows[0]['sent'];last_good=None;accepted_count=0;blocked=False;failures=[];outcomes=[]
 class Connection:
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def setsockopt(self,*args):pass
  def sendall(self,data):
   nonlocal now
   row=rows[index];seq,sent=clock.REQUEST.unpack(data)
   if sent!=row['sent']:raise AssertionError((index,sent,row['sent']))
   now=row['received']
   if row.get('error')=='socket':raise OSError('injected_socket_loss')
   echoed=seq+1 if row.get('error')=='echo' else seq
   self.data=clock.RESPONSE.pack(bytes.fromhex(row['responder']),echoed,sent,row['remote'])
  def recv(self,n):out=self.data[:n];self.data=self.data[n:];return out
 class Event:
  def is_set(self):return index>=len(rows)
  def wait(self,*args):
   nonlocal index,now,last_good,accepted_count,blocked
   row=rows[index]
   transport_bad=row.get('error') or row['responder']!=ID
   if transport_bad:blocked=True
   elif row.get('reset'):blocked=True;accepted_count=0
   elif row['accepted']:accepted_count+=1;last_good=now;blocked=False
   expected=not blocked and accepted_count>=500 and last_good is not None and 0<=now-last_good<=clock.SYNC_TTL_NS
   try:estimate=client.estimate();actual=True
   except clock.ClockUnavailable as exc:estimate=None;actual=False;reason=str(exc)
   if expected!=actual:failures.append({'index':index,'expected':expected,'actual':actual,'reason':None if actual else reason})
   if estimate is not None and estimate.sampled_local_ns!=last_good:failures.append({'index':index,'cache_timestamp_changed':True})
   outcomes.append(actual);index+=1
   if index<len(rows):now=rows[index]['sent']
   return False
 with tempfile.TemporaryDirectory() as tmp:
  client=clock.ClockClient('unused',0,Path(tmp)/'samples.jsonl');client.stop_event=Event()
  fake_socket=SimpleNamespace(create_connection=lambda *a,**k:Connection(),IPPROTO_TCP=6,TCP_NODELAY=1)
  with patch.object(clock,'socket',fake_socket),patch.object(clock,'time',SimpleNamespace(monotonic_ns=lambda:now)):
   client._run()
 return failures,outcomes
class ClockCacheTests(unittest.TestCase):
 def test_recorded_rejections_preserve_fresh_estimate(self):
  source=BASE/'runs/v17_building_route01/clock_samples.jsonl';rows=[json.loads(s) for s in source.read_text().splitlines()];rows=[r for r in rows if 'sent' in r]
  # Use the uninterrupted connection prefix so no omitted transport events can
  # silently restore a cached estimate in this recorded-data test.
  prefix=[]
  for r in rows:
   if r['seq']!=len(prefix)+1:break
   r=dict(r);r['error']=None;prefix.append(r)
  bad,_=exercise(prefix);self.assertGreater(len(prefix),500);self.assertEqual(bad,[],str(bad[:5]))
 def test_rejected_samples_do_not_refresh_ttl(self):
  rows=[sample(i) for i in range(501)]+[sample(i,accepted=False,rtt=11000000) for i in range(501,555)]
  bad,out=exercise(rows);self.assertEqual(bad,[],str(bad[:5]));self.assertTrue(out[501]);self.assertFalse(out[-1])
 def test_filter_reset_invalidates_cached_estimate(self):
  rows=[sample(i) for i in range(501)]+[sample(i,accepted=False,delta=50000000,reset=i==511) for i in range(501,512)]
  bad,out=exercise(rows);self.assertEqual(bad,[],str(bad[:5]));self.assertFalse(out[-1])
 def test_socket_failure_is_not_revived_by_rejected_sample(self):
  rows=[sample(i) for i in range(501)]+[sample(501,accepted=False,error='socket'),sample(502,accepted=False,rtt=11000000)]
  bad,out=exercise(rows);self.assertEqual(bad,[],str(bad[:5]));self.assertEqual(out[-2:],[False,False])
 def test_identity_and_echo_errors_invalidate_immediately(self):
  for kind in ['identity','echo']:
   final=sample(501,accepted=False,identity='0'*32 if kind=='identity' else ID,error='echo' if kind=='echo' else None)
   bad,out=exercise([sample(i) for i in range(501)]+[final]);self.assertEqual(bad,[],str(bad[:5]));self.assertFalse(out[-1])
if __name__=='__main__':unittest.main()
