"use strict";
const { chromium } = require("playwright");

async function main() {
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
      const indexUrl = new URL("generated/reader-index.json", document.baseURI);
      const indexResponse = await fetch(indexUrl);
      if (!indexResponse.ok) throw new Error("Public reader index did not resolve: " + indexResponse.status);
      const reader = await indexResponse.json();
      const sha256 = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)))
        .map(value => value.toString(16).padStart(2, "0")).join("");
      const loadGroup = async (name, refs) => {
        const entries = Object.entries(refs || {});
        const payloads = await Promise.all(entries.map(async ([id, ref]) => {
          if (!ref || typeof ref.path !== "string" || !/^[a-f0-9]{64}$/.test(ref.sha256 || ""))
            throw new Error("Invalid public " + name + " reference: " + id);
          const response = await fetch(new URL(ref.path, indexUrl));
          if (!response.ok) throw new Error("Public " + name + " chunk did not resolve: " + id);
          const bytes = await response.arrayBuffer();
          if (await sha256(bytes) !== ref.sha256) throw new Error("Public " + name + " chunk hash mismatch: " + id);
          const payload = JSON.parse(new TextDecoder().decode(bytes));
          if (payload.id !== id) throw new Error("Public " + name + " chunk identity mismatch: " + id);
          return payload;
        }));
        return payloads;
      };
      const [scenes, audioChunks, preludeReceipts] = await Promise.all([
        loadGroup("scene", reader.scene_chunks),
        loadGroup("audio", reader.audio_chunks),
        loadGroup("prelude", reader.prelude_receipts),
      ]);
      const audioFiles = audioChunks.flatMap(chunk => Array.isArray(chunk.files) ? chunk.files : Object.values(chunk.files || {}));
      const firstAudio = audioFiles.find(path => typeof path === "string");
      const audioPath = firstAudio ? (firstAudio.startsWith("manual/") ? firstAudio.slice(7) : firstAudio).replace(/^\/+/, "") : null;
      const audioStatus = audioPath ? (await fetch(new URL("../" + audioPath, indexUrl), { method: "HEAD" })).status : null;
      const title = document.querySelector("#feature-title")?.textContent?.trim() || "";
      return {
        featureCount: Array.isArray(reader.features) ? reader.features.length : 0,
        sceneCount: scenes.length,
        audioCount: Array.isArray(reader.audio_examples) ? reader.audio_examples.length : audioChunks.length,
        audioStatus,
        preludeCount: preludeReceipts.length,
        navCount: document.querySelectorAll(".sidebar nav a").length,
        title,
      };
    });
    if (!report.featureCount || !report.sceneCount || !report.navCount || !report.title)
      throw new Error("Packaged manual did not render: " + JSON.stringify(report));
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
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
