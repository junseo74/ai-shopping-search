import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import catalog from './catalog.mjs';
import {request,tag} from './net.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url));
const output=path.join(dir,'document_checks.json');
const prior=fs.existsSync(output)?JSON.parse(fs.readFileSync(output,'utf8')):[];
const cache=new Map(prior.map(r=>[r.url,r]));
const discovered=JSON.parse(fs.readFileSync(path.join(dir,'document_discovery.json'),'utf8'));
for(const d of discovered) if(d.http_status===200) cache.set(d.url,{url:d.url,http_status:d.http_status,observed_at:d.observed_at,verification:'prior_live_document_discovery',content_type:d.content_type,bytes:d.bytes});
const tasks=catalog.map(c=>({id:c.id,url:c.primary_url}));
const result=[];
for(let i=0;i<tasks.length;i+=3){
 const batch=await Promise.all(tasks.slice(i,i+3).map(async ({id,url})=>{
  if(cache.has(url)) return {...cache.get(url),id,reused:true};
  const row={id,url,observed_at:new Date().toISOString(),verification:'live_document_only'};
  try{
   const r=await request(url);Object.assign(row,{http_status:r.http_status,content_type:r.content_type,bytes:r.bytes,body_sha256:r.body_sha256,title:tag(r.text,'title').slice(0,120)});
   row.document_access=r.http_status===200?'http_ok_content_requires_review':([301,302,303,307,308].includes(r.http_status)?'redirect_not_followed':'http_error_stop');
   row.markers={product_search:/ProductSearch|상품 검색|상품검색|getItemList/.test(r.text),seller_context:/판매자|협력사|거래처/.test(r.text),login:/로그인|login/i.test(r.text),challenge:/captcha|access denied|비정상적인 접근/i.test(r.text)};
  }catch(e){row.error_code=e.cause?.code||e.name;}
  return row;
 }));
 result.push(...batch);for(const r of batch) console.log(JSON.stringify({id:r.id,http_status:r.http_status,error_code:r.error_code,reused:r.reused}));
}
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
