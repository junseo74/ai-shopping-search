# 국내외 쇼핑몰 연동 후보 및 수집 경로 조사

확인일: **2026-11-08 (Asia/Seoul)**. 목표는 최소 100개 쇼핑몰 연동과 상품 판매정보 3,000,000건이다. 이번 결과는 **140개 후보 조사**이며 연동 성공 목록이 아니다. 기존 7개 사이트의 실제 상품 응답 검증은 여전히 0개다. 이번 조사에서도 실제 상품 응답 검증 완료 0개, 확보한 상품 판매정보 0건이다.

## 조사 범위와 판정 방법

140개 후보 각각의 공식 주소를 웹 도구로 조회했다. 홈페이지 응답 확인 115개, 본문 불충분 9개, 도구 접근 실패 16개다. 이는 웹 도구의 조회 결과이며 로컬 크롤러의 HTTP 성공률이 아니다. 도구의 403·429·timeout은 관측된 도구 접근 실패로만 적었으며 사이트의 모든 접속이나 공식 API가 차단됐다고 해석하지 않았다.

상품 데이터 경로는 공식 API 레퍼런스·정책·제휴 안내를 우선 조사했다. **직접적인 API/피드 문서를 확인하지 못한 후보도 포함**하며 해당 행은 정책 확인 필요로 남겼다. 공식 홈페이지는 쇼핑몰 정체성·업종을 확인하는 근거일 뿐 데이터 이용허가 문서가 아니다. 문서가 없는 행의 CSV `official_documentation_url`은 빈 값이며 `evidence_url`에는 공식 주소를 남겼다. 문서가 있어도 본문 미확인/접근 실패인 경우 근거에 명시했다. 제휴 프로그램 존재만으로 상품피드 제공을 확정하지 않았다.

- **검증 완료:** 허용된 production 경로에서 실제 상품 판매 응답과 필수 필드를 확인한 경우만 사용. 이번 0개. Sandbox·문서 예시·홈페이지 노출은 제외.
- **자격증명 필요:** 공식 읽기 경로와 인증 요구사항은 확인했지만 실제 키/응답 미검증. 대량저장 권한까지 확인됐다는 뜻이 아님.
- **승인 필요:** 파트너·퍼블리셔·판매자·앱 심사, 커넥터 연결 또는 해당 용도 이용 승인 필요.
- **정책 확인 필요:** 현행 경로·사용범위·웹수집 허용·문서 본문 또는 제공 여부를 확인하지 못함. 금지/허용 중 어느 쪽도 확정하지 않음.
- **제한 확인:** 해당 자체 UA/경로 또는 집계·보관 목적에 대한 제한 확인. 다른 승인 경로까지 전면 금지된다는 뜻은 아님.

| 분류 | 후보 수 |
|---|---:|
| 검증 완료 | 0 |
| 자격증명 필요 | 3 |
| 승인 필요 | 17 |
| 정책 확인 필요 | 116 |
| 제한 확인 | 4 |
| 합계 | 140 |

**개별 실수집 허용과 장기 DB 보존을 분리**했다. 모든 행에 확보 방법·API 범위·필요 자격·근거·보존 조건·실제 검증 수량·다음 검증 단계를 CSV로 제공한다. 가격·판매처·상태·이미지는 이번 후보 조사에서 만들어 넣지 않았다. 후보명과 공식 주소는 조사 대상 정보이며 가상 상품 데이터가 아니다.

## 우선 검증할 상위 10개

다음 순서는 공식 읽기 문서의 구체성, 기존 코드 재사용 가능성, 피드 확장 가능성, 자격 확보 단계와 보존 제약을 고려한 **작업 우선순위**다. 수집 성공률이나 예상 확보 건수 점수가 아니다. **지금 이 환경에서 자격·승인 없이 실제 상품 수집까지 확인한 후보는 없다.** 키 발급·승인 이전에 성공으로 표시하지 않는다.

