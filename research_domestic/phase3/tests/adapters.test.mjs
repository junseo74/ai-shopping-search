import test from 'node:test';
import assert from 'node:assert/strict';
import { normalize as apple, run as appleRun } from '../adapters/apple.mjs';
import { normalize as off, run as offRun } from '../adapters/openfoodfacts.mjs';
import { normalize as prices, run as pricesRun } from '../adapters/openprices.mjs';
import { evidence,amount,safeUrl } from '../adapters/common.mjs';
import { eligibility,sources } from '../sources.mjs';
const app={trackName:'Synthetic application',price:0,currency:'USD',sellerName:'Fixture Company',trackId:123,
  trackViewUrl:'https://apps.apple.com/us/app/fixture/id123',artworkUrl100:'https://is1-ssl.mzstatic.com/fixture.png'};
const food={code:'0000000000000',product_name:'Synthetic food',stores:'Fixture Shop',image_url:'https://images.openfoodfacts.org/fixture.png'};
const observation={id:1,product_code:food.code,product:{...food},price:'2.50',currency:'EUR',date:'2026-01-01',location:{osm_name:'Fixture Shop'},owner:'SYNTHETIC_OWNER',proof:{receipt:'SYNTHETIC_PRIVATE'}};
test('Apple preserves valid zero price and actual seller field; all seven fields',()=>{
  const r=apple({results:[app]});assert.equal(r.products[0].price,0);
  assert.equal(r.products[0].seller,app.sellerName);
  assert.equal(evidence({status:'ok',...r}).samples[0].complete_seven_fields,true);
});
test('OFF missing price/currency/product URL stays null',()=>{
  const p=off({product:food}).products[0];assert.equal(p.price,null);assert.equal(p.currency,null);assert.equal(p.product_url,null);
});
test('Open Prices retains dated observation semantics and drops owner/proof/location PII',()=>{
  const p=prices({items:[observation]}).products[0];assert.equal(p.price,2.5);
  assert.equal(p.product_url,null);assert.equal(p.price_observed_date,'2026-01-01');
  assert.match(p.price_kind,/historical/);assert.doesNotMatch(JSON.stringify(p),/SYNTHETIC_OWNER|SYNTHETIC_PRIVATE/);
});
test('Three response normalizers remove duplicate IDs',()=>{
  for(const [normalize,data] of [[apple,{results:[app,app]}],[prices,{items:[observation,observation]}]]) {
    const r=normalize(data);assert.equal(r.products.length,1);assert.equal(r.duplicates,1);
  }
});
test('Apple also removes duplicate product URLs',()=>{
  assert.equal(apple({results:[app,{...app,trackId:124}]}).duplicates,1);
});
test('Dated price observations sharing a barcode are not falsely merged',()=>{
  assert.equal(prices({items:[observation,{...observation,id:2,date:'2026-01-02'}]}).products.length,2);
});
test('All adapters return genuinely empty results without manufactured products',()=>{
  assert.equal(apple({results:[]}).products.length,0);assert.equal(off({status:0}).products.length,0);assert.equal(prices({items:[]}).products.length,0);
});
test('All adapters enforce three-record cap',()=>{
  assert.equal(apple({results:Array.from({length:20},(_,i)=>({...app,trackId:i,trackViewUrl:`https://apps.apple.com/id${i}`}))}).products.length,3);
  assert.equal(prices({items:Array.from({length:20},(_,i)=>({...observation,id:i}))}).products.length,3);
});
test('Invalid/missing product names and IDs are rejected',()=>{
  assert.equal(apple({results:[{...app,trackName:''}]}).invalid,1);
  assert.equal(off({product:{...food,code:''}}).invalid,1);
});
test('Invalid prices cannot become zero by coercion',()=>{
  for(const v of [null,undefined,'',true,false,[],{},-1,Infinity,'NaN'])assert.equal(amount(v),null);
});
test('Product URLs reject credentials, encoded secret query keys and lookalike hosts',()=>{
  for(const u of ['https://user:FIXTURE_ONLY@apps.apple.com/id1','https://apps.apple.com/id1?%74oken=FIXTURE_ONLY',
    'https://apps.apple.com/id1?x=api%255Fkey%253DFIXTURE_ONLY','https://apps.apple.com.evil.test/id1','http://apps.apple.com/id1'])
    assert.equal(safeUrl(u,['apps.apple.com']),null);
});
test('Evidence contains presence/hash only for names/sellers/URLs and no raw content',()=>{
  const proof=evidence({status:'ok',...apple({results:[app]})});
  const encoded=JSON.stringify(proof);for(const s of [app.trackName,app.sellerName,app.trackViewUrl,app.artworkUrl100])assert.ok(!encoded.includes(s));
});
test('Every adapter maps schema mismatch to sanitized schema_error',async()=>{
  for(const run of [appleRun,offRun,pricesRun])assert.equal((await run({fetcher:async()=>Response.json({unrecognized:true})})).status,'schema_error');
});
test('Metadata contains 30 distinct offering IDs and only verified live adapters',()=>{
  assert.equal(sources.length,30);assert.equal(new Set(sources.map(s=>s.id)).size,30);
  assert.equal(sources.filter(s=>eligibility(s.id).allowed).length,2);
});
// These are permission-gate simulations, not implementations or live API successes.
for(const s of sources.filter(s=>!['apple','openfoodfacts'].includes(s.id))) {
  test(`Unapproved source ${s.id} stays gated (simulation; no network)`,()=>{
    const decision=eligibility(s.id);assert.equal(decision.allowed,false);
    assert.match(decision.reason,/not_verified|insufficient/);
  });
}
