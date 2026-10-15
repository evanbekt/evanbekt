#!/usr/bin/env bash
# THE STILLNESS, PART 3 — TikTok cut only (1080x1920). About 2 h on 4 cores.
#   KATHLEEN=/path/to/en-us-kathleen-low.onnx tools/deliver.sh   (re-synthesize the narration)
#   SKIP_RENDER=1 tools/deliver.sh                                 (reuse out/video_9x16.mp4)
# Needs ../voicemail/audio/stems/l1.wav and l9.wav copied to audio/stems/p2_hi.wav, p2_whisper.wav.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out audio/stems
node tools/export-cues.mjs > audio/cues.json
if [ -n "${KATHLEEN:-}" ]; then python3 audio/voice.py audio/cues.json "$KATHLEEN"; fi
python3 audio/score.py audio/cues.json out/voice.wav out/score.wav
[ -n "${SKIP_RENDER:-}" ] || node tools/render.mjs --w 1080 --h 1920 --sub 8 --workers 4 --crf 17 --out out/video_9x16.mp4
ffmpeg -y -loglevel error -i out/video_9x16.mp4 -i out/score.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -ar 48000 -movflags +faststart -shortest out/THE_SEVEN_MINUTES_9x16_master.mp4
# TikTok upload copy: H.264, two-pass to a 27 MB budget, with sound
ffmpeg -y -loglevel error -i out/THE_SEVEN_MINUTES_9x16_master.mp4 -c:v libx264 -preset slow -b:v 3440k -pass 1 -passlogfile out/.x264 -an -f mp4 /dev/null
ffmpeg -y -loglevel error -i out/THE_SEVEN_MINUTES_9x16_master.mp4 -c:v libx264 -preset slow -b:v 3440k -maxrate 6M -bufsize 8M -pass 2 -passlogfile out/.x264 \
  -pix_fmt yuv420p -profile:v high -level 4.2 -c:a aac -b:a 160k -movflags +faststart out/THE_SEVEN_MINUTES_9x16_tiktok.mp4
rm -f out/.x264*
ls -la out
