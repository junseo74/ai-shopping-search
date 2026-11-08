# 3차 국내외 상품 데이터 소스 발굴·실증

조사일 **2026-11-08 (Asia/Seoul)**. 브랜치 feature/domestic-source-research. 이번 결과와 실행 파일은 phase3/에만 작성했다. 계정 생성·API 신청·약관 대리 동의·유료 가입·외부 자료 제출·대량 수집을 하지 않았다. 공통 엔진이나 DB에 통합하지 않았다.

## 집계

| 구분 | 수 | 의미 |
|---|---:|---|
| 신규 조사 | 30 | 신규 소스/상품 서비스; 30개 신규 쇼핑몰이라는 뜻이 아님 |
| 공식 상품 접근 경로 확인 | 25 | API/피드/라이선스 상품 제공 경로 존재; 판매자/계약 전용 포함 |
| 공식 경로 미확정 | 5 | Target, AliExpress, Taobao, Shopee, ISBNdb; 포털/문서 접근 한계 명시 |
| 실제 상품 응답 성공 제공처 | 2 | Apple, Open Food Facts; 과거 국내 RSS 성공은 재집계 안 함 |
| 성공 엔드포인트 | 3 | Apple Search, OFF v3 product, Open Prices |
| 같은 응답의 7필드 완전 검증 제공처 | 1 | Apple 앱 3건; 실물 상품의 7필드 완전 검증은 0개 |
| 인증형 API 실제 성공 | 0 | 승인받은 자격증명을 이번 작업에서 확인/사용하지 않음 |
| 즉시 실운영 가능 | 0 | 배포/라이선스 의무 이행/상품 범위 요구까지 충족한 소스 없음 |
| 공개 라이선스상 장기 저장 가능 | 1 | OFF 계열 ODbL 조건부; 프로젝트 독점 상품 DB 승인과 다름 |
| 프로젝트 별도 장기 저장 승인 획득 | 0 | 개별 계약/승인을 받지 않음 |
| 독립 어댑터 | 3 | 실제 응답 확인 뒤 구현; 인증형 어댑터를 추정으로 추가하지 않음 |
| 오프라인 테스트 | 50/50 통과 | 합성/권한 게이트 테스트. 실제 서비스 검증 횟수 아님 |

증거는 [verification.json](verification.json), 테스트는 [tests/results.json](tests/results.json). 조사 완료·HTTP200·정규화 성공·운영 허가·저장 라이선스를 서로 다른 필드로 기록했다. 성공은 2개 **제공처**이며 Open Prices를 별도 제공처로 부풀리지 않았다. Rakuten Advertising도 상품 피드 공식 경로를 확인했지만 Ichiba와 기업군 중복을 피하려고 최종30개에서 제외했다.

## 중복 제거

1차 README/후보30 CSV, 2차 README/추가 조사 데이터 및 docs/source-access.md를 읽기 전용으로 확인했다. docs/의 후보 문서는 현재 source-access.md 하나이며 별도 140개 목록은 파일명 검색에서 찾지 못했다. 기존 국내30 및 eBay, Google Merchant, Meta, YouTube Shopping, 당근, 번개장터, 기존 국내 공공 데이터, 2차에 언급한 LinkPrice를 신규 후보에서 제외했다. 전체 후보 ID 중복 검사는 [deduplication.json](deduplication.json)에 기록했다. 다른 파일명으로 숨겨진 목록의 부재까지 단정하지 않는다.

## 실제 응답과 7개 필드

각 칸은 검증 표본 중 필드가 존재한 수다. 같은 상품 객체에서 추출했다. 매핑은 adapters/ 코드에 있으며 누락값은 null이다. 상품명·판매자명·URL·ID는 메모리에서 확인한 뒤 결과 파일에는 해시와 존재 여부만 남겼다. 이미지나 상품 상세 페이지를 따라 요청하지 않았다.

| 경로 | 응답 | 상품명 | 가격 | 통화 | 판매처 | 상품 URL | 이미지 URL | ID |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| apple | 200 / ok | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| off | 200 / ok | 1/1 | 0/1 | 0/1 | 1/1 | 0/1 | 1/1 | 1/1 |
| prices | 200 / ok | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 | 3/3 |

