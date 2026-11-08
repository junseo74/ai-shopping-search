import test from 'node:test';
import assert from 'node:assert/strict';
import { request } from '../transport.mjs';
test('Exactly one request; GET/manual redirect/no cookies/no auth',async()=>{
  let calls=0;
  const r=await request('apple',{fetcher:async(url,options)=>{calls++;assert.equal(options.method,'GET');
    assert.equal(options.redirect,'manual');assert.equal(options.credentials,'omit');assert.equal(options.headers.Authorization,undefined);
    assert.match(url,/limit=3/);return Response.json({results:[]});}});
  assert.equal(calls,1);assert.equal(r.status,'ok');
});
test('Network failures are sanitized and never retried',async()=>{
  let calls=0;const r=await request('apple',{fetcher:async()=>{calls++;throw new Error('SYNTHETIC_PRIVATE_ERROR');}});
  assert.equal(calls,1);assert.equal(r.status,'network_error');assert.doesNotMatch(JSON.stringify(r),/SYNTHETIC_PRIVATE_ERROR/);
});
test('Timeout aborts stalled fetch and returns timeout',async()=>{
  const r=await request('apple',{timeoutMs:15,fetcher:(_u,{signal})=>new Promise((_resolve,reject)=>{
    signal.addEventListener('abort',()=>reject(new Error('synthetic timeout')),{once:true});
  })});assert.equal(r.status,'timeout');
});
test('Timeout also aborts stalled body consumption',async()=>{
  const r=await request('apple',{timeoutMs:15,fetcher:async(_u,{signal})=>new Response(new ReadableStream({
    start(controller){signal.addEventListener('abort',()=>controller.error(new Error('synthetic body timeout')),{once:true});}
  }))});assert.equal(r.status,'timeout');
});
test('Redirect/auth/rate-limit/server failures stop without follow-up',async()=>{
  for(const status of [301,302,401,403,429,500,503]) {
    let calls=0;const r=await request('apple',{fetcher:async()=>{calls++;return new Response('SYNTHETIC_PRIVATE_BODY',{status});}});
    assert.equal(r.status,'http_error');assert.equal(r.http_status,status);assert.equal(calls,1);
    assert.doesNotMatch(JSON.stringify(r),/SYNTHETIC_PRIVATE_BODY/);
  }
});
test('Oversize response is rejected and cancelled',async()=>{
  const r=await request('apple',{maxBytes:5,fetcher:async()=>new Response('123456')});assert.equal(r.status,'size_limit');
});
test('Malformed JSON is rejected without echoing response',async()=>{
  const r=await request('apple',{fetcher:async()=>new Response('SYNTHETIC_PRIVATE_NOT_JSON')});assert.equal(r.status,'invalid_json');
  assert.doesNotMatch(JSON.stringify(r),/SYNTHETIC_PRIVATE_NOT_JSON/);
});
test('Arbitrary endpoints rejected before calling fetch',async()=>{
  let calls=0;await assert.rejects(()=>request('https://example.com',{fetcher:async()=>{calls++;}}),/endpoint_not_allowed/);
  assert.equal(calls,0);
});
