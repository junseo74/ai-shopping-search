# 국내 공식 데이터 소스 확보 2차 결과

조사일: 2026-11-08 (Asia/Seoul). 1차 README·30개 후보 CSV를 분석한 뒤 미해결 승인/정책 항목을 보강했다. 1차 원본 파일·분류를 다시 생성하지 않고 이번 추가 결과만 이 폴더에 기록했다. 데스크톱 공통 엔진과 자동 통합하지 않았다.

**이번 실제 검증: 1개 쇼핑몰(알라딘), 새 RSS 1개, 상품명·판매가·URL 3건 성공. 새로 성공한 쇼핑몰 수는 0개다.** 기존과 합쳐 기술적 응답 성공 사이트는 2개(예스24 RSS는 오래된 자료), 최근 피드 확인 사이트는 1개다. 인증 API 실응답 성공은 0개, 상용 장기 상품 DB 저장권 확보는 0개다. 문서 HTTP 200, 검색 발췌, 합성 fixture 테스트를 실제 상품 응답 성공으로 집계하지 않았다.

## 1차 대비 확보한 것

- **실제 수집 경로 확대**: 경제경영 분야의 [공식 RSS alternate 안내](https://www.aladin.co.kr/shop/wbrowse.aspx?CID=170)에서 `new_all/170`을 발견하고 HTTPS로 1회만 읽어 3개 상품을 확인했다. 1차 `new_all/351`을 재수집하지 않았다. 결과는 [live_results.json](live_results.json)에 해시·판매가·관측 시각만 남겼다.
- **신규 판매자 문서 2곳**: [SSG EAPI](https://eapi.ssgadm.com/info/main.ssg), [NS홈쇼핑 공식 GitHub INBOUND API](https://github.com/nsshopping/Affiliate-API). NS는 최신 스펙·방화벽 요청 자료가 있으나 입점몰이 NS에 연동하는 방향이므로 전체 상품 수집 경로로 승격하지 않았다.
- **예스24 활용 범위 구체화**: [FAQ](https://developers.yes24.com/support/faq)에서 상업 모델·타 판매처 링크 병기·Partner 요청 정보를 추가 확인했다. 출처와 원상품 링크, 일시 캐시 조건을 지키는 검색 MVP는 검토할 수 있다. 장기 DB 적재/재배포 제한은 그대로다.
- **신청 오류 예방**: 도매꾹·도매매의 [목적별 신청 가이드](https://openapi.domeggook.com/ko/articles/API-신청-가이드-787a96cd)를 확보했다. 기본 Open 안내와 자체 개발 목적의 신청 절차를 함께 읽어야 한다. 가격비교 서비스는 공식 기술지원의 유형·권한 회신 전 보류한다.
- **갱신 설계 근거**: 오너클랜 [상품 명세](https://www.ownerclan.com/V2/service/api-center-item.php)의 상품검색·변경이력·갱신시각을 확인했다. URL 필드가 미확정이므로 임의 URL로 제품을 완성하지 않았다.
- **피드로 오인하기 쉬운 경로 분리**: [올리브영 큐레이터](https://m.oliveyoung.co.kr/m/mtn/affiliate/guide)와 컬리 공식 큐레이터 설명은 링크 홍보 경로다. 에누리·다나와 EP는 입점몰→가격비교사 데이터 제출이며, 우리가 읽는 공개 상품 피드가 아니다. 링크프라이스 핫딜 API는 공식 대안이나 30개 몰별 참여·인증·저장권은 미확정이다.

## 비교·신청 준비 문서

| 결과물 | 내용 |
|---|---|
| [approvals.md](approvals.md) / [approvals.json](approvals.json) | 인증 대기 7개 각각의 신청 사이트·확인된 입력정보·서류·미확정 조건·사용자 직접 수행 체크리스트; 알라딘 추가 절차 |
| [application_drafts.md](application_drafts.md) | 실제 프로젝트를 기준으로 쓴 신청 목적·처리 방식·권한 문의 문안. 제출 안 함; 사용자/서비스 URL 등 미입력 표시 |
| [revalidation.csv](revalidation.csv) | 정책 대기 21개 추가 조사 결론·근거·보류 이유. 새 문서 확보와 제한된 검색에서 미발견을 구분 |
| [comparison.csv](comparison.csv) | 기존 30개 각각의 연동 가능성·승인 난이도·상품 범위·갱신·상업 사용·장기 저장을 분리한 비교 |
| [evidence.json](evidence.json) / [new_document_checks.json](new_document_checks.json) | 추가 공식 근거·관측 방법·신청 페이지 접근 상태; 원문 복사나 인증값 없음 |

계정 생성과 양식 제출까지 끝났다는 의미의 신청 준비 완료는 아니다. 신청 문안·체크리스트는 준비됐지만 실사용자 정보, 실제 공개 URL, 현행 로그인 양식, 제공자의 답변이 필요하다. 공개 자료에서 보이지 않은 필수서류·심사기간·가격·TTL은 만들어 넣지 않았다.

## 독립 수집기와 검증

[collector.mjs](collector.mjs)는 기존 1차의 해시 진단을 넘어 API 응답을 메모리의 표준 상품 객체로 반환한다. 5개 API 어댑터는 예스24·알라딘·11번가·도매꾹·도매매이며 공식 계약 사양을 이용한다. 별도로 신규 알라딘 RSS 어댑터 1개가 있다. 원래 수집기와 DB를 import하지 않는다.

표준 필드: source, name, price, currency, url, price_field, min_order_qty, business_only, observed_at, commercial_use, long_term_storage, redistribution. 판매가와 정가를 구분하고 도매 MOQ·사업자 조건을 보존한다. 반환 상품은 메모리에서만 유지하며 CLI는 해시/가격 증거만 쓴다. 상품 객체가 존재한다고 저장권이 생기지 않는다.

```powershell
node --test research_domestic/phase2/test_collector.mjs
node research_domestic/phase2/run_validation.mjs --source=yes24
node research_domestic/phase2/build_phase2_report.mjs
```

`--source`는 yes24/aladin/elevenst/domeggook/domeme/aladin_rss_170만 허용한다. 키는 프로세스 환경에서 읽고 `.env`는 자동으로 읽지 않는다. 이번에는 4종 키가 모두 없어 API 5개 몰 호출은 0회로 보류했다. API 실제 성공을 증명한 것은 아니다. 도매꾹·도매매는 키가 있어도 목적 승인 전에는 호출하지 않으며, 실제 승인 후에만 `DOMESTIC_DOME_PURPOSE_APPROVED=true`를 설정한다. 이 변수는 승인 신청이나 권한 부여를 대신하지 않는다.

HTTPS 고정 endpoint, GET만 허용, 최대 3개 상품/1회 요청, 15초 timeout·2MB 상한을 사용한다. 리다이렉트·429·401·403에서 즉시 멈추고 재시도/페이지 순회/우회를 하지 않는다. 에러 본문·요청 URL·헤더·토큰을 출력하지 않는다. 상품 URL에 인증 쿼리가 있으면 제외한다.

합성 fixture 및 제어 흐름 테스트 **15개 통과**. 5개 응답 정규화, 1회 호출 제한, 키 누락 시 미호출, 목적 승인 게이트, 정가/판매가, MOQ, 비정상 URL·인증 쿼리, XML 외부 엔티티, 401/403/429/302 중단, 예외 비밀값 출력 방지, 중복 제거를 검사했다. 이 테스트는 실제 제공자의 승인·가동 여부나 모든 XML 변형을 보장하지 않는다. 키가 있는 API 경로의 실서비스 검증은 남아 있다.

## 운영 전 남은 일

사용자가 우선 예스24 기본 키와 이용 약관을 확인하고 캐시형 검색 용도로 소량 시험하는 경로가 가장 구체적이다. 11번가 신규 검색키·알라딘 TTB·도매꾹/도매매 목적 권한이 다음이며, 오너클랜/쿠팡/GS SHOP은 별도 승인/계약을 기다려야 한다. 21개 정책 대기 몰은 승인된 전체 상품 수집 경로가 새로 열렸다고 판단하지 않았다.

[summary.json](summary.json)은 1차 누적 수와 2차 신규 수를 분리한다. [integrity.json](integrity.json)은 원래 보호 파일 및 1차 입력 파일의 무결성 점검 결과다. 기존 실험·공통 엔진 파일은 수정하지 않았다. Git 전환/병합/푸시/리셋/클린과 계정 생성·신청 제출·유료 가입은 수행하지 않았다.
