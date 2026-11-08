import crypto from 'node:crypto';
export const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
export async function request(url,headers={}) {
 const res=await fetch(url,{method:'GET',redirect:'manual',signal:AbortSignal.timeout(15000),headers:{'User-Agent':'DomesticSourceResearch/1.0 (small official-source verification)',...headers}});
 const chunks=[];let size=0;
 for await (const chunk of res.body) {
  size+=chunk.length;
  if(size>2_000_000){await res.body.cancel().catch(()=>{});throw new Error('response_size_limit');}
  chunks.push(chunk);
 }
 const bytes=Buffer.concat(chunks);
 const headerCharset=res.headers.get('content-type')?.match(/charset=([^; ]+)/i)?.[1];
 const xmlCharset=bytes.subarray(0,150).toString().match(/encoding=["']([^"']+)/i)?.[1];
 const charset=(xmlCharset||headerCharset||'utf-8').replace(/^ks_c_5601-1987$/i,'euc-kr');
 return {http_status:res.status,content_type:res.headers.get('content-type'),bytes:bytes.length,body_sha256:sha(bytes),text:new TextDecoder(charset).decode(bytes),location:res.headers.get('location')};
}
export const strip=s=>s.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g,'$1').replace(/<[^>]*>/g,' ').replace(/&nbsp;/gi,' ').replace(/&amp;/gi,'&').replace(/&lt;/gi,'<').replace(/&gt;/gi,'>').replace(/\s+/g,' ').trim();
export const tag=(s,n)=>strip(s.match(new RegExp('<'+n+'(?:\\s[^>]*)?>([\\s\\S]*?)</'+n+'>','i'))?.[1]||'');
export function proof(title,price,url,allowedHosts){
 let valid=false;
 try{const u=new URL(url);valid=['http:','https:'].includes(u.protocol)&&allowedHosts.some(h=>u.hostname===h||u.hostname.endsWith('.'+h));}catch{}
 const amount=typeof price==='number'?price:Number(String(price).replaceAll(',',''));
 return {name_present:!!title?.trim(),name_sha256:sha(title||''),price_present:Number.isFinite(amount)&&amount>0,price_krw:Number.isFinite(amount)?amount:null,url_present:valid,url_sha256:sha(url||''),same_product_binding:true};
}
