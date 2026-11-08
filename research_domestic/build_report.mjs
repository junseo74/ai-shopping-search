import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import catalog from './catalog.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url));
const read=name=>JSON.parse(fs.readFileSync(path.join(dir,name),'utf8'));
const rss=read('public_verification.json'),apis=read('api_verification.json'),docs=read('document_checks.json'),details=read('elevenst_document_checks.json');
const inventory=read('local_inventory.json');
const successful=rss.filter(r=>r.http_status===200&&r.three_fields_verified);
const current=successful.filter(r=>r.freshness==='recent_feed_not_price_guarantee');
const counts=catalog.reduce((a,r)=>(a[r.status]=(a[r.status]||0)+1,a),{});
const provider=id=>['domeggook','domeme'].includes(id)?'domeggook_domeme':['gmarket','auction'].includes(id)?'esm_group':id;
const all=catalog.map(c=>{
 const r=rss.find(r=>r.id===c.id),a=apis.find(a=>a.id===c.id);
 const d=details.find(d=>d.url===c.primary_url)||docs.find(d=>d.url===c.primary_url)||docs.find(d=>d.id===c.id);
 return {id:c.id,name:c.name,checked_date_kst:'2026-11-08',status:c.status,priority_rank:c.priority_rank,scope:c.scope,provider_group:provider(c.id),official_api:c.official_api,official_rss:c.official_rss,affiliate_feed:c.affiliate_feed,auth_requirements:c.auth_requirements,credential_env:c.credential_env||'',storage_reuse_policy:c.storage_reuse_policy,storage_approved:'false',production_ready:'false',policy_url:c.policy_url,primary_url:c.primary_url,supporting_urls:(c.supporting_urls||[]).join(' | '),document_http_status:d?.http_status||'',document_checked_at:d?.observed_at||'',live_three_fields_verified:String(!!r?.three_fields_verified),live_validated_samples:r?.sample_checks?.filter(p=>p.name_present&&p.price_present&&p.url_present).length||0,feed_freshness:r?.freshness||'not_requested',api_validation:a?.reason||'not_implemented_or_not_authorized',finding:c.finding,next_step:c.next_step};
});
const fields=Object.keys(all[0]);
const csvcell=v=>'"'+String(v??'').replaceAll('"','""')+'"';
fs.writeFileSync(path.join(dir,'candidates.csv'),'\uFEFF'+[fields,...all.map(r=>fields.map(k=>r[k]))].map(row=>row.map(csvcell).join(',')).join('\r\n')+'\r\n','utf8');
const summary={checked_date_kst:'2026-11-08',candidate_sites:catalog.length,status_counts:counts,live_three_field_success_sites:successful.length,live_recent_feed_sites:current.length,live_api_success_sites:apis.filter(r=>r.three_fields_verified).length,production_ready_sites:0,validated_sample_products:successful.reduce((n,r)=>n+r.sample_checks.filter(p=>p.name_present&&p.price_present&&p.url_present).length,0),priority_sites:catalog.filter(c=>c.priority_rank).sort((a,b)=>a.priority_rank-b.priority_rank).map(c=>({rank:c.priority_rank,id:c.id,name:c.name})),raw_product_responses_stored:false,product_names_and_urls_stored:'sha256_only',protected_baseline_files:inventory.protected_files.length};
fs.writeFileSync(path.join(dir,'summary.json'),JSON.stringify(summary,null,2)+'\n');
const top10=catalog.filter(c=>c.priority_rank).sort((a,b)=>a.priority_rank-b.priority_rank);
const md=s=>String(s).replaceAll('|','\\|').replaceAll('\n',' ');
const priorityReasons={aladin:'신간 RSS 실제 검증 성공; TTB 검색 API와 저장권 확인을 우선',yes24:'현행 전체 카탈로그 검색 문서와 즉시 키 발급; API 캐시 중심 설계 필요',elevenst:'전 카탈로그 검색용 ProductSearch 공식 가이드 및 기존 수집기 접점',domeggook:'공식 검색 API에 상품명·단가·URL 명시',domeme:'도매매 market=supply로 동일 공식 엔진 재사용 가능',ownerclan:'판매사에 공급 카탈로그를 제공하는 공식 GraphQL; 검색 재사용권 협의',coupang:'판매자 API와 별개인 공식 파트너스 상품 경로; 최종 승인 필요',gsshop:'공식 제휴 API 정책·범위 협의 절차 존재',enuri:'공식 운영사 상품 DB 솔루션 사업 소개를 근거로 공급 계약 가능성 확인',danawa:'가격비교 분야 보완 후보; 구형 API 대신 현행 데이터 제휴부터 확인'};
const lines=[
'# 국내 쇼핑몰 공식 데이터 소스 조사',
'',
'조사일: 2026-11-08 (Asia/Seoul). 브랜치: `feature/domestic-source-research`. 신규 파일은 모두 `research_domestic/` 안에 작성했다. 브랜치 전환·병합·커밋·푸시를 수행하지 않았다.',
'',
`30개 후보를 조사했다. 최종 분류는 **성공 ${counts['성공']}개 / 인증 대기 ${counts['인증 대기']}개 / 정책 확인 필요 ${counts['정책 확인 필요']}개 / 접근 불가 ${counts['접근 불가']}개**다. 상품명·판매가·URL의 실제 응답 검증은 **${successful.length}개 사이트, 각 3건(총 6건)**에서 성공했다. 이 중 예스24 RSS는 오래된 자료다. 최근 발행 피드를 확인한 곳은 **알라딘 1개**이며, 영구 상품 DB 저장·상용 재사용까지 승인된 운영 연동은 **0개**다. 성공은 응답 필드 검증을 뜻하며 저장 라이선스 승인을 뜻하지 않는다.`,
'',
'## 실제 응답 검증',
'',
'| 사이트 | 실제 요청 | 검증 결과 | 최신성 및 한계 |',
'|---|---|---|---|',
...rss.map(r=>`| ${r.id==='yes24'?'예스24':'알라딘'} | [공식 RSS](${r.url}) | HTTP ${r.http_status}; 같은 상품의 필드 ${r.sample_checks?.length||0}건 검증 | ${r.id==='yes24'?'본문 2025-06-08, 피드 생성 2025-06-07. 현재 가격 소스로 제외; API 키 발급 대기':'피드 생성 2026-11-08. 컴퓨터/모바일 신간 일부만 포함; 전 카탈로그 검색 아님'} |`),
'',
'알라딘 RSS는 공식 [분야별 모든 신간 안내](https://www.aladin.co.kr/rsscenter/new_all.aspx)와 분야 페이지의 `rel=alternate` 링크에서 찾았다. 예스24 RSS는 공식 [베스트셀러 RSS 안내](https://www.yes24.com/rss/bestSeller.aspx)에 공개된 주소다. 게시된 RSS의 HTTPS 주소로만 요청했고 상품 상세페이지나 피드의 링크를 따라가지 않았다. 구독 목적의 소량 응답 검사이며, 외부 검색 서비스에서의 저장·재사용 승인으로 간주하지 않는다.',
'',
'예스24는 여러 책이 하나의 RSS item 설명에 들어 있어 각 상품 링크부터 다음 상품 링크 전까지의 판매가를 묶었다. 채널 제목을 상품명으로 오인하지 않는다. 알라딘은 정가 대신 명시된 판매가를 검사한다. 원문·상품명·상품 URL은 파일에 저장하지 않았고, 해시·검증 여부·판매가 수치·피드 날짜만 남겼다. 실제 검증 증거는 [public_verification.json](public_verification.json), 주소 발견 근거는 [document_discovery.json](document_discovery.json)과 [rss_discovery.json](rss_discovery.json)이다.',
'',
'## 우선 연동 및 승인 추진 10개',
'',
'아래 순위는 조건 충족 후 연동할 후보의 순서다. 10개 모두 즉시 운영 가능한 소스라는 뜻은 아니다. 1~7은 실제 공식 카탈로그/상품 API가 확인된 후보, 8은 범위 협의가 필요한 직접 제휴, 9~10은 현행 상품 DB 공급 가능성부터 확인할 예비 후보다. 도매꾹·도매매는 서로 다른 몰이지만 공통 API 제공자이므로 독립 인증 시스템 2개로 집계하지 않는다.',
'',
'| 순위 | 몰 | 선정 이유 | 남은 절차 |',
'|---|---|---|---|',
...top10.map(c=>`| ${c.priority_rank} | [${c.name}](${c.primary_url}) | ${md(priorityReasons[c.id])} | ${md(c.next_step)} |`),
'',
'## 인증과 저장 정책에서 확인한 사항',
'',
'- **네이버쇼핑**: [공식 종료 공지](https://developers.naver.com/notice/article/32530)는 쇼핑·책·전문자료 검색 API가 2026-07-31 종료되었고, 기존 키 유예나 대체 API가 없다고 명시한다. 폐지된 API는 호출하지 않았다.',
'- **예스24**: [공식 키 발급 안내](https://developers.yes24.com/docs/apikey)는 로그인·목적 입력·약관 동의 후 즉시 발급을 안내한다. [API 약관 제6조](https://developers.yes24.com/support/terms)는 일시 캐시, 변동정보 갱신, 출처·원상품 링크 표시를 요구하며 별도 DB 구축을 위한 체계적 축적과 재배포를 제한한다. 현재 프로젝트의 영구 상품 DB 적재에는 별도 허가가 필요하다. API 약관의 허용을 RSS나 다른 몰에 적용하지 않는다.',
'- **알라딘**: [TTB 공식 안내](https://www.aladin.co.kr/ttb/wmain.aspx)는 회원가입·약관 동의·URL 등록을 안내한다. 연결된 API 약관 페이지는 웹 도구에서 403으로 본문 확인이 막혀 저장권을 미확정으로 두었다. RSS 성공과 TTB API 인증 성공을 구분한다.',
'- **11번가**: [현행 개발가이드](https://openapi.11st.co.kr/openapi/OpenApiGuide.tmall)에서 `ProductSearch`를 직접 확인했다. 기본 서비스 소개는 판매자 API 중심이고 구형 `OpenApiSearch.tmall` 문서는 404였다. 검색용 키 발급과 캐시/가격 갱신/저장 조건은 별도 확인해야 한다.',
'- **도매꾹·도매매**: [공식 상품목록 v4.1](https://docs.channel.io/domeggook_api/ko/articles/43780628)은 `getItemList`, `market=dome/supply`, `title/price/url`을 명시한다. 일반 Open API 키와 로그인·주문용 Private 승인권은 다르다. 도매 단가와 최소주문수량을 소비자 단품 판매가로 혼동하면 안 된다.',
'- **오너클랜**: [공식 API 사용법](https://ownerclan.com/V2/service/api-center-guide.php)은 판매사 JWT와 GraphQL을 안내한다. 공급 상품을 판매 채널로 보내는 권한과 독립 가격비교 DB 사용권은 구분해야 한다. 실제 상품 URL 필드까지 확인한 뒤 최소 쿼리를 구현해야 하므로 이번에 임의 GraphQL 요청을 보내지 않았다.',
'- **쿠팡·GS SHOP**: 쿠팡 [공식 파트너스 가이드](https://partners.coupangcdn.com/partners-guide/partners-guide-20240716100922.pdf)와 [파트너스 포털](https://partners.coupang.com/#/affiliate/ws), GS SHOP [제휴 API 안내](https://partners.gsshop.com/api/apiMain)를 근거로 분류했다. 쿠팡 현행 계정별 검색 권한·한도·저장 정책과 GS 제공 범위는 승인 후 확인한다. 쿠팡 판매자 키를 파트너스 키로 재사용하지 않는다.',
'',
'G마켓·옥션·롯데ON·CJ온스타일·카카오쇼핑 등은 판매자/권한 범위 중심이다. API나 파트너 포털이 있다는 이유로 전체 쇼핑몰 검색 권한을 가정하지 않는다. 나머지 몰의 미확인 정책에는 승인된 것으로 추정하는 대신 명시적으로 `storage_approved=false`를 기록했다. 공식 문의를 실제 발송하거나 계정 생성·약관 동의를 대행하지 않았다.',
'',
'## 30개 후보 및 근거',
'',
'상세 API/RSS/제휴 피드, 인증, 저장 정책, 근거 URL, 응답 확인 시각, 다음 조치는 [candidates.csv](candidates.csv)에 있다. 공개 API 미확인은 검토한 공식 자료에서 찾지 못했다는 의미이며 존재하지 않는다는 확정 판단이 아니다. 일반적인 제휴 문의 창구를 상품 피드 제공 약속으로 해석하지 않는다.',
'',
'| 몰 | 범위 | 상태 | 조사 결론 / 공식 근거 |',
'|---|---|---|---|',
...catalog.map(c=>`| ${c.name} | ${c.scope} | ${c.status} | [공식 자료](${c.primary_url}) — ${md(c.finding)} |`),
'',
'[공식 문서 HTTP 확인 결과](document_checks.json)는 상품 데이터 성공 건수에 포함하지 않는다. 무신사 기업 CMS 문서와 올리브영 문서는 직접 요청에서 403이었고 중단했다. 홈앤쇼핑은 직접 요청 302를 따라가지 않았다. 웹 검색 도구의 요약/캐시 확인과 로컬의 실제 HTTP 응답은 구분하며, 200이어도 로그인/JS 셸이면 API 권한이나 본문 확보를 뜻하지 않는다.',
'',
'## 로컬 기존 실험 분석',
'',
`루트의 *_probe.py **${inventory.probes.length}개**를 읽기 전용으로 분석했다. 분석 도구는 실행문을 호출하거나 import하지 않고 파일 전체를 읽어 import·함수·URL·추출 신호를 기록했다. [local_inventory.json](local_inventory.json)에 파일별 SHA-256과 분석 목록이 있다.`,
'',
'- 일반 쇼핑몰 probe: HTML 카드, JSON-LD, NEXT_DATA/임베디드 JSON, 가격/URL 후보를 찾는 실험이다. 파싱 가능성은 공식 수집 허가를 의미하지 않는다.',
'- `elevenst_api_probe.py`, `elevenst_xhr_probe.py`: 저장 HTML/자바스크립트 번들에서 검색 내부 요청을 탐색한다. `ProductSearch` Open API와 구분했다.',
'- 중고나라 probe 3개: HTML·API 후보·Playwright 네트워크 관찰 실험이다. 비공개 API 검증이나 브라우저 재수집을 수행하지 않았다.',
'- 다수 probe가 `crawler_output/` 등에 파일을 저장하므로 기존 스크립트를 실행하지 않았다. `.tmp_kurly_*` 폴더도 해시 확인만 했다.',
'',
'로컬 파일 이름과 docs/backend/crawler_engine/tests의 후보 관련 텍스트를 확인했지만 기존 140개 쇼핑몰 후보 자료는 발견하지 못했다. `docs/source-access.md`의 기존 공식 접근 정책과 11번가/네이버 조사 결과는 참고했고, 공식 문서로 현재 상태만 보강했다. 미발견은 이 작업공간에서의 조사 결과이며 다른 컴퓨터/브랜치에 없다는 뜻은 아니다.',
'',
'## 재실행',
'',
'Node.js 20 이상, 외부 npm 패키지 불필요. 이번 환경은 Node 24.20.0으로 실행했다. `.venv`가 참조하는 Python이 없어 기존 Python 환경은 수정하지 않았다. 모든 출력 경로는 스크립트 위치 기준 `research_domestic/`로 고정된다.',
'',
'```powershell',
'node --test research_domestic/test_rss.mjs',
'node research_domestic/check_public.mjs',
'node research_domestic/check_apis.mjs',
'node research_domestic/build_report.mjs',
'node research_domestic/inventory.mjs',
'```',
'',
'`check_public.mjs --source=aladin` 또는 `--source=yes24`로 피드 1개만 확인할 수 있다. 두 피드를 기본 각 1회 요청하고 같은 상품의 필드 최대 3건만 검사한다. 피드 크기는 서버가 정하며 알라딘 응답 25 item 중 3개만 검사했다. 15초 timeout, 2MB 상한, 재시도·페이지 순회·리다이렉트 추적 없음. 파서 회귀 검사 3개 통과: 요약 RSS 상품 연결, 정가/판매가 구분, 잘못된 응답·외부 엔티티 거부.',
'',
'`check_apis.mjs`는 프로세스 환경변수의 존재만 확인한다. `.env`를 읽지 않고 키나 헤더·원응답·키가 들어간 URL·오류 본문을 출력하지 않는다. 이번 실행에서 `YES24_API_KEY`, `ALADIN_TTB_KEY`, `ELEVENST_API_KEY`, `DOMEGGOOK_API_KEY`가 없어 5개 몰 모두 네트워크 호출 0회로 보류했다. 승인받은 키가 환경에 주입되면 `--source=yes24|aladin|elevenst|domeggook|domeme` 중 하나를 지정할 수 있으며 공식 GET을 1회, 결과 최대 3건만 검사한다. 키가 있는 경로의 라이브 실행은 아직 검증하지 못했다.',
'',
'`check_documents.mjs`는 이미 기록된 공식 문서 응답을 재사용하여 불필요한 재요청을 피한다. 강제 최신성 검사가 필요하면 별도의 명시적 작업으로 진행해야 한다. `inspect_docs.mjs`는 최초 공식 안내 링크 발견용, `check_elevenst_docs.mjs`는 판매자 문서와 ProductSearch 문서 구분용이다. 관측값과 정책 판단은 날짜가 있으므로 재실행 후 새 약관/내용을 검토하여 `catalog.mjs`의 판단도 갱신해야 한다. 보고서 생성만으로 정책 승인 상태가 자동 바뀌지 않는다.',
'',
'## 남은 승인 절차와 통합 인계',
'',
'1. 예스24·알라딘·11번가·도매꾹/도매매의 공식 키를 발급하고 최소 API 응답을 확인한다. 키는 파일/CSV/채팅에 넣지 않고 환경변수로 전달한다.',
'2. 각 제공자에게 검색 서비스 노출, 영구 DB/가격 이력 보관, 캐시 TTL, 업데이트·삭제, 재배포, AI 학습/가공 용도를 구분해 서면 허용 범위를 확인한다. 확인 안 된 보관기간을 임의 숫자로 정하지 않는다.',
'3. 쿠팡은 파트너스 최종 승인 및 현행 상품 검색 사용권, 오너클랜은 판매사 API/검색 재사용권, GS SHOP은 제휴 제안과 데이터 범위·정책 협의를 진행한다. 에누리·다나와는 현행 DB 공급 가능성부터 확인한다.',
'4. 다른 컴퓨터의 `laptop-work-backup` 공통 엔진에는 이번 파일을 자동 연결하지 않는다. 승인 이후 검증된 source만 수동 검토해 반영한다. 특히 예스24의 체계적 영구 DB 축적 제한, 네이버 검색 종료, 판매자 API 범위, 도매 최소주문수량을 통합 설계에 반영해야 한다.',
'',
`[integrity_check.json](integrity_check.json)으로 기존 보호 대상 ${inventory.protected_files.length}개 파일의 변경·누락 여부를 대조한다. 실험 파일과 backend/crawler_engine/docs 등은 변경하지 않았다.`,
''];
fs.writeFileSync(path.join(dir,'README.md'),lines.join('\n'),'utf8');
console.log(JSON.stringify(summary));
