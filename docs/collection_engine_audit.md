# 수집 엔진 감사 및 안정화 보고서

작성: 2026-11-11 (Asia/Seoul). 작업 위치: `C:\Users\User\ai-shopping-search-unified`. 브랜치: `desktop/unified-development`, 시작 커밋: `30a89ac`.

기존 엔진·파서·테스트를 먼저 분석하고, 이미 있던 재시도·중복 억제·체크포인트·outbox를 보강했다. 기본 수집 정책과 검증 3건 상한은 유지했다. 이번 세션의 상품 API/OAuth/쇼핑몰 페이지 실호출은 **0회**다. 인터넷은 공식 개발 문서 조사에만 사용했다. 계정 생성, 유료 호출, 대량 수집, 신청 제출, 커밋·푸시를 하지 않았다. 데스크톱 프로젝트, 다른 작업 트리, `research_domestic/`, PostgreSQL 스키마, `backend/db.py`, `backend/models.py`는 수정하지 않았다.

## 1. 분석 범위와 기존 구조

- `collection_engine/` 전체: 계약, registry, 정책, 어댑터, HTTP, runner, 파일 상태·outbox, CLI.
- `backend/collectors/` 전체: eBay·11번가·Apple·YES24·공식 해외 카탈로그, 승인 HTML, 자동 수집 설정·파서, 합성 fixture.
- `tests/` 전체 테스트 수집·실행 및 수집 엔진/API/legacy HTML/DB·파일 테스트 검토.
- `docs/crawler_architecture.md`, `docs/live_crawler_progress.md`, `collection_engine/source_policies.json`과 API 접근 관련 문서.
- 국내 7개 소스의 `crawler_engine` 연결 경계: 기존 추출·집계·정규화 재사용 여부, 내부 API와 보유 HTML 처리의 구분.

`Adapter.fetch_page → CollectionRunner → JsonlSink → FileState`를 유지한다. 기존 backend `collect()`는 단일 요청 인터페이스이며, 없는 페이지 기능을 만들어내지 않는다. `Product` 스키마를 바꾸지 않고 `source_product_id`, 판매 ID, 정책·TTL, 내용 fingerprint를 envelope에 유지한다. DB로 자동 삽입하지 않는다.

기존 구현에 이미 있던 기능은 HTTPS JSON transport의 20초 타임아웃, 최대 3회 재시도, 429/일부 5xx 처리, 지수 백오프·jitter, 정책 gate, 최대 입력 건수, 같은 페이지 중복 제거, 버전 비교, 파일 잠금, 원자적 저장, job 재개다. 이를 새 엔진으로 중복 개발하지 않았다.

## 2. 수집처별 구현·실시간 가능성

아래의 실시간은 요청 시점 조회 또는 허용 범위의 재조회 가능성을 뜻한다. 스트리밍, 전수 카탈로그 동기화, 실시간 변경 알림을 구현했다는 뜻이 아니다. API 존재, 엔진 구현, 키 준비, 사용 허용, 실응답 성공은 각각 별개다.

