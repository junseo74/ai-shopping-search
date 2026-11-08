// Initial schema confirmation. Persist no raw response, usernames, receipts, or product content.
import { request } from './transport.mjs';
import { writeFile, readFile } from 'node:fs/promises';
const results = [];
for (const id of ['apple', 'prices']) {
  const r = await request(id);
  const rows = id === 'apple' ? r.data?.results : id === 'off' ? (r.data?.product ? [r.data.product] : []) : r.data?.items;
  const result = { id, observed_at: new Date().toISOString(), status: r.status, http_status: r.http_status,
    response_keys: r.data ? Object.keys(r.data) : [], rows_received: Array.isArray(rows) ? rows.length : 0,
    field_names: Array.isArray(rows) && rows[0] ? Object.keys(rows[0]) : [],
    nested_field_names: Array.isArray(rows) && rows[0] ? Object.fromEntries(Object.entries(rows[0]).filter(([k,v]) => ['product','location'].includes(k) && v && typeof v === 'object').map(([k,v])=>[k,Object.keys(v)])) : {} };
  results.push(result); console.log(JSON.stringify(result));
}
let previous=[];
try { previous=JSON.parse(await readFile(new URL('./schema_checks.json',import.meta.url),'utf8')); } catch {}
await writeFile(new URL('./schema_checks.json', import.meta.url), JSON.stringify([...previous,...results], null, 2) + '\n');
