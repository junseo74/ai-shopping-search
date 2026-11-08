import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseFeed} from './rss.mjs';
import {sha} from './net.mjs';
// Synthetic regression fixtures; these are NOT real merchant products.
test('summary RSS binds each book and selling price; stale content overrides recent build date',()=>{
 const xml='<rss><channel><lastBuildDate>Sun, 08 Nov 2026 09:00:00 +0900</lastBuildDate><item><title>channel summary</title><link>https://www.yes24.com/</link><description><![CDATA[2025년 06월 08일 <a href="http://www.yes24.com/Goods/FTGoodsView.aspx?goodsNo=1"><img src="x"></a><a href="http://www.yes24.com/Goods/FTGoodsView.aspx?goodsNo=1">fixture A</a> 정가 20,000원 판매가 18,000원 <a href="https://event.yes24.com/1">event</a><a href="http://www.yes24.com/Goods/FTGoodsView.aspx?goodsNo=2">fixture B</a> 판매가 9,000원]]></description></item></channel></rss>';
 const r=parseFeed('yes24',xml,'2026-11-08T11:30:00Z');
 assert.equal(r.sample_checks.length,2);assert.equal(r.sample_checks[0].name_sha256,sha('fixture A'));assert.deepEqual(r.sample_checks.map(x=>x.price_krw),[18000,9000]);assert.equal(r.freshness,'stale');assert.equal(r.three_fields_verified,true);
});
test('Aladin separates selling/list price and rejects unrelated links',()=>{
 const xml='<rss><channel><item><title>fixture</title><link>https://www.aladin.co.kr/rsscenter/go.aspx?type=item&amp;itemId=1</link><description><![CDATA[정가: 10,000 원 / 판매가: 9,000 원]]></description></item></channel></rss>';
 assert.equal(parseFeed('aladin',xml).sample_checks[0].price_krw,9000);
 assert.equal(parseFeed('aladin',xml.replace('www.aladin.co.kr','example.com')).three_fields_verified,false);
});
test('HTML, missing sale price, malformed XML and entities cannot produce success',()=>{
 assert.equal(parseFeed('aladin','<html>상품 100원</html>').three_fields_verified,false);
 assert.equal(parseFeed('aladin','<rss><item><title>fixture</title><link>https://www.aladin.co.kr/rsscenter/go.aspx?itemId=1</link><description>정가: 100원</description></item></rss>').three_fields_verified,false);
 assert.equal(parseFeed('aladin','<rss><item>').three_fields_verified,false);
 assert.throws(()=>parseFeed('aladin','<!DOCTYPE rss SYSTEM "https://example.com"><rss/>'));
});