| 수집처 / source | 현재 구현·공식 접근 | 인증정보 | 엔진 실조회 / 저장 HTML 의존 | 페이지네이션 | 실제 장애·우선순위 |
|---|---|---|---|---|---|
| 11번가 / `elevenst` | 기존 공식 ProductSearch XML 수집기 + 보유 HTML 어댑터. 별도의 legacy 내부 검색 호출 코드는 공식 API가 아님 | `ELEVENST_API_KEY` | **차단**. API 자체는 HTML 불필요, 보유 HTML만 별도 로컬 처리 가능 | 공식 규격은 `pageNum/pageSize`; 기존 backend는 첫 페이지만, 공통 엔진에는 활성 페이지 어댑터 없음 | **P1** 공식 HTTPS 확인 필요. 현재 코드·공식 예시는 HTTP여서 registry에서도 키 전송 전 차단. 정책도 false |
| 다나와 / `danawa` | legacy 추출기·보유 HTML 어댑터. 공식 MCP 연결 방식은 존재하나 엔진용 연결 어댑터 없음 | 엔진 등록 키 없음; 공식 연결·재사용 조건 확인 필요 | **엔진 실조회 불가**, HTML 필요. 공식 커넥터 사용 가능성과 엔진 재사용 권한은 별도 | 보유 HTML 1회 처리 | **P2** 지정 커넥터와 데이터 재사용 계약 확인. 직접 MCP 접속이나 IP 제한 우회 없음 |
| 무신사 / `musinsa` | 기존 HTML/내장 데이터 파서. 발견한 공식 Public API는 기업 CMS이며 상품 카탈로그가 아님 | 상품 수집용 공식 인증 방식 미확인 | **불가**, HTML 필요 | 없음 | **P2** 상품 feed/API 제휴 확인. CMS를 상품 검색 API로 연결하지 않음 |
| 29CM / `29cm` | 기존 HTML 파서. 공식 제휴 상품 등록·수정 API 존재, 전체 시장 검색 API와 구분 | 제휴 API 문서의 ClientId/ClientSecret·Partner-Key. 엔진에는 미등록 | **불가**, HTML 필요 | 없음 | **P2** 제휴 범위·조회 feed 별도 확인. 관리 API만으로 전체 상품 수집 권한을 가정하지 않음 |
| 컬리 / `kurly` | 기존 HTML 파서. 공식 KLS 문서는 물류·배송·운송장 API | KLS 인증은 별도; 상품 검색용 인증·권한 미확인 | **불가**, HTML 필요 | 없음 | **P2** 카탈로그 제휴 확인. 웹 서비스 내부 검색 URL을 공식 공개 API로 사용하지 않음 |
| 롯데온 / `lotteon` | 기존 HTML 파서. 공식 판매자 운영 API와 전체 상품 카탈로그 수집을 구분 | 판매자 API 발급·권한 필요; 엔진용 키 미등록 | **불가**, HTML 필요 | 없음 | **P2** 허용 조회 범위·제휴 feed 확인. 공식 API 페이지의 일부 내용은 JS 화면만 반환되어 상세 규격 미검증 |
| 중고나라 / `joongna` | 기존 파서 + legacy 내부 검색 API 코드 보존. 공통 엔진은 내부 API를 실행하지 않음 | 공식 공개 상품 API·인증 방식 미확인 | **불가**, HTML 필요 | legacy 내부 코드의 페이지 반복은 있지만 공통 엔진의 허용된 live 페이지 기능은 아님 | **P2** 공식 제휴·허용 데이터 접근부터 확보. 비공식 내부 API를 공식 API로 표시하지 않음 |
| eBay / `ebay_browse` | 공식 Browse 검색, 기존 OAuth·상품 mapper 재사용 | `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`; 선택 `EBAY_MARKETPLACE_ID` | **구현됨**, 키·운영 접근 권한 필요. HTML 불필요. 이번 세션 실조회 미수행 | offset, 최대 검색 범위 10,000, 요청 크기 1~200. 엔진 기본 검증은 총 3건 | **P0** 키·승인 확인 후 1건 명시적 실검증. OAuth 재시도·만료 갱신, offset 정렬 보강 |
| Yahoo! Shopping / `yahoo_shopping` | 공식 상품 검색 v3 어댑터 구현 | `YAHOO_CLIENT_ID` | **구현되었으나 정책 차단**, HTML 불필요. 키만 추가해도 gate는 해제되지 않음 | start/results, 합계 1,000 상한. 현재 어댑터 요청당 1~3건 | **P1** 이용 목적·표시·저장 조건 검토 후 정책 설정 및 키 준비, 실응답 검증 |
| Rakuten Ichiba / `rakuten_ichiba` | 공식 2026-07-01 검색 규격 어댑터 구현 | `RAKUTEN_APPLICATION_ID`, `RAKUTEN_ACCESS_KEY` | **구현되었으나 정책 차단**, HTML 불필요. 실응답 미검증 | page/hits, 100페이지 상한, 요청당 1~3건. 크기 변경 시 위치 보존 | **P1** 앱 등록·허용 도메인·현재 인증/헤더 요구사항 재확인. 문서 본문 접근은 timeout, 공식 검색 색인·탐색기에서 버전·키 확인 |
| Best Buy / `bestbuy_products` | 공식 Products API 어댑터 구현 | `BESTBUY_API_KEY` | **구현되었으나 정책 차단**, HTML 불필요. 실응답 미검증 | page/pageSize, 응답 totalPages, 요청당 1~3건 | **P1** 비교 서비스 목적과 사용 조건 검토 후 키·정책 준비. 응답 구매 URL 그대로 보존 |
| Apple Books / `apple_books_lookup` | 공식 ISBN lookup. 기존 robots 검사 유지 | API 키 불필요 | **구현됨**, 현재 robots 허용 필요. HTML 불필요. 일반 텍스트 검색은 제공하지 않음 | 단일 ISBN lookup, 1~3건, 페이지 없음 | **P0** 명시적 1건 실검증. robots 확인도 공통 HTTP 제한·재시도 적용 |

