// Reads the SPEECH block from index.html and lists every line to record.
import {readFileSync,writeFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=join(dirname(fileURLToPath(import.meta.url)),'..');
const html=readFileSync(join(root,'index.html'),'utf8');
const a=html.indexOf('/*SPEECH-START*/'),b=html.indexOf('/*SPEECH-END*/');
if(a<0||b<0)throw new Error('SPEECH markers not found');
const block=html.slice(a+16,b);
const {LEVELS,levelPhrases,globalPhrases,clipKey,speakable,clipText}=new Function(block+"; return {LEVELS,levelPhrases,globalPhrases,clipKey,speakable,clipText};")();
const all=[...globalPhrases(),...LEVELS.flatMap((_,i)=>levelPhrases(i))];
const seen=new Map();
for(const {t,v} of all){const key=clipKey(t,v);if(!seen.has(key))seen.set(key,{key,text:speakable(t),raw:clipText(t),v})}
writeFileSync(join(root,'tools','jobs.json'),JSON.stringify([...seen.values()],null,1));
console.log(`${seen.size} clips`);
