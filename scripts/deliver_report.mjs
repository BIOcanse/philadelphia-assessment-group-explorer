// Use the packaged report pipeline; fix its proven Windows scrollbar overflow locally.
import { pathToFileURL } from 'node:url';
import { writeFileSync } from 'node:fs';
import path from 'node:path';
const [inputPath='outputs/report/artifact.json',outputPath='outputs/report/初版报告_Draft_Report.html',readyTimeout='20000']=process.argv.slice(2);
const outputDir=path.dirname(outputPath);
const readyTimeoutMs=Number(readyTimeout);
if(!Number.isSafeInteger(readyTimeoutMs)||readyTimeoutMs<=0||readyTimeoutMs>60000)throw new Error('Reader timeout must be between 1 and 60000 ms.');
const plugin='C:/Users/kings/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.10-13ceeea1f599/skills/build-report/scripts/';
const {buildPortableArtifact,readPackagedReaderRuntime}=await import(pathToFileURL(plugin+'build_portable_artifact.mjs'));
const {deliverPortableArtifact}=await import(pathToFileURL(plugin+'deliver_portable_artifact.mjs'));
const packaged=readPackagedReaderRuntime().html;
if (!packaged.includes('.analytics-top-bar')) throw new Error('Expected reader top-bar class is absent.');
// Compiled JavaScript contains its own HTML strings; use the actual final head tag.
const headEnd=packaged.lastIndexOf('</head>');
if (headEnd<0 || !/^<\/head>\s*<body>/.test(packaged.slice(headEnd))) throw new Error('Reader head was not found.');
const fix='<style>#data-analytics-portable-reader .analytics-top-bar{width:calc(100% + 2 * var(--ds-gutter));margin-left:calc(-1 * var(--ds-gutter));margin-right:calc(-1 * var(--ds-gutter));}</style>';
const runtimeHtml=packaged.slice(0,headEnd)+fix+packaged.slice(headEnd);
const result=await deliverPortableArtifact({
 inputPath,outputPath,
 readyTimeoutMs,timeoutMs:Math.max(40000,readyTimeoutMs),screenshotPath:path.join(outputDir,'render_failure.png')
},{build:(input,options={})=>buildPortableArtifact(input,{...options,runtimeHtml})});
writeFileSync(path.join(outputDir,'report_delivery_validation.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result));
if (!result.ok) process.exitCode=1;
