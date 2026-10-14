// Export the cue list the score is built from: node tools/export-cues.mjs > audio/cues.json
import { cueList } from '../src/timeline.js';
process.stdout.write(JSON.stringify(cueList(), null, 1));
