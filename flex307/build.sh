#!/bin/sh
# 307: OCCUPIED — voice, score, picture, then the TikTok master (H.264, under 30 MB).
set -e
cd "$(dirname "$0")"
VOICE=${VOICE:-/tmp/claude-0/voices/kathleen/en-us-kathleen-low.onnx}
python3 src/segment.py assets/source.jpg assets/m && python3 src/mask.py
python3 audio/voice.py "$VOICE"
python3 audio/score.py
for a in 0 450 900 1350; do python3 src/render.py seg $a $((a + 450)) & done
wait
printf "file 'seg_%05d.mp4'\n" 0 450 900 1350 > out/segs.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i out/segs.txt -i out/score.wav -map 0:v -map 1:a -frames:v 1800 \
  -c:v libx264 -preset slow -b:v 3400k -maxrate 5000k -bufsize 8000k -pix_fmt yuv420p -profile:v high \
  -c:a aac -b:a 192k -movflags +faststart -shortest out/307_OCCUPIED_tiktok.mp4
ls -la out/307_OCCUPIED_tiktok.mp4
