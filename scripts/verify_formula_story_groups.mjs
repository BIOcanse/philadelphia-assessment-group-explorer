async (page) => {
  const base = await page.evaluate(() => new URL('.', location.href).href);
  const checks = [];
  for (const id of ['main-02124043', 'main-04783053']) {
    await page.goto(base + 'research-story.html');
    const link = page.locator('#data-analytics-portable-reader a[href="./index.html#group=' + id + '"]');
    await link.waitFor({state: 'visible'});
    const title = await link.getAttribute('title');
    if (!title || !title.includes('Bedrooms') || !title.includes('Manufacturing share'))
      throw new Error('Missing condition tooltip for ' + id);
    if (await link.evaluate(a => a.href) !== base + 'index.html#group=' + id)
      throw new Error('Wrong group destination');
    await link.click();
    await page.locator('#groupDialog[open] #detail .identifier').filter({hasText: id}).waitFor({state: 'visible'});
    checks.push({id, conditions: title, detail: 'passed'});
  }
  return {status: 'passed', checks};
}
