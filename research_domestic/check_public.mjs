import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {request} from './net.mjs';
import {parseFeed} from './rss.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url));
const feeds=[['yes24','https://www.yes24.com/_par_/Rss/KBO001.xml'],['aladin','https://www.aladin.co.kr/rss/new_all/351']];
const selected=process.argv.find(a=>a.startsWith('--source='))?.slice(9);
if(selected&&!feeds.some(([id])=>id===selected))throw new Error('unknown_source');
const results=[];
for(const [id,url] of feeds.filter(([id])=>!selected||id===selected)){
 const row={id,url,observed_at:new Date().toISOString(),transport:'live_https',request_count:1};
 try{
  const r=await request(url);Object.assign(row,{http_status:r.http_status,content_type:r.content_type,bytes:r.bytes,body_sha256:r.body_sha256});
  if(r.http_status===200)Object.assign(row,parseFeed(id,r.text,row.observed_at));
  else row.reason='http_error_stop';
 }catch(e){row.error_code=e.cause?.code||e.name;}
 results.push(row);console.log(JSON.stringify(row));
}
const output=path.join(dir,'public_verification.json');
const prior=fs.existsSync(output)?JSON.parse(fs.readFileSync(output,'utf8')):[];
fs.writeFileSync(output,JSON.stringify([...prior.filter(r=>!results.some(x=>x.id===r.id)),...results],null,2)+'\n');
