#!/usr/bin/env bash
# Build every deliverable from the timeline. Rendering is the slow part (about 1 frame/s on 4 cores).
#   tools/deliver.sh            render both formats, score, mux, phone copy, poster, styleframes
#   SKIP_RENDER=1 tools/deliver.sh   reuse out/*_video.mp4
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out
node tools/check-timeline.mjs | tail -1
node tools/export-cues.mjs > audio/cues.json
python3 audio/score.py audio/cues.json out/score.wav
if [ -z "${SKIP_RENDER:-}" ]; then
  node tools/render.mjs --w 1920 --h 1080 --sub 8 --workers 4 --out out/video_16x9.mp4
  node tools/render.mjs --w 1080 --h 1920 --sub 8 --workers 4 --out out/video_9x16.mp4
fi
mux() { ffmpeg -y -loglevel error -i "$1" -i out/score.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -ar 48000 -movflags +faststart -shortest "$2"; }
mux out/video_16x9.mp4 out/THE_OFFER_16x9_master.mp4
mux out/video_9x16.mp4 out/THE_OFFER_9x16.mp4
# phone copy: two-pass to a size budget (target 27 MB, under the 30 MB limit)
vb=$(( 27 * 8 * 1000 / 60 - 160 ))k
ffmpeg -y -loglevel error -i out/THE_OFFER_16x9_master.mp4 -c:v libx264 -preset slow -b:v $vb -pass 1 -passlogfile out/.p2 -an -f mp4 /dev/null
ffmpeg -y -loglevel error -i out/THE_OFFER_16x9_master.mp4 -c:v libx264 -preset slow -b:v $vb -maxrate 6M -bufsize 8M -pass 2 -passlogfile out/.p2 \
  -pix_fmt yuv420p -profile:v high -level 4.2 -c:a aac -b:a 160k -movflags +faststart out/THE_OFFER_16x9_phone.mp4
rm -f out/.p2*
# poster (scene 3, the grid) and styleframes, rendered lossless from the same timeline
node tools/render.mjs --stills 23.20 --ssub 16 --outdir out/.poster
mv out/.poster/still_023.20.png out/THE_OFFER_poster_16x9.png
node tools/render.mjs --w 1080 --h 1920 --stills 23.20 --ssub 16 --outdir out/.poster
mv out/.poster/still_023.20.png out/THE_OFFER_poster_9x16.png
rm -rf out/.poster
python3 tools/styleframes.py out/THE_OFFER_styleframes.png
ls -la out
