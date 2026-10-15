#!/usr/bin/env bash
# THE STILLNESS, PARTS 4-6 — TikTok cuts (1080x1920), rendered one after another (~1 h 50 min each on 4 cores).
#   PARTS="4 5 6" tools/deliver.sh
#   KATHLEEN=/path/to/en-us-kathleen-low.onnx tools/deliver.sh    (re-synthesize the voices)
# Needs Part 2's stems in audio/stems/p2_*.wav (copied from ../voicemail/audio/stems/).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out audio/stems
for p in ${PARTS:-4 5 6}; do
  node tools/export-cues.mjs $p > audio/cues$p.json
  if [ -n "${KATHLEEN:-}" ]; then python3 audio/voice.py $p audio/cues$p.json "$KATHLEEN"; fi
  python3 audio/score.py $p audio/cues$p.json out/voice$p.wav out/score$p.wav
  node tools/render.mjs --part $p --w 1080 --h 1920 --sub 8 --workers 4 --crf 17 --out out/video$p.mp4
  ffmpeg -y -loglevel error -i out/video$p.mp4 -i out/score$p.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -ar 48000 -movflags +faststart -shortest out/THE_STILLNESS_PART${p}_master.mp4
  ffmpeg -y -loglevel error -i out/THE_STILLNESS_PART${p}_master.mp4 -c:v libx264 -preset slow -b:v 3440k -pass 1 -passlogfile out/.x264_$p -an -f mp4 /dev/null
  ffmpeg -y -loglevel error -i out/THE_STILLNESS_PART${p}_master.mp4 -c:v libx264 -preset slow -b:v 3440k -maxrate 6M -bufsize 8M -pass 2 -passlogfile out/.x264_$p \
    -pix_fmt yuv420p -profile:v high -level 4.2 -c:a aac -b:a 160k -movflags +faststart out/THE_STILLNESS_PART${p}_tiktok.mp4
  rm -f out/.x264_$p*
  echo "PART $p READY"
done
