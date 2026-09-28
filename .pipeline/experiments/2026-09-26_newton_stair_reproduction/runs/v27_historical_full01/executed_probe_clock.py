"""Compare the clock port with extracted upstream C++, then qualify transport."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from clock_sync import ClockClient, ClockEstimate, ClockUnavailable, MavrosFilter
from bridge_adapter import DomainCommandState
from lite3_sim_bridge.command_state import CommandLimits
from lite3_sim_bridge.protocol import CommandV1, ProtocolError

BASE = Path(__file__).resolve().parents[1]


def extract_function(text, signature):
    begin = text.index(signature)
    brace = text.index("{", begin)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[begin:end]


def check_reference(out):
    manifest = json.loads((BASE / "references/mavros_clock_port.json").read_text())
    source = (BASE.parents[2] / manifest["source_path"]).read_text()
    if hashlib.sha256(source.encode()).hexdigest() != manifest["source_sha256"]:
        raise ValueError("Upstream clock source identity changed")
    observe = extract_function(source, "void add_timesync_observation(")
    # Omit ROS diagnostic publication only; filter/control branches unchanged.
    observe = observe[:observe.index("// Publish timesync status")] + "}"
    methods = [observe] + [extract_function(source, s) for s in
                           ("void add_sample(", "void reset_filter(", "inline bool sync_converged(")]
    scaffold = '''#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#define RCLCPP_ERROR(...) (void)0
#define RCLCPP_WARN(...) (void)0
struct Node { uint64_t value; Node now(){return *this;} uint64_t nanoseconds(){return value;} };
struct Dummy {void clear(){} void set_timestamp(uint64_t){} void set_time_offset(double){}};
class Filter {public:
 Node n; Node* node=&n; Dummy dt_diag, u; Dummy* uas=&u;
 double time_offset=0,time_skew=0,filter_alpha=.05,filter_beta=.05;
 uint32_t sequence=0;
 float filter_alpha_initial=.05f,filter_beta_initial=.05f,filter_alpha_final=.003f,filter_beta_final=.003f;
 int convergence_window=500,max_rtt_sample=10,max_deviation_sample=10;
 int max_cons_high_rtt=10,max_cons_high_deviation=10,high_rtt_count=0,high_deviation_count=0;
'''
    cpp = scaffold + "\n".join(methods) + '''\n};
int main(){Filter f; long long offset; unsigned long long rtt;
while(std::cin>>offset>>rtt){f.n.value=100000000000ULL+rtt;
f.add_timesync_observation(offset,100000000000ULL,1);
std::cout<<std::setprecision(17)<<f.time_offset<<" "<<f.time_skew<<" "<<f.sequence<<" "
<<f.high_rtt_count<<" "<<f.high_deviation_count<<"\\n";}}
'''
    path = out / "mavros_reference.cpp"
    path.write_text(cpp)
    command = ["/usr/bin/clang++", "-std=c++17", "-O0", str(path), "-o", str(out / "mavros_reference")]
    compile_result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (out / "compile.json").write_text(json.dumps({"command": command, "stderr": compile_result.stderr,
                                                "exit_code": compile_result.returncode}, indent=2) + "\n")
    compile_result.check_returncode()
    cases = [(128000000000000 + (i % 7 - 3) * 20000, 2_000_000) for i in range(550)]
    cases += [(128000000000000, 20_000_000)] * 12
    cases += [(128000100000000, 2_000_000)] * 12
    cases += [(128000100000000 + (i % 7 - 3) * 20000, 2_000_000) for i in range(550)]
    native = subprocess.run([str(out / "mavros_reference")], input="".join(f"{a} {b}\n" for a, b in cases),
                            capture_output=True, text=True, timeout=10)
    native.check_returncode()
    filtered = MavrosFilter()
    max_error = 0.
    for sample, line in zip(cases, native.stdout.splitlines(), strict=True):
        filtered.observe(*sample)
        values = line.split()
        error = max(abs(filtered.offset - float(values[0])), abs(filtered.skew - float(values[1])))
        max_error = max(max_error, error)
        if [filtered.sequence, filtered.high_rtt_count, filtered.high_deviation_count] != list(map(int, values[2:])):
            raise AssertionError("Upstream clock acceptance/reset sequence mismatch")
    if max_error > 10:
        raise AssertionError(f"Upstream numeric mismatch {max_error}ns")
    (out / "reference_output.txt").write_text(native.stdout)
    return {"samples": len(cases), "max_filter_difference_ns": max_error,
            "convergence_rejection_reset_sequences_equal": True}


def check_commands(estimate):
    class FixedClock:
        failed = False
        def estimate(self):
            if self.failed:
                raise ClockUnavailable("injected_sync_loss")
            return estimate
    clock = FixedClock()
    state = DomainCommandState(clock, CommandLimits())
    local = estimate.sampled_local_ns
    remote = local - estimate.local_minus_remote_ns
    command = CommandV1(.2, 0., 0.)
    state.update(command, 1, remote, local)
    assert not state.snapshot(local).stale
    for seq, stamp in ((2, remote - 300_000_000), (3, remote + 50_000_000)):
        try:
            state.update(command, seq, stamp, local)
        except ProtocolError:
            pass
        else:
            raise AssertionError("stale/future command admitted")
    assert state.snapshot(local + 250_000_001).command == state.ZERO
    state.update(command, 4, remote + 300_000_000, local + 300_000_000)
    clock.failed = True
    assert state.snapshot(local + 300_000_000).command == state.ZERO
    assert state.snapshot(local + 300_000_000).reason == "clock_unsynchronized"
    return {"fresh_admitted": True, "stale_rejected": True, "future_rejected": True,
            "original_250ms_watchdog_zeroes": True, "sync_loss_zeroes": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    out = Path(os.environ["NEWTON_RUN_DIR"])
    for name in ("clock_sync.py", "bridge_adapter.py", "probe_clock.py"):
        shutil.copyfile(Path(__file__).with_name(name), out / ("executed_" + name))
    result = {"reference": check_reference(out)}
    synthetic = ClockEstimate(128000000000000, 11_000_000, 128050000000000, 500, "fixture", 2_000_000)
    result["command_contracts"] = check_commands(synthetic)
    if args.port:
        clock = ClockClient("127.0.0.1", args.port, out / "clock_samples.jsonl")
        clock.start()
        try:
            estimate = clock.wait_ready(30)
            result["live_estimate"] = asdict(estimate)
            result["live_command_contracts"] = check_commands(estimate)
        finally:
            clock.stop()
        time.sleep(.21)
        try:
            clock.estimate()
        except ClockUnavailable:
            result["stopped_clock_expires"] = True
        else:
            raise AssertionError("Stopped clock remains usable")
    result["accepted"] = True
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
