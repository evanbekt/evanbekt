#!/bin/sh
# THE TALL ONE — voices and timeline, score, picture, then the phone master (H.264, under 30 MB).
set -e
cd "$(dirname "$0")"
mkdir -p out audio/stems
python3 audio/voice.py
python3 audio/score.py
N=$(python3 -c "import json,math;print(math.ceil(json.load(open('out/timeline.json'))['total']*30))")
Q=$(( (N + 3) / 4 ))
for i in 0 1 2 3; do a=$((i * Q)); b=$(( (i + 1) * Q < N ? (i + 1) * Q : N )); python3 src/render.py seg $a $b & done
wait
ls out/seg_*.mp4 | sort | sed "s|out/\(.*\)|file '\1'|" > out/segs.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i out/segs.txt -i out/score.wav -map 0:v -map 1:a -frames:v "$N" \
  -c:v libx264 -preset slow -b:v 3200k -maxrate 5000k -bufsize 8000k -pix_fmt yuv420p -profile:v high \
  -c:a aac -b:a 192k -movflags +faststart -shortest out/THE_TALL_ONE.mp4
ls -la out/THE_TALL_ONE.mp4
