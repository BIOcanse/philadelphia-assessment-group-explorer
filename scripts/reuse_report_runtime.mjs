// Reuse the verified compiled reader when its original plugin build files are gone.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
import {groupLinkHints} from './report_group_links.mjs';

const [input,output,base='outputs/formula_validation_report/research-story.html']=process.argv.slice(2);
if(!input||!output)throw new Error('artifact input and HTML output required');
const artifact=JSON.parse(readFileSync(input,'utf8'));
const old=readFileSync(base,'utf8');
const hash=value=>createHash('sha256').update(value).digest('hex');
const pattern=kind=>new RegExp('(<template[^>]*'+kind+'-source[^>]*>)([\\s\\S]*?)(</template>)');
const decoded=kind=>gunzipSync(Buffer.from(old.match(pattern(kind))[2].replace(/\s/g,''),'base64')).toString('utf8');
const oldPayload=JSON.parse(decoded('payload'));
const payload={...oldPayload,...artifact};
const oldRuntime=decoded('runtime');
const hintsPattern=/<script>\(\(\)=>\{\s*const conditions=[\s\S]*?<\/script>/g;
assert.equal([...oldRuntime.matchAll(hintsPattern)].length,1,'Prior hint adapter must be uniquely identifiable');
const core=oldRuntime.replace(hintsPattern,'');
const runtime=oldRuntime.replace(hintsPattern,()=>groupLinkHints(artifact));
assert.equal(runtime.replace(hintsPattern,''),core,'Compiled canonical reader changed');
const encoded=value=>gzipSync(Buffer.from(value),{level:9}).toString('base64');
let html=old.replace(pattern('payload'),(_,a,b,c)=>a+encoded(JSON.stringify(payload))+c)
  .replace(pattern('runtime'),(_,a,b,c)=>a+encoded(runtime)+c);
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
html=html.replace(/<title>[\s\S]*?<\/title>/,()=>'<title>'+esc(artifact.manifest.title)+'</title>');
const fallbackPattern=/<main id="data-analytics-portable-fallback"[\s\S]*?<\/main>/;
assert.equal([...html.matchAll(new RegExp(fallbackPattern.source,'g'))].length,1);
html=html.replace(fallbackPattern,'<main id="data-analytics-portable-fallback" class="portable-fallback"><p>正在载入报告 / Loading report…</p></main>');
// The original fallback-only tooltip script targets the old source rows.
html=html.replace(/<script data-data-analytics-portable-source-tooltips="true">[\s\S]*?<\/script>/,'');
writeFileSync(output,html);

const require=createRequire('D:/Code/CommonAssets/Tools/PlaywrightCLI/package.json');
const {chromium}=require('playwright');
const executable=['C:/Program Files/Google/Chrome/Application/chrome.exe',
 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',chromium.executablePath()].find(existsSync);
assert.ok(executable,'No existing Chromium browser');
const browser=await chromium.launch({executablePath:executable,headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
const folder=path.dirname(output);const evidence=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const open=async()=>{
   await page.goto(pathToFileURL(path.resolve(output)).href);
   await page.waitForFunction(()=>document.documentElement.dataset.dataAnalyticsPortableReader==='ready');
 };
 await open();
 // Capture the canonical renderer itself, rather than implement a second chart renderer.
 const snapshot=await page.evaluate(()=>{
   const clone=document.querySelector('#data-analytics-portable-reader').cloneNode(true);
   clone.id='fallback-canonical-render';clone.removeAttribute('inert');clone.removeAttribute('aria-hidden');
   const ids=new Map();
   for(const e of clone.querySelectorAll('[id]')){ids.set(e.id,'fallback-'+e.id);e.id='fallback-'+e.id;}
   for(const e of clone.querySelectorAll('*')){
     for(const attr of ['aria-labelledby','aria-describedby','for']){
       if(e.hasAttribute(attr))e.setAttribute(attr,e.getAttribute(attr).split(' ').map(x=>ids.get(x)||x).join(' '));
     }
     for(const attr of ['fill','clip-path','mask']){
       const value=e.getAttribute(attr);if(value?.startsWith('url(#'))e.setAttribute(attr,value.replace('url(#','url(#fallback-'));
     }
   }
   for(const e of clone.querySelectorAll('button,input,select,textarea'))e.setAttribute('disabled','');
   return {body:clone.outerHTML,styles:[...document.querySelectorAll('style[data-data-analytics-portable-runtime-style]')].map(s=>s.textContent).join('\n')};
 });
 const fallback='<main id="data-analytics-portable-fallback" class="portable-fallback" data-portable-fallback="true" data-portable-surface="report">'+snapshot.body+'</main>';
 html=html.replace(fallbackPattern,()=>fallback).replace('</head>',()=>'<style data-preserved-canonical-fallback="true">'+snapshot.styles+
   '\n#data-analytics-portable-fallback.portable-enhanced-hidden{display:none!important}</style></head>');
 writeFileSync(output,html);
 await open();
 for(const width of [1440,1200]){
   await page.setViewportSize({width,height:1000});
   const visible=page.locator('#data-analytics-portable-reader');
   const expected=artifact.manifest.blocks.map(b=>b.id);
   const actual=await visible.locator('[data-artifact-block-id]').evaluateAll(es=>es.map(e=>e.dataset.artifactBlockId));
   assert.deepEqual(actual,expected);
   for(const b of artifact.manifest.blocks){
     const node=visible.locator('[data-artifact-block-id="'+b.id+'"]');
     assert.ok(await node.isVisible(),b.id);
     if(b.type==='chart')assert.ok(await node.locator('svg').count()>0,b.id+' chart missing');
     if(b.type==='table')assert.ok(await node.locator('table').count()>0,b.id+' table missing');
   }
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'page overflows');
   await page.screenshot({path:path.join(folder,'desktop-'+width+'.png')});
   evidence.push({width,blocks:actual.length,charts:artifact.manifest.charts.length,tables:artifact.manifest.tables.length,status:'passed'});
 }
 await page.setViewportSize({width:1440,height:1000});
 await page.locator('#data-analytics-portable-reader [data-artifact-block-id="raw-comparison-table-block"]').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(folder,'comparison.png')});
 const options=page.locator('#data-analytics-portable-reader [data-artifact-block-id="raw-family-chart-block"] button[aria-label^="Open options"]');
 await options.evaluate(e=>e.scrollIntoView({block:'center'}));
 await options.focus();
 try{await options.click({timeout:5000});}catch(error){
   console.log(JSON.stringify(await options.evaluate(e=>{const r=e.getBoundingClientRect();return {
     pointer:getComputedStyle(e).pointerEvents,opacity:getComputedStyle(e).opacity,
     hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,600),
     ancestors:[e,e.parentElement,e.parentElement.parentElement].map(x=>({tag:x.tagName,cls:x.className,style:x.getAttribute('style'),pointer:getComputedStyle(x).pointerEvents})),
     fallbackDisplay:getComputedStyle(document.getElementById('data-analytics-portable-fallback')).display};})));
   throw error;
 }
 const sourceAction=page.getByRole('menuitem').filter({hasText:/source/i});
 await sourceAction.first().click();
 await page.getByRole('dialog').waitFor({state:'visible'});
 const sourceText=await page.getByRole('dialog').innerText();
 assert.ok(sourceText.includes('raw_family_scores')||sourceText.includes('Main cohort, same test transactions'),
   'new source missing: '+sourceText.slice(0,2000));
 await page.screenshot({path:path.join(folder,'source-dialog.png'),animations:'disabled'});
 const fallbackPage=await browser.newPage({javaScriptEnabled:false,viewport:{width:1440,height:1000}});
 await fallbackPage.goto(pathToFileURL(path.resolve(output)).href);
 assert.ok((await fallbackPage.locator('#data-analytics-portable-fallback').innerText()).includes('14套误差更低'));
 assert.equal(await fallbackPage.locator('#data-analytics-portable-fallback [data-artifact-block-id]').count(),artifact.manifest.blocks.length);
 assert.ok(await fallbackPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'fallback overflows');
 await fallbackPage.screenshot({path:path.join(folder,'no-javascript.png')});
 assert.deepEqual(errors,[]);
 const embedded=JSON.parse(gunzipSync(Buffer.from(html.match(pattern('payload'))[2],'base64')).toString());
 assert.equal(hash(JSON.stringify(embedded)),hash(JSON.stringify(payload)),'Embedded JSON differs');
 const receipt={ok:true,stages:{build:'passed',verification:'passed'},verifier:'project retained-runtime renderer and Playwright checks',
   removed_plugin_verifier_used:false,sourceDialog:'passed',fallback:'canonical DOM capture; no-JavaScript checked',viewports:evidence,
   artifact_sha256:hash(readFileSync(input)),base_html_sha256:hash(old),core_runtime_sha256:hash(core),
   loader_sha256:hash(old.match(/<script data-data-analytics-portable-loader="true">[\s\S]*?<\/script>/)[0]),
   html_sha256:hash(html),runtime_core_unchanged:true};
 writeFileSync(path.join(folder,'report_delivery_validation.json'),JSON.stringify(receipt,null,2));
 console.log(JSON.stringify(receipt));
}finally{await browser.close();}
