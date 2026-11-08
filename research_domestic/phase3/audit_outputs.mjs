// Local output audit: report path/line/type only, never a matched value.
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const here=new URL('./',import.meta.url);
const findings=[];let files=0,jsonFiles=0;
async function inspect(dir) {
  for(const e of await fs.readdir(dir,{withFileTypes:true})) {
    const u=new URL(e.name+(e.isDirectory()?'/':''),dir);
    if(e.isDirectory()){await inspect(u);continue;}
    if(!e.isFile()||e.name==='audit_outputs.json')continue;
    files++;const content=await fs.readFile(u,'utf8');
    if(e.name.endsWith('.json')){JSON.parse(content);jsonFiles++;}
    const lines=content.split(/\r?\n/);
    for(let i=0;i<lines.length;i++) {
      const line=lines[i];
      const types=[];
      if(/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/.test(line))types.push('private_key');
      if(/\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/.test(line))types.push('cloud_access_key');
      if(/\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/.test(line))types.push('jwt');
      if(/\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{20,}/.test(line))types.push('provider_token');
      if(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(line)) {
        // Negative URL-userinfo fixture deliberately contains synthetic credentials.
        if(!line.includes('user:FIXTURE_ONLY@'))types.push('email_or_userinfo_review');
      }
      if(/\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b/.test(line))types.push('korean_mobile_number');
      if(/\b\d{6}-[1-4]\d{6}\b/.test(line))types.push('resident_id_pattern');
      for(const type of types)findings.push({file:fileURLToPath(u).replaceAll('\\','/').split('/phase3/')[1],line:i+1,type});
    }
  }
}
await inspect(here);
const result={observed_at:new Date().toISOString(),files,jsonFiles,findings,
  scope:'phase3 output only; key/JWT/private-key/PII pattern and JSON parsing checks',
  manual_review:'Only fixed public URLs, no auth inputs/headers/cookies; hash strings and synthetic fixtures are not live credentials',
  limitation:'Pattern checks are not proof of absence of every secret format'};
await fs.writeFile(new URL('./audit_outputs.json',here),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({files,jsonFiles,findings}));if(findings.length)process.exitCode=1;
