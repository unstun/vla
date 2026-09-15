set -euo pipefail
D=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
RUNS=$D/public_scenes/runs
ENV=$D/official_r2r/official_env
KEEP=$D/official_r2r/official_env_024
REF=/home/ubuntu/vla-runs/2026-09-11_lite3_isaac_v12_vla/tools/local_ablation_runs_sha256.txt
for p in "$RUNS" "$ENV" "$KEEP"; do [[ -d $p && ! -L $p ]] || { echo "refusing: $p is not a plain directory"; exit 1; }; done
ls -d "$ENV"/lib/python3.9/site-packages/habitat_lab-0.3.3.dist-info > /dev/null || { echo "refusing: $ENV is not the habitat-lab 0.3.3 env"; exit 1; }
if pgrep -f "$ENV/bin/" > /dev/null; then echo "refusing: a process is using $ENV"; exit 1; fi
if pgrep -f "public_scenes/runs" > /dev/null; then echo "refusing: a process references public_scenes/runs"; exit 1; fi
echo "## df_before"; df -Pk / | tail -1
echo "## verify remote ablation runs against local hashes"
( cd "$RUNS" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) > /home/ubuntu/vla-runs/2026-09-11_lite3_isaac_v12_vla/tools/remote_ablation_runs_sha256.txt
awk 'NR==FNR {ref[$2]=$1; next} { total++; if (!($2 in ref)) {missing++; print "NOT LOCAL: " $2} else if (ref[$2] != $1) {diff++; print "HASH DIFF: " $2} } END {printf "remote files %d, not local %d, hash differs %d\n", total, missing+0, diff+0; exit (missing+diff > 0)}' "$REF" /home/ubuntu/vla-runs/2026-09-11_lite3_isaac_v12_vla/tools/remote_ablation_runs_sha256.txt
echo "## sizes"; du -sh "$RUNS"; echo "official_env unique: $(du -sh "$KEEP" "$D/sim_env" "$D/mamba/pkgs" "$ENV" | tail -1 | cut -f1)"; find "$RUNS" -type f | wc -l
rm -rf --one-file-system "$RUNS"
rm -rf --one-file-system "$ENV"
echo "## after_checks"
[[ -e $RUNS ]] && echo "runs still present" || echo "public_scenes/runs removed"
[[ -e $ENV ]] && echo "official_env still present" || echo "official_env removed"
"$KEEP/bin/python" -c "import habitat, habitat_sim, torch, transformers; print('official_env_024 ok', habitat.__version__, habitat_sim.__version__, torch.__version__, transformers.__version__)" 2>&1 | tail -1
echo "## df_after"; df -Pk / | tail -1; df -h / | tail -1
