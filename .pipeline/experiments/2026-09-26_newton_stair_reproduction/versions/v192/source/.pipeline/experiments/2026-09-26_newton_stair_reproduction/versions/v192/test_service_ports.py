"""Real Linux listener tests, distinct from navigation acceptance."""
import errno,os,platform,socket,sys,time,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
sys.path.insert(0,str(BASE/'runtime_sources/bridge'))
from lite3_sim_bridge.transport import TelemetryPublisherServer
@unittest.skipUnless(platform.system()=='Linux','Linux ephemeral-port behavior')
class Tests(unittest.TestCase):
 def test_service_ports_outside_actual_ephemeral_range(self):
  low,high=map(int,Path('/proc/sys/net/ipv4/ip_local_port_range').read_text().split())
  for p in (24600,24601,24602,24651):self.assertFalse(low<=p<=high)
 def test_old_port_self_connection_blocks_listener(self):
  with socket.socket() as client:
   client.settimeout(1);client.bind(('127.0.0.1',46200));client.connect(('127.0.0.1',46200));self.assertEqual(client.getsockname(),client.getpeername())
   server=TelemetryPublisherServer('127.0.0.1',46200)
   with self.assertRaises(OSError) as e:server.start()
   self.assertEqual(e.exception.errno,errno.EADDRINUSE)
 def test_real_new_listener_and_automatic_client_do_not_self_connect(self):
  server=TelemetryPublisherServer('127.0.0.1',24600)
  try:
   server.start()
   with socket.create_connection(('127.0.0.1',24600),timeout=1) as client:
    self.assertNotEqual(client.getsockname(),client.getpeername())
    end=time.monotonic()+1
    while server.stats().accepted_connections<1 and time.monotonic()<end:time.sleep(.005)
    self.assertEqual(server.stats().accepted_connections,1)
  finally:server.stop()
if __name__=='__main__':unittest.main()
