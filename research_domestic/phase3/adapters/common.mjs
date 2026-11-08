import crypto from 'node:crypto';
import { request } from '../transport.mjs';
export const fields=['name','price','currency','seller','product_url','image_url','product_id'];
export const sha=v=>crypto.createHash('sha256').update(String(v)).digest('hex');
export const text=v=>typeof v==='string' && v.trim()?v.trim():null;
export const amount=v=>((typeof v==='number'||(typeof v==='string'&&v.trim()!=='')) && Number.isFinite(Number(v)) && Number(v)>=0)?Number(v):null;
export function safeUrl(value,hosts) {
  try {
    const u=new URL(value);
    if(u.protocol!=='https:' || u.username || u.password || (u.port&&u.port!=='443')) return null;
    if(!hosts.some(h=>u.hostname===h||u.hostname.endsWith('.'+h))) return null;
    let decoded=u.search;
    for(let i=0;i<3;i++) { try{decoded=decodeURIComponent(decoded);}catch{break;} }
    if(/(?:token|secret|password|cookie|authorization|api[_-]?key|access[_-]?key|session|signature)/i.test(decoded)) return null;
    u.hash=''; return u.href;
  } catch { return null; }
}
export function finish(rows) {
  const ids=new Set(),urls=new Set(),products=[];let duplicates=0,invalid=0;
  for(const p of rows) {
    if(!p.name || !p.product_id) {invalid++;continue;}
    const id=`${p.source}:${p.product_id}`;
    if(ids.has(id)||(p.product_url&&urls.has(p.product_url))) {duplicates++;continue;}
    ids.add(id);if(p.product_url)urls.add(p.product_url);products.push(p);
    if(products.length===3)break;
  }
  return {products,duplicates,invalid};
}
export async function collect(id,normalize,options={}) {
  const r=await request(id,options);
  if(r.status!=='ok') return {...r,products:[],duplicates:0,invalid:0};
  try {
    const result=normalize(r.data);
    return {status:result.products.length?'ok':'empty',http_status:r.http_status,bytes:r.bytes,...result};
  } catch {return {status:'schema_error',http_status:r.http_status,products:[],duplicates:0,invalid:0};}
}
export function evidence(result) {
  return {status:result.status,http_status:result.http_status,bytes:result.bytes??null,
    products_verified:result.products.length,duplicates:result.duplicates,invalid:result.invalid,
    samples:result.products.map(p=>({
      fields:Object.fromEntries(fields.map(k=>[k,p[k]!==null&&p[k]!==undefined&&p[k]!=='' ])),
      complete_seven_fields:fields.every(k=>p[k]!==null&&p[k]!==undefined&&p[k]!==''),
      name_sha256:sha(p.name),product_id_sha256:sha(p.product_id),
      seller_sha256:p.seller?sha(p.seller):null,
      product_url_sha256:p.product_url?sha(p.product_url):null,
      image_url_sha256:p.image_url?sha(p.image_url):null,
      price:p.price,currency:p.currency,price_kind:p.price_kind,price_observed_date:p.price_observed_date??null,
      attribution:p.attribution,
    }))};
}
