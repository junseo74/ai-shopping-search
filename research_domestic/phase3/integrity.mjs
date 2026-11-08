import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
const here = path.join(root, 'research_domestic', 'phase3');
async function inventory(dir) {
  const entries = await fs.readdir(dir, { withFileTypes:true }); const out = {};
  for (const e of entries) {
    const p = path.join(dir,e.name);
    if (p === here || e.isSymbolicLink() || e.name === '.env' || e.name.startsWith('.env.')) continue;
    if (e.isDirectory()) Object.assign(out, await inventory(p));
    else if(e.isFile()) out[path.relative(root,p).replaceAll('\\','/')] = crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
  }
  return out;
}
async function protectedFiles() {
  const out = {};
  for (const name of ['backend','crawler_engine','collection_engine','docs','samples','research_domestic']) {
    try { Object.assign(out, await inventory(path.join(root,name))); } catch(e) { if(e.code!=='ENOENT') throw e; }
  }
  for (const e of await fs.readdir(root,{withFileTypes:true})) {
    if (e.isFile() && e.name.endsWith('_probe.py')) out[e.name]=crypto.createHash('sha256').update(await fs.readFile(path.join(root,e.name))).digest('hex');
    if (e.isDirectory() && e.name.startsWith('.tmp_')) Object.assign(out,await inventory(path.join(root,e.name)));
  }
  return out;
}
const target = path.join(here,'protected_baseline.json');
if (process.argv.includes('--baseline')) {
  await fs.writeFile(target,JSON.stringify(await protectedFiles(),null,2)+'\n',{flag:'wx'});
  console.log('Protected baseline recorded');
} else {
  const before=JSON.parse(await fs.readFile(target,'utf8')), after=await protectedFiles();
  const changed=[...new Set([...Object.keys(before),...Object.keys(after)])].filter(k=>before[k]!==after[k]);
  const report={observed_at:new Date().toISOString(),protected_files:Object.keys(before).length,changed};
  await fs.writeFile(path.join(here,'integrity.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report)); if(changed.length) process.exitCode=1;
}
