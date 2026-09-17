#!/usr/bin/env bash
set -euo pipefail
root=${1:?usage: install_deepseek.sh REMOTE_ROOT}
mkdir -p "$root/tools" "$root/setup" "$root/dsh_home"
exec 9>"$root/setup/deepseek_install.lock"
flock -n 9 || exit 73
trap 'rc=$?; printf "%s\n" "$rc" > "$root/setup/deepseek_install.exit"' EXIT
readarray -t pin < <(python3 - "$root/setup/node_runtime_pin.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
for key in ['version','filename','sha256','url']: print(x[key])
PY
)
archive="$root/tools/${pin[1]}"
node_root="$root/tools/node-${pin[0]}-linux-x64"
if [[ ! -x "$node_root/bin/node" ]]; then
  curl --fail --location --retry 3 --connect-timeout 20 "${pin[3]}" -o "$archive.part"
  printf '%s  %s\n' "${pin[2]}" "$archive.part" | sha256sum -c -
  mv "$archive.part" "$archive"
  tar -xJf "$archive" -C "$root/tools"
fi
export PATH="$node_root/bin:$PATH"
export npm_config_cache="$root/tools/npm_cache"
export DSH_HOME="$root/dsh_home"
export DSH_TELEMETRY_DISABLED=1
node --version
mkdir -p "$root/tools/deepseek_harness"
cp "$root/configs/dsh-package.json" "$root/tools/deepseek_harness/package.json"
if [[ -f "$root/setup/dsh_package_lock.json" ]]; then
  cp "$root/setup/dsh_package_lock.json" "$root/tools/deepseek_harness/package-lock.json"
  npm ci --prefix "$root/tools/deepseek_harness" --no-audit --no-fund
else
  npm install --prefix "$root/tools/deepseek_harness" --save-exact --no-audit --no-fund @deepseek-ai/dsh@0.1.5-rc.1
fi
dsh="$root/tools/deepseek_harness/node_modules/.bin/dsh"
"$dsh" --help > "$root/setup/dsh_help.txt"
"$dsh" --profile headless --dump-default-config > "$root/setup/dsh_default_config.yaml"
cp "$root/tools/deepseek_harness/package-lock.json" "$root/setup/dsh_package_lock.json"
date -u +%FT%TZ > "$root/setup/deepseek_installed"
