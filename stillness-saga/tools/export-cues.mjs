// node tools/export-cues.mjs 4 > audio/cues4.json
import { make } from '../src/timelines.js';
process.stdout.write(JSON.stringify(make(+process.argv[2]).cueList(), null, 1));
