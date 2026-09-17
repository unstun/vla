#!/usr/bin/env bash
# CPU rehearsal of scripts/phase_d1_run_stage_audit.sh on the execution host, with fake sudo/docker/nvidia-smi and a
# fake cgroup tree. No GPU, no real container, no real docker call: PATH puts the fakes first and the fake sudo execs
# its arguments without privilege. Run from the run root:
#
#   bash scripts/rehearse_phase_d1_driver.sh
#
# Scenarios:
#   1. good: vendor process only; the fake "container" writes a record then hangs -> the driver must stop it after the
#      grace period, the sampler must survive failing nvidia-smi calls, the summary must exit 0 on the fake record.
#   2. foreign: a GPU process outside the vendor container -> refuse (exit 75) before anything starts.
#   3. unlisted: device memory not explained by listed processes -> refuse (exit 75).
set -uo pipefail
REAL_ROOT=$(pwd)
[[ -f scripts/phase_d1_run_stage_audit.sh && -f phase_d/stage_audit_thresholds_d1b.json ]] || { echo "run from the run root" >&2; exit 64; }
R=$REAL_ROOT/checks/d1b_driver_rehearsal_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$R"/{phase_d,phase_c/episodes,tools,scripts,setup/phase_d1_interioragent,fakebin,fakecg,state,driver_logs}
cp phase_d/stage_audit.py phase_d/stage_audit_lib.py phase_d/stage_audit_thresholds_d1b.json phase_d/fusion_isaac_c8.json \
   phase_d/test_stage_audit.py "$R/phase_d/"
cp phase_c/episodes/c_red_box_ahead_v1.json "$R/phase_c/episodes/"
cp tools/phase_b_camera_probe.py "$R/tools/"
cp scripts/phase_d1_run_stage_audit.sh scripts/phase_d1b_stage_audit_summary.py "$R/scripts/"
cp setup/phase_d1_interioragent/kujiale_0031_val_unseen_episodes.json "$R/setup/phase_d1_interioragent/"
S=$R/scenes/interioragent_ac599fe2
mkdir -p "$S/kujiale_0031/Meshes"
echo '#usda 1.0' > "$S/kujiale_0031/kujiale_0031.usda"
for i in $(seq 1 450); do echo "$i" > "$S/kujiale_0031/Meshes/f_$i.usd"; done
( cd "$S/kujiale_0031" && find . -type f ! -name SHA256SUMS.txt | sed 's|^\./||' | sort | xargs sha256sum > SHA256SUMS.txt )
echo '{}' > "$S/kujiale_0031_download_record.json"
VENDOR_ID=16998b63e8dd8608f6947016bda58d0b0227b2dbbbab4c92cad2ef6011b1868f
OWN_ID=aaaaaaaaaaaa1111111111111111111111111111111111111111111111111111
FOREIGN_ID=cccccccccccc2222222222222222222222222222222222222222222222222222
mkdir -p "$R/fakecg/1240" && echo "0::/system.slice/docker-$VENDOR_ID.scope" > "$R/fakecg/1240/cgroup"
mkdir -p "$R/fakecg/5555" && echo "0::/system.slice/docker-$FOREIGN_ID.scope" > "$R/fakecg/5555/cgroup"

cat > "$R/fakebin/sudo" <<'EOF'
#!/usr/bin/env bash
exec "$@"
EOF
cat > "$R/fakebin/nvidia-smi" <<EOF
#!/usr/bin/env bash
ST=$R/state
n=\$(( \$(cat \$ST/smi_calls 2>/dev/null || echo 0) + 1 )); echo \$n > \$ST/smi_calls
own_pid=\$(cat \$ST/container.pid 2>/dev/null || true)
alive=0; [[ -n \$own_pid ]] && kill -0 "\$own_pid" 2>/dev/null && alive=1
scenario=\$(cat \$ST/scenario)
case "\$*" in
  *--query-compute-apps*)
    (( n > 10 && n % 7 == 0 )) && exit 1
    echo "1240, 2859"
    [[ \$scenario == foreign ]] && echo "5555, 900"
    (( alive )) && echo "\$own_pid, 4100"
    ;;
  *memory.used,utilization.gpu*)
    (( n > 10 && n % 5 == 0 )) && exit 1
    echo "\$(( 2903 + alive * 4100 )), 21" ;;
  *--query-gpu=memory.used*)
    if [[ \$scenario == unlisted ]]; then echo 5200; else echo \$(( 2903 + alive * 4100 )); fi ;;
  *name,memory.total*)
    echo "name, memory.total [MiB], memory.used [MiB], utilization.gpu [%]"; echo "FAKE 4090, 24564 MiB, 2903 MiB, 21 %" ;;
  *) exit 2 ;;
esac
EOF
cat > "$R/fakebin/docker" <<EOF
#!/usr/bin/env bash
ST=$R/state
own_pid=\$(cat \$ST/container.pid 2>/dev/null || true)
alive=0; [[ -n \$own_pid ]] && kill -0 "\$own_pid" 2>/dev/null && alive=1
name=\$(cat \$ST/container.name 2>/dev/null || true)
case "\$1" in
  image) exit 0 ;;
  ps)
    fmt=\${*: -1}
    if [[ \$fmt == *ID* ]]; then echo "isaac-sim nvcr.io/nvidia/isaac-sim:5.1.0 Up 5 hours 16998b63e8dd"; (( alive )) && echo "\$name e01-walking-isaaclab:20260905 Up 1 second aaaaaaaaaaaa"
    else echo "isaac-sim"; (( alive )) && echo "\$name"; fi
    exit 0 ;;
  inspect)
    target=\${*: -1}
    [[ \$target == isaac-sim ]] && { echo $VENDOR_ID; exit 0; }
    [[ \$target == "\$name" ]] && (( alive )) && { echo $OWN_ID; exit 0; }
    exit 1 ;;
  kill)
    [[ \$2 == "\$name" ]] && (( alive )) && kill -TERM "\$own_pid" && echo killed >> \$ST/kills
    exit 0 ;;
  run)
    shift; out=; cname=
    while (( \$# )); do
      case "\$1" in --name) cname=\$2; shift ;; --output-dir) out=\$2; shift ;; esac; shift
    done
    echo "\$cname" > \$ST/container.name; echo \$\$ > \$ST/container.pid
    mkdir -p $R/fakecg/\$\$ && echo "0::/system.slice/docker-$OWN_ID.scope" > $R/fakecg/\$\$/cgroup
    host_out=\${out/\/workspace/$R}
    python3 - "\$host_out" <<'PY'
