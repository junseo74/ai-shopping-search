// Explicit opt-in live run. This program never writes raw response or product names/URLs.
import { writeFile,readFile } from 'node:fs/promises';
import { run as apple } from './adapters/apple.mjs';
import { run as off } from './adapters/openfoodfacts.mjs';
import { run as prices } from './adapters/openprices.mjs';
import { evidence } from './adapters/common.mjs';
import { sources } from './sources.mjs';
if(!process.argv.includes('--live')) throw new Error('Pass --live for three documented public GET requests');
const endpoints=[];
for(const [id,provider,run] of [['apple','apple',apple],['off','openfoodfacts',off],['prices','openfoodfacts',prices]]) {
  const result=await run();
  const proof={id,provider,observed_at:new Date().toISOString(),...evidence(result)};
  endpoints.push(proof);console.log(JSON.stringify({id,status:proof.status,products_verified:proof.products_verified}));
}
const successfulProviders=[...new Set(endpoints.filter(e=>e.status==='ok').map(e=>e.provider))];
const fullProviders=[...new Set(endpoints.filter(e=>e.samples.some(s=>s.complete_seven_fields)).map(e=>e.provider))];
const report={observed_at:new Date().toISOString(),research_date:'2026-11-08',
  definitions:{live_success:'HTTP200 plus at least one normalized genuine product; missing fields are reported, never fabricated',
    complete_success:'All seven requested fields are present on the same product response',
    operation_ready:'Project currently has credentials/permissions and production license obligations implemented',
    storage_license_permits:'Published license permits retention subject to obligations; not a project-specific approval'},
  counts:{new_candidates:sources.length,official_paths:sources.filter(s=>s.official_path_confirmed).length,
    live_verified_providers:successfulProviders.length,live_verified_endpoints:endpoints.filter(e=>e.status==='ok').length,
    complete_seven_field_providers:fullProviders.length,operation_ready:0,
    storage_license_permitted_providers:sources.filter(s=>s.storage_license_permits).length,
    project_specific_long_term_storage_approvals:0,implemented_adapters:3,authenticated_api_live_successes:0},
  successful_providers:successfulProviders,complete_providers:fullProviders,
  endpoints,not_called:sources.filter(s=>!['apple','openfoodfacts'].includes(s.id)).map(s=>({id:s.id,reason:s.live_status})),
  limitations:['No website UI, database integration, application submission or production rollout',
    'Two providers; Open Prices is not a third provider',
    'Initial schema probe returned 10 Prices rows because page_size was ignored; no extra pages requested. size=3 validated subsequently',
    'Sandbox network failure was resolved using authorized direct network access; no service restriction bypass',
    'Only hashes/presence/price/currency/date retained; product contents and personal data not persisted']};
let previous=[];
try{previous=JSON.parse(await readFile(new URL('./verification_attempts.json',import.meta.url),'utf8'));}catch{}
previous.push({observed_at:report.observed_at,endpoints:report.endpoints});
await writeFile(new URL('./verification_attempts.json',import.meta.url),JSON.stringify(previous,null,2)+'\n');
await writeFile(new URL('./verification.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
