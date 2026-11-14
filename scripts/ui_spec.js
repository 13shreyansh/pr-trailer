// UI acceptance tests (owned by the product team) + evidence recording.
// usage: node ui_spec.js <baseUrl> <outDir> [captionsJson]
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const [baseUrl, outDir, captionsArg] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });

const tests = {
  "REQ_UI_601.test_ac1_fee_updates": async (page) => {
    await page.fill("#amount", "100.00");
    await expectText(page, "#fee", "€0.00");
    await page.selectOption("#kind", "instant");
    await expectText(page, "#fee", "€0.50");
    await page.fill("#amount", "1000.00");
    await expectText(page, "#fee", "€2.00");
  },
  "REQ_UI_601.test_ac2_total_shown": async (page) => {
    await page.fill("#amount", "100.00");
    await page.selectOption("#kind", "instant");
    await expectText(page, "#total", "€100.50");
  },
  "REQ_UI_602.test_ac1_remembers_type": async (page) => {
    await page.selectOption("#kind", "instant");
    await page.reload();
    const v = await page.$eval("#kind", (el) => el.value);
    if (v !== "instant") throw new Error(`after reload transfer type is "${v}", expected "instant"`);
  },
};

async function expectText(page, sel, want, ms = 1500) {
  const t0 = Date.now();
  let got = null;
  while (Date.now() - t0 < ms) {
    got = await page.$eval(sel, (el) => el.textContent.trim()).catch(() => null);
    if (got === want) return;
    await page.waitForTimeout(50);
  }
  throw new Error(`${sel} shows ${JSON.stringify(got)}, expected ${JSON.stringify(want)}`);
}

async function caption(page, text) {
  await page.evaluate((t) => {
    let el = document.getElementById("__trailer_caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "__trailer_caption";
      el.style.cssText = "position:fixed;left:0;right:0;bottom:0;padding:14px 18px;background:#111c;color:#fff;" +
        "font:600 15px/1.4 system-ui;z-index:99999";
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, text);
}

(async () => {
  const browser = await chromium.launch();
  const results = [];
  for (const [id, fn] of Object.entries(tests)) {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    try {
      await page.goto(baseUrl);
      await page.waitForLoadState("networkidle");
      await fn(page);
      results.push({ id, status: "pass", detail: "" });
    } catch (e) {
      results.push({ id, status: "fail", detail: String(e.message || e).slice(0, 400) });
    }
    await ctx.close();
  }

  // Evidence: a captioned walkthrough video plus a still of the final state.
  const captions = captionsArg ? JSON.parse(captionsArg) : {};
  const ctx = await browser.newContext({ viewport: { width: 640, height: 640 }, recordVideo: { dir: outDir, size: { width: 640, height: 640 } } });
  const page = await ctx.newPage();
  await page.goto(baseUrl);
  await page.waitForLoadState("networkidle");
  await caption(page, captions.intro || "Transfer form, as built by this PR");
  await page.waitForTimeout(1200);
  await page.fill("#amount", "250.00");
  await caption(page, captions.amount || "Customer enters EUR 250.00");
  await page.waitForTimeout(1200);
  await page.selectOption("#kind", "instant");
  await caption(page, captions.kind || "Switches to Instant: fee should become €0.50");
  await page.waitForTimeout(1600);
  await page.screenshot({ path: path.join(outDir, "final.png") });
  await page.click("#send");
  await page.waitForTimeout(800);
  await caption(page, captions.sent || "Sends the transfer");
  await page.waitForTimeout(1200);
  const video = page.video();
  await ctx.close();
  const vpath = await video.path();
  fs.renameSync(vpath, path.join(outDir, "walkthrough.webm"));
  await browser.close();
  console.log(JSON.stringify(results));
})();
