// Optional presentation QA: npm install playwright, then supply a local report.
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {createHash} = require('node:crypto');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const source = path.resolve(process.argv[2]);
  const output = path.resolve(process.argv[3]);
  await fs.mkdir(output); // New output only.
  const errors = [];
  const browser = await chromium.launch({headless:true,
    ...(process.env.Q9_BROWSER_EXECUTABLE ? {executablePath:process.env.Q9_BROWSER_EXECUTABLE} : {})});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1100}});
    page.on('pageerror', error => errors.push(String(error)));
    await page.goto(pathToFileURL(path.join(source,'Informe.html')).href);
    await page.locator('svg').first().waitFor();
    const desktopOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    await page.locator('article').first().screenshot({path:path.join(output,'desktop.png')});
    const chartCount = await page.locator('svg').count();
    await page.setViewportSize({width:430,height:1000});
    await page.locator('figure').first().scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'mobile.png')});
    const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    const plotScroll = await page.locator('.plot').first().evaluate(el => el.scrollWidth > el.clientWidth);
    await page.setViewportSize({width:1440,height:1100});
    await page.pdf({path:path.join(output,'Print.pdf'),preferCSSPageSize:true,printBackground:true,tagged:true});
    if (desktopOverflow || mobileOverflow || errors.length || !plotScroll) {
      throw new Error(JSON.stringify({desktopOverflow,mobileOverflow,errors,plotScroll}));
    }
    const files = {};
    for (const name of ['desktop.png','mobile.png','Print.pdf']) {
      files[name] = createHash('sha256').update(await fs.readFile(path.join(output,name))).digest('hex');
    }
    const evidence = {ok:true,desktop_width:1440,mobile_width:430,chart_count:chartCount,
      desktop_page_overflow:desktopOverflow,mobile_page_overflow:mobileOverflow,
      mobile_plot_scroll:plotScroll,javascript_errors:errors,files_sha256:files,
      report_html_sha256:createHash('sha256').update(await fs.readFile(path.join(source,'Informe.html'))).digest('hex'),
      checked_at_utc:new Date().toISOString()};
    await fs.writeFile(path.join(output,'Evidence.json'),JSON.stringify(evidence,null,2)+'\n');
    console.log(JSON.stringify(evidence));
  } finally {
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
