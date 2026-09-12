async (page) => {
  const base=await page.evaluate(()=>new URL('.',location.href).href);
  await page.goto(base+'research-story.html');
  await page.waitForFunction(()=>document.documentElement.dataset.dataAnalyticsPortableReader==='ready');
  await page.setViewportSize({width:1440,height:1000});
  const checks=[];
  for(const id of ['raw-family-chart','raw-learning-chart','raw-transfer-chart','raw-residual-chart']){
    const block=page.locator('#data-analytics-portable-reader [data-artifact-block-id="'+id+'-block"]');
    const svg=block.locator('.chart-frame svg');
    if(await svg.count()<1)throw new Error('Missing chart-frame SVG: '+id);
    if((await svg.first().textContent()).length<20)throw new Error('Missing chart labels: '+id);
    await block.scrollIntoViewIfNeeded();
    await block.screenshot({path:'outputs/raw_feature_formula_report/'+id+'.png',animations:'disabled'});
    checks.push({id,chartSvg:await svg.count(),labels:'passed'});
  }
  const params=page.locator('#data-analytics-portable-reader [data-artifact-block-id="raw-equations-table-block"]');
  if(!(await params.innerText()).includes('λ = 1e-'))throw new Error('Regularization precision lost');
  await params.screenshot({path:'outputs/raw_feature_formula_report/equation-parameters.png',animations:'disabled'});
  return {status:'passed',checks,parameterPrecision:'passed'};
}
