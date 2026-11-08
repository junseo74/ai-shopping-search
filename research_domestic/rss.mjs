import {sha,strip,tag} from './net.mjs';
export function parseFeed(id,text,observedAt=new Date().toISOString()) {
 if(!['yes24','aladin'].includes(id)) throw new Error('unsupported_feed');
 if(/<!DOCTYPE|<!ENTITY/i.test(text)) throw new Error('xml_entities_rejected');
 const items=[...text.matchAll(/<item(?:\s[^>]*)?>([\s\S]*?)<\/item>/gi)].map(m=>m[1]);
 const blocks=[];
 for(const item of items){
  const description=item.match(/<description(?:\s[^>]*)?>([\s\S]*?)<\/description>/i)?.[1]?.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g,'$1')||'';
  if(id==='yes24'){
   const anchors=[...description.matchAll(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)].filter(m=>/yes24\.com\/(?:Goods\/FTGoodsView\.aspx|Product\/Goods\/)/i.test(m[1])&&strip(m[2]));
   for(let i=0;i<Math.min(anchors.length,3);i++) blocks.push({title:strip(anchors[i][2]),url:anchors[i][1],description:strip(description.slice(anchors[i].index,anchors[i+1]?.index??description.length))});
  }else blocks.push({title:tag(item,'title'),url:tag(item,'link'),description:strip(description)});
  if(blocks.length>=3)break;
 }
 const samples=blocks.slice(0,3).map(({title,url,description})=>{
  const match=description.match(/판매가\s*[:：]?\s*([\d,]+)\s*원/);
  let validUrl=false;
  try{const u=new URL(url.replaceAll('&amp;','&'));validUrl=['http:','https:'].includes(u.protocol)&&u.hostname===(id==='yes24'?'www.yes24.com':'www.aladin.co.kr')&&(id==='yes24'?/goodsNo=\d+|\/goods\/\d+/i:/itemId=\d+/i).test(u.href);}catch{}
  return {name_present:!!title,name_sha256:sha(title),url_present:validUrl,url_sha256:sha(url),same_product_binding:true,price_present:!!match&&Number(match[1].replaceAll(',',''))>0,price_krw:match?Number(match[1].replaceAll(',','')):null,price_label:match?'판매가':null};
 });
 const feedDate=tag(text,'lastBuildDate')||tag(text,'pubDate')||null;
 const contentDate=id==='yes24'?strip(items[0]||'').match(/(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일/):null;
 const contentISO=contentDate?`${contentDate[1]}-${contentDate[2].padStart(2,'0')}-${contentDate[3].padStart(2,'0')}T00:00:00+09:00`:null;
 const date=Date.parse(contentISO||feedDate||'');
 const age=Number.isFinite(date)?Math.floor((Date.parse(observedAt)-date)/86400000):null;
 return {is_rss:/<rss\b/i.test(text),items_in_response:items.length,sample_checks:samples,feed_date:feedDate,feed_content_date:contentISO,feed_age_days:age,freshness:age===null?'unknown':age<0?'future_date_requires_review':age>7?'stale':'recent_feed_not_price_guarantee',three_fields_verified:/<rss\b/i.test(text)&&samples.some(s=>s.name_present&&s.url_present&&s.price_present)};
}
