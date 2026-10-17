"""Exercise the actual launcher boundary that blocked v161 before physics."""
from pathlib import Path
import json,os,platform,subprocess,sys,tempfile,unittest
HERE=Path(__file__).resolve().parent
@unittest.skipUnless(platform.system()=='Darwin','Mac execution-root integration')
class MacSupervisorTests(unittest.TestCase):
 def invoke(self,root,run,code):
  env=dict(os.environ,V194_TEMP_ROOT=str(root))
  return subprocess.run([sys.executable,str(HERE/'mac_supervisor.py'),'--run-id',run,'--deadline','2','--',sys.executable,'-c',code],env=env,capture_output=True,text=True)
 def test_actual_entry_and_duplicate_rejection(self):
  root=Path(tempfile.mkdtemp(prefix='v194_probe_',dir='/private/tmp/vla_stop_audit_20261012'));run='entry'
  (root/'runs'/run/'artifacts/external_episode').mkdir(parents=True)
  r=self.invoke(root,run,'print("owned child executed")');self.assertEqual(r.returncode,0,r.stderr)
  record=json.loads((root/'runs'/run/'process.json').read_text());self.assertEqual(record['exit_code'],0);self.assertFalse(record['timed_out']);self.assertGreater(record['child_peak_rss_bytes'],1024*1024)
  self.assertIn('owned child executed',(root/'runs'/run/'run.log').read_text())
  before=(root/'runs'/run/'process.json').read_bytes();r=self.invoke(root,run,'raise RuntimeError("must not run")');self.assertNotEqual(r.returncode,0);self.assertEqual((root/'runs'/run/'process.json').read_bytes(),before)
 def test_nonowned_root_rejected(self):
  r=self.invoke(Path('/private/tmp/v194_nonowned'),'bad','raise RuntimeError("must not run")');self.assertNotEqual(r.returncode,0);self.assertIn('AssertionError',r.stderr)
 def test_child_failure_propagates(self):
  root=Path(tempfile.mkdtemp(prefix='v194_probe_',dir='/private/tmp/vla_stop_audit_20261012'))
  r=self.invoke(root,'child_failure','import sys;sys.exit(7)');self.assertEqual(r.returncode,7,r.stderr)
 def test_actual_managed_retention_chain_and_episode_storage(self):
  from run_local_episode import prepare_external_directory
  root=Path(tempfile.mkdtemp(prefix='v194_managed_probe_',dir='/private/tmp/vla_stop_audit_20261012'))
  run=root/'runs'/'entry';(run/'artifacts/external_episode').mkdir(parents=True)
  prepare_external_directory(run)
  (root/'scripts').mkdir();(root/'scripts/run_bounded.py').symlink_to(HERE/'mac_supervisor.py')
  code='from pathlib import Path; import os; (Path(os.environ["NEWTON_RUN_DIR"])/"result.json").write_text("{}")'
  r=subprocess.run([sys.executable,str(HERE/'mac_managed.py'),'--run-id','entry','--deadline','3','--retention','archive','--',sys.executable,'-c',code],env=dict(os.environ,V194_TEMP_ROOT=str(root)),capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(json.loads((run/'retention_result.json').read_text())['status'],'completed')
  (run/'artifacts/external_episode/existing').write_text('preserve')
  with self.assertRaises(FileExistsError):prepare_external_directory(run)
if __name__=='__main__':unittest.main()
