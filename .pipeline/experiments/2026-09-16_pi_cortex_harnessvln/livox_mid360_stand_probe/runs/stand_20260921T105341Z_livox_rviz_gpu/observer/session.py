"""Optional passive RViz/capture session around the unchanged navigation run."""

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import threading
import time


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


class DisplayProbe:
    def __init__(self, run_root):
        self.root = Path(run_root)
        self.source = self.root / 'observer'
        self.output = self.root / 'artifacts/pointcloud_observer'
        self.output.mkdir(parents=True, exist_ok=True)
        self.config = json.loads((self.source / 'config.json').read_text())
        self.mode = self.config['mode']
        self.rviz_config_file = self.config.get('rviz_config_file', 'pointcloud.rviz')
        self.expected_window_title = '/observer/' + self.rviz_config_file + ' - RViz'
        self.monitor = None
        self.container_started = False
        self.capture = None
        self.capture_thread = None
        self.done = threading.Event()
        self.pids = {}
        self.pid_lock = threading.Lock()
        self.records = {'mode': self.mode, 'config': self.config, 'errors': [], 'commands': []}
        self.name = 'vla-pointcloud-' + self.root.name.lower().replace('_', '-')
        self.xenv = dict(os.environ, DISPLAY=self.config['display'], XAUTHORITY=self.config['xauthority'])

    def record_process(self, name, pid):
        with self.pid_lock:
            self.pids[name] = int(pid)
            write_json(self.output / 'pids.json', self.pids)

    def _run(self, command, timeout=15, check=True, env=None):
        self.records['commands'].append(command)
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
        if check and result.returncode:
            raise RuntimeError('observer command failed: ' + result.stderr[-1500:])
        return result

    def _windows(self):
        text = self._run(['xwininfo', '-root', '-tree'], env=self.xenv).stdout
        found = {}
        for line in text.splitlines():
            if '"' + self.expected_window_title + '"' not in line:
                continue
            match = re.match(r'\s*(0x[0-9a-fA-F]+)\s+', line)
            if match:
                found[match.group(1)] = line.strip()
        return found

    def start(self):
        write_json(self.output / 'pids.json', {})
        monitor_cmd = [sys.executable, str(self.source / 'resource_monitor.py'),
                       '--output', str(self.output / 'resource_samples.jsonl'),
                       '--pids', str(self.output / 'pids.json'),
                       '--snapshot', str(self.root / 'artifacts/external_episode/current_command.json')]
        self.records['commands'].append(monitor_cmd)
        self.monitor = subprocess.Popen(monitor_cmd, stdout=(self.output / 'monitor.log').open('w'),
                                        stderr=subprocess.STDOUT, start_new_session=True)
        self.record_process('resource_monitor', self.monitor.pid)
        if self.mode == 'off':
            write_json(self.output / 'session.json', self.records)
            return
        if self.mode not in {'rviz', 'rviz-gpu'}:
            raise ValueError('unknown observer mode')
        if (self.rviz_config_file != 'pointcloud_' + self.root.name + '.rviz'
                or not re.fullmatch(r'[A-Za-z0-9_.-]+\.rviz', self.rviz_config_file)):
            raise RuntimeError('display configuration must have a unique run-specific filename')
        if not Path(self.config['xauthority']).is_file():
            raise RuntimeError('observer Xauthority path unavailable')
        before = set(self._windows())
        if self._run(['podman', 'container', 'exists', self.name], check=False).returncode == 0:
            raise RuntimeError('observer container already exists')
        inner = '''set -e
source /opt/ros/foxy/setup.bash
export ROS_DOMAIN_ID=94
export ROS_LOCALHOST_ONLY=1
cd /observer-out
python3 /observer/cloud_audit.py --output /observer-out/cloud_receipts.jsonl &
python3 /observer/aabb_hit_marker.py --output /observer-out/aabb_hits.jsonl --setup /run-artifacts/runner_output/unmapped_box_setup.json &
python3 /observer/occupancy_audit.py --output /observer-out/occupancy_receipts.jsonl --setup /run-artifacts/runner_output/unmapped_box_setup.json &
exec rviz2 --ogre-log -d ''' + shlex.quote('/observer/' + self.rviz_config_file) + ''' --ros-args -p use_sim_time:=true
'''
        command = ['podman', 'run', '-d', '--pull=never', '--network=host', '--ipc=host',
                   '--cpus=2', '--memory=2g', '--name', self.name,
                   '-e', 'DISPLAY=' + self.config['display'], '-e', 'XAUTHORITY=/tmp/.Xauthority',
                   '-e', 'QT_X11_NO_MITSHM=1', '-e', 'ROS_LOG_DIR=/observer-out/ros_logs',
                   '-e', 'PYTHONDONTWRITEBYTECODE=1',
                   '-v', '/tmp/.X11-unix:/tmp/.X11-unix:ro',
                   '-v', self.config['xauthority'] + ':/tmp/.Xauthority:ro',
                   '-v', str(self.source) + ':/observer:ro',
                   '-v', str(self.output) + ':/observer-out:rw',
                   '-v', str(self.root / 'artifacts') + ':/run-artifacts:ro']
        if self.config.get('gpu_display'):
            runtime = self.config['nvidia_runtime']
            for device in runtime['devices']:
                command.extend(['--device', device])
            for mount in runtime['mounts']:
                source = Path(mount['source'])
                actual = hashlib.sha256(source.read_bytes()).hexdigest()
                if actual != mount['sha256']:
                    raise RuntimeError('NVIDIA provider identity changed: ' + str(source))
                command.extend(['-v', str(source) + ':' + mount['destination'] + ':ro'])
            for key, value in runtime['environment'].items():
                command.extend(['-e', key + '=' + value])
            self.records['nvidia_provider_hashes_verified'] = True
        else:
            command.extend(['-e', 'LIBGL_ALWAYS_SOFTWARE=1', '-e', 'LP_NUM_THREADS=2'])
        command.extend([self.config['rviz_image_id'], 'bash', '-lc', inner])
        self._run(command, timeout=30)
        self.container_started = True
        deadline = time.monotonic() + 30
        window = None
        while time.monotonic() < deadline:
            current = self._windows()
            new = set(current) - before
            visible = []
            for candidate in new:
                size = re.search(r'\s(\d+)x(\d+)[+-]', current[candidate])
                if size and int(size.group(1)) >= 640 and int(size.group(2)) >= 480:
                    visible.append((int(size.group(1)) * int(size.group(2)), candidate))
            if visible:
                window = max(visible)[1]
                self.records['window'] = current[window]
                self.records['window_matches_run_specific_title'] = True
                break
            time.sleep(0.2)
        if window is None:
            raise RuntimeError('RViz window not observed within deadline')
        if self.config.get('gpu_display'):
            self._verify_nvidia_renderer()
        pid = int(self._run(['podman', 'inspect', '--format', '{{.State.Pid}}', self.name]).stdout.strip())
        self.record_process('rviz_container_init', pid)
        geometry = self._run(['xwininfo', '-id', window], env=self.xenv).stdout
        self.records['window_geometry'] = geometry
        width = int(re.search(r'Width:\s+(\d+)', geometry).group(1))
        height = int(re.search(r'Height:\s+(\d+)', geometry).group(1))
        self.records['capture_resolution'] = [width, height]
        self.records['capture_wall_fps'] = 10
        self.capture_thread = threading.Thread(target=self._capture_when_active,
                                               args=(window, width, height), daemon=True)
        self.capture_thread.start()
        write_json(self.output / 'session.json', self.records)

    def _verify_nvidia_renderer(self):
        deadline = time.monotonic() + 8
        renderer = []
        while time.monotonic() < deadline:
            log = self.output / 'Ogre.log'
            if log.exists():
                renderer = [line for line in log.read_text(errors='replace').splitlines()
                            if 'GL_RENDERER' in line or 'GL_VENDOR' in line]
                if any('GL_RENDERER' in line and 'NVIDIA' in line and '5070 Ti' in line
                       for line in renderer):
                    self.records['renderer_log_lines'] = renderer
                    self.records['nvidia_renderer_verified'] = True
                    return
            time.sleep(0.1)
        self.records['renderer_log_lines'] = renderer
        self.records['nvidia_renderer_verified'] = False
        self.records['errors'].append('NVIDIA RTX 5070 Ti renderer not verified')
        raise RuntimeError('NVIDIA renderer gate failed: ' + repr(renderer))

    def _capture_when_active(self, window, width, height):
        try:
            snapshot_path = self.root / 'artifacts/external_episode/current_command.json'
            while not self.done.wait(0.1):
                try:
                    snapshot = json.loads(snapshot_path.read_text())
                    if snapshot.get('run_id') == self.root.name and snapshot.get('sim_step', 0) >= 10:
                        break
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
            if self.done.is_set():
                return
            command = ['ffmpeg', '-hide_banner', '-loglevel', 'info', '-f', 'x11grab',
                       '-draw_mouse', '0', '-framerate', '10', '-window_id', str(int(window, 16)),
                       '-video_size', '%dx%d' % (width, height), '-i', self.config['display'] + '.0',
                       '-an']
            encoder = self.config.get('capture_encoder', 'libx264')
            if encoder == 'h264_nvenc':
                command.extend(['-c:v', 'h264_nvenc', '-gpu', '0', '-preset', 'p4',
                                '-tune', 'hq', '-rc', 'vbr', '-cq', '24', '-b:v', '0'])
            elif encoder == 'libx264':
                command.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '24'])
            else:
                raise ValueError('unsupported capture encoder: ' + encoder)
            command.extend(['-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                            str(self.output / 'rviz_live_wall_time.mp4')])
            self.records['commands'].append(command)
            self.records['capture_started_monotonic_ns'] = time.monotonic_ns()
            self.capture = subprocess.Popen(command, stdout=(self.output / 'capture.log').open('w'),
                                            stderr=subprocess.STDOUT, env=self.xenv, start_new_session=True)
            self.record_process('rviz_capture', self.capture.pid)
        except Exception as error:
            self.records['errors'].append('capture:' + str(error))

    def stop(self):
        self.done.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=3)
        if self.capture is not None:
            try:
                self.capture.send_signal(signal.SIGINT)
                self.capture.wait(timeout=8)
            except Exception as error:
                self.records['errors'].append('capture_stop:' + str(error))
                self.capture.kill()
            self.records['capture_exit_code'] = self.capture.poll()
            self.records['capture_stopped_monotonic_ns'] = time.monotonic_ns()
        if self.container_started:
            try:
                log = self._run(['podman', 'logs', self.name], check=False)
                (self.output / 'rviz.log').write_text(log.stdout + log.stderr)
                removal = self._run(['podman', 'rm', '-f', '-t', '2', self.name], timeout=15, check=False)
                self.records['container_removal'] = {'returncode': removal.returncode, 'stderr': removal.stderr}
                if removal.returncode:
                    self.records['errors'].append('observer_container_removal_failed')
            except Exception as error:
                self.records['errors'].append('container_stop:' + str(error))
        if self.monitor is not None:
            try:
                self.monitor.terminate()
                self.monitor.wait(timeout=5)
            except Exception as error:
                self.records['errors'].append('monitor_stop:' + str(error))
                self.monitor.kill()
            self.records['monitor_exit_code'] = self.monitor.poll()
        write_json(self.output / 'session.json', self.records)
        return dict(self.records)
