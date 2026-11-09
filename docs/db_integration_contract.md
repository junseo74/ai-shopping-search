# 소병선 팀원 전달용 PostgreSQL 연동 계약 초안

2026-11-08. **DB 연결·DDL 실행·상품 INSERT는 수행하지 않았다.** 기존 모델/DB 구조와 별도로 검토할 전달 명세다.

## Python 경계

`collection_engine.contracts.Sink.write_batch(batch_id, records)`와 `StateStore`가 확장 인터페이스다. 현재 Sink 구현은 JSONL 파일뿐이다. PostgreSQL 연결 클래스나 마이그레이션은 추가하지 않았다. 승인 후 담당자가 기존 repository 구조에 맞게 구현할 수 있다.

## JSONL envelope v1.0

| 필드 | 의미·형식 |
|---|---|
| schema_version | `1.0` |
| event_id | source 관측 이벤트의 멱등 키, SHA-256 hex. job/page/offer/content 기반 |
| source | 실제 수집기 식별자. eBay 판매자를 독립 쇼핑몰로 세지 않음 |
| source_product_id | 공식 상품 ID 우선; 없으면 명시된 URL 해시 |
| source_offer_id | 공급자 판매 ID. eBay는 marketplace:itemId. 향후 옵션·판매자·판매조건 식별자 확장 검토 |
| identity_basis | `provider_id` / `product_url_hash_fallback` |
| offer_key | source/product/offer/currency 조합 해시 |
| fingerprint | 허용된 Product 내용의 변경 해시. 관측 시각·로컬 DB id 제외 |
| observed_at | UTC ISO8601 수집 관측 시각. 공급자 수정 시각을 의미하지 않음 |
| expires_at | 로컬 검증 캐시의 사용 만료 시각. 공급자 정책이 더 엄격하면 그 정책 우선 |
| policy_reference, purpose | 약관/승인 근거 링크와 `validation` 등 사용 목적 |
| synthetic | 합성 데이터 여부. true는 실상품 건수에서 제외하고 운영 판매 테이블로 전달 금지 |
| product | 기존 `backend.models.Product` 호환 객체. 미확보 필드는 null |

Product 핵심 필드는 product_name, price, currency, platform, product_url, image_url, category, condition, seller, data_source, collected_at, source_observed_at이다. 조건은 new/used/refurbished/unknown이다. Apple 등 판매자를 관측하지 못한 항목은 null이며 임의 문자열을 넣지 않는다. seller 등 정책 생략 필드는 raw에도 보존하지 않는다. `source_license`가 URL인 경우 라이선스 이름이나 자유 이용 허가가 아닌 관련 문서 링크다.

price는 기존 모델 호환 때문에 float다. DB에서는 금액을 float로 누적 계산하지 말고 NUMERIC+통화로 다루는 것이 권장된다. 현재 JSON 숫자는 임의 정밀도의 공급자 원문 decimal을 보장하지 않으므로, 고정밀 금액을 요구하는 공급자에는 원문 decimal 문자열 보존을 추가 합의해야 한다. 이번 eBay·Apple 샘플은 원본 금액과 Decimal 비교를 통과했다.

## 소비 순서·중복·충돌

1. JSON schema/목적·소스 권한·synthetic·TTL을 확인한다. 만료 또는 범위 밖 데이터는 처리하지 않고 원인 코드를 남긴다.
2. 한 배치의 이벤트를 트랜잭션으로 처리하고 `event_id` 중복 수신을 무해하게 만든다. 동일 상품의 서로 다른 offer를 합치지 않는다.
3. 현재 판매 상태는 offer_key 기준으로 upsert하되 오래된 관측이 최신 값을 덮어쓰지 않게 한다. provider updated_at이 있으면 활용하고, 없으면 observed_at과 DB 수신 순서의 충돌 규칙을 담당자와 합의한다. 현재 파일 엔진은 분산 worker의 전역 순서를 보장하지 않는다.
4. Sink가 성공을 반환한 후에만 엔진이 버전·cursor를 갱신한다. 소비 장애는 배치를 재전달한다. 파일 엔진의 checkpoint와 미래 PostgreSQL transaction은 같은 트랜잭션이 아니므로 exactly-once를 주장하지 않는다.
5. 중복 재시도 이벤트와 별도 갱신 이벤트를 구분한다. 새로운 job_id의 가격 변경은 새 event_id이고 같은 offer_key다. 수신 event_id만 집계하면 상품 수와 다르다.

현재 unchanged 관측은 출력하지 않으며 last_seen heartbeat는 제공하지 않는다. 전체 snapshot이 아닌 검색 결과에서 사라진 항목을 삭제·품절로 추정하지 않는다. 삭제·취소 이벤트는 공급자 공식 피드와 권한 확보 후 별도 버전으로 합의한다.

## 규모·보존 합의 항목

현재 판매 300만 행, 관측 이력 증가량, source별 TTL, 임시 raw 보존 여부, tenant·marketplace·옵션 identity, 배치 100~1,000 범위, 금액 precision, idempotency 인덱스, 관측 시각 인덱스, 오류 격리 큐를 합의한다. 소스마다 장기 이력 자체가 금지될 수 있으므로 공통 무기한 보존 설정을 두지 않는다.

운영 적용 승인 항목은 DB 접속 환경·권한, 기존 테이블 매핑, 새 테이블/인덱스 필요성, 정책별 삭제 작업이다. 이 문서는 DDL 적용 승인이나 신규 수집 권한을 대신하지 않는다.
