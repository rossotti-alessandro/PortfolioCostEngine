// Renders each Jev candidate's OCR text the way the vendor renderer lays it out (SC-5.13):
// the vendor's page CSS, 18 px text, DPR 1, white border trimmed. Reads var/ocrbench/jev/samples.json,
// writes var/ocrbench/jev/renders/<id>.png. Plain text only: our OCR lines carry no tables or formulas.
// Usage: node data/specimens/ocrbench/jev_render.mjs
import { readFileSync, mkdirSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const J = join(dirname(fileURLToPath(import.meta.url)), "../../../var/ocrbench/jev");
const samples = JSON.parse(readFileSync(join(J, "samples.json"), "utf8"));
mkdirSync(join(J, "renders"), { recursive: true });

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const page = await (await chromium.launch()).newPage({ deviceScaleFactor: 1 });
await page.setViewportSize({ width: 1200, height: 400 });
let n = 0;
for (const s of samples) {
  const out = join(J, "renders", `${s.id}.png`);
  if (existsSync(out)) continue;
  await page.setContent(`<!doctype html><meta charset="utf-8"><style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC", sans-serif;
      padding: 0; margin: 0; background: #fff; font-size: 18px; line-height: 2.0; }
    p { margin: 0.2em 0; } #c { display: inline-block; padding: 16px; max-width: 1168px; }
  </style><div id="c"><p>${esc(s.text)}</p></div>`);
  await page.locator("#c").screenshot({ path: out });
  n++;
}
console.log("rendered", n);
process.exit(0);
