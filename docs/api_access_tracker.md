# API 접근·신청 준비 현황

확인일 2026-11-08. 계정 생성·약관 동의·개인정보 제출·외부 신청·메일 발송은 수행하지 않았다. **실제 제출 후 승인 대기 0건**, 자격증명 준비 필요 후보 6개, 제휴/연결 권한 추가 확인 후보 3개다. 후자는 제출된 신청 건수가 아니다. 인증정보는 값이 아닌 존재 여부만 확인한다.

| 후보 | 현재 상태 / 필요한 환경변수 | 최신 공식 절차·개인/학생 자격 근거 | 보존·재사용 / 다음 행동 |
|---|---|---|---|
| eBay | 운영 실응답 검증. EBAY_CLIENT_ID / EBAY_CLIENT_SECRET 설정됨 | 기존 운영 계정 재사용; 신규 신청 없음. [운영 요구사항](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html) | [라이선스](https://developer.ebay.com/join/api-license-agreement)에 맞춘 제한적 연동 검증. 대량 feed·장기 축적은 별도 자격·계약 검토 |
| Apple Books | 무인증 ISBN 조회 실응답 검증 | [공식 API](https://performance-partners.apple.com/search-api)의 공개 조회. 별도 계정 신청 없음 | 키가 없다는 이유로 무제한 축적 가능하다고 판단하지 않음. 공개 프로모션 배지·링크 및 자산 사용 조건 준수 |
| YES24 | 구현됨, YES24_API_KEY 없음 | [개발자센터](https://developers.yes24.com/)가 개인 개발자/사이드 프로젝트를 이용 예로 안내. 로그인 → 활용 목적·상세 설명 → 약관 동의 → 즉시 키 발급 안내. 학생 전용 예외는 확인하지 못함 | [약관](https://developers.yes24.com/support/terms)상 서비스용 캐싱과 별도 DB 축적을 구분. 사용자가 발급 후 루트 .env에 설정하면 소량 실검증 가능 |
| 11번가 | 기존 공식 XML 구현, ELEVENST_API_KEY 없음 | [공식 포털](https://openapi.11st.co.kr/openapi/OpenApiFrontMain.tmall), [소개](https://openapi.11st.co.kr/openapi/OpenApiServiceIntroduce.tmall). 이번 문서 도구에서 502/접근 오류로 현재 가입·심사·학생/개인 허용 여부 확인 불가 | 판매자 관리 API와 ProductSearch 구분. 현재 발급 절차·이용목적·보존·공식 HTTPS 지원부터 확인. 기존 HTTP 주소에 키 전송하지 않음 |
| Yahoo! Shopping | 신규 어댑터 구현, YAHOO_CLIENT_ID 없음; 정책 gate 차단 | [시작 가이드](https://developer.yahoo.co.jp/start/): Yahoo! JAPAN ID 취득 → 가이드의 앱 등록 링크 → Client ID. 가이드가 법인 전용이라고 명시하지는 않지만 한국 거주 학생의 계정/전화 인증 가능성을 확인한 것은 아님 | [가이드라인](https://developer.yahoo.co.jp/guideline/)과 공통 규약, [검색 규격](https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html) 확인. 출처·크레딧 규칙 및 저장 조건 검토 후 gate 해제. 키만으로 자동 해제 안 함 |
| Rakuten Ichiba | 신규 어댑터 구현, RAKUTEN_APPLICATION_ID / RAKUTEN_ACCESS_KEY 없음; 정책 gate 차단 | [공식 guide](https://webservice.rakuten.co.jp/guide/), [앱 관리](https://webservice.rakuten.co.jp/app/list), [검색 문서](https://webservice.rakuten.co.jp/index.php/documentation/ichiba-item-search). 직접 열기 timeout, 검색 색인에서 공식 2026-07-01 규격과 App ID/access key 필수 확인. 개인·학생·한국 거주 신청 자격은 미확인 | 문서 기준 어댑터 초안이며 실응답 미검증. 사용자 로그인 후 앱 등록 항목·허용 서비스 도메인·현재 API/저장 조건을 재확인. 범위가 확인되기 전 실행 차단 |
| Best Buy | 신규 어댑터 구현, BESTBUY_API_KEY 없음; 정책 gate 차단 | [개발자센터](https://developer.bestbuy.com/) → Get API Key → [로그인](https://developer.bestbuy.com/login). 개발자 계정 요구는 확인했으나 개인·학생·국외 신청 승인 조건은 공개 문서에서 확정 못함 | [약관](https://developer.bestbuy.com/legal)은 표시 목적 임시 캐시 최대 72시간, 타 소매업체를 위한 가격 분석 등 제한. 비교 서비스 목적 적합성과 이용 범위 검토 필요 |
| Etsy | 미구현, ETSY_API_KEY / ETSY_SHARED_SECRET 없음 | [앱 시작 안내](https://developers.etsy.com/documentation/), [인증 규격](https://developers.etsy.com/documentation/essentials/requests/). 앱 등록과 commercial access 범위 확인 필요. 개인·학생 팀 자격은 미확인 | 공개 listing 검색과 판매자 OAuth 작업을 구분. 허용 서비스·캐싱·재배포 범위부터 확인한 뒤 구현 |
| Newegg / iHerb | 제휴 권한 확인 필요, 제출 안 함 | [Newegg](https://promotions.newegg.com/affiliate_program/affiliate.html), [iHerb](https://www.iherb.com/info/affiliates). Publisher 가입과 광고주 승인·실제 feed 부여가 별도 | 네트워크 계정만으로 두 쇼핑몰 성공을 계산하지 않음. 승인된 feed 범위·지역·갱신·보존 계약 확인 |
| 다나와 | 지정 연결 수단 확인 필요, 제출 안 함 | [현재 MCP 문서](https://mcp.ai.cowave.kr/docs)는 지정 플러그인·커넥터와 네트워크 제한 안내. 현 세션에 연결된 도구 없음 | 직접 연결/IP 우회 안 함. 사용자 환경에서 공식 연결 가능 여부와 backend 데이터 재사용 조건 확인 |

위 자격 근거는 공개 문서 확인 범위이며 실제 계정 발급·승인 성공을 보장하지 않는다. 학생 할인·사업자등록 불필요 등 확인하지 않은 조건은 신청 가능으로 단정하지 않았다.

## 신청에 사용할 공통 문안

서비스명: ai-shopping-search. 개발 주체: 프로젝트 개발 팀. 대표자·연락처·소속·학적·서비스 공개 URL은 사용자 확인 후 입력해야 하며 임의 작성하지 않는다.

**이용 목적 초안**

> ai-shopping-search는 여러 쇼핑몰의 상품 판매 정보를 정규화해 사용자가 상품을 탐색하고 원본 쇼핑몰의 구매 페이지로 이동하도록 돕는 개발 프로젝트입니다. 초기 단계에서는 공식 상품 검색 API를 통해 요청당 1~3개 상품의 상품명·가격·통화·상품 URL을 검증합니다. 제공자 출처와 구매 링크를 유지하고, 서비스 제공에 필요한 제한적 임시 캐시만 이용할 예정입니다. 전체 상품 DB의 영구 축적·재배포는 기본 API 이용 권한에 포함된다고 가정하지 않습니다. 향후 최소 100개 쇼핑몰 및 300만 판매 정보 규모의 처리 구조를 목표로 하며, 그러한 데이터 확보·저장·재사용은 별도의 제휴 feed와 명시적 승인/계약이 있는 소스에 한해 진행하려고 합니다. 이 목적에 적합한 API 등급, 캐시·보존 조건과 제휴 절차를 안내해 주시기 바랍니다.

**예상 호출량 초안**: 초기 소량 검증은 사이트당 1~5회/일, 요청당 1~3개, 순차 요청 및 최소 3.1초 간격을 제안한다. 이는 신청용 추정치이며 공급자의 더 낮은 한도가 우선한다. 운영 트래픽·사용자 수·요청량은 아직 정해지지 않았고 승인 없이 상향하지 않는다. 300만 건을 검색 API 반복 호출로 즉시 확보하겠다고 신청하지 않는다.

**English draft**

> ai-shopping-search is a team development project for product discovery with direct links to the original stores. Initial validation uses 1–3 product offers per request and approximately 1–5 requests per day per provider. We will preserve required attribution and purchase links and use only a limited temporary cache permitted by your terms. Our longer-term architecture targets 100 stores and up to three million offer records; we understand that acquisition, persistent storage and reuse at that scale require an appropriate approved feed or separate agreement. Please advise on eligibility, permitted use, retention and the suitable access tier. Applicant identity, contact information and the public service URL will be supplied by the account owner.

## 준비 자동화와 사용자 행동

공통 엔진 registry가 필요한 환경변수 이름과 설정 여부를 판별하며 키 값은 기록하지 않는다. `samples/verify_common_engine.py`가 준비 상태를 실제 수집 증거와 별도로 저장한다. OAuth 토큰 발급 자동화는 이미 승인된 기존 eBay 계정에만 수행한다.

사용자 복귀 후 우선 YES24 계정으로 활용 목적과 약관을 검토하고 API 키를 발급해 `.env`의 `YES24_API_KEY`에 설정한다. 나머지 계정의 가입·약관 동의·개인정보 제출·최종 신청은 위 문안과 실제 입력값을 확인한 후 사용자 승인 단계로 남겨 두었다. 준비 문안을 자동 제출하거나 제휴사에 메일을 보내지 않았다.
