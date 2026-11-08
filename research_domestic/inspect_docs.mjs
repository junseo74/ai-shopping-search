// Read-only official documentation discovery; never fetches discovered product links.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
const urls=[
 'https://www.yes24.com/rss/bestSeller.aspx',
 'https://www.aladin.co.kr/rsscenter/best.aspx',
 'https://developers.yes24.com/docs',
 'https://openapi.11st.co.kr/openapi/OpenApiServiceIntroduce.tmall',
 'https://openapi.domeggook.com/ko',
];
const results=[];
for(const url of urls){
 const r={url,observed_at:new Date().toISOString()};
 try{
  const res=await fetch(url,{signal:AbortSignal.timeout(15000),redirect:'error',headers:{'User-Agent':'DomesticSourceResearch/1.0 (documentation verification)'}});
  r.http_status=res.status;
  const body=await res.text();
  r.content_type=res.headers.get('content-type');
  r.bytes=Buffer.byteLength(body);
  r.feed_links=[...new Set([...body.matchAll(/(?:https?:\/\/[^\s"'<>]+|(?:href|value)=["'][^"']+)/g)].map(m=>m[0]).filter(x=>/rss|feed/i.test(x)))].slice(-40);
  r.doc_links=[...new Set([...body.matchAll(/href=["']([^"']+)/g)].map(m=>m[1]).filter(x=>/api|doc|term|policy|guide/i.test(x)))].slice(0,25);
 }catch(e){r.error_code=e.cause?.code||e.name;}
 results.push(r);console.log(JSON.stringify(r));
}
fs.writeFileSync(path.join(dir,'document_discovery.json'),JSON.stringify(results,null,2)+'\n');