추가 등록 소스:

| source | 상태와 준비사항 |
|---|---|
| `yes24_api` | 공식 단일 요청 수집기. `YES24_API_KEY` 필요. 이번에 엔진 경로에 공통 transport 및 원본 itemId 연결. 별도 카탈로그 DB 축적과 서비스 캐싱 조건 구분. 실응답 미검증 |
| `approved_html` | 명시적으로 허용된 URL·selector·재사용 권한·robots가 필요. 정책 기본 차단. 무허가 쇼핑몰을 자동 등록하지 않음 |
| `shopping_auto` | 기존 설정 기반 다중 수집기. 하위 소스별 허용·키·설정 필요. 공통 정책 기본 차단이며 내부 수집기별 HTTP 동작은 동일하지 않음 |
| `test_fixture` | 로컬 합성 데이터. 실제 상품 실조회 근거가 아니며 정책 기본 차단 유지 |

### 공식 문서 확인 근거

- 11번가: [현재 공식 포털](https://openapi.11st.co.kr/openapi/OpenApiFrontMain.tmall), [ProductSearch 개발 가이드](https://openapi.11st.co.kr/openapi/OpenApiGuide.tmall). 검색·XML·키·pageNum/pageSize와 HTTP 호출 예시 확인. HTTPS 지원을 입증하지는 못했다. 포털의 키 유효기간 관련 공지도 계정 운영 시 확인해야 한다.
- 다나와: [공식 MCP 안내](https://mcp.ai.cowave.kr/docs). 지정 플러그인/커넥터 이용과 직접 연결 네트워크 제한 안내 확인. 엔진의 무제한 backend 데이터 수집 허가는 확인되지 않았다.
- 무신사: [기업 CMS Public API 명세](https://dev-api.corp.musinsa.com/api-docs/public). 공식 검색 색인은 기업 연혁·공지·보도자료 등을 안내한다. 직접 열기는 403이었으며 상품 카탈로그 API로 해석하지 않았다.
- 29CM: [공식 외부연동 문서](https://partner-stage.one.musinsa.com/29cm_category_v2_api.html). 제휴 인증·상품 등록/수정 범위 확인. 일반 소비자 검색 feed의 공개 허용 근거는 확인되지 않았다.
- 컬리: [KLS API](https://developers.kurly.com/docs/api/). 물류대행·배송대행·운송장 추적 문서임을 확인. 상품 검색 API의 공개 이용 문서로 볼 근거 없음.
- 롯데온: [공식 API 시작 안내](https://api.lotteon.com/apiService/?apiNm=GetStarted). 공식 색인에 공용/특정 거래처 API 구분이 있으며 직접 조회는 JS 로딩 화면이어서 상세 범위는 추가 확인 필요.
- 중고나라: [공식 서비스 약관](https://common.joongna.com/static/terms/TermsOfService_new.html?v=1741849515252)과 공식 도메인 검색 범위에서 공개 상품 수집 개발 문서를 확인하지 못했다. 이는 API가 절대 없다는 증명이 아니다. legacy 내부 URL의 접근 가능성도 이용 허가로 보지 않는다.
- eBay: [현재 Browse 검색 규격](https://developer.ebay.com/develop/api/buy/browse_api/item/search). offset은 0 또는 limit의 배수여야 하며 검색 범위에 상한이 있다. [운영 접근 요구사항](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html) 별도 검토 필요.
- Yahoo: [공식 검색 v3](https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html). endpoint, Client ID, JPY 가격·상품 필드와 start+results 상한 확인.
- Rakuten: [공식 규격](https://webservice.rakuten.co.jp/index.php/documentation/ichiba-item-search), [공식 탐색기](https://webservice.rakuten.co.jp/explorer/api/IchibaItem/Search). 본문 timeout 때문에 현재 버전·필수 키는 공식 색인/탐색기 확인 범위로 제한한다. 문서 예시의 자격증명은 복사하거나 사용하지 않았다.
- Best Buy: [공식 개발 문서](https://bestbuyapis.github.io/api-documentation/), [사용 조건](https://developer.bestbuy.com/legal). 페이지와 응답 URL 형식 확인. 가격 분석·제3자 이익 목적, 캐싱 조건 등 서비스 적합성 검토 전 gate 유지.
- Apple: [공식 Search/Lookup 문서](https://performance-partners.apple.com/search-api). ISBN lookup, 콘텐츠 사용 조건과 호출 제한 안내 확인. 엔진은 기존 ISBN 전용·robots 검사 경계를 유지한다.

## 3. 실제 검증과 미검증의 구분

| 항목 | 이번 검증 범위 |
|---|---|
| 수정 전 기준 | 기존 228개 테스트 전부 통과, 경고 2개 |
| 수정 후 전체 | `python -m pytest tests -q`: **402 passed, 2 warnings**. 외부 TCP 연결·getaddrinfo 차단, dotenv 자동 로드 비활성화, 실제 키 제거, 기본 DB 임시 경로 격리 상태 |
| 진단 CLI | 기본 module, `diagnose --source`, 별도 diagnostics module, 기존 verification script의 기본 동작 4가지 실제 실행 성공. 16개 소스 출력, 모두 network_used=false |
| 공급자 정상/오류 응답 | 합성 JSON·mock transport로 검증. API 서버의 현재 가용성·quota·실제 권한을 입증하지 않음 |
| 과거 실조회 기록 | 기존 문서에는 2026-11-08 eBay·Apple 각 1건 성공 기록이 있음. 이번에는 재조회하거나 현재 성공으로 재계상하지 않음 |
| 실시간 상품 수집 | 이번 세션 0회. 실제 키의 유효성, 국가/계정 제한, 현재 robots, 실제 응답 schema 차이는 미검증 |
| 보유 HTML | 기존 7개 parser 및 기존 fixture 테스트 유지. 특정 쇼핑몰의 현재 live 접근 허가·동작을 입증하지 않음 |
| 저장·재개 | 파일 잠금, timeout/429 이후 재개, outbox/버전/체크포인트 중간 실패, 저장 데이터 변조·손상, TTL·동일 이벤트 재전달을 오프라인 검증 |

기존 경고는 `TestFixtureCollector`의 pytest 클래스 수집 경고와 FastAPI/Starlette TestClient의 httpx 관련 deprecation이다. 이번 작업에서 새 의존성을 설치하거나 경고 해결을 위해 무관한 코드를 수정하지 않았다.

## 4. 이번 수정 사항

### HTTP와 API 경계

- 기본 20초 및 connect/read timeout 쌍 설정 검증. 무제한 timeout, 음수·비유한 대기, 잘못된 시도 횟수 거부.
- timeout·연결 오류, 429, 500/502/503/504만 제한 재시도. 기본 최대 3회, 3.1초 간격, 지수 백오프·jitter 유지.
- Retry-After 초·HTTP 날짜 처리 및 NaN/무한대·잘못된 값 방어. 30초보다 긴 정상 Retry-After는 조기 재시도하지 않고 중단·보고.
- 401/403·리다이렉트·기타 영구 오류는 같은 요청에서 재시도하지 않음. 응답 자원 닫기. 예외 본문·헤더·인증 URL을 보고하지 않음.
- 반복 가능한 client-credentials OAuth용 POST와 robots용 text 응답에 같은 transport 적용. eBay 기본 엔진 어댑터의 토큰 발급·검색이 transport를 공유.
- eBay 만료 시간에 따른 사전 갱신. 검색 401에서는 토큰을 폐기하고 종료하며, 다음 명시적 재개에서 새 토큰 발급. 만료 정보 없는 주입 수집기의 토큰은 임의 만료 시간을 만들지 않음.
- Apple·YES24는 transport 주입을 추가해 공통 엔진 경로에서 사용. 기존 직접 호출 인터페이스와 Apple robots 검사는 유지.
- 배열/객체/중첩 필드·공급자 ID·총건수/페이지 수 형식 검사. 비어 있는 정상 결과와 잘못된 응답을 구분하고, 비어 있지 않은 응답의 페이지 메타데이터 누락을 완료로 오판하지 않음.
- 11번가 공식 HTTPS가 미확인인 상태에서 registry가 기존 HTTP 수집기로 연결되지 않도록 추가 차단.

### 페이지·재개·저장

- 현재 커서뿐 아니라 이전 커서 해시를 체크포인트에 저장해 `A → B → A` 순환도 재개 간 감지.
- 빈 페이지가 다음 커서를 제시하면 `empty_page_with_cursor`로 중단. 잘못된 rejected 수·커서 타입·초과 페이지 결과도 거부.
- Rakuten·Best Buy 새 다건 커서는 `page:size`. 남은 예산이 줄면 논리적 상품 위치를 보존하는 정렬된 요청으로 전환. eBay도 offset/limit 배수 규칙을 지킴. 상품 상한을 초과해 미리 읽지 않음.
- `max_items`는 유효·무효·중복을 포함한 받은 상품 예산이며 job 전체에 유지. `max_pages`는 **명령 실행 1회당** 예산이므로 같은 job을 재개하면 추가 페이지 처리 가능.
- 체크포인트 저장 전 통계·완료 상태를 확정하지 않음. 저장 실패 시 마지막으로 저장된 진행 상태를 보고.
- 새 체크포인트에 정책과 어댑터 문맥 서명 추가. 정책·eBay marketplace가 바뀐 job은 새 ID 요구. 기존 형식은 읽되 과거 커서/문맥까지 소급 검증한다고 주장하지 않음.
- outbox 저장/재사용/읽기에 상품 스키마·식별자·내용 hash·TTL 시간 검증 추가. 같은 event_id를 가진 변조 파일도 그대로 수용하지 않음.
- 손상된 체크포인트·버전 인덱스는 오류로 보고하고 자동 초기화·삭제하지 않음. 원자적 JSON 저장 실패 시 기존 파일 보존 및 임시 파일 정리 확인.

### 정규화·품질

| 필드 | 처리 |
|---|---|
| product_name | 비어 있거나 공백인 이름 거부, 앞뒤 공백 정리. eBay의 가짜 기본 상품명 제거 |
| price | 명확한 숫자/소수/정상 천 단위 쉼표 문자열만 숫자로 변환. 음수·NaN·무한대·boolean·모호한 지역 표기·문의/통화 기호는 거부. 빠진 가격을 0으로 만들지 않음 |
| currency | 명시 값의 영문 3자리 형식 검증·대문자 정리. 환율 변환 없음. eBay 누락 통화를 USD로 채우지 않음. 전체 ISO 코드 목록 유효성까지 검증한 것은 아님 |
| seller | 원본 값 또는 null. eBay 가짜 판매자 이름 제거. 정책상 생략 필드는 기존대로 null |
| platform / condition | 기존 Product enum 재검증. Like New를 new로 오분류하지 않도록 eBay mapper 보강. 알 수 없는 상태는 unknown |
| product_url / image_url | 기존 스키마·공개 HTTP(S) URL 검증. 누락 상품 URL을 검색 페이지로 생성하지 않음. 로컬 별칭·사설 IP·인증정보·잘못된 port 거부. 이미지 미제공은 null |
| category | 제공된 값만 유지, 없으면 null |
| source_product_id | 원본 ID 우선. Apple trackId·YES24 itemId 연결. 기존 보유 HTML 등 원본 ID 없는 경로는 URL hash fallback임을 identity_basis에 표시 |
| collected_at | 엔진 관측 시각을 UTC로 기록. 제공자의 수정 시각으로 추정하지 않음 |

Product의 변경·검증 우회 값을 어댑터 경계에서 다시 검사하며 원본 객체는 변형하지 않는다. original_price·shipping_fee의 비정상 수치도 거부한다. eBay 배송비는 상품 가격과 통화가 명시적으로 같은 경우만 공통 금액 필드에 담으며 다른 통화를 임의 합산하지 않는다. 누락률은 정책 생략 전 입력 기준이다. 같은 페이지 중복은 duplicates, 다른 페이지/갱신의 동일 내용은 버전 비교에 따라 unchanged로 집계한다.

### 진단·기본 실행

기본 `python -m collection_engine`은 이제 오프라인 진단이다. 등록 목록, 인증 환경변수 **이름과 존재 여부**, live/페이지 기능, 정책 gate, 준비사항, 테스트 명령을 JSON으로 출력한다. 인증정보 값은 출력하지 않는다. 진단의 ready는 실응답 성공이나 사업 목적 승인 증명이 아니다. `.env`는 통합 프로젝트 루트만 확인하고 환경변수의 우선순위를 유지한다.

기존 수집 CLI와 `samples/verify_common_engine.py`의 상품 실호출은 `--live`가 있어야 한다. Python 라이브러리의 직접 `collect()`/`runner.run()` 호출까지 이 CLI 옵션으로 통제하는 것은 아니다.

## 5. 추가 테스트와 변경 파일

기존 228개 테스트와 해당 파일을 그대로 보존했다. 새 테스트 **174개**, 최종 **402개**다.

- `tests/test_collection_engine_hardening.py`: 가격·통화·URL·잘못된 mutable Product, 빈 응답, 커서 순환/재개, 상품·페이지 예산, timeout·연결 복구·429·HTTP 날짜·401/403, 진단 비밀정보 비노출/무통신, 저장 손상·원자적 실패·정책 변경.
- `tests/test_catalog_resilience.py`: 해외 3개 API의 정상·빈·중첩 오류·총건수 오류·커서, 페이지 크기 변경 후 실제 runner 재개, eBay OAuth 만료/401/offset/배송비/상태, Apple robots·YES24 원본 ID·오류 분류, 기존 검증 스크립트 기본 진단.
- `tests/conftest.py`: 테스트 수집 전에 실제 키를 테스트 프로세스 환경에서 제거하고 dotenv 자동 로드를 끔. 기본 DB를 임시 위치로 격리. 외부 주소의 getaddrinfo 및 IPv4/IPv6 connect/connect_ex 차단, 로컬 fixture 서버의 loopback은 허용. 테스트 종료 시 환경 복원·임시 DB 정리. OS 전체나 별도 subprocess의 네트워크를 봉쇄하는 기능은 아님.

| 구분 | 수정·추가 파일 |
|---|---|
| 엔진 수정 | `collection_engine/transport.py`, `runner.py`, `adapters.py`, `storage.py`, `registry.py`, `__main__.py` |
| 엔진 추가 | `collection_engine/diagnostics.py`, `quality.py`, `responses.py` |
| 기존 수집기 보강 | `backend/collectors/ebay.py`, `apple_books.py`, `yes24.py`, `official_catalogs.py` |
| 테스트 추가 | 위 테스트 2개와 `tests/conftest.py` |
| 실행 예·문서 | `samples/verify_common_engine.py`, `docs/crawler_architecture.md`, 본 보고서 |

`collection_engine/source_policies.json`의 허용 범위와 bulk/조회 gate는 변경하지 않았다. 기존 스키마와 DB 팀 코드는 수정하지 않았다.

## 6. 실행 방법

통합 프로젝트에서 실행한다. 새 패키지 설치는 필요하지 않았다. 이번 셸에서는 python이 PATH에 없어 기존 데스크톱 가상환경의 인터프리터를 **실행만** 했다. 해당 환경의 패키지를 설치·수정하지 않았으며 PYTHONDONTWRITEBYTECODE로 그 프로젝트의 바이트코드 쓰기도 방지했다.

```powershell
Set-Location C:\Users\User\ai-shopping-search-unified
# python을 사용할 수 없는 현재 셸에서만 필요한 별칭
Set-Alias python C:\Users\User\ai-shopping-search\.venv\Scripts\python.exe
$env:PYTHONDONTWRITEBYTECODE = '1'

# 네트워크 없는 진단
python -m collection_engine
python -m collection_engine diagnose --source ebay_browse
python -m collection_engine.diagnostics --source elevenst
python samples/verify_common_engine.py

# 전체 오프라인 테스트
python -m pytest tests -q
```

키와 사용 범위를 준비한 후에만 아래처럼 명시적으로 조회한다. 이번 작업에서는 이 명령들을 실행하지 않았다.

```powershell
python -m collection_engine --live --source ebay_browse --query keyboard --job-id ebay-check-001 --max-items 1 --page-size 1 --max-pages 1 --output collection_output/ebay
python -m collection_engine --live --source apple_books_lookup --query 9780316069359 --job-id apple-check-001 --max-items 1 --page-size 1 --max-pages 1 --output collection_output/apple
```

재개는 같은 source/query/job-id/max-items/page-size/output을 사용한다. max-pages는 재개 시 바꿀 수 있다. 완료된 job은 다시 API를 호출하지 않으며 갱신에는 새 job-id를 사용한다. 같은 output의 state를 재사용해야 이전 내용과 비교한다. outbox는 JSONL, state는 버전·체크포인트, runs는 실행 결과이며 파일 이름은 job/batch 해시다. 소비자는 event_id로 중복 전달을 처리해야 한다.

## 7. API 키와 사용자 조치

| 서비스 | 통합 프로젝트의 환경변수 | 추가 준비 |
|---|---|---|
| eBay | EBAY_CLIENT_ID, EBAY_CLIENT_SECRET | 유효한 운영 접근·marketplace 확인 |
| Yahoo | YAHOO_CLIENT_ID | 이용 목적/표시/저장 조건 검토, 정책 gate 설정 |
| Rakuten | RAKUTEN_APPLICATION_ID, RAKUTEN_ACCESS_KEY | 앱·허용 도메인/인증 요구 재확인, 정책 gate 설정 |
| Best Buy | BESTBUY_API_KEY | 서비스 목적 적합성·보존 조건 확인, 정책 gate 설정 |
| YES24 | YES24_API_KEY | 캐싱과 별도 카탈로그 DB 축적 조건 확인 |
| 11번가 | ELEVENST_API_KEY | 공식 HTTPS endpoint 확인 후 어댑터 보강·정책 검토. 키만 넣어 실행하지 않음 |
| Apple Books | 없음 | ISBN과 현재 robots 허용, 콘텐츠 사용 범위 |

키는 **통합 프로젝트**의 로컬 `.env` 또는 실행 프로세스 환경변수에 사용자가 설정한다. 기존 데스크톱 `.env`를 자동 복사하거나 출력하지 않았다. `.env`·키·토큰을 보고서·커밋에 넣지 않는다.

사용자가 직접 할 일은 계정 소유자에 의한 키 발급/갱신, 약관·실제 서비스 목적/저장 범위 확인, 허용된 소스의 정책 설정, 준비 완료 후 명시적 1건 실검증이다. 설정 뒤 먼저 오프라인 진단의 blockers를 확인한다. 국내 제휴 소스는 API/feed 권한을 확보해야 하며 계정 생성·신청·파트너 문의를 대신 실행하지 않았다.

## 8. 남은 제약과 다음 우선순위

1. **P0: eBay·Apple 1건 실검증.** 이번 코드의 실제 서버 응답은 검증하지 않았다. 키의 존재만으로 유효성·quota·현재 이용 허가가 확인되지 않는다.
2. **P1: Yahoo·Rakuten·Best Buy 준비.** 키뿐 아니라 사용 범위와 정책 gate가 필요하다. Rakuten의 현재 등록 도메인/Origin 등 요구를 공식 문서·계정에서 재확인한 뒤 필요한 설정만 구현한다. 임의 Origin이나 다른 앱의 키는 넣지 않는다.
3. **P1: 11번가 HTTPS·XML 페이지 어댑터.** 보안 endpoint 확인 전 실행 차단 유지. 공식 오류 코드와 native ProductCode, 페이지 종료 근거를 연결하는 다음 작업이 필요하다. 기존 backend 직접 호출 경로는 여전히 HTTP를 사용하므로 준비된 공통 엔진 경로와 혼동하지 않는다.
4. **P2: 국내 승인된 API/feed 확보.** CMS·물류·판매자 관리 API와 전체 쇼핑몰 상품 검색은 목적이 다르다. 미확인 내부 API나 자동 브라우저 수집으로 대체하지 않는다.
5. **실제 운영 자동화는 후속 단계.** 검색 페이지는 snapshot이 아니므로 순위 변경·삭제·누락을 완전히 추적하지 못한다. 현재 증분은 재조회 후 내용 비교다. 공식 변경 feed, 작업 큐, 여러 worker의 공용 quota/임대, heartbeat가 필요하다.
6. **파일 참조 저장의 한계.** 저장은 at-least-once이며 outbox·버전·체크포인트의 분산 트랜잭션이 아니다. 저장 중 장애 후 같은 이벤트가 여러 파일에 남을 수 있다. 체크포인트 통계는 저장된 진행 기준이므로 장애 직전 outbox 전송 건수와 다를 수 있다. TTL 만료는 reader에서 제외하며 물리 파기는 자동 실행하지 않는다. 기존 파일을 삭제해 복구하지 않는다.
7. **기존 경로의 범위.** 공통 transport의 전체 재시도/분류는 registry로 만든 엔진 경로에 적용한다. 예전 backend 직접 호출과 하위 HTML 수집기의 모든 HTTP 동작을 일괄 재작성하지 않았다. legacy 보유 HTML 파서는 기존 통화/상태 기본값·텍스트 추론을 포함하므로 해당 값의 공급자 증거를 추가하는 후속 개선이 필요하다.
8. **검증의 한계.** URL 검사는 문자열·주소 검증이며 DNS 재해석이나 실제 상품 페이지 GET 검증을 하지 않는다. 내용 해시는 손상 검사용으로 전자서명이 아니다. 실제 대량 처리·상품 전수 확보·서비스 이용 계약·PostgreSQL sink는 이번 결과에 포함되지 않는다.

기존 `live_crawler_progress.md`에는 이미 물음표로 대체된 문장이 있어 원문을 추정 복원하지 않았다. 과거 자료는 보존하고 이번 작업의 상태와 근거는 이 보고서에 기록했다.