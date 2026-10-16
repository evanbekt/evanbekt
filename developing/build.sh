#!/usr/bin/env bash
# DEVELOPING — build all six parts at once (~10-15 min on 4 cores).
#   KATHLEEN=/path/to/en-us-kathleen-low.onnx ./build.sh    (also re-synthesize the voices)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out audio/stems
if [ -n "${KATHLEEN:-}" ]; then python3 audio/voice.py "$KATHLEEN"; fi
for p in 1 2 3 4 5 6; do python3 audio/score.py $p & done; wait
for p in 1 2 3 4 5 6; do python3 src/render.py $p out/video$p.mp4 > out/render$p.log 2>&1 & done; wait
for p in 1 2 3 4 5 6; do
  ffmpeg -y -loglevel error -i out/video$p.mp4 -i out/score$p.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 \
    -movflags +faststart -shortest "out/DEVELOPING_PART${p}.mp4"
done
ls -la out/DEVELOPING_PART*.mp4
