set -euo pipefail
PIPC=/home/ubuntu/sun/vla_exec/2026-09-10_x_navdp_lite3_rented4090/runtime/pip_cache
PKGS=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/mamba/pkgs
for p in "$PIPC" "$PKGS" "$PKGS/cache"; do [[ -d $p && ! -L $p ]] || { echo "refusing: $p is not a plain directory"; exit 1; }; done
[[ -d $PIPC/http-v2 ]] || { echo "refusing: $PIPC does not look like a pip cache"; exit 1; }
for name in pip pip3 mamba micromamba conda; do
  if pgrep -x "$name" > /dev/null; then echo "refusing: $name is running"; exit 1; fi
done
echo "## df_before"; df -Pk / | tail -1
echo "## pip_cache files bytes"; find "$PIPC" -type f -printf "%s\n" | awk '{s+=$1} END {print NR, s}'
echo "## pkgs_index_cache files bytes"; find "$PKGS/cache" -type f -printf "%s\n" | awk '{s+=$1} END {print NR, s}'
echo "## pkgs_tarballs size name links"; find "$PKGS" -maxdepth 1 -type f \( -name "*.conda" -o -name "*.tar.bz2" \) -printf "%s\t%f\t%n\n" | sort -k2
rm -rf --one-file-system "$PIPC"
rm -rf --one-file-system "$PKGS/cache"
find "$PKGS" -maxdepth 1 -type f \( -name "*.conda" -o -name "*.tar.bz2" \) -delete
echo "## after_checks"
[[ -e $PIPC ]] && echo "pip_cache still present" || echo "pip_cache removed"
[[ -e $PKGS/cache ]] && echo "index cache still present" || echo "index cache removed"
echo "tarballs left: $(find "$PKGS" -maxdepth 1 -type f \( -name "*.conda" -o -name "*.tar.bz2" \) | wc -l)"
echo "## env_sanity"
/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/official_r2r/official_env_024/bin/python -c "import habitat, habitat_sim; print('official_env_024 ok', habitat.__version__, habitat_sim.__version__)" 2>&1 | tail -1 || true
/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/sim_env/bin/python -c "import habitat_sim; print('sim_env ok', habitat_sim.__version__)" 2>&1 | tail -1 || true
/home/ubuntu/sun/vla_exec/2026-09-10_x_navdp_lite3_rented4090/runtime/py311/bin/python -c "import torch; print('navdp py311 ok', torch.__version__)" 2>&1 | tail -1 || true
echo "## df_after"; df -Pk / | tail -1; df -h / | tail -1