- **Apple**: 공개 [Search API](https://performance-partners.apple.com/search-api)의 software 검색. trackName/price/currency/sellerName/trackViewUrl/artworkUrl/trackId를 실제 추출. 세 표본은 무료 앱으로 가격0은 정상이며 앱 내 과금 가격을 뜻하지 않는다. 미국 storefront의 USD 디지털 상품으로 국내 실물 쇼핑 DB 커버리지가 늘어난 것은 아니다. 초기 음악 응답은 판매자 필드가 없어 완전 성공 집계에서 제외하고, 문서가 지원하는 앱 검색으로 매핑을 확인했다. 콘텐츠 홍보 목적·badge/링크 조건을 준수해야 하며 독립 장기 DB 사용 허가는 확인되지 않았다.
- **OFF**: [v3 제품 API](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/)에서 한 바코드의 이름/이미지/유통점 목록/ID를 확인. stores는 기여자가 기록한 유통점 목록이며 현재 재고·계약된 판매처 보장이 아니다. 가격·통화·상품 구매 URL은 반환되지 않았다.
- **Open Prices**: [공식 가격 프로젝트](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/product-prices/)에서 같은 바코드의 가격·통화·상점·관측일을 확인. 과거의 crowdsourced 가격으로 현재 판매가나 온라인 구매 링크로 취급하지 않는다. ID는 가격 관측 ID이며 barcode는 별도다. 같은 상품의 다른 날짜/판매처 관측을 중복 상품처럼 제거하면 가격 이력이 사라진다. 원응답의 owner/proof/영수증/좌표/주소/댓글을 결과·상품 객체에 포함하지 않았다.

초기 Prices 요청의 page_size=3은 무시되어10건이 돌아왔다. 추가 페이지를 읽지 않았고 원문은 저장하지 않았다. size=3으로 수정한 재검증은3건만 반환했다. 최초 sandbox 네트워크 오류는 허용된 직접 네트워크 실행으로 해결했다. 서비스의 403·429·CAPTCHA를 우회하지 않았다. 스키마 확인 기록은 [schema_checks.json](schema_checks.json), 재실행 이력은 [verification_attempts.json](verification_attempts.json)에 있다.

## 후보 30개

API 종류, 인증, 승인 조건/난이도, 제한, 검색 범위, 갱신, 보관/재사용, 근거 방식과 날짜는 [candidates.csv](candidates.csv)에 있다. 모르는 TTL/요금/승인 기간은 미확인으로 적었다. 공식 API가 존재해도 전체 상품 검색이나 모든 몰에 대한 이용권을 뜻하지 않는다.

| 소스 | 접근 범위 | 공식 경로 | 이번 상태 | 근거 |
|---|---|---|---|---|
| Rakuten Ichiba | full_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://webservice.rakuten.co.jp/index.php/documentation/ichiba-item-search) |
| Yahoo! Shopping Japan | full_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html) |
| Amazon Creators API | affiliate_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction) |
| Etsy | reviewed_public_and_seller_scopes | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developers.etsy.com/documentation/) |
| Best Buy | retailer_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developer.bestbuy.com/) |
| Walmart Marketplace | authorized_seller_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developer.walmart.com/us-marketplace/docs/items) |
| Target Partners | affiliate_unconfirmed_feed | 미확정 | 문서/정책 보류 | [공식 자료](https://partners.target.com/) |
| AliExpress | affiliate_or_seller_unconfirmed | 미확정 | 문서/정책 보류 | [공식 자료](https://open.aliexpress.com/) |
| Taobao / Tmall | affiliate_or_seller_unconfirmed | 미확정 | 문서/정책 보류 | [공식 자료](https://open.taobao.com/) |
| JD Union | affiliate_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://jos.jd.com/jdunion) |
| Shopee | seller_integration_unconfirmed | 미확정 | 문서/정책 보류 | [공식 자료](https://open.shopee.com/documents/v2/api-reference) |
| Lazada | seller_only | 확인 | 인증·목적 승인 대기 | [공식 자료](https://open.lazada.com/apps/doc/doc?docId=108146&lang=en_US&nodeId=10556) |
| Mercado Libre | authenticated_public_listing_and_seller | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developers.mercadolibre.com.ar/en_us/items-and-searches) |
| bol | seller_supplier_advertiser | 확인 | 인증·목적 승인 대기 | [공식 자료](https://api.bol.com/retailer/public/Retailer-API/index.html) |
| Allegro | seller_product_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developer.allegro.pl/documentation/) |
| Cafe24 | merchant_authorized_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://apidocs.cafe24.com/en/docs/guide/intro) |
| 메이크샵 | merchant_authorized_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://openapi.makeshop.co.kr/common/) |
| Awin | joined_advertiser_feeds | 확인 | 인증·목적 승인 대기 | [공식 자료](https://help.awin.com/developers/docs/product-feed-intro) |
| CJ Affiliate | affiliate_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developers.cj.com/) |
| impact.com | partner_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://integrations.impact.com/partner-api-reference/reference/catalogs.md) |
| StockX | approved_partner_catalog_and_selling | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developer.stockx.com/portal/api-reference) |
| Webgains | joined_advertiser_feeds | 확인 | 인증·목적 승인 대기 | [공식 자료](https://knowledgehub.webgains.com/home/product-feeds-for-publishers) |
| Tradedoubler | joined_advertiser_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://dev.tradedoubler.com/products/publisher/) |
| Admitad (Mitgo) | affiliate_feeds | 확인 | 인증·목적 승인 대기 | [공식 자료](https://developers.mitgo.com/hc/en-us/articles/34481349447058-Affiliate-programs) |
| Open Food Facts + Open Prices | open_product_database | 확인 | 실응답 확인 | [공식 자료](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/) |
| Icecat | licensed_brand_catalog | 확인 | 인증·목적 승인 대기 | [공식 자료](https://icecat.com/content-subscription/) |
| Apple iTunes / App Store Search | digital_store_catalog | 확인 | 실응답 확인 | [공식 자료](https://performance-partners.apple.com/search-api) |
| ISBNdb | licensed_book_database_unconfirmed | 미확정 | 문서/정책 보류 | [공식 자료](https://isbndb.com/apidocs/v2) |
| GS1 US Data Hub | licensed_gtin_validation | 확인 | 인증·목적 승인 대기 | [공식 자료](https://www.gs1us.org/tools/gs1-us-data-hub) |
| Datafiniti Product Data | commercial_licensed_dataset | 확인 | 인증·목적 승인 대기 | [공식 자료](https://docs.datafiniti.co/docs/api-product-data) |

공식 문서 직접 열기가 실패해도 공식 검색 색인 본문으로 확인한 Mercado Libre/CJ/Icecat/StockX는 evidence_method에 이를 구분했다. Shopee의 문서 제목/색인만으로 상품조회 권한을 인정하지 않았다. 미확정 5개는 접근 허가가 없다는 단정이 아니라 이번 증거로 허용 범위를 확인하지 못했다는 뜻이다.

## 우선 확보 경로와 승인 준비

1. **OFF**: 공개 라이선스 기반 상품 metadata/역사 가격 보강에 우선 적합. [라이선스 문서](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/)와 [Prices 데이터 안내](https://github.com/openfoodfacts/open-prices/blob/main/docs/guides/data.md)를 근거로 ODbL 출처·공개 파생DB share-alike 및 이미지 CC BY-SA/제3자 권리를 설계한다. 비공개 제휴 데이터와 분리할 라이선스 경계를 검토해야 한다. 대량은 API 반복 대신 공식 dump 경로의 허용 조건부터 확인한다.
2. **Apple**: 디지털 상품 홍보형 실시간 검색 시범 후보. 원상품 링크/badge·asset 목적 조건을 UI에 반영하고 수익제휴/EPF가 필요하면 사용자가 별도 신청한다. 현재 어댑터는 메모리 검증용이다.
3. **Best Buy**: 키 발급 후 최소 조회를 할 수 있는 비교적 구체적인 실물 상품 API 후보. [약관](https://developer.bestbuy.com/legal)은 임시 캐시 최대72시간이므로3백만 건 영구 DB 용도로 승인된 것으로 취급하지 않는다.
4. **Rakuten Ichiba / Yahoo JP**: 전체 상품 검색 후보. 현행 App ID+Access Key/Client ID 등록, 사이트·목적 심사, 캐시/가격갱신·이미지 노출·국가 제한을 확인한다. 현재 키를 발급하거나 예제 키를 사용하지 않았다.
5. **Awin / CJ / Webgains / Tradedoubler / impact.com / Admitad**: 단일 계약에서 여러 승인 광고주를 확보할 수 있어 사이트 수 확대에 유리하다. 브랜드 참여 목록·실제 필드·가격 최신성·갱신/탈퇴 시 삭제 조건은 계정과 광고주 승인 후 검증한다. 네트워크 개수를 판매처 수로 환산하지 않는다.
6. **Cafe24 / 메이크샵**: 국내 몰 소유자의 직접 동의를 받는 방식. 플랫폼 전체 상품 접근권과 달리 상점마다 계약·권한이 필요하다. 상품 데이터만 최소 scope로 요청하고 회원·주문 API는 사용하지 않는다.
7. **Amazon/Etsy/JD/StockX 및 판매자 전용 API**: 실적·수동 심사·지역/파트너 자격이 있어 후순위. Amazon은 [현행 Creators 등록](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding/register-for-creators-api)과 [한도](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/concepts/api-rates)를 기준으로 준비한다. 구 PA-API를 재시도하지 않는다. StockX는 [공식 Catalog/Market Data](https://developer.stockx.com/portal/api-reference)가 있으나 정가·최저ask·최고bid가 서로 다르고 외부 서비스 재사용 허가는 별도다.

사용자가 직접 수행해야 할 공통 체크리스트(미제출):

- [ ] 공개 서비스 URL·사업자/담당자 정보·개인정보처리방침·제휴 표시 예시를 준비한다. 값은 이 저장소에 기록하지 않는다.
- [ ] candidates.csv 각 소스 approval과 공식 신청 포털에서 대상국/개인·사업자 자격/필요서류를 확인한다. 확인되지 않은 서류를 필수라고 가정하지 않는다.
- [ ] API 이용 목적을 소비자 검색/가격비교로 명시하고 상품 범위·7필드·판매가 기준·이미지 표시권을 확인한다.
- [ ] 원상품 링크·가격관측시각·제휴 고지·갱신 주기·캐시 TTL·영구저장·재배포/판매·해지 삭제 의무를 서면 또는 적용 약관으로 확정한다.
- [ ] 사용자 본인이 계정 등록/약관 동의/신청·유료 계약을 승인 후 수행한다. 이번에는 수행하지 않았다.
- [ ] 발급된 키는 비밀관리 또는 프로세스 환경변수로 제공한다. 응답이나 URL/로그·CSV·Git에 저장하지 않는다.
- [ ] 승인된 실제 계정으로1회1~3건 검증한 뒤에만 인증형 어댑터를 추가한다. 테스트 fixture는 실제 성공으로 집계하지 않는다.

## 100개 사이트·300만 건 목표

현재 자료는 기존 국내30과 신규 소스30이다. 신규30에는 제휴망·호스팅 플랫폼·디지털/metadata 제공처가 포함되므로 **60개 쇼핑몰 확보**가 아니다. 승인 광고주/몰 목록이 없어100개 사이트 달성률은 산정할 수 없다. 권한이 확인된 개별 판매처 목록과 독립 판매처/상품/offer 세 가지 집계를 먼저 분리해야 한다.

300만 건을100개 몰로 균등 분배하면 몰당3만 건이다. OFF 제품조회15회/분으로 한 건씩300만 회를 읽으면 이상적 최소 약139일이며, 공식 문서는 몇백 개 초과 시 dump 사용을 권한다. 이 계산은 수집 계획이나 허용량이 아니다. 100개 몰의 현재 가격을 매일 갱신하려면300만 offer/day 및 변경 피드·페이지 크기·쿼터/비용을 별도로 충족해야 한다. Search 결과 상한/제휴범위 때문에 단순 페이지 순회로 전체 상품을 확보할 수 있다고 가정하지 않는다.

용량 예시: 레코드 평균1KB이면 원문만 약3GB(십진), 색인/이력/중복/이미지는 별도다. 실제 평균 크기와 중복률은 측정하지 않았다. OFF의 공개 metadata를 많이 확보해도 현재 판매가·구매 URL을 갖춘300만 쇼핑 offer가 되지 않는다. 현재 확보한7필드 표본은 디지털3건, 실물 완전 표본0건이며 전체 운영 승인0개다. 대규모 시작 조건은 계약 범위/쿼터·갱신/삭제·중복 제거·데이터 품질 검증 통과다. 대량 요청·dump 다운로드는 시작하지 않았다.

## 재현 및 테스트

외부 패키지 설치 없이 Node.js 내장 기능만 사용한다. 독립 어댑터는 apple.mjs / openfoodfacts.mjs / openprices.mjs 세 개다. request 함수는3개 고정 HTTPS 경로의 GET만 허용하며 요청당 최대3개 정규화,15초 timeout,1MB 상한, 리다이렉트/재시도 없음이다. 이미지·상품페이지를 가져오지 않으며 인증정보를 읽지 않는다. 향후 수집 쿼리 확장은 권한/필드 재검증 후 코드 변경이 필요하다.

```powershell
node research_domestic/phase3/run_tests.mjs
node research_domestic/phase3/verify.mjs --live
node research_domestic/phase3/build_report.mjs
node research_domestic/phase3/integrity.mjs
```

테스트 50개는 실제 응답을 복사하지 않은 합성 값으로 응답 정규화,0원,누락값,중복 ID/URL,가격 관측 구분,빈 결과,스키마 불일치,타임아웃(헤더/본문),네트워크 예외,HTTP301/302/401/403/429/500/503,응답 크기,잘못된JSON,인증 쿼리/호스트 검증,비밀값 에러 반출 방지와 미승인28개 소스 게이트를 확인한다. 인증이 없는28개에는 네트워크 호출 없이 권한 보류만 모의 검증했고 실제 파서나 운영 성공으로 집계하지 않았다. 실제 네트워크 성공 요청은 스키마 확인5회+최종 어댑터 검증3회로 총8회다(이전 sandbox 전송 실패3회 별도). 최종 어댑터 통합 증거는 verification.json에 있다. synthetic 테스트 통과가 제공자의 승인이나 SLA를 보장하지 않는다.

보호 대상의 작업 전 해시는 protected_baseline.json, 작업 후 비교는 integrity.json이다. Git 브랜치 변경/병합/푸시/리셋/클린/커밋/스테이징을 하지 않았다.
