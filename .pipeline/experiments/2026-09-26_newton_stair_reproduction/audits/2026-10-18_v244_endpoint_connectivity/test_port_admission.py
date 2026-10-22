"""A real TCP listener must block; a closed owned socket's TIME_WAIT must not."""
import errno,socket
with socket.socket() as server:
 server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);server.bind(('127.0.0.1',0));server.listen()
 address=server.getsockname()
 with socket.socket() as occupied:
  occupied.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
  try:occupied.bind(address)
  except OSError as e:assert e.errno==errno.EADDRINUSE
  else:raise AssertionError('active listener was not rejected')
 client=socket.create_connection(address);peer,_=server.accept()
 peer.shutdown(socket.SHUT_WR);assert client.recv(1)==b'';client.close();assert peer.recv(1)==b'';peer.close()
with socket.socket() as plain:
 try:plain.bind(address)
 except OSError as e:assert e.errno==errno.EADDRINUSE
 else:raise AssertionError('TIME_WAIT control was not created')
with socket.socket() as available:
 available.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);available.bind(address);available.listen()
print('active_listener_rejected=1 own_time_wait_control_reproduced=1 reuse_probe_succeeds=1')
