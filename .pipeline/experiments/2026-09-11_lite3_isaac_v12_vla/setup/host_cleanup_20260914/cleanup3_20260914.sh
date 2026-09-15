set -euo pipefail
# Approved by Dr Sun 2026-09-14: delete the NavDP runtime (8.7 GB) on rented4090. Nothing else.
NAVDP=/home/ubuntu/sun/vla_exec/2026-09-10_x_navdp_lite3_rented4090
R=$NAVDP/runtime
[[ -d $R && ! -L $R ]] || { echo "refusing: $R is not a plain directory"; exit 1; }
[[ -d $R/py311/conda-meta && -d $R/mamba && -d $R/mpc_codegen ]] || { echo "refusing: $R does not look like the NavDP runtime"; exit 1; }
extra=$(find "$R" -mindepth 1 -maxdepth 1 ! -name py311 ! -name mamba ! -name mpc_codegen | wc -l)
[[ $extra -eq 0 ]] || { echo "refusing: unexpected entries in $R"; find "$R" -mindepth 1 -maxdepth 1; exit 1; }
if [[ $(findmnt -rn -o TARGET | { grep -cF "$R" || true; }) -gt 0 ]]; then echo "refusing: a mount point is inside $R"; exit 1; fi
if pgrep -f "x_navdp_lite3_rented4090" > /dev/null; then echo "refusing: a process references the NavDP tree"; exit 1; fi
links=$(find /home/ubuntu/sun/vla_exec /home/ubuntu/vla-runs -xdev -type l -lname "*x_navdp_lite3_rented4090/runtime*" 2>/dev/null | { grep -v "^$R/" || true; } | wc -l)
[[ $links -eq 0 ]] || { echo "refusing: symlinks outside $R point into it"; exit 1; }
echo "## df_before"; df -Pk / | tail -1
echo "## sizes"; du -xsh "$R"/* "$R"
echo "## rebuild provenance: python and conda packages"
"$R/py311/bin/python" -VV
"$R/py311/bin/python" -m pip list --format=freeze 2>/dev/null
ls "$R/py311/conda-meta" | grep '\.json$' | sed 's/\.json$//'
echo "## rebuild provenance: generated acados solver sources"
( cd "$R/mpc_codegen" && find . -type f -print0 | sort -z | xargs -0 sha256sum )
rm -rf --one-file-system "$R"
echo "## after_checks"
[[ -e $R ]] && echo "runtime still present" || echo "NavDP runtime removed"
ls "$NAVDP"
echo "## other environments still import"
/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/official_r2r/official_env_024/bin/python -c "import habitat, torch, transformers, sys; sys.path.insert(0, '/home/ubuntu/vla-runs/2026-09-11_lite3_isaac_v12_vla/pydeps'); import casadi; print('official_env_024 ok', torch.__version__, transformers.__version__, 'casadi', casadi.__version__)" 2>&1 | tail -1
echo "## df_after"; df -Pk / | tail -1; df -h / | tail -1
