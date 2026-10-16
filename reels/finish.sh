#!/bin/sh
# Wait for the three renders (PIDs in pids.txt), then mux each with its score.
cd "$(dirname "$0")"
while read r pid n; do
  while kill -0 "$pid" 2>/dev/null; do sleep 10; done
done < pids.txt
for r in wild him30 transfer; do
  n=$(awk -v r=$r '$1==r{print $3}' pids.txt)
  ffmpeg -y -loglevel error -i $r/out/seg_00000.mp4 -i $r/out/score.wav -map 0:v -map 1:a -frames:v $n \
    -c:v libx264 -preset medium -b:v 3600k -maxrate 5500k -bufsize 9000k -pix_fmt yuv420p -profile:v high \
    -c:a aac -b:a 192k -movflags +faststart -shortest $r/out/final.mp4
  echo "$r $(ffprobe -v error -show_entries format=duration -of csv=p=0 $r/out/final.mp4)s $(du -h $r/out/final.mp4 | cut -f1)"
done
