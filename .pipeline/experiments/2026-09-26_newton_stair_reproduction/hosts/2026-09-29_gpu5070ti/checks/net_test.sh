#!/usr/bin/env bash
# Shim and networking test on gpu5070ti: host-loopback server reachable as host.docker.internal from the main
# container, a published 127.0.0.1 port reachable from the host, and the arm64 image mapped and emulated or not.
set -uo pipefail
export PATH=$HOME/vla_exec/bin:$PATH
AMD=sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb
ARM=sha256:1c102582b40d5305e310788c79e963e4b6cde13aea2bc5db3b7c1800e821935d
echo "docker resolves to: $(command -v docker)"
python3 -c 'import socket,time
s=socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("127.0.0.1", 46299)); s.listen(1)
c,_=s.accept(); c.sendall(b"host-loopback-ok\n"); c.close(); time.sleep(0.2)' &
SRV=$!
sleep 0.5
echo "--- 1. /etc/hosts and a connection to the host loopback from the main container"
docker run --rm --pull=never --platform=linux/amd64 --name vla-port-nettest -e ROS_LOCALHOST_ONLY=1 --memory=5g --cpus=4 \
  -p 127.0.0.1:46298:46298 --entrypoint /bin/bash "$AMD" -c '
grep -E "host\.(docker|containers)\.internal" /etc/hosts
getent hosts host.docker.internal
python3 -c "import socket; s=socket.create_connection((\"host.docker.internal\", 46299), timeout=5); print(s.recv(64).decode().strip())"
python3 -c "import socket; s=socket.socket(); s.bind((\"0.0.0.0\", 46298)); s.listen(1); c,_=s.accept(); c.sendall(b\"published-port-ok\n\"); c.close()" &
sleep 4; wait' &
RUN=$!
sleep 3
echo "--- 2. host connects to the published 127.0.0.1:46298"
python3 -c 'import socket,time
for i in range(20):
    try:
        s=socket.create_connection(("127.0.0.1", 46298), timeout=2); print(s.recv(64).decode().strip()); break
    except OSError as e:
        time.sleep(0.25)
else:
    print("published port FAILED")'
wait $RUN; echo "run exit=$?"
kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
echo "--- 3. arm64 image reference and emulation"
docker create -i --pull never --name vla-port-armtest --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 1 --pids-limit 64 --user "$(id -u):$(id -g)" --entrypoint /bin/sh "$ARM" -c 'uname -m; g++ --version | head -1' && \
  docker start -ai vla-port-armtest; echo "arm start exit=$?"
docker rm -f vla-port-armtest >/dev/null 2>&1
ls /proc/sys/fs/binfmt_misc/ | tr '\n' ' '; echo
