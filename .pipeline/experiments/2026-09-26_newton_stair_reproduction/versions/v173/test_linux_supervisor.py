"""Exercise the actual launcher boundary that blocked v161 before physics."""
from pathlib import Path
import json,os,platform,subprocess,sys,tempfile,unittest
HERE=Path(__file__).resolve().parent
@unittest.skipUnless(platform.system()=='Linux','Linux execution-root integration')
class LinuxSupervisorTests(unittest.TestCase):
 def invoke(self,root,run,code):
  env=dict(os.environ,V173_TEMP_ROOT=str(root))
  return subprocess.run([sys.executable,str(HERE/'mac_supervisor.py'),'--run-id',run,'--deadline','2','--',sys.executable,'-c',code],env=env,capture_output=True,text=True)
 def test_actual_entry_and_duplicate_rejection(self):
  root=Path(tempfile.mkdtemp(prefix='v173_probe_',dir='/data/sun/vla_mppi_20261009/trials'));run='entry'
  (root/'runs'/run/'artifacts/external_episode').mkdir(parents=True)
  r=self.invoke(root,run,'print("owned child executed")');self.assertEqual(r.returncode,0,r.stderr)
  record=json.loads((root/'runs'/run/'process.json').read_text());self.assertEqual(record['exit_code'],0);self.assertFalse(record['timed_out']);self.assertGreater(record['child_peak_rss_bytes'],1024*1024)
  self.assertIn('owned child executed',(root/'runs'/run/'run.log').read_text())
  before=(root/'runs'/run/'process.json').read_bytes();r=self.invoke(root,run,'raise RuntimeError("must not run")');self.assertNotEqual(r.returncode,0);self.assertEqual((root/'runs'/run/'process.json').read_bytes(),before)
 def test_nonowned_root_rejected(self):
  r=self.invoke(Path('/private/tmp/v173_nonowned'),'bad','raise RuntimeError("must not run")');self.assertNotEqual(r.returncode,0);self.assertIn('AssertionError',r.stderr)
 def test_child_failure_propagates(self):
  root=Path(tempfile.mkdtemp(prefix='v173_probe_',dir='/data/sun/vla_mppi_20261009/trials'))
  r=self.invoke(root,'child_failure','import sys;sys.exit(7)');self.assertEqual(r.returncode,7,r.stderr)
if __name__=='__main__':unittest.main()
