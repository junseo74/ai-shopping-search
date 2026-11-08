// Local-only integrity/schema/secret checks. Emits locations and types, never matched values.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {sha} from '../net.mjs';
import {applications,revalidation} from './research_data.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(dir,'../..');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const baseline=read(path.join(dir,'../local_inventory.json'));
const changed=baseline.protected_files.filter(p=>!fs.existsSync(path.join(root,p.path))||sha(fs.readFileSync(path.join(root,p.path)))!==p.sha256).map(p=>p.path);
function csv(text){
 const rows=[];let row=[],cell='',quoted=false;
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
  else if(c===','&&!quoted){row.push(cell);cell='';}
  else if(c==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}
  else cell+=c;
 }
 if(quoted)throw new Error('invalid_csv');
 const keys=rows.shift().map(x=>x.replace(/^\uFEFF/,''));
 return rows.filter(r=>r.length>1).map(r=>Object.fromEntries(keys.map((k,i)=>[k,r[i]])));
}
const candidates=csv(fs.readFileSync(path.join(dir,'../candidates.csv'),'utf8'));
const sameIds=(a,b)=>JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
if(!sameIds(applications.map(a=>a.id),candidates.filter(c=>c.status==='인증 대기').map(c=>c.id)))throw new Error('approval_scope_mismatch');
if(!sameIds(revalidation.map(a=>a.id),candidates.filter(c=>c.status==='정책 확인 필요').map(c=>c.id)))throw new Error('revalidation_scope_mismatch');
if(csv(fs.readFileSync(path.join(dir,'comparison.csv'),'utf8')).length!==30)throw new Error('comparison_scope_mismatch');
const findings=[];let syntax=0,jsons=0,syntheticFixtureExclusions=0;
for(const name of fs.readdirSync(dir)){
 const file=path.join(dir,name);if(!fs.statSync(file).isFile())continue;
 if(name.endsWith('.mjs')){execFileSync(process.execPath,['--check',file],{stdio:'pipe'});syntax++;}
 const text=fs.readFileSync(file,'utf8');
 if(name.endsWith('.json')){JSON.parse(text);jsons++;}
 for(const [i,line]of text.split(/\r?\n/).entries()){
  for(const [type,re]of [
   ['private_key',/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
   ['provider_key',/\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}/],
   ['jwt',/\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/],
   ['auth_literal',/\b(?:Bearer|Basic)\s+[A-Za-z0-9+\/_=-]{16,}/i],
   ['email_or_personal_contact',/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)/i],
  ]){
   const matched=line.match(re);if(!matched)continue;
   // The invalid-URL regression test deliberately contains synthetic userinfo.
   if(name==='test_collector.mjs'&&type==='email_or_personal_contact'&&matched[0]===['TEST_ONLY','www.yes24.com'].join('@')){syntheticFixtureExclusions++;continue;}
   findings.push({file:'research_domestic/phase2/'+name,line:i+1,type});
  }
 }
}
const inputSummary=read(path.join(dir,'summary.json')).first_phase_inputs;
const inputsUnchanged=sha(fs.readFileSync(path.join(dir,'../README.md')))===inputSummary.readme_sha256&&sha(fs.readFileSync(path.join(dir,'../candidates.csv')))===inputSummary.candidates_csv_sha256;
const report={checked_at:new Date().toISOString(),protected_baseline_files:baseline.protected_files.length,protected_changed_or_missing:changed,first_phase_readme_csv_unchanged:inputsUnchanged,approval_ids_match_first_phase_7:true,revalidation_ids_match_first_phase_21:true,comparison_rows:30,syntax_checked:syntax,json_validated:jsons,synthetic_fixture_exclusions:syntheticFixtureExclusions,sensitive_pattern_findings:findings};
fs.writeFileSync(path.join(dir,'integrity.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
if(changed.length||!inputsUnchanged||findings.length)process.exitCode=1;
