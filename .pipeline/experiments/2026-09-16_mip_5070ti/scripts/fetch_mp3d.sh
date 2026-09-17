#!/usr/bin/env bash
# Dr Sun confirmed MP3D access for this reproduction on 2026-09-16.
set -euo pipefail
task_root=${1:?usage: fetch_mp3d.sh REMOTE_ROOT}
source_root="$task_root/source/AgentCanvas"
setup="$task_root/setup"
data_root="$source_root/data/habitat/scene_datasets"
mkdir -p "$setup" "$data_root"
exec 9>"$setup/mp3d_download.lock"
flock -n 9 || { echo 'Another MP3D acquisition is active'; exit 73; }
test -f "$task_root/configs/MP3D_AUTHORIZED.txt"
test "$(git -C "$source_root" rev-parse HEAD)" = b2b363af80a010ea9f73a0be9d49bc75555efdef
trap 'rc=$?; printf "%s\n" "$rc" > "$setup/mp3d_download.exit"' EXIT
date -u +%FT%TZ > "$setup/mp3d_download.started"
url=https://kaldir.vc.in.tum.de/matterport/v1/tasks/mp3d_habitat.zip
archive="$data_root/mp3d_habitat.zip"
printf '%s\n' "$url" > "$setup/mp3d_download.url"
if [[ ! -f "$setup/mp3d_extracted.ok" ]]; then
  if [[ ! -f "$archive" ]]; then
    wget --continue --timeout=45 --tries=5 --progress=dot:giga "$url" -O "$archive.part"
    unzip -tq "$archive.part"
    mv "$archive.part" "$archive"
  fi
  sha256sum "$archive" > "$setup/mp3d_archive.sha256"
  unzip -q -n "$archive" -d "$data_root"
  test "$(find "$data_root/mp3d" -name '*.glb' -type f | wc -l)" -gt 0
  (cd "$data_root"; find mp3d -type f -print0 | sort -z | xargs -0 sha256sum) > "$setup/mp3d_files.sha256"
  date -u +%FT%TZ > "$setup/mp3d_extracted.ok"
fi
mkdir -p "$source_root/data/scene_datasets"
if [[ ! -e "$source_root/data/scene_datasets/mp3d" ]]; then
  ln -s ../habitat/scene_datasets/mp3d "$source_root/data/scene_datasets/mp3d"
fi
date -u +%FT%TZ > "$setup/mp3d_download.finished"
