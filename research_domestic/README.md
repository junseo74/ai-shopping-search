# 국내 쇼핑몰 공식 데이터 소스 조사

조사일: 2026-11-08 (Asia/Seoul). 브랜치: `feature/domestic-source-research`. 신규 파일은 모두 `research_domestic/` 안에 작성했다. 브랜치 전환·병합·커밋·푸시를 수행하지 않았다.

30개 후보를 조사했다. 최종 분류는 **성공 1개 / 인증 대기 7개 / 정책 확인 필요 21개 / 접근 불가 1개**다. 상품명·판매가·URL의 실제 응답 검증은 **2개 사이트, 각 3건(총 6건)**에서 성공했다. 이 중 예스24 RSS는 오래된 자료다. 최근 발행 피드를 확인한 곳은 **알라딘 1개**이며, 영구 상품 DB 저장·상용 재사용까지 승인된 운영 연동은 **0개**다. 성공은 응답 필드 검증을 뜻하며 저장 라이선스 승인을 뜻하지 않는다.

## 실제 응답 검증

| 사이트 | 실제 요청 | 검증 결과 | 최신성 및 한계 |
|---|---|---|---|
| 예스24 | [공식 RSS](https://www.yes24.com/_par_/Rss/KBO001.xml) | HTTP 200; 같은 상품의 필드 3건 검증 | 본문 2025-06-08, 피드 생성 2025-06-07. 현재 가격 소스로 제외; API 키 발급 대기 |
| 알라딘 | [공식 RSS](https://www.aladin.co.kr/rss/new_all/351) | HTTP 200; 같은 상품의 필드 3건 검증 | 피드 생성 2026-11-08. 컴퓨터/모바일 신간 일부만 포함; 전 카탈로그 검색 아님 |

알라딘 RSS는 공식 [분야별 모든 신간 안내](https://www.aladin.co.kr/rsscenter/new_all.aspx)와 분야 페이지의 `rel=alternate` 링크에서 찾았다. 예스24 RSS는 공식 [베스트셀러 RSS 안내](https://www.yes24.com/rss/bestSeller.aspx)에 공개된 주소다. 게시된 RSS의 HTTPS 주소로만 요청했고 상품 상세페이지나 피드의 링크를 따라가지 않았다. 구독 목적의 소량 응답 검사이며, 외부 검색 서비스에서의 저장·재사용 승인으로 간주하지 않는다.

예스24는 여러 책이 하나의 RSS item 설명에 들어 있어 각 상품 링크부터 다음 상품 링크 전까지의 판매가를 묶었다. 채널 제목을 상품명으로 오인하지 않는다. 알라딘은 정가 대신 명시된 판매가를 검사한다. 원문·상품명·상품 URL은 파일에 저장하지 않았고, 해시·검증 여부·판매가 수치·피드 날짜만 남겼다. 실제 검증 증거는 [public_verification.json](public_verification.json), 주소 발견 근거는 [document_discovery.json](document_discovery.json)과 [rss_discovery.json](rss_discovery.json)이다.

## 우선 연동 및 승인 추진 10개

아래 순위는 조건 충족 후 연동할 후보의 순서다. 10개 모두 즉시 운영 가능한 소스라는 뜻은 아니다. 1~7은 실제 공식 카탈로그/상품 API가 확인된 후보, 8은 범위 협의가 필요한 직접 제휴, 9~10은 현행 상품 DB 공급 가능성부터 확인할 예비 후보다. 도매꾹·도매매는 서로 다른 몰이지만 공통 API 제공자이므로 독립 인증 시스템 2개로 집계하지 않는다.

| 순위 | 몰 | 선정 이유 | 남은 절차 |
|---|---|---|---|
| 1 | [알라딘](https://www.aladin.co.kr/ttb/wmain.aspx) | 신간 RSS 실제 검증 성공; TTB 검색 API와 저장권 확인을 우선 | TTBKey 발급; 상품 정보 저장·상용 검색 재사용·가격 갱신 허용 범위를 공식 확인 |
| 2 | [예스24](https://developers.yes24.com/api-doc/goods-item-list) | 현행 전체 카탈로그 검색 문서와 즉시 키 발급; API 캐시 중심 설계 필요 | 키 발급 후 API 1~3건 검증; 프로젝트 영구 상품 DB 구조는 별도 허가 전 연동 보류; RSS 갱신 여부 문의 |
| 3 | [11번가](https://openapi.11st.co.kr/openapi/OpenApiGuide.tmall) | 전 카탈로그 검색용 ProductSearch 공식 가이드 및 기존 수집기 접점 | ProductSearch 사용 가능 키 발급 및 현행 약관의 캐시/저장/가격 갱신 조건 확인 |
| 4 | [도매꾹](https://docs.channel.io/domeggook_api/ko/articles/43780628) | 공식 검색 API에 상품명·단가·URL 명시 | Open API 키 발급; 시장별 1~3건 검증; 도매 단가·최소주문수량·사업자 전용 여부 보존; 외부 DB 저장 권한 확인 |
| 5 | [도매매](https://docs.channel.io/domeggook_api/ko/articles/43780628) | 도매매 market=supply로 동일 공식 엔진 재사용 가능 | Open API 키 발급; 시장별 1~3건 검증; 도매 단가·최소주문수량·사업자 전용 여부 보존; 외부 DB 저장 권한 확인 |
| 6 | [오너클랜](https://ownerclan.com/V2/service/api-center-guide.php) | 판매사에 공급 카탈로그를 제공하는 공식 GraphQL; 검색 재사용권 협의 | 판매사 API 서비스 이용 가능 여부와 외부 검색 서비스 사용권 계약 확인; 실제 상품 URL 필드 사양 확보 후 최소 GraphQL 조회 구현 |
| 7 | [쿠팡](https://partners.coupang.com/#/affiliate/ws) | 판매자 API와 별개인 공식 파트너스 상품 경로; 최종 승인 필요 | 최종 승인 및 키 발급 후 현재 검색 권한·광고 표시·저장 조건 확인; 판매 실적 등 세부 승인 수치는 미확정 |
| 8 | [GS SHOP](https://partners.gsshop.com/api/apiMain) | 공식 제휴 API 정책·범위 협의 절차 존재 | 상품 검색/추천 서비스 제안 후 제공 카탈로그 범위·보관기간·갱신 주기 합의 |
| 9 | [에누리](https://www.enuri.com/index.html) | 공식 운영사 상품 DB 솔루션 사업 소개를 근거로 공급 계약 가능성 확인 | 검색용 DB 공급 여부·현재 계약 창구·비용·보관/갱신·제3자 노출권 확인 |
| 10 | [다나와](https://img.danawa.com/new/open_api/api_guide.html) | 가격비교 분야 보완 후보; 구형 API 대신 현행 데이터 제휴부터 확인 | 현행 상품 DB/검색 제휴 제공 여부와 보관·가공·재배포 허가 문의; 구형 endpoint 호출 보류 |

## 인증과 저장 정책에서 확인한 사항

- **네이버쇼핑**: [공식 종료 공지](https://developers.naver.com/notice/article/32530)는 쇼핑·책·전문자료 검색 API가 2026-07-31 종료되었고, 기존 키 유예나 대체 API가 없다고 명시한다. 폐지된 API는 호출하지 않았다.
- **예스24**: [공식 키 발급 안내](https://developers.yes24.com/docs/apikey)는 로그인·목적 입력·약관 동의 후 즉시 발급을 안내한다. [API 약관 제6조](https://developers.yes24.com/support/terms)는 일시 캐시, 변동정보 갱신, 출처·원상품 링크 표시를 요구하며 별도 DB 구축을 위한 체계적 축적과 재배포를 제한한다. 현재 프로젝트의 영구 상품 DB 적재에는 별도 허가가 필요하다. API 약관의 허용을 RSS나 다른 몰에 적용하지 않는다.
- **알라딘**: [TTB 공식 안내](https://www.aladin.co.kr/ttb/wmain.aspx)는 회원가입·약관 동의·URL 등록을 안내한다. 연결된 API 약관 페이지는 웹 도구에서 403으로 본문 확인이 막혀 저장권을 미확정으로 두었다. RSS 성공과 TTB API 인증 성공을 구분한다.
- **11번가**: [현행 개발가이드](https://openapi.11st.co.kr/openapi/OpenApiGuide.tmall)에서 `ProductSearch`를 직접 확인했다. 기본 서비스 소개는 판매자 API 중심이고 구형 `OpenApiSearch.tmall` 문서는 404였다. 검색용 키 발급과 캐시/가격 갱신/저장 조건은 별도 확인해야 한다.
- **도매꾹·도매매**: [공식 상품목록 v4.1](https://docs.channel.io/domeggook_api/ko/articles/43780628)은 `getItemList`, `market=dome/supply`, `title/price/url`을 명시한다. 일반 Open API 키와 로그인·주문용 Private 승인권은 다르다. 도매 단가와 최소주문수량을 소비자 단품 판매가로 혼동하면 안 된다.
- **오너클랜**: [공식 API 사용법](https://ownerclan.com/V2/service/api-center-guide.php)은 판매사 JWT와 GraphQL을 안내한다. 공급 상품을 판매 채널로 보내는 권한과 독립 가격비교 DB 사용권은 구분해야 한다. 실제 상품 URL 필드까지 확인한 뒤 최소 쿼리를 구현해야 하므로 이번에 임의 GraphQL 요청을 보내지 않았다.
- **쿠팡·GS SHOP**: 쿠팡 [공식 파트너스 가이드](https://partners.coupangcdn.com/partners-guide/partners-guide-20240716100922.pdf)와 [파트너스 포털](https://partners.coupang.com/#/affiliate/ws), GS SHOP [제휴 API 안내](https://partners.gsshop.com/api/apiMain)를 근거로 분류했다. 쿠팡 현행 계정별 검색 권한·한도·저장 정책과 GS 제공 범위는 승인 후 확인한다. 쿠팡 판매자 키를 파트너스 키로 재사용하지 않는다.

G마켓·옥션·롯데ON·CJ온스타일·카카오쇼핑 등은 판매자/권한 범위 중심이다. API나 파트너 포털이 있다는 이유로 전체 쇼핑몰 검색 권한을 가정하지 않는다. 나머지 몰의 미확인 정책에는 승인된 것으로 추정하는 대신 명시적으로 `storage_approved=false`를 기록했다. 공식 문의를 실제 발송하거나 계정 생성·약관 동의를 대행하지 않았다.

## 30개 후보 및 근거

상세 API/RSS/제휴 피드, 인증, 저장 정책, 근거 URL, 응답 확인 시각, 다음 조치는 [candidates.csv](candidates.csv)에 있다. 공개 API 미확인은 검토한 공식 자료에서 찾지 못했다는 의미이며 존재하지 않는다는 확정 판단이 아니다. 일반적인 제휴 문의 창구를 상품 피드 제공 약속으로 해석하지 않는다.

| 몰 | 범위 | 상태 | 조사 결론 / 공식 근거 |
|---|---|---|---|
| 네이버쇼핑 | retired | 접근 불가 | [공식 자료](https://developers.naver.com/notice/article/32530) — 2026-07-31 서비스 종료 공식 공지. 커머스 API는 별도의 판매자 API로 전체 쇼핑검색 대체 불가 |
| 쿠팡 | affiliate_catalog | 인증 대기 | [공식 자료](https://partners.coupang.com/#/affiliate/ws) — 공식 이용 가이드는 파트너스 상품 API를 안내. 판매자 API는 본인 상품 관리용이며 대체 검색 수단이 아님 |
| 11번가 | full_catalog | 인증 대기 | [공식 자료](https://openapi.11st.co.kr/openapi/OpenApiGuide.tmall) — 현행 공식 개발가이드에서 ProductSearch 재확인. 서비스 소개 기본 페이지는 판매자 문서이며 구형 OpenApiSearch.tmall은 404. 루트 probe의 /search/api/tab는 공식 Open API가 아님 |
| G마켓 | seller_only | 정책 확인 필요 | [공식 자료](https://etapi.gmarket.com/) — 공식 문서의 상품·프로모션 관리는 판매자 범위. 전체 상품 검색 API 권한/현행 제휴 피드는 미확인 |
| 옥션 | seller_only | 정책 확인 필요 | [공식 자료](https://api.auction.co.kr/Archesystem/mainservice.asmx) — 공식 SOAP 서비스 존재는 확인하되 전체 시장 검색 권한을 입증하지 않음. G마켓과 별도 몰로 집계하되 ESM 권한은 중복 가능 |
| SSG.COM | seller_portal_unconfirmed_api | 정책 확인 필요 | [공식 자료](https://partners.ssgadm.com/) — 공식 파트너 포털은 판매자를 위한 안내. API 계정 존재를 전체 상품 데이터 권한으로 확대 해석하지 않음 |
| 롯데ON | seller_only | 정책 확인 필요 | [공식 자료](https://api.lotteon.com/apiService/?apiNm=GetStarted) — 공용 API는 판매자 API 중 공용 규격이라는 의미. 전 쇼핑몰 상품을 누구나 검색한다는 뜻이 아님 |
| CJ온스타일 | seller_only | 정책 확인 필요 | [공식 자료](https://partners.cjonstyle.com/standardApi) — 공식 설명은 상품등록·주문조회·배송 처리. 타 판매자 포함 전체 상품 검색용으로 판단하지 않음 |
| GS SHOP | partner_contract | 인증 대기 | [공식 자료](https://partners.gsshop.com/api/apiMain) — 제휴 상품 데이터 연동을 공식 안내. 검색용 상품 피드 범위와 저장권은 계약으로 확정해야 함 |
| 현대Hmall | partner_portal_unconfirmed_api | 정책 확인 필요 | [공식 자료](https://partner.hmall.com/) — 공식 포털은 웹 검색 도구에서 읽을 본문이 없음. APIM 관련 제3자 설명만으로 사양/승인을 확정하지 않음 |
| 롯데홈쇼핑 | partner_portal_unconfirmed_api | 정책 확인 필요 | [공식 자료](https://partners.lotteimall.com/) — 공식 파트너 URL 확인. 내부 웹 XHR 경로를 API로 채택하지 않음 |
| NS홈쇼핑 | unconfirmed | 정책 확인 필요 | [공식 자료](https://www.nsmall.com/) — 공식 홈페이지가 웹 도구에 읽을 본문을 제공하지 않음. API/RSS의 부재나 서비스 장애로 단정하지 않음 |
| 홈앤쇼핑 | unconfirmed | 정책 확인 필요 | [공식 자료](https://www.hnsmall.com/) — 공식 홈페이지 웹 도구 접근은 timeout. 상품 feed 존재/인증·저장 조건은 미확인 |
| 알라딘 | full_catalog_plus_category_rss | 성공 | [공식 자료](https://www.aladin.co.kr/ttb/wmain.aspx) — 공식 TTB는 알라딘 상품 카탈로그 검색. 실응답은 컴퓨터/모바일 분야 신간 RSS 1개에서 3건만 검증 |
| 예스24 | full_catalog_plus_bestseller_rss | 인증 대기 | [공식 자료](https://developers.yes24.com/api-doc/goods-item-list) — 공식 Goods API 검색 제공. 공개 RSS는 응답하지만 본문 날짜가 2025-06-08로 오래됨. 현재 가격으로 사용 금지 |
| 교보문고 | unconfirmed | 정책 확인 필요 | [공식 자료](https://www.kyobobook.co.kr/) — 검색 페이지 내부 JSON 경로와 제3자 API 소개 글은 공식 이용 허가 증거로 사용하지 않음 |
| 도매꾹 | full_market_catalog | 인증 대기 | [공식 자료](https://docs.channel.io/domeggook_api/ko/articles/43780628) — 공식 v4.1 상품목록: title/price/url; market으로 도매꾹·도매매 구분. 서로 다른 몰이지만 공통 엔진/인증 제공자 |
| 도매매 | full_market_catalog | 인증 대기 | [공식 자료](https://docs.channel.io/domeggook_api/ko/articles/43780628) — 공식 v4.1 상품목록: title/price/url; market으로 도매꾹·도매매 구분. 서로 다른 몰이지만 공통 엔진/인증 제공자 |
| 오너클랜 | authorized_reseller_catalog | 인증 대기 | [공식 자료](https://ownerclan.com/V2/service/api-center-guide.php) — 공급 카탈로그를 판매사가 조회하는 경로. 자기 등록 상품 관리에만 한정된 API와 구분하되 소비자 검색 서비스 전용 권한은 미확인 |
| 무신사 | unconfirmed | 정책 확인 필요 | [공식 자료](https://dev-api.corp.musinsa.com/api-docs/public) — 공식 Public API 문서는 기업 홈페이지 연혁/보도자료 CMS API이며 상품 검색용이 아님 |
| 29CM | unconfirmed | 정책 확인 필요 | [공식 자료](https://www.29cm.co.kr/) — probe의 HTML·NEXT_DATA 추출 가능성을 제휴 상품 피드 허가로 취급하지 않음 |
| 에이블리 | seller_integration | 정책 확인 필요 | [공식 자료](https://square.a-bly.com/businesspage-brand) — 공식 브랜드 안내에 외부 솔루션 연동 명시. 다른 회사인 ably.com 메시징 API는 제외 |
| 지그재그 | seller_integration | 정책 확인 필요 | [공식 자료](https://partnerlounge.kakaostyle.com/brand) — 공식 파트너라운지의 API는 주문관리 맥락. 상품 피드 제공/전체 상품 검색으로 확장 해석하지 않음 |
| 오늘의집 | unconfirmed | 정책 확인 필요 | [공식 자료](https://ohou.se/contacts/new?type=request) — 공식 제휴 문의 창구만 확인. /productions/feed 같은 웹 페이지 경로는 RSS 피드가 아님 |
| 컬리 | unconfirmed | 정책 확인 필요 | [공식 자료](https://www.kurly.com/main) — 기존 probe의 HTML/임베디드 데이터와 .tmp 실험은 허가 근거가 아님. 내부 API 무단 검증 제외 |
| 올리브영 | unconfirmed | 정책 확인 필요 | [공식 자료](https://www.oliveyoung.co.kr/store/main/main.do?oy=0&transSite=true) — 공식 홈페이지의 제휴 제안 창구 확인. 상품 검색 HTML과 비공식 크롤링 API는 제외 |
| 다나와 | legacy_unconfirmed | 정책 확인 필요 | [공식 자료](https://img.danawa.com/new/open_api/api_guide.html) — 오래된 공식 가이드는 예시/미완성 필드가 있어 현행 작동 증거로 사용할 수 없음. 종료 주장도 1차 공지 미확보로 확정하지 않음 |
| 에누리 | data_licensing_unconfirmed | 정책 확인 필요 | [공식 자료](https://www.enuri.com/index.html) — 공식 운영사 소개의 상품 DB 솔루션 사업은 후보 근거. 개방형 API나 우리 서비스 사용권을 의미하지 않음 |
| 중고나라 | unconfirmed | 정책 확인 필요 | [공식 자료](https://web.joongna.com/) — 루트의 API 후보·브라우저 network probe는 내부 요청 탐색. 허가된 Open API나 라이선스로 간주하지 않음 |
| 카카오쇼핑(선물하기/톡스토어) | seller_only | 정책 확인 필요 | [공식 자료](https://shopping-developers.kakao.com/hc/ko/articles/4681097907087-카카오쇼핑-Open-API-안내) — 공식 안내의 선물하기/톡스토어 판매채널 연동. 전체 쇼핑 상품 검색 API로 분류하지 않음 |

[공식 문서 HTTP 확인 결과](document_checks.json)는 상품 데이터 성공 건수에 포함하지 않는다. 무신사 기업 CMS 문서와 올리브영 문서는 직접 요청에서 403이었고 중단했다. 홈앤쇼핑은 직접 요청 302를 따라가지 않았다. 웹 검색 도구의 요약/캐시 확인과 로컬의 실제 HTTP 응답은 구분하며, 200이어도 로그인/JS 셸이면 API 권한이나 본문 확보를 뜻하지 않는다.

## 로컬 기존 실험 분석

루트의 *_probe.py **18개**를 읽기 전용으로 분석했다. 분석 도구는 실행문을 호출하거나 import하지 않고 파일 전체를 읽어 import·함수·URL·추출 신호를 기록했다. [local_inventory.json](local_inventory.json)에 파일별 SHA-256과 분석 목록이 있다.

- 일반 쇼핑몰 probe: HTML 카드, JSON-LD, NEXT_DATA/임베디드 JSON, 가격/URL 후보를 찾는 실험이다. 파싱 가능성은 공식 수집 허가를 의미하지 않는다.
- `elevenst_api_probe.py`, `elevenst_xhr_probe.py`: 저장 HTML/자바스크립트 번들에서 검색 내부 요청을 탐색한다. `ProductSearch` Open API와 구분했다.
- 중고나라 probe 3개: HTML·API 후보·Playwright 네트워크 관찰 실험이다. 비공개 API 검증이나 브라우저 재수집을 수행하지 않았다.
- 다수 probe가 `crawler_output/` 등에 파일을 저장하므로 기존 스크립트를 실행하지 않았다. `.tmp_kurly_*` 폴더도 해시 확인만 했다.

로컬 파일 이름과 docs/backend/crawler_engine/tests의 후보 관련 텍스트를 확인했지만 기존 140개 쇼핑몰 후보 자료는 발견하지 못했다. `docs/source-access.md`의 기존 공식 접근 정책과 11번가/네이버 조사 결과는 참고했고, 공식 문서로 현재 상태만 보강했다. 미발견은 이 작업공간에서의 조사 결과이며 다른 컴퓨터/브랜치에 없다는 뜻은 아니다.

## 재실행

Node.js 20 이상, 외부 npm 패키지 불필요. 이번 환경은 Node 24.20.0으로 실행했다. `.venv`가 참조하는 Python이 없어 기존 Python 환경은 수정하지 않았다. 모든 출력 경로는 스크립트 위치 기준 `research_domestic/`로 고정된다.

```powershell
node --test research_domestic/test_rss.mjs
node research_domestic/check_public.mjs
node research_domestic/check_apis.mjs
node research_domestic/build_report.mjs
node research_domestic/inventory.mjs
```

`check_public.mjs --source=aladin` 또는 `--source=yes24`로 피드 1개만 확인할 수 있다. 두 피드를 기본 각 1회 요청하고 같은 상품의 필드 최대 3건만 검사한다. 피드 크기는 서버가 정하며 알라딘 응답 25 item 중 3개만 검사했다. 15초 timeout, 2MB 상한, 재시도·페이지 순회·리다이렉트 추적 없음. 파서 회귀 검사 3개 통과: 요약 RSS 상품 연결, 정가/판매가 구분, 잘못된 응답·외부 엔티티 거부.

`check_apis.mjs`는 프로세스 환경변수의 존재만 확인한다. `.env`를 읽지 않고 키나 헤더·원응답·키가 들어간 URL·오류 본문을 출력하지 않는다. 이번 실행에서 `YES24_API_KEY`, `ALADIN_TTB_KEY`, `ELEVENST_API_KEY`, `DOMEGGOOK_API_KEY`가 없어 5개 몰 모두 네트워크 호출 0회로 보류했다. 승인받은 키가 환경에 주입되면 `--source=yes24|aladin|elevenst|domeggook|domeme` 중 하나를 지정할 수 있으며 공식 GET을 1회, 결과 최대 3건만 검사한다. 키가 있는 경로의 라이브 실행은 아직 검증하지 못했다.

`check_documents.mjs`는 이미 기록된 공식 문서 응답을 재사용하여 불필요한 재요청을 피한다. 강제 최신성 검사가 필요하면 별도의 명시적 작업으로 진행해야 한다. `inspect_docs.mjs`는 최초 공식 안내 링크 발견용, `check_elevenst_docs.mjs`는 판매자 문서와 ProductSearch 문서 구분용이다. 관측값과 정책 판단은 날짜가 있으므로 재실행 후 새 약관/내용을 검토하여 `catalog.mjs`의 판단도 갱신해야 한다. 보고서 생성만으로 정책 승인 상태가 자동 바뀌지 않는다.

## 남은 승인 절차와 통합 인계

1. 예스24·알라딘·11번가·도매꾹/도매매의 공식 키를 발급하고 최소 API 응답을 확인한다. 키는 파일/CSV/채팅에 넣지 않고 환경변수로 전달한다.
2. 각 제공자에게 검색 서비스 노출, 영구 DB/가격 이력 보관, 캐시 TTL, 업데이트·삭제, 재배포, AI 학습/가공 용도를 구분해 서면 허용 범위를 확인한다. 확인 안 된 보관기간을 임의 숫자로 정하지 않는다.
3. 쿠팡은 파트너스 최종 승인 및 현행 상품 검색 사용권, 오너클랜은 판매사 API/검색 재사용권, GS SHOP은 제휴 제안과 데이터 범위·정책 협의를 진행한다. 에누리·다나와는 현행 DB 공급 가능성부터 확인한다.
4. 다른 컴퓨터의 `laptop-work-backup` 공통 엔진에는 이번 파일을 자동 연결하지 않는다. 승인 이후 검증된 source만 수동 검토해 반영한다. 특히 예스24의 체계적 영구 DB 축적 제한, 네이버 검색 종료, 판매자 API 범위, 도매 최소주문수량을 통합 설계에 반영해야 한다.

[integrity_check.json](integrity_check.json)으로 기존 보호 대상 137개 파일의 변경·누락 여부를 대조한다. 실험 파일과 backend/crawler_engine/docs 등은 변경하지 않았다.
