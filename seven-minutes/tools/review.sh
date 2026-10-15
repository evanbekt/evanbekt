#!/usr/bin/env bash
# Contact sheet pulled from an actual encode: tools/review.sh out/file.mp4 sheet.jpg "t1 t2 ..." [cols] [thumbW]
set -euo pipefail
src=$1; sheet=$2; times=$3; cols=${4:-6}; tw=${5:-320}
d=$(mktemp -d)
for t in $times; do ffmpeg -loglevel error -ss "$t" -i "$src" -frames:v 1 "$d/f_$(printf '%06.2f' "$t").png"; done
python3 "$(dirname "$0")/contact.py" "$sheet" "$cols" "$tw" "$d"/f_*.png
rm -rf "$d"
