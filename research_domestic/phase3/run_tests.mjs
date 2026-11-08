import { spawnSync } from 'node:child_process';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const files=['adapters.test.mjs','transport.test.mjs'].map(f=>fileURLToPath(new URL(`./tests/${f}`,import.meta.url)));
const r=spawnSync(process.execPath,['--test','--test-reporter=tap',...files],{encoding:'utf8',timeout:30000});
const output=r.stdout||'';
const total=Number(output.match(/^# tests (\d+)/m)?.[1]||0);
const passed=Number(output.match(/^# pass (\d+)/m)?.[1]||0);
const failed=Number(output.match(/^# fail (\d+)/m)?.[1]||0);
const result={observed_at:new Date().toISOString(),test_kind:'synthetic_and_permission_gate_tests_not_live_service',
  node:process.version,total,passed,failed,exit_code:r.status,all_passed:r.status===0&&total>0&&passed===total};
await writeFile(new URL('./tests/results.tap',import.meta.url),output);
await writeFile(new URL('./tests/results.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));if(!result.all_passed){console.log(output);process.exitCode=1;}
