import {test} from 'node:test';
import assert from 'node:assert/strict';
import {collect,evidence,buildRequest,normalize,parseProducts} from './collector.mjs';
// All fixtures and credentials here are synthetic; no recorded merchant product is used.
const env={YES24_API_KEY:'TEST_ONLY',ALADIN_TTB_KEY:'TEST_ONLY',ELEVENST_API_KEY:'TEST_ONLY',DOMEGGOOK_API_KEY:'TEST_ONLY'};
const fixtures={
 yes24:JSON.stringify({success:true,data:{items:[{title:'synthetic book',shopPrice:100,salePrice:90,link:'https://www.yes24.com/Product/Goods/1'}]}}),
 aladin:JSON.stringify({item:[{title:'synthetic book',priceStandard:100,priceSales:90,link:'https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=1'}]}),
 elevenst:'<ProductSearchResponse><Products><Product><ProductName><![CDATA[synthetic keyboard]]></ProductName><ProductPrice>90</ProductPrice><DetailPageUrl>https://www.11st.co.kr/products/1</DetailPageUrl></Product></Products></ProductSearchResponse>',
 domeggook:JSON.stringify({domeggook:{list:{item:[{title:'synthetic wholesale',price:90,url:'https://domeggook.com/1',unitQty:10,comOnly:true}]}}}),
 domeme:JSON.stringify({domeggook:{list:{item:{title:'synthetic wholesale',price:90,url:'https://domeme.com/1',unitQty:1,comOnly:false}}}}),
};
for(const id of Object.keys(fixtures))test(id+': one request, normalized products, no permanent-storage grant',async()=>{
 let calls=0;
 const r=await collect(id,{env,purposeApproved:true,fetcher:async(url,headers)=>{calls++;assert.equal(url.protocol,'https:');assert.equal(id==='yes24'?headers['X-Api-Key']:url.searchParams.get(id==='aladin'?'TTBKey':id==='elevenst'?'key':'aid'),'TEST_ONLY');return {http_status:200,text:fixtures[id]};}});
 assert.equal(calls,1);assert.equal(r.status,'verified_in_memory');assert.equal(r.products[0].price,90);assert.equal(r.products[0].long_term_storage,'not_approved');
 const safe=JSON.stringify(evidence(r));assert(!safe.includes('TEST_ONLY'));assert(!safe.includes('synthetic book'));assert(!safe.includes('https://'));
 if(id==='domeggook'){assert.equal(r.products[0].min_order_qty,10);assert.equal(r.products[0].business_only,true);}
});
test('missing credentials never calls a transport',async()=>{
 let calls=0;const r=await collect('yes24',{env:{},fetcher:async()=>{calls++;}});assert.equal(r.status,'needs_credentials');assert.equal(calls,0);
});
test('a key alone does not establish wholesale purpose approval',async()=>{
 let calls=0;const r=await collect('domeggook',{env,fetcher:async()=>{calls++;}});assert.equal(r.status,'needs_purpose_classification_approval');assert.equal(calls,0);
});
test('bounds, unsupported sources, and header injection fail before requests',async()=>{
 let calls=0;const fetcher=async()=>{calls++;};
 assert.equal((await collect('yes24',{env,limit:4,fetcher})).status,'invalid_arguments');
 assert.equal((await collect('yes24',{env,query:'',fetcher})).status,'invalid_arguments');
 assert.equal((await collect('internal_endpoint',{env,fetcher})).status,'unsupported_source');
 assert.equal((await collect('yes24',{env:{YES24_API_KEY:'TEST\r\nONLY'},fetcher})).status,'invalid_credential_format');assert.equal(calls,0);
});
test('401/403/429/redirect responses stop once without retries or body logging',async()=>{
 for(const code of [401,403,429,302]){
  let calls=0;const r=await collect('yes24',{env,fetcher:async()=>{calls++;return {http_status:code,text:'PRIVATE_BODY_TEST_ONLY'};}});
  assert.equal(calls,1);assert.equal(r.products.length,0);assert(!JSON.stringify(evidence(r)).includes('PRIVATE_BODY_TEST_ONLY'));
 }
});
test('transport errors cannot leak request URLs or credentials',async()=>{
 const r=await collect('yes24',{env,fetcher:async()=>{throw new Error('TEST_ONLY PRIVATE_BODY_TEST_ONLY https://invalid.example/?token=TEST_ONLY');}});
 const out=JSON.stringify(evidence(r));assert.equal(r.status,'transport_or_parse_error');assert(!out.includes('TEST_ONLY'));assert(!out.includes('https://'));
});
test('invalid prices, foreign hosts, userinfo, and auth query strings are rejected',()=>{
 const p={name:'synthetic',price:90,url:'https://www.yes24.com/Product/Goods/1'};
 for(const price of [null,false,0,-1,'','NaN'])assert.equal(normalize('yes24',{...p,price},'x'),null);
 for(const url of ['https://evil.example/1','https://www.yes24.com.evil.example/1','https://user:TEST_ONLY@www.yes24.com/1','https://www.yes24.com/1?token=TEST_ONLY','javascript:alert(1)'])assert.equal(normalize('yes24',{...p,url},'x'),null);
 assert.equal(normalize('yes24',{...p,name:'<b></b>'},'x'),null);
});
test('schema examples cannot count as live success; parser error and XML entities fail closed',async()=>{
 const r=await collect('yes24',{env,fetcher:async()=>({http_status:200,text:JSON.stringify({success:false,data:{items:[{title:'synthetic',salePrice:90,link:'https://www.yes24.com/1'}]}})})});assert.equal(r.technical_success,false);
 assert.throws(()=>parseProducts('elevenst','<!DOCTYPE x><Product/>'));
 const bad=await collect('yes24',{env,fetcher:async()=>({http_status:200,text:'not json TEST_ONLY'})});assert.equal(bad.status,'transport_or_parse_error');
});
test('fixed endpoints, request sizes, and market selection have no pagination expansion',()=>{
 for(const id of Object.keys(fixtures)){
  const r=buildRequest(id,'TEST_ONLY','query',3);assert.equal(r.url.protocol,'https:');assert(!r.url.href.includes('localhost'));
  if(id==='domeme')assert.equal(r.url.searchParams.get('market'),'supply');
  if(id==='domeggook')assert.equal(r.url.searchParams.get('sz'),'3');
 }
});
test('authorized public RSS returns same-product sale prices and feed freshness',async()=>{
 const text='<rss><channel><lastBuildDate>Sun, 08 Nov 2026 07:00:00 +0900</lastBuildDate><item><title>synthetic RSS book</title><link>https://www.aladin.co.kr/rsscenter/go.aspx?itemId=1</link><description><![CDATA[정가: 100 원 / 판매가: 90 원]]></description></item></channel></rss>';
 const r=await collect('aladin_rss_170',{env:{},now:()=> '2026-11-08T10:00:00Z',fetcher:async()=>({http_status:200,text})});
 assert.equal(r.products[0].price,90);assert.equal(r.freshness,'recent_feed_not_price_guarantee');assert.equal(r.long_term_storage,'not_approved');assert.equal(r.commercial_use,'unconfirmed');
});
test('duplicate records are not counted twice',async()=>{
 const p={title:'synthetic',salePrice:90,link:'https://www.yes24.com/Product/Goods/1'};
 const r=await collect('yes24',{env,fetcher:async()=>({http_status:200,text:JSON.stringify({success:true,data:{items:[p,p,p]}})})});assert.equal(r.products.length,1);
});
