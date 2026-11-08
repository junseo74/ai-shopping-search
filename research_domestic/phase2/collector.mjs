// Read-only prototype. Products exist in memory only; CLI persists evidence, not a catalog.
import {request,strip,tag,sha} from '../net.mjs';
import {parseFeed} from '../rss.mjs';
export const sources=['yes24','aladin','elevenst','domeggook','domeme','aladin_rss_170'];
const credential={yes24:'YES24_API_KEY',aladin:'ALADIN_TTB_KEY',elevenst:'ELEVENST_API_KEY',domeggook:'DOMEGGOOK_API_KEY',domeme:'DOMEGGOOK_API_KEY'};
const hosts={yes24:['yes24.com'],aladin:['aladin.co.kr'],elevenst:['11st.co.kr'],domeggook:['domeggook.com','domeme.com'],domeme:['domeggook.com','domeme.com'],aladin_rss_170:['aladin.co.kr']};
const secretParam=/^(?:key|ttbkey|aid|api_?key|access_?token|refresh_?token|token|password|passwd|secret|client_?secret|authorization|cookie|session|signature|auth_?key)$/i;
function safeProductUrl(value,id){
 try{
  const u=new URL(value);
  if(!['http:','https:'].includes(u.protocol)||u.username||u.password||!hosts[id].some(h=>u.hostname===h||u.hostname.endsWith('.'+h)))return null;
  if([...u.searchParams.keys()].some(k=>secretParam.test(k)))return null;
  return u.href;
 }catch{return null;}
}
export function normalize(id,p,observedAt){
 if(typeof p.name!=='string'||!p.name.trim())return null;
 const name=strip(p.name);if(!name)return null;
 // Do not turn missing/null, booleans, or formatted unknown currency into prices.
 if(!['string','number'].includes(typeof p.price)||p.price==='')return null;
 const price=Number(String(p.price).replaceAll(',',''));
 if(!Number.isFinite(price)||price<=0)return null;
 const url=safeProductUrl(p.url,id);if(!url)return null;
 return {source:id,name,price,currency:'KRW',url,price_field:p.price_field,min_order_qty:p.min_order_qty??null,business_only:p.business_only??null,observed_at:observedAt,commercial_use:id==='yes24'?'allowed_with_attribution_link_and_terms':'unconfirmed',long_term_storage:'not_approved',redistribution:'not_approved'};
}
export function buildRequest(id,key,query,limit){
 const url=new URL({yes24:'https://apis.yes24.com/v1/goods/itemList',aladin:'https://www.aladin.co.kr/ttb/api/ItemSearch.aspx',elevenst:'https://openapi.11st.co.kr/openapi/OpenApiService.tmall',domeggook:'https://www.domeggook.com/ssl/api/',domeme:'https://www.domeggook.com/ssl/api/',aladin_rss_170:'https://www.aladin.co.kr/rss/new_all/170'}[id]);
 const params=id==='yes24'?{query,page:1,pageSize:limit,detail:'N'}:id==='aladin'?{TTBKey:key,Query:query,QueryType:'Keyword',MaxResults:limit,start:1,SearchTarget:'Book',output:'js',Version:'20131101'}:id==='elevenst'?{key,apiCode:'ProductSearch',keyword:query,pageNum:1,pageSize:limit}:['domeggook','domeme'].includes(id)?{ver:'4.1',mode:'getItemList',aid:key,market:id==='domeme'?'supply':'dome',om:'json',kw:query,sz:limit,pg:1}:{};
 for(const[k,v]of Object.entries(params))url.searchParams.set(k,String(v));
 return {url,headers:id==='yes24'?{'X-Api-Key':key}:{}};
}
export function parseProducts(id,text){
 if(/<!DOCTYPE|<!ENTITY/i.test(text))throw new Error('xml_entities_rejected');
 if(id==='yes24'){
  const j=JSON.parse(text);if(j.success!==true)return [];
  return (Array.isArray(j.data?.items)?j.data.items:[]).map(p=>({name:p.title,price:p.salePrice,url:p.link,price_field:'salePrice'}));
 }
 if(id==='aladin')return (JSON.parse(text).item||[]).map(p=>({name:p.title,price:p.priceSales,url:p.link,price_field:'priceSales'}));
 if(id==='elevenst')return [...text.matchAll(/<Product(?:\s[^>]*)?>([\s\S]*?)<\/Product>/g)].map(m=>({name:tag(m[1],'ProductName'),price:tag(m[1],'ProductPrice'),url:tag(m[1],'DetailPageUrl'),price_field:'ProductPrice'}));
 if(['domeggook','domeme'].includes(id)){
  const list=JSON.parse(text).domeggook?.list?.item;
  return (Array.isArray(list)?list:list&&typeof list==='object'?[list]:[]).map(p=>({name:p.title,price:p.price,url:p.url,price_field:'price',min_order_qty:p.unitQty,business_only:p.comOnly}));
 }
 if(id==='aladin_rss_170')return [...text.matchAll(/<item(?:\s[^>]*)?>([\s\S]*?)<\/item>/gi)].slice(0,3).map(m=>({name:tag(m[1],'title'),price:tag(m[1],'description').match(/판매가\s*[:：]?\s*([\d,]+)\s*원/)?.[1],url:tag(m[1],'link'),price_field:'RSS.description.판매가'}));
 return [];
}
export async function collect(id,{env=process.env,fetcher=request,query='컴퓨터',limit=3,purposeApproved=false,now=()=>new Date().toISOString()}={}){
 const result={source:id,observed_at:now(),status:'not_started',request_count:0,products:[],technical_success:false,commercial_use:id==='yes24'?'allowed_with_conditions':'unconfirmed',long_term_storage:'not_approved'};
 if(!sources.includes(id)){result.status='unsupported_source';return result;}
 if(!Number.isInteger(limit)||limit<1||limit>3||typeof query!=='string'||!query.trim()||query.length>100){result.status='invalid_arguments';return result;}
 const key=credential[id]?env[credential[id]]:null;
 if(credential[id]&&!key){result.status='needs_credentials';result.credential_env=credential[id];return result;}
 if(['domeggook','domeme'].includes(id)&&!purposeApproved){result.status='needs_purpose_classification_approval';return result;}
 if(key&&/[\r\n]/.test(key)){result.status='invalid_credential_format';return result;}
 try{
  const req=buildRequest(id,key,query,limit);result.request_count=1;
  const response=await fetcher(req.url,req.headers);result.http_status=response.http_status;
  if(response.http_status!==200){result.status=[401,403].includes(response.http_status)?'access_not_authorized':response.http_status===429?'rate_limited_stop':'http_error_stop';return result;}
  if(response.text.length>2_000_000){result.status='response_too_large';return result;}
  const seen=new Set();
  for(const p of parseProducts(id,response.text).slice(0,3)){
   const product=normalize(id,p,result.observed_at);
   if(product&&!seen.has(product.url)){seen.add(product.url);result.products.push(product);}
   if(result.products.length>=limit)break;
  }
  if(id==='aladin_rss_170'){
   const feed=parseFeed('aladin',response.text,result.observed_at);
   result.feed_date=feed.feed_date;result.freshness=feed.freshness;
   if(!feed.is_rss){result.products=[];result.status='invalid_feed';return result;}
  }
  result.technical_success=result.products.length>0;
  result.status=result.technical_success?'verified_in_memory':'empty_or_invalid_schema';
 }catch{
  // No error text, request URL, response body, cookie or auth value escapes.
  result.status='transport_or_parse_error';
 }
 return result;
}
export function evidence(result){
 const {products,...safe}=result;
 return {...safe,product_count:products.length,sample_checks:products.map(p=>({name_sha256:sha(p.name),price_krw:p.price,url_sha256:sha(p.url),price_field:p.price_field,min_order_qty:p.min_order_qty,business_only:p.business_only,three_fields_valid:true})),raw_response_stored:false,product_values_stored:'hashes_only_except_price_and_purchase_conditions'};
}
