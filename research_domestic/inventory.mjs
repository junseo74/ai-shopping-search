import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const out = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(out);
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const probes = fs.readdirSync(root).filter(n => n.endsWith('_probe.py')).sort().map(file => {
  const b = fs.readFileSync(path.join(root,file)), t=b.toString('utf8');
  return {file, sha256:sha(b), lines:t.split('\n').length,
    imports:t.split('\n').filter(l=>/^(import |from )/.test(l)),
    functions:[...t.matchAll(/^(?:async )?def ([\w]+)\(/gm)].map(m=>m[1]),
    endpoints:[...new Set([...t.matchAll(/https?:\/\/[^\s"'`<>\\{}]+/g)].map(m=>m[0].split('?')[0]))].sort(),
    signals:{html:/HTMLParser|BeautifulSoup|extract_scripts/.test(t), browser:/playwright|chromium|cdp/i.test(t), network:/urlopen|fetch\(|\.get\(/.test(t), embedded_json:/__NEXT_DATA__|json_ld|application\/ld\+json/.test(t)}};
});
function walk(dir, result=[]){
  for(const e of fs.readdirSync(dir,{withFileTypes:true})) {
    if(e.isSymbolicLink()) continue;
    const p=path.join(dir,e.name);
    if(e.isDirectory()) walk(p,result);
    else if(e.isFile()) result.push({path:path.relative(root,p).replaceAll('\\','/'),sha256:sha(fs.readFileSync(p))});
  }
  return result;
}
const protectedFiles=probes.map(p=>({path:p.file,sha256:p.sha256}));
for(const name of ['backend','crawler_engine','collection_engine','docs','samples',...fs.readdirSync(root).filter(n=>n.startsWith('.tmp_'))]){
  if(fs.existsSync(path.join(root,name))) walk(path.join(root,name),protectedFiles);
}
const inventory={observed_at:new Date().toISOString(),probes,protected_files:protectedFiles};
const dest=path.join(out,'local_inventory.json');
if(fs.existsSync(dest)) {
  const old=JSON.parse(fs.readFileSync(dest));
  const now=new Map(protectedFiles.map(x=>[x.path,x.sha256]));
  const changes=old.protected_files.filter(x=>now.get(x.path)!==x.sha256).map(x=>x.path);
  fs.writeFileSync(path.join(out,'integrity_check.json'),JSON.stringify({observed_at:new Date().toISOString(),baseline_files:old.protected_files.length,changed_or_missing:changes},null,2)+'\n');
  console.log(JSON.stringify({probes:probes.length,protected_files:protectedFiles.length,changed_or_missing:changes}));
} else {
  fs.writeFileSync(dest,JSON.stringify(inventory,null,2)+'\n');
  console.log(JSON.stringify({probes:probes.length,protected_files:protectedFiles.length}));
}
