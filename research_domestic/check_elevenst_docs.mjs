import fs from 'node:fs';
import {request,strip,tag} from './net.mjs';
const pages=['OpenApiServiceIntroduce.tmall','OpenApiSearch.tmall','OpenApiGuide.tmall','OpenApiFrontMain.tmall'];
const output=[];
for(const page of pages){
 const url='https://openapi.11st.co.kr/openapi/'+page;
 const row={url,observed_at:new Date().toISOString()};
 try{
  const r=await request(url);Object.assign(row,{http_status:r.http_status,body_sha256:r.body_sha256,title:tag(r.text,'title'),bytes:r.bytes});
  row.search_documented=/ProductSearch/.test(r.text);
  row.search_links=[...new Set([...r.text.matchAll(/href=["']([^"']+)["']/gi)].map(m=>m[1]).filter(s=>/Search|search|약관|Guide|Register/.test(s)))].slice(0,15);
  const t=strip(r.text.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,''));
  const k=t.search(/ProductSearch|상품검색 API|상품검색/);
  row.search_context=k>=0?t.slice(Math.max(0,k-30),k+260):null;
 }catch(e){row.error_code=e.cause?.code||e.name;}
 output.push(row);console.log(JSON.stringify(row));
}
fs.writeFileSync(new URL('./elevenst_document_checks.json',import.meta.url),JSON.stringify(output,null,2)+'\n');
