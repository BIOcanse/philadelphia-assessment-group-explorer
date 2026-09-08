async (page) => {
  const base = await page.evaluate(() => new URL('.', location.href).href);
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(base);
  const entry=page.locator('header a[href="research-story.html"]');
  await entry.waitFor({state:'visible'});
  if (!(await page.evaluate(() => document.documentElement.scrollWidth<=innerWidth))) throw new Error('Workbench header overflows desktop');
  await entry.click();
  await page.waitForURL('**/research-story.html');
  const link=page.locator('a[href="./index.html#view=overview"]').first();
  await link.waitFor({state:'visible'});
  const href=await link.evaluate(a=>a.href);
  if(href!==base+'index.html#view=overview') throw new Error('Report backlink escapes edition: '+href);
  const zip=await page.request.get(base+'research-story-sources.zip');
  if(zip.status()!==200 || (await zip.body()).length<10000) throw new Error('Evidence ZIP unavailable');
  await page.goto(href);
  await page.locator('#researchNav').getByRole('button').first().waitFor({state:'visible'});
  return {status:'passed',base,checks:['desktop entry','report navigation','edition-relative backlink','evidence download','original workbench return']};
}
