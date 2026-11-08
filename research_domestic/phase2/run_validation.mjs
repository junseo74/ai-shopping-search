import fs from 'node:fs';
import {collect,evidence,sources} from './collector.mjs';
const selected=process.argv.find(a=>a.startsWith('--source='))?.slice(9);
if(selected&&!sources.includes(selected)){console.log(JSON.stringify({status:'unsupported_source'}));process.exitCode=1;}
else{
 const results=[];
 for(const source of selected?[selected]:sources){
  // This does not submit an approval. Set only after the provider authorizes the stated purpose.
  const r=evidence(await collect(source,{purposeApproved:process.env.DOMESTIC_DOME_PURPOSE_APPROVED==='true'}));
  results.push(r);console.log(JSON.stringify(r));
 }
 const file=new URL('./live_results.json',import.meta.url);
 const previous=fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):[];
 fs.writeFileSync(file,JSON.stringify([...previous.filter(p=>!results.some(r=>r.source===p.source)),...results],null,2)+'\n');
}
