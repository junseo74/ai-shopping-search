// Diagnostic GETs only. No .env loading, seller mutations, pagination, or retries.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {request,tag,proof} from './net.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url));
const definitions=[
 {id:'yes24',env:'YES24_API_KEY',host:['yes24.com'],url:()=>new URL('https://apis.yes24.com/v1/goods/itemList?query='+encodeURIComponent('컴퓨터')+'&page=1&pageSize=3&detail=N'),headers:k=>({'X-Api-Key':k}),parse:t=>{const j=JSON.parse(t);return (j.success===true?j.data?.items:[])?.map(p=>[p.title,p.salePrice,p.link])||[];}},
 {id:'aladin',env:'ALADIN_TTB_KEY',host:['aladin.co.kr'],url:k=>{const u=new URL('https://www.aladin.co.kr/ttb/api/ItemSearch.aspx');for(const [n,v] of Object.entries({TTBKey:k,Query:'컴퓨터',QueryType:'Keyword',MaxResults:'3',start:'1',SearchTarget:'Book',output:'js',Version:'20131101'}))u.searchParams.set(n,v);return u;},parse:t=>(JSON.parse(t).item||[]).map(p=>[p.title,p.priceSales,p.link])},
 {id:'elevenst',env:'ELEVENST_API_KEY',host:['11st.co.kr'],url:k=>{const u=new URL('https://openapi.11st.co.kr/openapi/OpenApiService.tmall');for(const [n,v] of Object.entries({key:k,apiCode:'ProductSearch',keyword:'키보드',pageNum:'1',pageSize:'3'}))u.searchParams.set(n,v);return u;},parse:t=>[...t.matchAll(/<Product>([\s\S]*?)<\/Product>/g)].map(m=>[tag(m[1],'ProductName'),tag(m[1],'ProductPrice'),tag(m[1],'DetailPageUrl')])},
 ...[['domeggook','dome'],['domeme','supply']].map(([id,market])=>({id,env:'DOMEGGOOK_API_KEY',host:['domeggook.com','domeme.com'],url:k=>{const u=new URL('https://www.domeggook.com/ssl/api/');for(const [n,v] of Object.entries({ver:'4.1',mode:'getItemList',aid:k,market,om:'json',kw:'마스크',sz:'3',pg:'1'}))u.searchParams.set(n,v);return u;},parse:t=>{const j=JSON.parse(t);const items=j.domeggook?.list?.item||[];return (Array.isArray(items)?items:[items]).map(p=>[p.title,p.price,p.url]);}})),
];
const selected=process.argv.find(a=>a.startsWith('--source='))?.slice(9);
if(selected&&!definitions.some(d=>d.id===selected)) throw new Error('unknown_source');
const results=[];
for(const d of definitions.filter(d=>!selected||d.id===selected)){
 const row={id:d.id,observed_at:new Date().toISOString(),credential_env:d.env,credential_present:!!process.env[d.env],request_count:0};
 if(!row.credential_present){row.status='인증 대기';row.reason='missing_environment_credential';}
 else {
  try{
   row.request_count=1;const r=await request(d.url(process.env[d.env]),d.headers?.(process.env[d.env])||{});
   row.http_status=r.http_status;row.response_bytes=r.bytes;
   // Never log URLs, headers, error bodies or raw API responses containing keys.
   if(r.http_status===200){row.sample_checks=d.parse(r.text).slice(0,3).map(p=>proof(...p,d.host));row.three_fields_verified=row.sample_checks.some(p=>p.name_present&&p.price_present&&p.url_present);row.status=row.three_fields_verified?'성공':'정책 확인 필요';row.reason=row.three_fields_verified?'live_three_fields_verified':'empty_or_unexpected_schema';}
   else {row.status=[401,403].includes(r.http_status)?'인증 대기':'접근 불가';row.reason='http_error_stop';}
  }catch(e){row.status='접근 불가';row.error_code=e.cause?.code||e.name;}
 }
 results.push(row);console.log(JSON.stringify(row));
}
const output=path.join(dir,'api_verification.json');
const prior=fs.existsSync(output)?JSON.parse(fs.readFileSync(output,'utf8')):[];
fs.writeFileSync(output,JSON.stringify([...prior.filter(r=>!results.some(x=>x.id===r.id)),...results],null,2)+'\n');