| 순위 | 후보 | 현재 상태 | 확인된 경로와 범위 | 다음 소량 검증 |
|---:|---|---|---|---|
| 1 | [Rakuten Ichiba](https://www.rakuten.co.jp/) | 자격증명 필요 | [공식 근거](https://webservice.rakuten.co.jp/documentation/ichiba-item-search) 공식 상품 검색 API. 시장 내 검색 결과(판매자 소유 상품에 한정되지 않음) | 자격 발급 후 hits=3으로 상품명·가격·URL·통화 검증; 일괄 수집 허용·페이지 한계 확인 |
| 2 | [Yahoo!ショッピング](https://shopping.yahoo.co.jp/) | 자격증명 필요 | [공식 근거](https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html) 공식 상품 검색 API v3. Yahoo! 쇼핑 검색 결과 | 자격 확보 후 results=3 요청; 가격·판매처·상품URL 및 쿼터·페이지 상한 검증 |
| 3 | [eBay](https://www.ebay.com/) | 승인 필요 | [공식 근거](https://developer.ebay.com/api-docs/buy/browse/overview.html) Browse API; 별도 Feed API 승인 검토. 마켓플레이스 활성 판매 목록 검색; 판매자 관리 API와 별도 | 기존 EbayBrowseCollector로 승인된 production에서 limit=3 검증. Sandbox는 실상품 증거에서 제외 |
| 4 | [Etsy](https://www.etsy.com/) | 승인 필요 | [공식 근거](https://developers.etsy.com/documentation/reference) Etsy Open API v3 활성 listing 검색. findAllListingsActive 검색; 개인 상점 관리 API와 구분 | 승인된 앱으로 키·스코프 확인 후 활성 판매 listing 3개만 요청 |
| 5 | [Newegg](https://www.newegg.com/) | 승인 필요 | [공식 근거](https://promotions.newegg.com/affiliate_program/affiliate.html) 공식 affiliate 상품 카탈로그/RSS; 판매자 API와 별도. 제휴 프로그램에서 제공하는 상품 카탈로그 범위 | 승인 계정의 feed 목록·버전·배포권 확인 후 3행 샘플 검증; 광고 링크 API를 상품 피드로 오인하지 않음 |
| 6 | [iHerb](https://www.iherb.com/) | 승인 필요 | [공식 근거](https://www.iherb.com/info/affiliates) 공식 affiliate 제휴; 네트워크 피드 제공 여부 확인. 승인된 광고주/국가 카탈로그만; 전 상품 피드는 미확인 | 승인된 CJ/Awin/Impact 계정에서 iHerb 실제 feed ID 확인 후 3개 상품 검증 |
| 7 | [다나와](https://www.danawa.com/) | 승인 필요 | [공식 근거](https://mcp.ai.cowave.kr/docs) 공식 상품조회 MCP 연결. 상품 검색·판매처 가격 조회; 영구 카탈로그 덤프 미확인 | 공식 연결 후 limit=3 상품조회. 자체 UA의 HTML 수집이나 IP 제한 우회 미사용 |
| 8 | [Best Buy](https://www.bestbuy.com/) | 자격증명 필요 | [공식 근거](https://developer.bestbuy.com/apis) 공식 Products API. 현재 및 과거 제품 카탈로그; 현재 판매 offer와 구분 | 키 발급 후 현재 판매 제품 3개 응답만 검증; 시연 캐시와 영구 보관 분리 |
| 9 | [Reverb](https://reverb.com/) | 승인 필요 | [공식 근거](https://reverb.com/page/api) 공식 Reverb JSON API. 마켓플레이스/계정별 리소스는 승인된 endpoint·scope에 한정 | production 조회 권한 확인 후 판매 listing 3개. 계정 관리·주문 쓰기 호출 미실행 |
| 10 | [StockX](https://stockx.com/) | 승인 필요 | [공식 근거](https://developer.stockx.com/portal/getting-started) 공식 Catalog API + 허용된 market data 조회. 카탈로그·variant와 판매자 listing 관리 기능 구분 | 카탈로그3개와 권한 있는 market-data를 연결해 판매정보 필드 여부 검증 |

Rakuten은 2026-07-01 문서 기준으로 앱 ID뿐 아니라 accessKey가 필요하다. Yahoo! Shopping은 appid 기반 상품 검색을 제공한다. eBay는 기존 `backend/collectors/ebay.py`를 재사용할 수 있지만 운영 접근은 파트너 심사·계약 대상이므로 개발자 키만으로 가능하다고 하지 않는다. Etsy의 활성 상품 검색은 판매자 개인 상점 API와 구분되며 앱의 상업적 접근 범위를 먼저 확인해야 한다.

Newegg은 공식 안내에 상품 카탈로그와 RSS가 명시돼 대량 피드 검증 가치가 높다. iHerb는 공식 제휴 네트워크가 확인됐지만 **실제 계정의 피드 제공은 아직 미확인**이므로 승인 후 feed ID부터 확인한다. 다나와 MCP는 허용 커넥터가 필요하고 현재 세션에 연결된 도구가 없다. Best Buy는 읽기 API 시연 후보지만 일반 약관의 임시 캐시 최대72시간 때문에 **영구 300만건 확보량에는 산입하지 않는다**. Reverb·StockX는 운영 읽기 자격을 확인해야 하며 StockX 카탈로그 ID만 받는 것은 판매 가격 확보 성공이 아니다.

11번가는 상위 10개와 별개로 기존 공식 ProductSearch 구현을 유지한다. 현행 기능·계약을 재확인하지 못했으므로 키만 넣으면 된다고 보고하지 않는다. 알라딘은 공식 도메인 검색 색인에 “OpenAPI 서비스 종료 안내(26.10.30)” 제목이 있지만 현재 본문 재확인이 안 돼 종료 확정이나 정상 이용 가능 모두 주장하지 않는다. 공식 OpenAPI/상품DB 제휴 문의로 상태를 확인해야 한다.

정책 판단의 추가 1차 근거: [eBay 운영 접근 요구사항](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html), [Best Buy 보관 제한 약관](https://developer.bestbuy.com/legal), [Amazon Program policies](https://affiliate-program.amazon.com/help/operating/policies), [29CM 약관](https://www.29cm.co.kr/terms/agreement). CSV의 `policy_documentation_urls`에도 해당 링크를 별도로 기록했다. 마지막 링크 재조회에서는 Rakuten 문서 timeout, Etsy 로딩 화면, StockX 빈 본문이 있었으며 앞서 읽은 공식 문서·색인 근거를 이용했다. 이것도 상품 API 장애의 증거는 아니다.

## 100개·300만건 달성을 위한 수집 전략

1. **광고주별 허용 피드 확보를 중심으로 확장한다.** Awin·CJ·Impact·Rakuten Advertising은 별도 유통 경로이며 쇼핑몰 수에 포함하지 않는다. 계정에서 실제로 승인된 광고주·feed ID·권리 범위를 확인한 뒤 각 쇼핑몰을 독립 연동으로 등록한다. 네트워크가 피드를 지원한다는 이유로 이 목록의 모든 브랜드가 해당 네트워크에서 피드를 준다고 추측하지 않는다.
2. **공식 시장검색 API는 초기 연결·온디맨드 검증에 사용한다.** 검색 API의 페이지 상한·검색 누락·속도 제한 때문에 전 상품 수량을 추정하거나 키워드 쪼개기로 제한을 회피하지 않는다. 300만건에는 허용된 전체/증분 피드와 장기보존 계약이 우선이다.
3. **판매자 전용 API는 보유·위임 상품만 수집한다.** ESM(G마켓/옥션), 롯데ON, 29CM, Walmart의 판매자/공급사 경로를 전체몰 검색 API로 표시하지 않는다. 다수 판매자가 데이터 제공에 동의하면 그 범위만 연동한다. 쿠팡도 판매자 OPEN API와 제휴 광고 프로그램을 구분한다.
4. **웹수집은 마지막 후보 경로다.** 약관과 정확한 UA·호스트·경로별 robots를 모두 확인하고 필요한 승인을 받은 경로만 사용한다. 홈페이지 응답, sitemap, JSON-LD, 공개된 내부 API, 검색엔진 색인 노출은 수집·재배포 허가가 아니다.
5. **연동 수와 데이터 수의 완료 기준을 고정한다.** 연동 1개는 고유 쇼핑 서비스에서 허용된 production 판매정보 응답·필수 필드 검증·증거 보존·갱신 경로 확인까지 충족한 경우다. 같은 서비스의 국가별 도메인과 API 버전을 중복 산입하지 않는다. 이 목록은 브랜드/서비스 후보 140개이며 독립 기업 140개라는 뜻은 아니다.
6. **300만건은 고유 판매 offer 수로 센다.** source storefront·판매처·source 상품 ID·variant·시장/통화 기준으로 중복을 분리하고 가격 갱신 이벤트를 새 상품으로 세지 않는다. 품절/삭제·과거 카탈로그·판매가격 없는 메타데이터·Sandbox를 활성 판매정보 수와 구분한다. 기존 DB는 이번에 바꾸지 않는다.
7. **각 경로는 3단계로 승격한다.** 자격/권리 확인 → production 1~3개 필드·원본·상품 URL 검증 → 승인된 범위의 페이지/피드 전체 처리·중복·증분/삭제·관측시각 검증. 마지막 단계 전에는 예상 카탈로그 규모를 실제 확보량으로 보고하지 않는다.

100개에 균등 배분하면 300만÷100=평균 3만건이 필요하다는 산술만 가능하다. **각 쇼핑몰이 3만건을 제공한다거나 확보 가능하다는 예측은 하지 않는다.** 현재 계약/검증 상태로 목표 달성을 보장할 수 없으며 확보 가능한 feed 규모·갱신주기·저장권을 먼저 측정해야 한다.

## 네트워크별 공식 데이터 경로

| 경로 | 공식 문서 | 확인된 기능 | 선행 조건·한계 |
|---|---|---|---|
| Awin | [Feed 목록 다운로드](https://help.awin.com/developers/docs/downloading-a-list-of-your-product-feeds), [Enhanced JSONL](https://help.awin.com/apidocs/retail-publisher-productapidocumentation-1) | 접근 가능한 광고주별 feed 목록·갱신일·행수·다운로드 링크 | Publisher ID와 data feed key 또는 Bearer token. 광고주별 사용조건 적용. 일반 Publisher API 키와 feed key 구분 |
| CJ | [개발자 포털](https://developers.cj.com/), [인증](https://developers.cj.com/authentication/overview) | 퍼블리셔 Product Feed GraphQL API | PAT·publisher 자격 및 광고주별 접근 범위. 계정 승인 전 브랜드/규모 미확정 |
| Impact | [공식 Integrations](https://integrations.impact.com/), [Catalog 버전 안내](https://integrations.impact.com/impact-publisher/changelog/catalogs-endpoint-versions-update) | Partner용 catalog API 계열 존재 | 승인된 계약과 계정의 현행 레퍼런스 필요. 오래된 예제의 v11 이하 사용 금지 |
| Rakuten Advertising | [Product Search](https://developers.rakutenadvertising.com/guides/product_search) | 파트너 광고주 상품 검색, XML | Bearer token·광고주별 권한. Rakuten Ichiba API와 다른 서비스. 검색은 전체 export 보장이 아님 |

제휴 네트워크는 단순 광고 링크·거래 실적 API만 제공할 수도 있다. **실제 상품 피드의 존재·명시적 계약이 확인된 광고주만 수집 대상으로 승격**한다.

## 실제 수행한 무자격 후보 검증

Apple Books는 [현행 공식 Search API 문서](https://performance-partners.apple.com/search-api)의 전자책 검색을 3개로 제한해 준비했다. 자체 UA `ai-shopping-search-db-samples/1.0`로 `https://itunes.apple.com/robots.txt`를 조회한 결과 HTTP 200, 일반 그룹 `Disallow: /search*`가 적용됐다. 따라서 **상품 endpoint 요청은 0회**이며 검증된 상품도 0개다. 이를 API가 HTTP 오류를 반환한 것으로 보고하지 않는다. 허용 봇 사칭이나 다른 IP 경유를 시도하지 않았다. 공식 EPF 문서가 존재하더라도 도서 제공 범위·자격·보존권은 별도 확인이 필요하다.

증거: 검증 기록 (??? ???? ? ?????? ??), robots 원본 (??? ???? ? ?????? ??). 기존 7개 사이트의 앞선 감사 (??? ???? ? ?????? ??)도 유지했다. 새 후보 140개 중 robots·약관 전문을 모두 검증한 것은 아니며 미확인 행을 허용 웹수집 경로로 표시하지 않았다.

## 카테고리별 후보

주 카테고리는 분류용이며 복수 카테고리를 취급하는 몰도 한 번만 기재했다. `country`는 브랜드/기준 서비스의 참조 국가이고 실제 응답 리다이렉트·배송 가능국·가격 통화를 확정하는 값이 아니다. 국가별 storefront를 구현할 때 다시 정해야 한다. 아래의 “제공 요청/문의”는 **확보된 경로가 아니라 다음 확인 행동**이다.

| 주 카테고리 | 후보 수 |
|---|---:|
| 식품·식자재 | 14 |
| 의류·패션 | 14 |
| 종합몰 | 15 |
| 전자제품 | 15 |
| 뷰티 | 14 |
| 가구·인테리어 | 13 |
| 스포츠·아웃도어 | 14 |
| 도서 | 14 |
| 반려동물 | 11 |
| 중고·리셀 | 16 |
| 합계 | 140 |

### 식품·식자재

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| kurly | [컬리](https://www.kurly.com/) (KR) | 제한 확인 | 판매자·제휴 데이터 제공 요청. 웹 검색은 허용되나 상품 API는 자체 UA 금지. 필요: 공식 데이터 제공 승인; 판매자 데이터 범위 확인 | [문서/안내](https://api.kurly.com/robots.txt) · [공식 주소 확인](https://www.kurly.com/). 이전 실제 robots 원본에서 API 일반봇 전체금지, 상품 응답0. 약관의 무단수집 제한도 별도 확인 홈 조회: 공식 페이지 응답 확인. |
| oasis | [오아시스마켓](https://www.oasis.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.oasis.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| nhmall | [농협몰](https://www.nonghyupmall.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.nonghyupmall.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| foodspring | [식봄](https://www.foodspring.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.foodspring.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| baeminmart | [배민상회](https://mart.baemin.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://mart.baemin.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 본문 확인 불충분. |
| cjmarket | [CJ더마켓](https://www.cjthemarket.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.cjthemarket.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| dongwon | [동원몰](https://www.dongwonmall.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.dongwonmall.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| jungone | [정원e샵](https://www.jungoneshop.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.jungoneshop.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| ottogi | [오뚜기몰](https://www.otokimall.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.otokimall.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| pulmuone | [풀무원 공식몰](https://shop.pulmuone.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://shop.pulmuone.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| kroger | [Kroger](https://www.kroger.com/) (US) | 정책 확인 필요 | 공식 개발자 포털의 Products API 제공범위 재확인. 공식 문서 본문 미확인; 전체몰/점포별 범위 미확정. 필요: 현재 Public Products 문서·자격·지역별 가격필드·계약 확인 | [문서/안내](https://developer.kroger.com/reference) · [공식 주소 확인](https://www.kroger.com/). 공식 개발자 포털은 응답하지만 본문을 읽을 수 없어 자격·endpoint를 1차근거로 확정하지 않음 홈 조회: 공식 페이지 응답 확인. |
| ocado | [Ocado](https://www.ocado.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.ocado.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| thrive | [Thrive Market](https://thrivemarket.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://thrivemarket.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| costco | [Costco](https://www.costco.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.costco.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |

### 의류·패션

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| musinsa | [무신사](https://www.musinsa.com/) (KR) | 제한 확인 | 공식 데이터 제휴 요청. 확인된 자체 UA 웹검색 경로 금지; 제휴 제공범위 미확인. 필요: 데이터 제공 제휴/상품 보유 브랜드 승인 | [문서/안내](https://www.musinsa.com/robots.txt) · [공식 주소 확인](https://www.musinsa.com/). 보존된 robots는 자체 UA에 * Disallow: /. 특정 허용 봇 규칙을 적용하지 않음 홈 조회: 공식 페이지 응답 확인. |
| 29cm | [29CM](https://www.29cm.co.kr/) (KR) | 승인 필요 | 공식 파트너 외부연동 API. 판매자/파트너 권한 내 상품 검색·조회(전체몰 권한 아님). 필요: 파트너 발급키·읽기 권한·데이터 이용 동의 | [문서/안내](https://partner-stage.one.musinsa.com/29cm_category_v2_api.html) · [공식 주소 확인](https://www.29cm.co.kr/). 공식 Partner-Key 기반 items/search·items/{key} 문서. 웹은 사전 동의 없는 추출 제한 약관 확인 홈 조회: 공식 페이지 응답 확인. |
| zigzag | [지그재그](https://zigzag.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://zigzag.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| ably | [에이블리](https://a-bly.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://a-bly.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 본문 확인 불충분. |
| wconcept | [W컨셉](https://www.wconcept.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.wconcept.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| eql | [EQL](https://www.eqlstore.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.eqlstore.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| ssf | [SSF SHOP](https://www.ssfshop.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.ssfshop.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| lfmall | [LF몰](https://www.lfmall.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.lfmall.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 본문 확인 불충분. |
| hfashion | [H패션몰](https://www.hfashionmall.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.hfashionmall.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| farfetch | [FARFETCH](https://www.farfetch.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.farfetch.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| asos | [ASOS](https://www.asos.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.asos.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| zalando | [Zalando](https://www.zalando.de/) (DE) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.zalando.de/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| nordstrom | [Nordstrom](https://www.nordstrom.com/) (US) | 승인 필요 | 공식 제휴 프로그램; 상품 피드 제공 여부 문의. 승인된 제휴 콘텐츠만; 상품 피드는 미확정. 필요: 프로그램 승인·상품 피드 제공/저장/갱신 범위 확인 | [문서/안내](https://www.nordstrom.com/browse/affiliate-program) · [공식 주소 확인](https://www.nordstrom.com/). 공식 퍼블리셔 affiliate 모집. 상품 피드 제공·현재 데이터 권한은 미확인 홈 조회: 공식 페이지 응답 확인. |
| uniqlo | [UNIQLO](https://www.uniqlo.com/) (JP) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.uniqlo.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |

### 종합몰

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| ssg | [SSG.COM](https://www.ssg.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.ssg.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| coupang | [쿠팡](https://www.coupang.com/) (KR) | 승인 필요 | 파트너스 제휴 검토; 판매자 OPEN API 별도. 파트너스 광고용 상품 범위와 판매자 자신 상품 관리 구분. 필요: 파트너스 승인·API 제공 자격·데이터 저장/광고 목적 계약 확인 | [문서/안내](https://partners.coupang.com/) · [공식 주소 확인](https://www.coupang.com/). 공식 파트너스 프로그램 존재 확인. 판매자 상품등록 API는 전체몰 상품검색이 아님. 현행 제휴 API endpoint 권한은 미확인 홈 조회: 공식 페이지 응답 확인. |
| 11st | [11번가](https://www.11st.co.kr/) (KR) | 정책 확인 필요 | 기존 공식 ProductSearch 구현의 현행 지원·자격 검토. 기존 backend는 상품검색; crawler의 비공식 검색호스트와 별도. 필요: 현행 ProductSearch 지원 확인·ELEVENST_API_KEY·이용 조건 | [문서/안내](https://openapi.11st.co.kr/openapi/OpenApiFrontMain.tmall) · [공식 주소 확인](https://www.11st.co.kr/). 포털·키 발급 안내 및 backend/collectors/elevenst.py 구현 확인. 최신 ProductSearch 계약/기능까지 미확인, 키 없음 홈 조회: 도구 접근 실패. |
| gmarket | [G마켓](https://www.gmarket.co.kr/) (KR) | 승인 필요 | ESM Trading API. 판매자 자신/위임 계정 등록 상품. 필요: ESM 판매자 인증·권한·상품 제공 동의 | [문서/안내](https://etapi.gmarket.com/160) · [공식 주소 확인](https://www.gmarket.co.kr/). 공식 상품목록조회 문서가 ESM+ 등록상품·siteSellerId·siteId를 정의. 전체마켓 공개검색 API 아님 홈 조회: 공식 페이지 응답 확인. |
| auction | [옥션](https://www.auction.co.kr/) (KR) | 승인 필요 | ESM Trading API. 옥션 판매자 자신/위임 계정 등록 상품. 필요: ESM 판매자 자격·조회 권한·상품 제공 동의 | [문서/안내](https://etapi.gmarket.com/160) · [공식 주소 확인](https://www.auction.co.kr/). ESM 문서의 siteId=1은 옥션·2는 G마켓. 별도 두 사이트로 기재하되 커넥터 공유 홈 조회: 공식 페이지 응답 확인. |
| lotteon | [롯데ON](https://www.lotteon.com/) (KR) | 승인 필요 | 공식 판매자 OpenAPI. 판매자 보유/위임 상품; 전체몰 조회권으로 해석 금지. 필요: 판매자 키·보유 상품 데이터 제공권 | [문서/안내](https://api.lotteon.com/apiGuide) · [공식 주소 확인](https://www.lotteon.com/). 입점 판매자용 상품·주문 API 및 판매자센터 인증키 안내. 자체 UA 웹검색은 robots 금지 홈 조회: 본문 확인 불충분. |
| amazon | [Amazon](https://www.amazon.com/) (US) | 제한 확인 | Creators API(제휴) / SP-API(판매자) 구분. 제휴 광고 목적 카탈로그; SP-API는 판매자 권한. 필요: 본 프로젝트 집계·장기DB 목적에 대한 명시적 서면 승인 후 자격 발급 | [문서/안내](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction) · [공식 주소 확인](https://www.amazon.com/). Creators API 상품검색·자격 명시. 공식 Program policies는 서면 승인 없는 집계·분석·추출·재목적화 제한 홈 조회: 공식 페이지 응답 확인. |
| rakuten | [Rakuten Ichiba](https://www.rakuten.co.jp/) (JP) | 자격증명 필요 | 공식 상품 검색 API. 시장 내 검색 결과(판매자 소유 상품에 한정되지 않음). 필요: 앱 승인·applicationId·accessKey; 현행 이용약관과 대량 조회 범위 확인 | [문서/안내](https://webservice.rakuten.co.jp/documentation/ichiba-item-search) · [공식 주소 확인](https://www.rakuten.co.jp/). 2026-07-01 버전 문서에 상품 검색 및 applicationId와 accessKey 필수 명시. 경매·C2C 등 제외 홈 조회: 공식 페이지 응답 확인. |
| yahoo | [Yahoo!ショッピング](https://shopping.yahoo.co.jp/) (JP) | 자격증명 필요 | 공식 상품 검색 API v3. Yahoo! 쇼핑 검색 결과. 필요: Yahoo! JAPAN Client ID와 이용 조건 확인 | [문서/안내](https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html) · [공식 주소 확인](https://shopping.yahoo.co.jp/). 공식 v3 문서가 shopping.yahooapis.jp의 itemSearch와 appid 요청을 정의 홈 조회: 공식 페이지 응답 확인. |
| aliexpress | [AliExpress](https://www.aliexpress.com/) (CN) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.aliexpress.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| walmart | [Walmart](https://www.walmart.com/) (US) | 승인 필요 | Marketplace/Supplier API; 제휴 카탈로그는 별도 문의. 판매자·공급사 자격 데이터(전체 Walmart 소비자검색 아님). 필요: 판매자/공급사 승인·OAuth·허용된 상품 범위 | [문서/안내](https://developer.walmart.com/) · [공식 주소 확인](https://www.walmart.com/). 공식 포털은 Marketplace 판매자와 1P Supplier API로 구분. 전체 상품공개검색 권한 확인 못함 홈 조회: 공식 페이지 응답 확인. |
| target | [Target](https://www.target.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.target.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| etsy | [Etsy](https://www.etsy.com/) (US) | 승인 필요 | Etsy Open API v3 활성 listing 검색. findAllListingsActive 검색; 개인 상점 관리 API와 구분. 필요: 앱 키·shared secret·상업적 접근/사용범위 승인 확인 | [문서/안내](https://developers.etsy.com/documentation/reference) · [공식 주소 확인](https://www.etsy.com/). 공식 레퍼런스에 findAllListingsActive, api_key 인증, 페이지 최대100 정의. 요청규격은 keystring:shared_secret 형식 홈 조회: 공식 페이지 응답 확인. |
| lazada | [Lazada](https://www.lazada.sg/) (SG) | 정책 확인 필요 | Open Platform 공식 권한·상품조회 범위 확인. 미확인; 전체 쇼핑몰 검색 API로 간주 금지. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | [문서/안내](https://open.lazada.com/) · [공식 주소 확인](https://www.lazada.sg/). 공식 Open Platform은 응답하나 문서 본문 없음. 판매자 권한/전체 카탈로그 접근 범위 미확인 홈 조회: 공식 페이지 응답 확인. |
| shopee | [Shopee](https://shopee.sg/) (SG) | 정책 확인 필요 | Open Platform 공식 권한·데이터 범위 확인. 미확인; 전체 쇼핑몰 검색 API로 간주 금지. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | [문서/안내](https://open.shopee.com/) · [공식 주소 확인](https://shopee.sg/). 공식 Open Platform 도구 조회403. 판매자/partner 상품관리와 전몰 조회범위·현행 문서 미확인 홈 조회: 공식 페이지 응답 확인. |

### 전자제품

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| danawa | [다나와](https://www.danawa.com/) (KR) | 승인 필요 | 공식 상품조회 MCP 연결. 상품 검색·판매처 가격 조회; 영구 카탈로그 덤프 미확인. 필요: 허용된 커넥터 연결·DB 저장/재사용 범위 확인 | [문서/안내](https://mcp.ai.cowave.kr/docs) · [공식 주소 확인](https://www.danawa.com/). 2026-11-06 갱신 공식 MCP 문서에 search_products 및 커넥터 서버 IP 허용 목록. 현재 연결 도구 없음. HTML 무단 복제·가공 제한은 별도 홈 조회: 공식 페이지 응답 확인. |
| compuzone | [컴퓨존](https://www.compuzone.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.compuzone.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| himart | [롯데하이마트](https://www.e-himart.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.e-himart.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 본문 확인 불충분. |
| etland | [전자랜드](https://www.etlandmall.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.etlandmall.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| samsung | [삼성닷컴](https://www.samsung.com/sec/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.samsung.com/sec/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| lge | [LG전자](https://www.lge.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.lge.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| apple | [Apple Store](https://www.apple.com/shop/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.apple.com/shop/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| bestbuy | [Best Buy](https://www.bestbuy.com/) (US) | 자격증명 필요 | 공식 Products API. 현재 및 과거 제품 카탈로그; 현재 판매 offer와 구분. 필요: 개발자 API key; 장기 보존은 별도 계약 확인 | [문서/안내](https://developer.bestbuy.com/apis) · [공식 주소 확인](https://www.bestbuy.com/). 공식 Products API 제공 확인. legal 문서는 임시 캐시72시간 제한 명시. API key 필요 홈 조회: 공식 페이지 응답 확인. |
| newegg | [Newegg](https://www.newegg.com/) (US) | 승인 필요 | 공식 affiliate 상품 카탈로그/RSS; 판매자 API와 별도. 제휴 프로그램에서 제공하는 상품 카탈로그 범위. 필요: 퍼블리셔 신청 승인·제휴 피드 접근키·저장/갱신 계약 | [문서/안내](https://promotions.newegg.com/affiliate_program/affiliate.html) · [공식 주소 확인](https://www.newegg.com/). 공식 affiliate 페이지가 다회 갱신 상품 카탈로그·RSS·Rakuten Marketing을 통한 신청 심사를 명시 홈 조회: 공식 페이지 응답 확인. |
| bh | [B&H Photo Video](https://www.bhphotovideo.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.bhphotovideo.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| adorama | [Adorama](https://www.adorama.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.adorama.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| microcenter | [Micro Center](https://www.microcenter.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.microcenter.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| currys | [Currys](https://www.currys.co.uk/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.currys.co.uk/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| biccamera | [ビックカメラ](https://www.biccamera.com/) (JP) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.biccamera.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| yodobashi | [ヨドバシ.com](https://www.yodobashi.com/) (JP) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.yodobashi.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |

### 뷰티

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| oliveyoung | [올리브영](https://www.oliveyoung.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.oliveyoung.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 본문 확인 불충분. |
| amore | [아모레몰](https://www.amoremall.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.amoremall.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| innisfree | [이니스프리](https://www.innisfree.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.innisfree.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| thefaceshop | [더페이스샵](https://www.thefaceshop.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.thefaceshop.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 본문 확인 불충분. |
| missha | [미샤](https://www.missha.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.missha.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 본문 확인 불충분. |
| tonymoly | [토니모리](https://tonymoly.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://tonymoly.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| clio | [클럽클리오](https://clubclio.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://clubclio.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| sephora | [Sephora](https://www.sephora.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.sephora.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| ulta | [Ulta Beauty](https://www.ulta.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.ulta.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| lookfantastic | [LOOKFANTASTIC](https://www.lookfantastic.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.lookfantastic.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| cultbeauty | [Cult Beauty](https://www.cultbeauty.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.cultbeauty.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| yesstyle | [YesStyle](https://www.yesstyle.com/) (HK) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.yesstyle.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| iherb | [iHerb](https://www.iherb.com/) (US) | 승인 필요 | 공식 affiliate 제휴; 네트워크 피드 제공 여부 확인. 승인된 광고주/국가 카탈로그만; 전 상품 피드는 미확인. 필요: 네트워크 퍼블리셔 및 iHerb 승인; 실제 feed 제공 여부·권한 확인 | [문서/안내](https://www.iherb.com/info/affiliates) · [공식 주소 확인](https://www.iherb.com/). 공식 안내에서 Partnerize·Impact·CJ·Awin과 쇼핑비교 파트너 모집 확인. 특정 계정의 상품 피드 접근은 미검증 홈 조회: 공식 페이지 응답 확인. |
| stylekorean | [STYLEKOREAN](https://www.stylekorean.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.stylekorean.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |

### 가구·인테리어

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| ohouse | [오늘의집](https://ohou.se/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://ohou.se/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| hanssem | [한샘몰](https://store.hanssem.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://store.hanssem.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| livart | [현대리바트](https://www.hyundailivart.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.hyundailivart.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| iloom | [일룸](https://www.iloom.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.iloom.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| desker | [데스커](https://www.desker.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.desker.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| marketb | [마켓비](https://www.marketb.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.marketb.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| guud | [까사미아·굳닷컴](https://www.guud.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.guud.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| ikea | [IKEA](https://www.ikea.com/) (SE) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.ikea.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| wayfair | [Wayfair](https://www.wayfair.com/) (US) | 승인 필요 | 공식 제휴 프로그램; 상품 피드 제공 여부 문의. 승인된 제휴 콘텐츠만; 상품 피드는 미확정. 필요: 프로그램 승인·상품 피드 제공/저장/갱신 범위 확인 | [문서/안내](https://www.wayfair.com/m/creators/) · [공식 주소 확인](https://www.wayfair.com/). 공식 creator 제휴·링크 기반 홍보 확인. 전체 상품피드 제공은 미확인 홈 조회: 공식 페이지 응답 확인. |
| westelm | [West Elm](https://www.westelm.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.westelm.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| potterybarn | [Pottery Barn](https://www.potterybarn.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.potterybarn.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| cratebarrel | [Crate & Barrel](https://www.crateandbarrel.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.crateandbarrel.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| article | [Article](https://www.article.com/) (CA) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.article.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |

### 스포츠·아웃도어

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| nike | [Nike](https://www.nike.com/) (US) | 승인 필요 | 공식 제휴 프로그램; 상품 피드 제공 여부 문의. 승인된 제휴 콘텐츠만; 상품 피드는 미확정. 필요: 프로그램 승인·상품 피드 제공/저장/갱신 범위 확인 | [문서/안내](https://www.nike.com/help/a/nike-affiliate-program) · [공식 주소 확인](https://www.nike.com/). 공식 affiliate 안내 주소 확인. 현재 국가별 가입·피드 범위는 별도 확인 필요 홈 조회: 공식 페이지 응답 확인. |
| adidas | [adidas](https://www.adidas.com/) (DE) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.adidas.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| decathlon | [Decathlon](https://www.decathlon.com/) (FR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.decathlon.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| underarmour | [Under Armour](https://www.underarmour.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.underarmour.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| newbalance | [뉴발란스 코리아](https://www.nbkorea.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.nbkorea.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| asics | [ASICS Korea](https://www.asics.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.asics.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 본문 확인 불충분. |
| fila | [FILA Korea](https://www.fila.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.fila.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| kolon | [코오롱스포츠](https://www.kolonsport.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.kolonsport.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| k2 | [K2](https://www.k2.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.k2.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| blackyak | [블랙야크](https://www.byn.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.byn.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| rei | [REI](https://www.rei.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.rei.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| dicks | [DICK'S Sporting Goods](https://www.dickssportinggoods.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.dickssportinggoods.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| backcountry | [Backcountry](https://www.backcountry.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.backcountry.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| gymshark | [Gymshark](https://www.gymshark.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.gymshark.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |

### 도서

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| kyobo | [교보문고](https://www.kyobobook.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.kyobobook.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| yes24 | [YES24](https://www.yes24.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.yes24.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| aladin | [알라딘](https://www.aladin.co.kr/) (KR) | 정책 확인 필요 | OpenAPI/상품DB 제휴 문의; 현행 서비스 상태 재확인. 기존 TTB/API 자료를 현재 지원 증거로 사용하지 않음. 필요: 서비스 종료 여부·대체 제휴DB 제공 여부를 공식 확인 | [문서/안내](https://www.aladin.co.kr/partnership/wguide.aspx) · [공식 주소 확인](https://www.aladin.co.kr/). 공식 OpenAPI/상품DB 문의처 확인. 공식 도메인 검색 색인에는 종료 공지(26.10.30) 제목이 있으나 최신 본문에서 재확인 못함 홈 조회: 공식 페이지 응답 확인. |
| ypbooks | [영풍문고](https://www.ypbooks.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.ypbooks.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| applebooks | [Apple Books](https://books.apple.com/) (US) | 제한 확인 | 공식 iTunes Search API / EPF 대량피드 조건 문의. 국가별 Apple Books 전자책 판매정보 검색. 필요: 현재 주체·경로 허용 여부와 EPF 제공/저장권 확인 | [문서/안내](https://performance-partners.apple.com/search-api) · [공식 주소 확인](https://books.apple.com/). 공식 API 문서 존재. 실제 itunes robots200의 일반봇 /search* 금지로 상품요청 전 중단. 응답 검증0 홈 조회: 공식 페이지 응답 확인. |
| bookshop | [Bookshop.org](https://bookshop.org/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://bookshop.org/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| bn | [Barnes & Noble](https://www.barnesandnoble.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.barnesandnoble.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| waterstones | [Waterstones](https://www.waterstones.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.waterstones.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| blackwells | [Blackwell's](https://blackwells.co.uk/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://blackwells.co.uk/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| abebooks | [AbeBooks](https://www.abebooks.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.abebooks.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| thriftbooks | [ThriftBooks](https://www.thriftbooks.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.thriftbooks.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| betterworld | [Better World Books](https://www.betterworldbooks.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.betterworldbooks.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| powells | [Powell's Books](https://www.powells.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.powells.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| bam | [Books-A-Million](https://www.booksamillion.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.booksamillion.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |

### 반려동물

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| petfriends | [펫프렌즈](https://www.pet-friends.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.pet-friends.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| fitpet | [핏펫몰](https://www.fitpetmall.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.fitpetmall.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| aboutpet | [어바웃펫](https://www.aboutpet.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.aboutpet.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| dogpre | [강아지대통령](https://dogpre.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://dogpre.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| catpre | [고양이대통령](https://catpre.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://catpre.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| chewy | [Chewy](https://www.chewy.com/) (US) | 승인 필요 | 공식 제휴 프로그램; 상품 피드 제공 여부 문의. 승인된 제휴 콘텐츠만; 상품 피드는 미확정. 필요: 프로그램 승인·상품 피드 제공/저장/갱신 범위 확인 | [문서/안내](https://www.chewy.com/app/content/affiliate) · [공식 주소 확인](https://www.chewy.com/). 공식 Impact 기반 affiliate 승인·링크 도구 안내. 상품 카탈로그 API/피드 제공은 별도 확인 필요 홈 조회: 공식 페이지 응답 확인. |
| petco | [Petco](https://www.petco.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.petco.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| petsmart | [PetSmart](https://www.petsmart.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.petsmart.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| zooplus | [zooplus](https://www.zooplus.com/) (DE) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.zooplus.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| petsathome | [Pets at Home](https://www.petsathome.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.petsathome.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| petcircle | [Pet Circle](https://www.petcircle.com.au/) (AU) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.petcircle.com.au/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |

### 중고·리셀

| ID | 쇼핑몰·공식 주소 | 상태 | 상품 데이터 확보 방법·범위 | 공식 문서·확인 근거 |
|---|---|---|---|---|
| joongna | [중고나라](https://web.joongna.com/) (KR) | 정책 확인 필요 | 공식 데이터 제휴·제공범위 문의. 웹 공개경로 허용은 내부 검색API 이용허가 아님. 필요: 데이터 수집·저장·개인판매자 정보 처리권한 확인 | [문서/안내](https://web.joongna.com/cs-center?categorySeq=6&faqSeq=160) · [공식 주소 확인](https://web.joongna.com/). 공식 광고/제휴 문의 확인. 기존 search-api 경로의 외부 사용계약 미확인. 상품 응답0 홈 조회: 공식 페이지 응답 확인. |
| bunjang | [번개장터](https://m.bunjang.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://m.bunjang.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| daangn | [당근](https://www.daangn.com/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.daangn.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| kream | [KREAM](https://kream.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://kream.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| soldout | [솔드아웃](https://www.soldout.co.kr/) (KR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.soldout.co.kr/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| ebay | [eBay](https://www.ebay.com/) (US) | 승인 필요 | Browse API; 별도 Feed API 승인 검토. 마켓플레이스 활성 판매 목록 검색; 판매자 관리 API와 별도. 필요: 개발자 키·OAuth Application token·운영 접근 승인/사용계약 | [문서/안내](https://developer.ebay.com/api-docs/buy/browse/overview.html) · [공식 주소 확인](https://www.ebay.com/). Browse의 검색 기능 및 Application token을 공식 확인. Buy API 운영 접근은 파트너 심사·계약 요구. backend에 기존 구현 있음 홈 조회: 공식 페이지 응답 확인. |
| stockx | [StockX](https://stockx.com/) (US) | 승인 필요 | 공식 Catalog API + 허용된 market data 조회. 카탈로그·variant와 판매자 listing 관리 기능 구분. 필요: 개발자 심사·API key·OAuth·market data 승인범위 | [문서/안내](https://developer.stockx.com/portal/getting-started) · [공식 주소 확인](https://stockx.com/). 공식 문서에 카탈로그 검색, 개발자 승인 후 키·OAuth 명시. catalog 제품 식별만으로 판매 가격 offer 확보를 의미하지 않음 홈 조회: 공식 페이지 응답 확인. |
| goat | [GOAT](https://www.goat.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.goat.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| grailed | [Grailed](https://www.grailed.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.grailed.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| vestiaire | [Vestiaire Collective](https://www.vestiairecollective.com/) (FR) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.vestiairecollective.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| therealreal | [The RealReal](https://www.therealreal.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.therealreal.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| vinted | [Vinted](https://www.vinted.com/) (LT) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.vinted.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| mercari | [Mercari Japan](https://jp.mercari.com/) (JP) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://jp.mercari.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 도구 접근 실패. |
| poshmark | [Poshmark](https://poshmark.com/) (US) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://poshmark.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| depop | [Depop](https://www.depop.com/) (GB) | 정책 확인 필요 | 공식 피드·제휴 데이터 제공 여부 문의. 미확인. 필요: 상품 데이터 제공 계약/피드 존재와 외부 검색·저장·재사용 조건 확인 | 연동 문서 미확인 · [공식 주소 확인](https://www.depop.com/). 공식 주소 조회를 수행했다. 상품 데이터 API·피드 제공 및 웹자동수집 허용은 확인하지 못했다. 홈 조회: 공식 페이지 응답 확인. |
| reverb | [Reverb](https://reverb.com/) (US) | 승인 필요 | 공식 Reverb JSON API. 마켓플레이스/계정별 리소스는 승인된 endpoint·scope에 한정. 필요: 앱 등록·production 접근·토큰·카탈로그 읽기 범위 확인 | [문서/안내](https://reverb.com/page/api) · [공식 주소 확인](https://reverb.com/). 공식 안내에 앱 등록·인증토큰·링크 기반 리소스 탐색 명시. sandbox 안내가 있어 운영 자격 별도 확인 홈 조회: 공식 페이지 응답 확인. |

## 파일과 검증 범위

- [CSV](shopping_mall_100_candidates.csv): 140개 후보와 22개 열, UTF-8 BOM, CSV 인용/개행 규칙 적용. 문서 미확인 값은 빈 칸이며 0개 상품 응답은 실제 0이다.
- 본 문서의 상위 10개와 전체 후보는 동일 원본에서 생성했고 ID·공식 주소 중복, 상태별/카테고리별 합계, 우선순위 1~10 유일성을 확인한다.
- 기존 `crawler_engine/`, `backend/`, DB 스키마·DB 데이터는 수정하지 않았다. 이 작업의 홈페이지/API 문서 조회와 실제 상품 endpoint 요청은 구분했다.
- 공개 검색도구의 접근 결과는 그 도구의 수집 시점/캐시·지역에 영향을 받는다. `checked_date`는 이번 확인일이며 페이지의 발행일·데이터 관측일이 아니다.
- 공식 프로그램·API의 조건은 바뀔 수 있다. 구현 직전에 문서 버전·본인 계정 자격·쿼터·캐시/표시/재배포 조건을 재확인해야 한다.


??? ??: ? ?? ??? ?? ??? ????. ?? ??? [??? ?? ??](live_crawler_progress.md)? ???. ?? ?? ??? ?? ??? ???? ? ??? worktree?? ???? ???.
