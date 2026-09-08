// The user requests PC-only reports. Reuse the official probes at two PC widths.
import { randomUUID } from 'node:crypto';
import { mkdtempSync,readFileSync,writeFileSync } from 'node:fs';
import { dirname,join } from 'node:path';
import { pathToFileURL } from 'node:url';

export async function verifyDesktopReport(options,plugin) {
  const { verifyPortableArtifactStructure }=await import(pathToFileURL(plugin+'verify_portable_artifact.mjs'));
  const { resolveChromiumExecutable }=await import(pathToFileURL(plugin+'portable_browser_helpers.mjs'));
  const { buildPortableVerifierHarness,chromiumDumpArguments,injectPortableVerifierProbe,
    parsePortableVerifierDump,spawnChromiumDump }=await import(pathToFileURL(plugin+'portable_browser_cli.mjs'));
  const structure=verifyPortableArtifactStructure(options);
  const html=readFileSync(options.htmlPath,'utf8');
  const folder=mkdtempSync(join(dirname(options.htmlPath),'desktop-check-'));
  const channel=randomUUID();const readyTimeoutMs=options.readyTimeoutMs??20000;
  const viewports=[{name:'desktop',width:1440,height:1000},{name:'desktop-1200',width:1200,height:1000}];
  const frames=viewports.map(viewport=>({viewport,html:injectPortableVerifierProbe(html,{
    actionTimeoutMs:5000,channel,checkSource:viewport.name==='desktop',expectedCounts:structure.counts,
    readerRoot:'#data-analytics-portable-reader-root',readyTimeoutMs,title:structure.title,viewport})}));
  const harness=join(folder,'harness.html');
  writeFileSync(harness,buildPortableVerifierHarness({channel,frames,timeoutMs:readyTimeoutMs+6000}));
  const result=await spawnChromiumDump({executablePath:resolveChromiumExecutable(),timeoutMs:options.timeoutMs??60000,
    arguments:chromiumDumpArguments({width:2656,height:1000,profilePath:join(folder,'profile'),
      url:pathToFileURL(harness).href,virtualTimeBudgetMs:readyTimeoutMs+6500})});
  const aggregate=parsePortableVerifierDump(result.stdout);
  writeFileSync(join(folder,'probe-result.json'),JSON.stringify(aggregate,null,2));
  if(!aggregate.ok||aggregate.results?.length!==2||aggregate.results.some(r=>!r.ok))
    throw new Error('Desktop report verification failed: '+JSON.stringify(aggregate));
  const desktop=aggregate.results.find(r=>r.viewport.name==='desktop');
  return {ok:true,counts:desktop.counts,html:options.htmlPath,sourceDialog:'passed',
    sourceInteraction:desktop.sourceInteraction,viewports:[1440,1200],scope:'PC only, as explicitly requested by the user',
    timings:{browserRunMs:desktop.timings?.readerReadyMs}};
}
