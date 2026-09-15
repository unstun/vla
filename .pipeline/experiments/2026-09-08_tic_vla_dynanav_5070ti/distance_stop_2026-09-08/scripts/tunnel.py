"""Reconnect the task-owned SSH forward after observed relay disconnects."""
import socket
import subprocess
import threading
import time


def main():
    with socket.socket() as singleton:
        singleton.bind(("127.0.0.1", 18768))
        singleton.listen(16)
        def health_checks():
            while True:
                connection, _ = singleton.accept()
                connection.close()
        threading.Thread(target=health_checks, daemon=True).start()
        while True:
            started = time.time()
            print("TUNNEL_CONNECT", started, flush=True)
            process = subprocess.Popen([
                "ssh", "-N", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12",
                "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=2",
                "-o", "ExitOnForwardFailure=yes", "-L", "127.0.0.1:18766:127.0.0.1:18766", "gpu5070ti"])
            code = process.wait()
            print("TUNNEL_DISCONNECTED", code, "after", time.time() - started, flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main()
