#!/usr/bin/env bash
# Build every deliverable. Rendering is the slow part (about an hour per format on 4 cores).
#   KATHLEEN=/path/to/en-us-kathleen-low.onnx tools/deliver.sh
#   SKIP_RENDER=1 tools/deliver.sh       reuse out/video_*.mp4
#   FORMATS="9x16 16x9" tools/deliver.sh  both formats (default: 9x16 only, the TikTok cut)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out audio/stems
node tools/export-cues.mjs > audio/cues.json
if [ -n "${KATHLEEN:-}" ]; then python3 audio/voice.py audio/cues.json "$KATHLEEN"; fi
python3 audio/score.py audio/cues.json out/voice.wav out/score.wav
if [ -z "${SKIP_RENDER:-}" ]; then
  for f in ${FORMATS:-9x16}; do
    if [ "$f" = 9x16 ]; then wh="--w 1080 --h 1920"; else wh="--w 1920 --h 1080"; fi
    node tools/render.mjs $wh --sub 8 --workers 4 --crf 17 --out out/video_$f.mp4
  done
fi
for f in ${FORMATS:-9x16}; do
  ffmpeg -y -loglevel error -i out/video_$f.mp4 -i out/score.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -ar 48000 -movflags +faststart -shortest out/ONE_NEW_VOICEMAIL_${f}_master.mp4
  # full 1080p60 HEVC under 30 MB (iPhone/Mac/modern Android), and H.264 under 30 MB (plays and uploads anywhere)
  ffmpeg -y -loglevel error -i out/ONE_NEW_VOICEMAIL_${f}_master.mp4 -c:v libx265 -preset medium -b:v 3550k -x265-params pass=1:stats=out/.x265_$f.log:log-level=error -an -f mp4 /dev/null
  ffmpeg -y -loglevel error -i out/ONE_NEW_VOICEMAIL_${f}_master.mp4 -c:v libx265 -preset medium -b:v 3550k -x265-params pass=2:stats=out/.x265_$f.log:vbv-maxrate=8000:vbv-bufsize=12000:log-level=error \
    -pix_fmt yuv420p -tag:v hvc1 -c:a aac -b:a 256k -movflags +faststart out/ONE_NEW_VOICEMAIL_${f}_hevc.mp4
  ffmpeg -y -loglevel error -i out/ONE_NEW_VOICEMAIL_${f}_master.mp4 -c:v libx264 -preset slow -b:v 3440k -pass 1 -passlogfile out/.x264_$f -an -f mp4 /dev/null
  ffmpeg -y -loglevel error -i out/ONE_NEW_VOICEMAIL_${f}_master.mp4 -c:v libx264 -preset slow -b:v 3440k -maxrate 6M -bufsize 8M -pass 2 -passlogfile out/.x264_$f \
    -pix_fmt yuv420p -profile:v high -level 4.2 -c:a aac -b:a 160k -movflags +faststart out/ONE_NEW_VOICEMAIL_${f}_h264.mp4
done
rm -f out/.x26*
ls -la out