import hashlib, importlib.util, json, pathlib, sys, time
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
root = out.parents[2]
spec = importlib.util.spec_from_file_location('tsa', root / 'phase_d' / 'test_stage_audit.py')
tsa = importlib.util.module_from_spec(spec); spec.loader.exec_module(tsa)
result = tsa.fake_result()
result['thresholds_sha256'] = hashlib.sha256((root / 'phase_d' / 'stage_audit_thresholds_d1b.json').read_bytes()).hexdigest()
result['marks'] = []
for name in ('app_started', 'sim_reset_done', 'render_B_done'):
    time.sleep(3)
    result['marks'].append({'mark': name, 't_s': 0, 'unix_s': time.time(), 'device_used_mib': 7003})
text = json.dumps(result) + '\n'
(out / 'stage_audit_result.json').write_text(text)
(out / 'STAGE_AUDIT_COMPLETE').write_text(hashlib.sha256(text.encode()).hexdigest() + '\n')
print('fake audit record written', flush=True)
PY
    echo "fake Kit hangs in shutdown"
    exec sleep 600 ;;
esac
EOF
chmod +x "$R"/fakebin/*

run_scenario() {  # NAME EXPECTED_RC
  local name=$1 want=$2 rc
  echo "$name" > "$R/state/scenario"; rm -f "$R/state/container.pid" "$R/state/kills"
  ( cd "$R" && VLA_RUN_ROOT=$R VLA_CGROUP_ROOT=$R/fakecg VLA_AFTER_RECORD_GRACE_S=5 PATH=$R/fakebin:$PATH \
      bash scripts/phase_d1_run_stage_audit.sh "rehearsal_$name" > "driver_logs/rehearsal_$name.log" 2>&1 )
  rc=$?
  echo "scenario=$name driver_rc=$rc expected=$want"
  [[ $rc -eq $want ]] || { echo "REHEARSAL_FAILED $name"; tail -20 "$R/driver_logs/rehearsal_$name.log"; return 1; }
}

fail=0
run_scenario good 0 || fail=1
if [[ -d $R/runs/rehearsal_good ]]; then
  G=$R/runs/rehearsal_good
  grep -q "PHASE_D1B_AUDIT_DONE run=rehearsal_good .*complete=yes summary_rc=0" "$R/driver_logs/rehearsal_good.log" \
    && echo "good: done line with summary_rc=0" || { echo "good: done line wrong"; fail=1; }
  [[ -e $G/KILLED_AFTER_RECORD ]] && echo "good: hanging fake Kit stopped after the grace period" || { echo "good: no KILLED_AFTER_RECORD"; fail=1; }
  blanks=$(grep -c '^[0-9.]*,,,' "$G/samples.csv"); total=$(( $(wc -l < "$G/samples.csv") - 1 ))
  echo "good: samples $total, failed nvidia-smi samples $blanks (sampler survived)"
  (( total >= 8 && blanks >= 1 )) || { echo "good: sampler did not survive"; fail=1; }
  python3 - "$G/summary.json" <<'PY' || fail=1
import json, sys
s = json.load(open(sys.argv[1]))
g = s['gpu']
ok = g['isaac_peak_mib'] == 4100 and g['coverage_ok'] and g['own_container_id12'] == 'aaaaaaaaaaaa' and s['gate']['admit_to_d1c']
print('good: summary isaac_peak', g['isaac_peak_mib'], 'coverage_ok', g['coverage_ok'], 'vendor', g['vendor_mib_min_max'], 'admit', s['gate']['admit_to_d1c'])
sys.exit(0 if ok else 1)
PY
  diff <(awk '{print $1}' "$G/containers_before.txt") <(grep -v '^vla-phase-d-' "$G/containers_after.txt" | awk '{print $1}') > /dev/null \
    && echo "good: vendor container listed before and after" || { echo "good: container lists differ"; fail=1; }
fi
run_scenario foreign 75 || fail=1
[[ ! -d $R/runs/rehearsal_foreign ]] && echo "foreign: nothing created" || { echo "foreign: run dir created"; fail=1; }
run_scenario unlisted 75 || fail=1
[[ ! -d $R/runs/rehearsal_unlisted ]] && echo "unlisted: nothing created" || { echo "unlisted: run dir created"; fail=1; }
own=$(cat "$R/state/container.pid" 2>/dev/null || true)
leftover=$(pgrep -f "$R/fakebin" | grep -v "^$$\$" || true)
if [[ -n $own ]] && kill -0 "$own" 2>/dev/null; then leftover="$leftover fake-container:$own"; fi
[[ -z $leftover ]] && echo "no leftover rehearsal processes" || { echo "leftover: $leftover"; fail=1; }
echo "REHEARSAL_DIR=$R"
(( fail == 0 )) && echo "REHEARSAL_PASSED" || echo "REHEARSAL_FAILED"
exit $fail
