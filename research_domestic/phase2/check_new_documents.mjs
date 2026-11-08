// Only new official documentation/approval pages. No form submission or API probing.
import fs from 'node:fs';
import {request,tag,sha} from '../net.mjs';
const pages=[
 ['yes24_faq','https://developers.yes24.com/support/faq'],
 ['dome_purpose','https://openapi.domeggook.com/ko/articles/API-신청-가이드-787a96cd'],
 ['dome_start','https://docs.channel.io/domeggook_api/ko/articles/OPEN-API-이용-방법-bd7265d8'],
 ['ownerclan_items','https://www.ownerclan.com/V2/service/api-center-item.php'],
 ['elevenst_registration','https://openapi.11st.co.kr/openapi/OpenApiServiceRegister.tmall'],
 ['elevenst_usage','https://openapi.11st.co.kr/openapi/OpenApiGuide.tmall?commonGuideNo=1'],
 ['ssg_docs','https://eapi.ssgadm.com/info/main.ssg'],
 ['nsmall_inbound','https://github.com/nsshopping/Affiliate-API'],
 ['oliveyoung_curator','https://m.oliveyoung.co.kr/m/mtn/affiliate/guide'],
 ['danawa_support','https://help.danawa.com/serviceHelpList.php?cate1=53&cate2=0'],
 ['enuri_ep','https://seller.enuri.com/sdul/Sdu_Guide.jsp'],
 ['zigzag_store','https://partnerlounge.kakaostyle.com/store'],
 ['coupang_revision','https://influencers.coupang.com/announcements/203'],
 ['aladin_new_category','https://www.aladin.co.kr/shop/wbrowse.aspx?CID=170'],
];
const result=[];
for(const [id,url] of pages){
 const row={id,url,observed_at:new Date().toISOString(),purpose:'new_document_or_approval_page_only'};
 try{
  const r=await request(url);Object.assign(row,{http_status:r.http_status,bytes:r.bytes,body_sha256:r.body_sha256,title:tag(r.text,'title').slice(0,120)});
  row.form_field_names=[...new Set([...r.text.matchAll(/<(?:input|select|textarea)\b[^>]*name=["']([^"']+)["']/gi)].map(m=>m[1]))].filter(n=>!/(?:token|password|secret|cookie|session)/i.test(n)).slice(0,25);
  row.document_markers={login:/로그인|login/i.test(r.text),product_api:/상품 API|ProductSearch|allItems/.test(r.text),commercial:/상업적 목적으로/.test(r.text),private_api:/Private API/.test(r.text)};
  if(id==='aladin_new_category'&&r.http_status===200){
   const alternates=[...r.text.matchAll(/<link\b[^>]*>/gi)].map(m=>m[0]).filter(s=>/rss/i.test(s)&&/alternate/i.test(s));
   row.published_feeds=alternates.map(s=>s.match(/href=["']([^"']+)/i)?.[1]).filter(Boolean);
  }
 }catch(e){row.error_code=e.cause?.code||e.name;}
 result.push(row);console.log(JSON.stringify({id,http_status:row.http_status,error_code:row.error_code,published_feeds:row.published_feeds}));
}
fs.writeFileSync(new URL('./new_document_checks.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
