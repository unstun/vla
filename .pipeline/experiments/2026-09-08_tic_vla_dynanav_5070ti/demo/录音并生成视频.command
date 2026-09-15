#!/bin/zsh
set -u
demo_dir="${0:A:h}"
"$demo_dir/.venv/bin/python" "$demo_dir/scripts/voice_to_video.py"
printf '\n按回车关闭窗口。'
read -r
