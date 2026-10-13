"use strict";
const { chromium } = require("playwright");
(async () => {
  const base = process.argv[2];
  if (!base) throw new Error("Pass the local static-site URL");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  try {
    const home = await page.goto(base, { waitUntil: "domcontentloaded" });
    if (!home || home.status() !== 200) throw new Error("Static site root did not return 200");
    await page.waitForFunction(() => location.pathname.endsWith("/manual/") || location.pathname.endsWith("/manual/index.html"));
    await page.waitForFunction(() => window.MosaicPlayer && !document.body.classList.contains("book-loading"), null, { timeout: 30000 });
    const report = await page.evaluate(async () => {
      const book = await (await fetch("/manual/generated/book.json")).json();
      const audio = await (await fetch("/manual/generated/audio-scenes.json")).json();
      const inventory = await (await fetch("/manual/inventory.json")).json();
      const examples = audio.examples || [];
      const files = examples.flatMap(example => Array.isArray(example.files) ? example.files : Object.values(example.files || {}));
      const path = files.length ? files[0].replace(/^manual\//, "") : null;
      const audioStatus = path ? (await fetch("/manual/" + path, { method: "HEAD" })).status : null;
      return { featureCount: book.features.length, sceneCount: Object.keys(book.scenes).length,
        inventoryCount: inventory.features.length, audioCount: examples.length, audioStatus,
        navCount: document.querySelectorAll(".sidebar nav a").length, title: document.title };
    });
    if (!report.featureCount || !report.sceneCount || !report.inventoryCount || !report.navCount)
      throw new Error("Packaged manual data did not render: " + JSON.stringify(report));
    if (report.audioCount && report.audioStatus !== 200)
      throw new Error("Packaged audio did not resolve: " + JSON.stringify(report));
    for (const route of ["/cheat_sheet.html", "/config_creator.html", "/README.md"]) {
      const response = await page.request.get(new URL(route, base).toString());
      if (response.status() !== 200) throw new Error("Required manual asset returned " + response.status() + ": " + route);
    }
    const quickReference = await page.request.get(new URL("/cheat_sheet.html", base).toString());
    if (!(await quickReference.text()).toLowerCase().includes("mosaic")) throw new Error("Generated quick reference is empty");
    if (pageErrors.length) throw new Error("Packaged browser error: " + pageErrors.join(" | "));
    console.log(JSON.stringify({ passed: true, ...report }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack || error.message || String(error)); process.exitCode = 1; });