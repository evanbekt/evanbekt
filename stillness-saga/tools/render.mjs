// Headless render controller: Chrome renders, we pull RGB in <=1 MB slices and pipe to ffmpeg.
//   node tools/render.mjs --w 1920 --h 1080 --sub 8 --workers 4 --out out/video_16x9.mp4
//   node tools/render.mjs --stills 3.2,14,25 --w 1920 --h 1080 --outdir review/stills
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const A = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, arr) => (v.startsWith('--') ? [...acc, [v.slice(2), arr[i + 1]]] : acc), []));
const W = +(A.w || 1920), H = +(A.h || 1080), SUB = +(A.sub || 8);
const FPS = 60, N = +(A.frames || 3600);
const FROM = +(A.from || 0), TO = +(A.to || N);
const WORKERS = +(A.workers || 4);

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.ttf': 'font/ttf' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const URL_ = `http://127.0.0.1:${server.address().port}/src/index.html?w=${W}&h=${H}&sub=${SUB}&part=${A.part || 4}`;

async function openPage() {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: Math.min(W, 1920), height: Math.min(H, 1920) } });
  page.on('pageerror', (e) => console.error('pageerror', e));
  page.on('console', (m) => { if (m.type() === 'error') console.error('console', m.text()); });
  await page.goto(URL_);
  await page.waitForFunction(() => window.READY || window.ERROR, null, { timeout: 60000 });
  const err = await page.evaluate(() => window.ERROR);
  if (err) throw new Error(err);
  const slices = await page.evaluate(() => window.sliceCount);
  return { browser, page, slices };
}

async function pull(page, slices, sink) {
  for (let k = 0; k < slices; k++) {
    const b64 = await page.evaluate((i) => window.getSlice(i), k);
    if (b64.length > 1_000_000) throw new Error(`slice ${k} too large: ${b64.length}`);
    const buf = Buffer.from(b64, 'base64');
    if (!sink.write(buf)) await new Promise((r) => sink.once('drain', r));
  }
}

function ffmpegRaw(args) {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', `${W}x${H}`, '-r', String(FPS), '-i', '-', ...args], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  return { ff, done };
}

if (A.stills) {
  const outdir = path.resolve(A.outdir || 'review/stills');
  fs.mkdirSync(outdir, { recursive: true });
  const { browser, page, slices } = await openPage();
  for (const ts of A.stills.split(',')) {
    const t = +ts;
    await page.evaluate(([tt, s]) => window.renderStill(tt, s), [t, +(A.ssub || 4)]);
    const { ff, done } = ffmpegRaw(['-frames:v', '1', path.join(outdir, `still_${t.toFixed(2).padStart(6, '0')}.png`)]);
    await pull(page, slices, ff.stdin);
    ff.stdin.end();
    await done;
  }
  await browser.close();
  server.close();
  process.exit(0);
}

// Video: split the frame range across workers, one encoded segment each, then concat.
const out = path.resolve(A.out || 'out/video.mp4');
const segDir = out + '.segs';
fs.mkdirSync(segDir, { recursive: true });
const crf = A.crf || '14';
const per = Math.ceil((TO - FROM) / WORKERS);
const t0 = Date.now();
let doneFrames = 0;
async function worker(wi) {
  const a = FROM + wi * per, e = Math.min(TO, a + per);
  if (a >= e) return null;
  const seg = path.join(segDir, `seg_${String(wi).padStart(2, '0')}.mp4`);
  const { browser, page, slices } = await openPage();
  const { ff, done } = ffmpegRaw(['-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-pix_fmt', 'yuv420p', '-profile:v', 'high',
    '-x264-params', 'keyint=120:min-keyint=120:scenecut=0', '-tune', 'grain', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', seg]);
  for (let f = a; f < e; f++) {
    await page.evaluate((fr) => window.renderFrame(fr), f);
    await pull(page, slices, ff.stdin);
    doneFrames++;
    if (doneFrames % 60 === 0) {
      const el = (Date.now() - t0) / 1000;
      console.log(`${doneFrames}/${TO - FROM} frames  ${el.toFixed(0)}s  eta ${((TO - FROM - doneFrames) * el / doneFrames).toFixed(0)}s`);
    }
  }
  ff.stdin.end();
  await done;
  await browser.close();
  return seg;
}
const segs = (await Promise.all(Array.from({ length: WORKERS }, (_, i) => worker(i)))).filter(Boolean);
fs.writeFileSync(path.join(segDir, 'list.txt'), segs.map((s) => `file '${s}'`).join('\n'));
await new Promise((res, rej) => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(segDir, 'list.txt'), '-c', 'copy', '-movflags', '+faststart', out], { stdio: 'inherit' })
  .on('close', (c) => (c === 0 ? res() : rej(new Error('concat failed')))));
console.log(`done ${out} in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
server.close();
