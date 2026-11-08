import fs from 'node:fs';
import {sha} from '../net.mjs';
import baseline from '../catalog.mjs';
import {evidence,revalidation,applications} from './research_data.mjs';
const out=new URL('./',import.meta.url);
const write=(file,text)=>fs.writeFileSync(new URL(file,out),text,'utf8');
const json=(file,value)=>write(file,JSON.stringify(value,null,2)+'\n');
const read=file=>JSON.parse(fs.readFileSync(new URL(file,import.meta.url),'utf8'));
const live=read('./live_results.json');
const prior=read('../summary.json');
if(applications.length!==7||revalidation.length!==21)throw new Error('unexpected_research_scope');
const csv=(file,rows)=>{const keys=Object.keys(rows[0]);const q=v=>'"'+String(v??'').replaceAll('"','""')+'"';write(file,'\uFEFF'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')+'\r\n');};
const md=s=>String(s).replaceAll('|','\\|').replaceAll('\n',' ');
const now=new Date().toISOString();
const supplement={
 aladin:{difficulty:'낮음~중간(TTB 가입·이용권 확인)',scope:'상품 검색 API 및 분야별 RSS',refresh:'추가 경제경영 RSS 2026-11-08 생성 확인; 판매가격의 실시간 일치 보증은 아님'},
 yes24:{difficulty:'낮음(키 발급); 장기 저장은 별도 허가',scope:'Goods 검색·상세 및 Category; 기존 RSS는 오래됨',refresh:'API 재조회로 갱신 가능; 공식 TTL 수치는 미확인'},
 elevenst:{difficulty:'중간(신규 발급 조건 확인)',scope:'ProductSearch 카탈로그 검색; 키 필요',refresh:'승인 후 검색 결과 재조회; 운영 갱신 정책은 확인 필요'},
 domeggook:{difficulty:'중간(목적 유형 사전확인)',scope:'market=dome 도매 상품목록',refresh:'검색·단종 제외 응답을 통한 갱신 가능; MOQ와 사업자 제한 보존'},
 domeme:{difficulty:'중간(목적 유형 사전확인)',scope:'market=supply 배송대행 상품목록',refresh:'공통 API이나 독립 소매상품 카탈로그로 과대 집계하지 않음'},
 ownerclan:{difficulty:'중간~높음(판매사·외부 검색 이용권)',scope:'판매사 공급상품 GraphQL; URL 사양 미확정',refresh:'updatedAt·itemHistories 변경이력 명세 신규 확인'},
 coupang:{difficulty:'높음(활동 채널 최종 승인)',scope:'파트너스 상품 정보; 계정별 검색권 확인',refresh:'현행 계정 한도 확인 전 주기 확정 불가'},
 gsshop:{difficulty:'높음(제휴 계약)',scope:'협의된 상품/주문 데이터 범위',refresh:'제공 방식·주기 계약 협의'},
 naver:{difficulty:'현재 불가',scope:'종료된 쇼핑 검색 API; 1차 결과 재사용',refresh:'종료된 API 재호출하지 않음'},
};
const comparison=baseline.map(b=>{
 const u=revalidation.find(r=>r.id===b.id),a=applications.find(a=>a.id===b.id),s=supplement[b.id];
 const v=live.find(r=>r.source===b.id)||live.find(r=>r.source==='aladin_rss_170'&&b.id==='aladin');
 return {id:b.id,name:b.name,baseline_status:b.status,phase2_review:u?.review_mode||(['naver'].includes(b.id)?'prior_verified_retirement_reused':'approval_or_feed_expansion'),integration_potential:b.id==='yes24'?'캐시형 검색 MVP 우선; 키 발급 필요':b.id==='aladin'?'공식 RSS 소량 진단 가능; 상용 데이터 사용권 미확정':a?'승인·목적 확인 후 제한적 시험':b.id==='naver'?'대체 공식 검색 API 전 보류':'판매자 동의 또는 별도 데이터 제휴 전 보류',approval_difficulty:s?.difficulty||'높음/미확정(추정; 일반 검색용 권한 없음)',difficulty_basis:'engineering_judgment_not_provider_SLA',product_scope:s?.scope||b.scope,refresh_capability:s?.refresh||u?.refresh||'공식 권한 확보 전 미확정',commercial_use:b.id==='yes24'?'API: allowed_with_conditions; RSS: unconfirmed':a?.commercial_use||'unconfirmed',long_term_storage:a?.long_term_storage||'not_approved',technical_phase2_status:v?.status||'no_product_request',new_three_field_samples:v?.product_count||0,additional_finding:u?.delta||s?.scope||'',next_action:u?.decision||a?.steps.join(' → ')||b.next_step,evidence_urls:u?.evidence_ids.map(id=>evidence[id].url).join(' | ')||a?.evidence_ids.map(id=>evidence[id].url).join(' | ')||b.primary_url};
});
csv('comparison.csv',comparison);
csv('revalidation.csv',revalidation.map(r=>({id:r.id,name:baseline.find(b=>b.id===r.id).name,checked_date_kst:'2026-11-08',review_mode:r.review_mode,new_finding:r.delta,decision:r.decision,refresh:r.refresh,commercial_use:r.commercial_use,long_term_storage:r.long_term_storage,evidence_urls:r.evidence_ids.map(id=>evidence[id].url).join(' | '),baseline_reference:r.evidence_ids.length?'../candidates.csv (previous_scope_only)':'../candidates.csv + targeted phase2 search; no newly confirmed source'})));
json('evidence.json',{observed_date_kst:'2026-11-08',evidence,search_method:'Targeted provider-domain and API/RSS/feed/affiliate searches; only primary official results used for positive conclusions. Negative findings are bounded, not proof of nonexistence.',revalidation_searches:[{ids:['kyobo','ohouse','kurly','oliveyoung'],query:'교보문고 Open API 제휴 / 오늘의집 API 큐레이터 / 컬리 API 제휴 / 올리브영 API 파트너스'},{ids:['ssg','danawa','enuri','musinsa','29cm','ably','zigzag'],query:'Official domain searches for 상품 API 제휴 / 크리에이터 어필리에이트 상품 데이터 API / 상품 데이터 API 제휴'},{ids:['hmall','lottehome','nsmall','hnsmall'],query:'각 쇼핑몰명 + Open API 개발자 상품 제휴'},{ids:['gmarket','auction','cjonstyle','lotteon','kakao'],query:'Official domain searches for 상품 API 개발 가이드 / 상품 피드 API 제휴'},{ids:['joongna'],query:'중고나라 상품 데이터 API 제휴 공식; domain joongna.com'}]});
json('approvals.json',{prepared_at:now,submission_status:'drafts_prepared_not_submitted',account_creation_performed:false,paid_subscription_performed:false,applications});
const approvalText=[
'# 공식 API 승인 신청 준비',
'',
'2026-11-08 기준. 아래 7개는 1차 `인증 대기` 몰과 정확히 일치한다. 신청 문안과 확인 항목을 준비했으며 실제 신청·계정 생성·결제는 하지 않았다. 개인·사업자 정보, 실제 서비스 URL, 요청량은 사용자가 기입해야 한다. 로그인 뒤에만 보이는 필수서류는 미확정으로 표시했다. 난이도는 개발 관점의 상대 평가이며 승인 가능성이나 처리기한을 보장하지 않는다.',
'',
'## 공통 체크리스트',
'',
'- [ ] 이용 주체(개인/개인사업자/법인)를 결정하고 본인 명의 계정 사용 권한을 확인한다.',
'- [ ] 실제 서비스명·접속 URL 또는 검토 화면, 담당자 정보를 공식 비공개 신청 양식에 입력한다. 이 저장소에는 신분증·통장·사업자 서류나 실명 연락처를 넣지 않는다.',
'- [ ] [신청 문안](application_drafts.md)의 제안 호출량·목적·수익 모델을 실제 운영 계획에 맞게 수정한다.',
'- [ ] 검색 결과 노출, 일시 캐시, 영구 DB, 가격 이력, 재배포, AI 학습 용도를 각각 확인한다. 한 가지 허용을 다른 용도에 확대하지 않는다.',
'- [ ] 현행 약관을 직접 읽고 사용자가 신청·동의·제출한다. 별도 비용이나 약정이 있으면 가입 전에 판단한다.',
'- [ ] 승인 회신/계약·허용 범위·갱신/삭제 조건을 비공개로 보관한다. 발급 키는 환경변수로만 전달한다.',
'',
...applications.flatMap(a=>{
 const b=baseline.find(b=>b.id===a.id);
 return ['## '+b.name,'',`신청 경로: [공식 사이트](${a.application_url}). 난이도: ${a.difficulty}.`,'',`확인된 조건: ${a.confirmed_inputs.join(' / ')}.`, '',`필요 서류: ${a.required_documents}`,'',`준비 정보(실제 값은 사용자 입력): ${a.prepared_information.join(' / ')}.`,'',...a.steps.map(s=>'- [ ] '+s),'',`미확정 항목: ${a.unconfirmed.join(' / ')}.`, '',a.evidence_ids.length?'추가 근거: '+a.evidence_ids.map(id=>`[${id}](${evidence[id].url})`).join(', ')+'.':'근거: 1차 공식 안내 + [2차 HTTP 문서 확인](new_document_checks.json). 비공개 필드를 추정하지 않음.',''];
 }),
'## 알라딘 추가 절차',
'',
'알라딘은 1차 RSS 성공으로 위 7개에 포함되지 않지만 TTB API 키는 별도로 필요하다. [공식 TTB](https://www.aladin.co.kr/ttb/wmain.aspx)에서 사용자가 회원가입·URL 등록·약관 동의·키 발급을 진행한다. 상업적 검색·장기 저장 범위는 아직 미확정이며 RSS 구독 허용을 API 데이터 라이선스로 해석하지 않는다. 키는 `ALADIN_TTB_KEY`로 주입한다.',
'',
'## 우선 순서',
'',
'1. 예스24 기본 키와 캐시형 검색부터 검토한다. FAQ상 일반 상업 모델은 가능하지만 영구 상품 DB는 별도 문제다. 애드온 가입은 기본 API 이용에 필수가 아니며 이번에 신청하지 않았다.',
'2. 11번가의 현재 신규 ProductSearch 발급 조건과 알라딘 TTB 사용권을 확인한다.',
'3. 도매꾹·도매매는 가격비교 목적 분류 회신부터 받는다. Open 키만 발급됐다고 자체 연동 전체가 승인됐다고 판단하지 않는다.',
'4. 오너클랜·쿠팡·GS SHOP은 용도 승인·범위·키/계약이 확보된 뒤 진행한다.',
''];
write('approvals.md',approvalText.join('\n'));
const newSuccess=live.filter(r=>r.technical_success);
const summary={prepared_at:now,phase2_revalidated_policy_candidates:revalidation.length,phase2_approval_drafts:applications.length,phase2_product_requests:live.reduce((n,r)=>n+r.request_count,0),phase2_verified_sites:[...new Set(newSuccess.map(r=>r.source.startsWith('aladin_')?'aladin':r.source))].length,phase2_verified_products:newSuccess.reduce((n,r)=>n+r.product_count,0),newly_verified_retailer_count:0,cumulative_technical_sites:prior.live_three_field_success_sites,cumulative_recent_feed_sites:1,live_authenticated_api_success_sites:live.filter(r=>r.technical_success&&!r.source.startsWith('aladin_rss')).length,commercial_api_permission_confirmed:['yes24 (conditional; no key/live API success yet)'],long_term_catalog_storage_approved_sites:0,new_public_machine_feed:['https://www.aladin.co.kr/rss/new_all/170'],new_official_vendor_document_paths:['https://eapi.ssgadm.com/info/main.ssg','https://github.com/nsshopping/Affiliate-API'],api_prototype_adapters:5,rss_prototype_adapters:1,api_fixture_tests_passed:15,forms_submitted:0,paid_signups:0,first_phase_inputs:{readme_sha256:sha(fs.readFileSync(new URL('../README.md',import.meta.url))),candidates_csv_sha256:sha(fs.readFileSync(new URL('../candidates.csv',import.meta.url)))}};
json('summary.json',summary);
const readme=[
'# 국내 공식 데이터 소스 확보 2차 결과',
'',
'조사일: 2026-11-08 (Asia/Seoul). 1차 README·30개 후보 CSV를 분석한 뒤 미해결 승인/정책 항목을 보강했다. 1차 원본 파일·분류를 다시 생성하지 않고 이번 추가 결과만 이 폴더에 기록했다. 데스크톱 공통 엔진과 자동 통합하지 않았다.',
'',
`**이번 실제 검증: ${summary.phase2_verified_sites}개 쇼핑몰(알라딘), 새 RSS 1개, 상품명·판매가·URL ${summary.phase2_verified_products}건 성공. 새로 성공한 쇼핑몰 수는 0개다.** 기존과 합쳐 기술적 응답 성공 사이트는 2개(예스24 RSS는 오래된 자료), 최근 피드 확인 사이트는 1개다. 인증 API 실응답 성공은 0개, 상용 장기 상품 DB 저장권 확보는 0개다. 문서 HTTP 200, 검색 발췌, 합성 fixture 테스트를 실제 상품 응답 성공으로 집계하지 않았다.`,
'',
'## 1차 대비 확보한 것',
'',
'- **실제 수집 경로 확대**: 경제경영 분야의 [공식 RSS alternate 안내](https://www.aladin.co.kr/shop/wbrowse.aspx?CID=170)에서 `new_all/170`을 발견하고 HTTPS로 1회만 읽어 3개 상품을 확인했다. 1차 `new_all/351`을 재수집하지 않았다. 결과는 [live_results.json](live_results.json)에 해시·판매가·관측 시각만 남겼다.',
'- **신규 판매자 문서 2곳**: [SSG EAPI](https://eapi.ssgadm.com/info/main.ssg), [NS홈쇼핑 공식 GitHub INBOUND API](https://github.com/nsshopping/Affiliate-API). NS는 최신 스펙·방화벽 요청 자료가 있으나 입점몰이 NS에 연동하는 방향이므로 전체 상품 수집 경로로 승격하지 않았다.',
'- **예스24 활용 범위 구체화**: [FAQ](https://developers.yes24.com/support/faq)에서 상업 모델·타 판매처 링크 병기·Partner 요청 정보를 추가 확인했다. 출처와 원상품 링크, 일시 캐시 조건을 지키는 검색 MVP는 검토할 수 있다. 장기 DB 적재/재배포 제한은 그대로다.',
'- **신청 오류 예방**: 도매꾹·도매매의 [목적별 신청 가이드](https://openapi.domeggook.com/ko/articles/API-신청-가이드-787a96cd)를 확보했다. 기본 Open 안내와 자체 개발 목적의 신청 절차를 함께 읽어야 한다. 가격비교 서비스는 공식 기술지원의 유형·권한 회신 전 보류한다.',
'- **갱신 설계 근거**: 오너클랜 [상품 명세](https://www.ownerclan.com/V2/service/api-center-item.php)의 상품검색·변경이력·갱신시각을 확인했다. URL 필드가 미확정이므로 임의 URL로 제품을 완성하지 않았다.',
'- **피드로 오인하기 쉬운 경로 분리**: [올리브영 큐레이터](https://m.oliveyoung.co.kr/m/mtn/affiliate/guide)와 컬리 공식 큐레이터 설명은 링크 홍보 경로다. 에누리·다나와 EP는 입점몰→가격비교사 데이터 제출이며, 우리가 읽는 공개 상품 피드가 아니다. 링크프라이스 핫딜 API는 공식 대안이나 30개 몰별 참여·인증·저장권은 미확정이다.',
'',
'## 비교·신청 준비 문서',
'',
'| 결과물 | 내용 |',
'|---|---|',
'| [approvals.md](approvals.md) / [approvals.json](approvals.json) | 인증 대기 7개 각각의 신청 사이트·확인된 입력정보·서류·미확정 조건·사용자 직접 수행 체크리스트; 알라딘 추가 절차 |',
'| [application_drafts.md](application_drafts.md) | 실제 프로젝트를 기준으로 쓴 신청 목적·처리 방식·권한 문의 문안. 제출 안 함; 사용자/서비스 URL 등 미입력 표시 |',
'| [revalidation.csv](revalidation.csv) | 정책 대기 21개 추가 조사 결론·근거·보류 이유. 새 문서 확보와 제한된 검색에서 미발견을 구분 |',
'| [comparison.csv](comparison.csv) | 기존 30개 각각의 연동 가능성·승인 난이도·상품 범위·갱신·상업 사용·장기 저장을 분리한 비교 |',
'| [evidence.json](evidence.json) / [new_document_checks.json](new_document_checks.json) | 추가 공식 근거·관측 방법·신청 페이지 접근 상태; 원문 복사나 인증값 없음 |',
'',
'계정 생성과 양식 제출까지 끝났다는 의미의 신청 준비 완료는 아니다. 신청 문안·체크리스트는 준비됐지만 실사용자 정보, 실제 공개 URL, 현행 로그인 양식, 제공자의 답변이 필요하다. 공개 자료에서 보이지 않은 필수서류·심사기간·가격·TTL은 만들어 넣지 않았다.',
'',
'## 독립 수집기와 검증',
'',
'[collector.mjs](collector.mjs)는 기존 1차의 해시 진단을 넘어 API 응답을 메모리의 표준 상품 객체로 반환한다. 5개 API 어댑터는 예스24·알라딘·11번가·도매꾹·도매매이며 공식 계약 사양을 이용한다. 별도로 신규 알라딘 RSS 어댑터 1개가 있다. 원래 수집기와 DB를 import하지 않는다.',
'',
'표준 필드: source, name, price, currency, url, price_field, min_order_qty, business_only, observed_at, commercial_use, long_term_storage, redistribution. 판매가와 정가를 구분하고 도매 MOQ·사업자 조건을 보존한다. 반환 상품은 메모리에서만 유지하며 CLI는 해시/가격 증거만 쓴다. 상품 객체가 존재한다고 저장권이 생기지 않는다.',
'',
'```powershell',
'node --test research_domestic/phase2/test_collector.mjs',
'node research_domestic/phase2/run_validation.mjs --source=yes24',
'node research_domestic/phase2/build_phase2_report.mjs',
'```',
'',
'`--source`는 yes24/aladin/elevenst/domeggook/domeme/aladin_rss_170만 허용한다. 키는 프로세스 환경에서 읽고 `.env`는 자동으로 읽지 않는다. 이번에는 4종 키가 모두 없어 API 5개 몰 호출은 0회로 보류했다. API 실제 성공을 증명한 것은 아니다. 도매꾹·도매매는 키가 있어도 목적 승인 전에는 호출하지 않으며, 실제 승인 후에만 `DOMESTIC_DOME_PURPOSE_APPROVED=true`를 설정한다. 이 변수는 승인 신청이나 권한 부여를 대신하지 않는다.',
'',
'HTTPS 고정 endpoint, GET만 허용, 최대 3개 상품/1회 요청, 15초 timeout·2MB 상한을 사용한다. 리다이렉트·429·401·403에서 즉시 멈추고 재시도/페이지 순회/우회를 하지 않는다. 에러 본문·요청 URL·헤더·토큰을 출력하지 않는다. 상품 URL에 인증 쿼리가 있으면 제외한다.',
'',
'합성 fixture 및 제어 흐름 테스트 **15개 통과**. 5개 응답 정규화, 1회 호출 제한, 키 누락 시 미호출, 목적 승인 게이트, 정가/판매가, MOQ, 비정상 URL·인증 쿼리, XML 외부 엔티티, 401/403/429/302 중단, 예외 비밀값 출력 방지, 중복 제거를 검사했다. 이 테스트는 실제 제공자의 승인·가동 여부나 모든 XML 변형을 보장하지 않는다. 키가 있는 API 경로의 실서비스 검증은 남아 있다.',
'',
'## 운영 전 남은 일',
'',
'사용자가 우선 예스24 기본 키와 이용 약관을 확인하고 캐시형 검색 용도로 소량 시험하는 경로가 가장 구체적이다. 11번가 신규 검색키·알라딘 TTB·도매꾹/도매매 목적 권한이 다음이며, 오너클랜/쿠팡/GS SHOP은 별도 승인/계약을 기다려야 한다. 21개 정책 대기 몰은 승인된 전체 상품 수집 경로가 새로 열렸다고 판단하지 않았다.',
'',
'[summary.json](summary.json)은 1차 누적 수와 2차 신규 수를 분리한다. [integrity.json](integrity.json)은 원래 보호 파일 및 1차 입력 파일의 무결성 점검 결과다. 기존 실험·공통 엔진 파일은 수정하지 않았다. Git 전환/병합/푸시/리셋/클린과 계정 생성·신청 제출·유료 가입은 수행하지 않았다.',
''];
write('README.md',readme.join('\n'));
console.log(JSON.stringify(summary));
