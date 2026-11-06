// Builds slides/<NAME>_Executive_Deck.pptx  (v2)
// All figures are SYNTHETIC. Numbers come from the app's demo prospect P-1042,
// produced by the engine on branch claude/project-thread-steqtm (see slides/README.md).
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const NAME = process.env.PRODUCT_NAME || "FeeLens";
const OUT = path.resolve(__dirname, "..", `${NAME.replace(/\s+/g, "")}_Executive_Deck.pptx`);
const IMG = (n) => path.join(__dirname, "img", n);

// Shared design tokens (docs/design/DESIGN_SYSTEM.md)
const THEME = {
  name: NAME,
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "14202E", lt1: "FFFFFF", dk2: "0F2A4A", lt2: "F7F6F2",
    accent1: "0F766E", accent2: "B45309", accent3: "B42318", accent4: "1E7A46",
    accent5: "2F5D8A", accent6: "5B6676", hlink: "0F766E", folHlink: "2F5D8A",
  },
};
const X = {
  text: "14202E", navy: "0F2A4A", teal: "0F766E", tealSoft: "E3F2F0", amber: "B45309", amberSoft: "FDF3E2",
  red: "B42318", redSoft: "FDECEA", green: "1E7A46", greenSoft: "E7F4EC", muted: "5B6676", bg: "F7F6F2",
  mutedSurface: "EFEDE7", border: "DEDAD1", l2: "2F5D8A", l3: "6B8FB3", l9: "A3A3A3", white: "FFFFFF",
};

async function icon(name, color, size = 256) {
  const C = lu[name] || lu.LuCircle;
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(C, { color: "#" + color, size: String(size), strokeWidth: 1.75 }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
function imgSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.title = `${NAME} · briefing for Safe Capital`;
  pres.author = `${NAME} project`;
  pres.company = NAME;
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // ---------- layouts ----------
  pres.defineSlideMaster({
    title: "Dark",
    background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.0, w: 11.5, h: 1.6, fontFace: THEME.headFontFace, fontSize: 60, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.8, w: 11.5, h: 1.4, fontSize: 24, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Content",
    background: { color: C.background1 },
    margin: [0.5, 0.6, 0.6, 0.6],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.62, w: 12.1, h: 0.75, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.text2, valign: "top", align: "left", margin: 0 }, text: "" } },
      { text: { text: `${NAME} · concept for Safe Capital · client figures synthetic, public sources cited`, options: { x: 0.6, y: 7.02, w: 9, h: 0.28, fontSize: 10, color: C.accent6, margin: 0 } } },
    ],
    slideNumber: { x: 12.2, y: 7.02, w: 0.5, h: 0.28, fontSize: 10, color: C.accent6, align: "right" },
  });

  const tb = (o) => Object.assign({ isTextBox: true, margin: 0, fontSize: 16, color: C.text1, valign: "top" }, o);
  const content = (kicker, title, section) => {
    const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
    s.addText(kicker.toUpperCase(), tb({ x: 0.6, y: 0.35, w: 9, h: 0.25, fontSize: 11, bold: true, color: C.accent1, charSpacing: 2 }));
    s.addText(title, { placeholder: "title" });
    return s;
  };
  const card = (s, x, y, w, h, fill, name) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: fill || X.bg }, line: { color: fill || X.bg }, objectName: name });
  const iconIn = async (s, x, y, d, name, bg, fg, objName) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: d, h: d, rectRadius: 0.08, fill: { color: bg }, line: { color: bg }, objectName: objName + " tile" });
    const p = d * 0.22;
    s.addImage({ data: await icon(name, fg), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, objectName: objName + " icon" });
  };
  const KIND = {
    obs: [X.greenSoft, X.green], con: ["E6ECF4", X.navy], est: [X.amberSoft, X.amber], unk: [X.redSoft, X.red],
    na: [X.mutedSurface, X.muted], pass: [X.greenSoft, X.green], fail: [X.redSoft, X.red], info: ["E6ECF4", X.navy],
  };
  const chip = (s, x, y, text, kind, w) => {
    const [bg, fg] = KIND[kind];
    const ww = w || Math.max(0.9, 0.09 * text.length + 0.35);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: ww, h: 0.3, rectRadius: 0.15, fill: { color: bg }, line: { color: bg }, objectName: "chip " + text });
    s.addText(text, tb({ x, y, w: ww, h: 0.3, fontSize: 11, bold: true, color: fg, align: "center", valign: "middle" }));
    return ww;
  };
  const fitImage = (s, file, box, name) => {
    const { w, h } = imgSize(file);
    const r = Math.min(box.w / w, box.h / h);
    const iw = w * r, ih = h * r;
    const rr = { x: box.x + (box.w - iw) / 2, y: box.y + (box.h - ih) / 2, w: iw, h: ih };
    s.addImage({ path: file, ...rr, objectName: name, altText: name });
    s.addShape(pres.shapes.RECTANGLE, { ...rr, fill: { type: "none" }, line: { color: X.border, width: 0.75 }, objectName: name + " frame" });
    return rr;
  };
  const arrow = (s, x, y, w, h, name) =>
    s.addShape(pres.shapes.LINE, { x, y, w, h, line: { color: X.muted, width: 1.5, endArrowType: "triangle" }, objectName: name });
  const arrowUp = (s, x, y, h, name) =>
    s.addShape(pres.shapes.LINE, { x, y, w: 0, h, flipV: true, line: { color: X.muted, width: 1.5, endArrowType: "triangle" }, objectName: name });

  // =====================================================================
  // WHY
  pres.addSection({ title: "Why" });
  {
    const s = pres.addSlide({ masterName: "Dark", sectionTitle: "Why" });
    s.addText(NAME, { placeholder: "title" });
    s.addText("See what a portfolio really costs. In minutes, with proof.", { placeholder: "body" });
    s.addText("Briefing for Massimo · Safe Capital, Lugano · November 2026", tb({ x: 0.8, y: 4.65, w: 11, h: 0.4, fontSize: 16, color: "9FB3C8" }));
    s.addText("Concept and working demo · every figure in this deck is synthetic", tb({ x: 0.8, y: 6.55, w: 11, h: 0.35, fontSize: 12, color: "9FB3C8" }));
    s.addNotes(`${NAME} (working name) reads a prospect's bank and product documents, finds every cost with its source, and compares it fairly with Safe Capital's offer. Everything shown uses the synthetic demo prospect P-1042; no real client, bank or saving is represented.`);
  }
  {
    const s = content("The problem", "Bank statements show only part of the cost", "Why");
    s.addText([
      { text: "CHF 40'160", options: { fontSize: 54, bold: true, color: C.text2, breakLine: true } },
      { text: "what the bank's cost report lists as charged", options: { fontSize: 16, color: C.accent6 } },
    ], tb({ x: 0.6, y: 1.8, w: 5.6, h: 1.4 }));
    s.addText([
      { text: "CHF 61'450", options: { fontSize: 54, bold: true, color: C.accent1, breakLine: true } },
      { text: "what the portfolio actually costs per year, at least", options: { fontSize: 16, color: C.accent6 } },
    ], tb({ x: 0.6, y: 3.45, w: 5.6, h: 1.4 }));
    s.addText("Synthetic prospect P-1042, CHF 4.3m at two banks. The CHF 21'290 gap is fund costs taken inside product prices, and Bank Beta's fees are still unknown.", tb({ x: 0.6, y: 5.15, w: 5.4, h: 1.2, fontSize: 14, color: C.accent6 }));
    const items = [
      ["LuLandmark", "Fee statements", "management, custody"],
      ["LuFileSignature", "Contracts & tariffs", "rates, tiers, minimums"],
      ["LuArrowLeftRight", "Trades & FX", "commissions, FX margins"],
      ["LuPieChart", "Fund prices", "ongoing charges inside NAV"],
      ["LuBoxes", "Structured notes", "issuer margin in the price"],
      ["LuUmbrella", "Insurance wrappers", "policy fees on top"],
    ];
    s.addText("Costs are spread over six kinds of document", tb({ x: 6.9, y: 1.8, w: 5.8, h: 0.4, fontSize: 16, bold: true }));
    for (let i = 0; i < 6; i++) {
      const y = 2.35 + i * 0.68;
      await iconIn(s, 6.9, y, 0.5, items[i][0], i >= 3 ? X.tealSoft : X.bg, i >= 3 ? X.teal : X.navy, items[i][1]);
      s.addText(items[i][1], tb({ x: 7.6, y: y + 0.08, w: 2.5, h: 0.35, fontSize: 15, bold: true }));
      s.addText(items[i][2], tb({ x: 10.1, y: y + 0.1, w: 2.6, h: 0.35, fontSize: 13, color: C.accent6 }));
    }
    s.addNotes("The three lower rows never appear as a debit: they are deducted inside the product price. That is why prospects usually underestimate what they pay. Figures are synthetic, from the demo engine.");
  }
  {
    const s = content(`What ${NAME} does`, "Upload, verify, compare: a free cost check in one meeting", "Why");
    const cols = [
      ["LuFileUp", "Upload", "The client's statements, cost reports and contracts from any bank: PDF, scans, Excel."],
      ["LuListChecks", "Verify", "Every cost is extracted, linked to its page, checked against other documents, and labelled proven, estimated or unknown."],
      ["LuScale", "Compare", "Same holdings with Safe Capital and its custodian bank, switching costs included, on one page for the client."],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.75, 3.8, 3.3, X.bg, "step card " + (i + 1));
      await iconIn(s, x + 0.35, 2.05, 0.7, cols[i][0], X.white, X.teal, cols[i][1]);
      s.addText(cols[i][1], tb({ x: x + 0.35, y: 2.95, w: 3.1, h: 0.45, fontSize: 22, bold: true, color: C.text2 }));
      s.addText(cols[i][2], tb({ x: x + 0.35, y: 3.5, w: 3.1, h: 1.4, fontSize: 15 }));
    }
    const rules = ["No source, no verified figure", "Missing is never zero", "No comparable service, no savings claim"];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      s.addImage({ data: await icon("LuShieldCheck", X.teal), x, y: 5.55, w: 0.4, h: 0.4, objectName: "rule icon " + (i + 1) });
      s.addText(rules[i], tb({ x: x + 0.55, y: 5.55, w: 3.3, h: 0.4, fontSize: 16, bold: true, color: C.text2, valign: "middle" }));
    }
    s.addText("Target: a first draft within minutes of upload, then an analyst check. Speed will be measured in the pilot.", tb({ x: 0.6, y: 6.25, w: 12, h: 0.35, fontSize: 13, color: C.accent6 }));
    s.addNotes("The three rules are what make the result defensible in front of a client and a compliance officer.");
  }

  // =====================================================================
  // HOW IT WORKS
  pres.addSection({ title: "How it works" });
  {
    const s = content("Workflow", "Who does what, from documents to report", "How it works");
    const lanes = [["Client", X.bg], [NAME, X.tealSoft], ["Safe Capital analyst", X.amberSoft], ["Output", "E6ECF4"]];
    const top = 1.6, lh = 1.2, lx = 0.6, lw = 1.7, gx = 2.45, cw = 1.73, bw = 1.5, bh = 0.72;
    lanes.forEach(([n, fill], i) => {
      s.addShape(pres.shapes.RECTANGLE, { x: lx, y: top + i * lh, w: 12.1, h: lh - 0.08, fill: { color: fill }, line: { color: fill }, objectName: "lane " + n });
      s.addText(n, tb({ x: lx + 0.15, y: top + i * lh, w: lw - 0.2, h: lh - 0.08, fontSize: 14, bold: true, color: C.text2, valign: "middle" }));
    });
    const bx = (col) => gx + col * cw + (cw - bw) / 2;
    const by = (lane) => top + lane * lh + (lh - 0.08 - bh) / 2;
    const box = (col, lane, text, strong) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx(col), y: by(lane), w: bw, h: bh, rectRadius: 0.06, fill: { color: strong ? X.navy : X.white }, line: { color: strong ? X.navy : X.border, width: 0.75 }, objectName: "step " + text });
      s.addText(text, tb({ x: bx(col) + 0.08, y: by(lane), w: bw - 0.16, h: bh, fontSize: 12, bold: true, color: strong ? C.background1 : C.text1, align: "center", valign: "middle" }));
    };
    box(0, 0, "Signs consent"); box(1, 0, "Hands over documents");
    box(1, 1, "Classify and read every page", true); box(2, 1, "Reconcile documents", true); box(3, 1, "Find fund costs in official KIDs", true); box(4, 1, "Build cost ledger and scenarios", true); box(5, 1, "Draft the report", true);
    box(2, 2, "Confirm flagged values"); box(4, 2, "Set Safe Capital and custodian fees (once)"); box(5, 2, "Approve and sign");
    box(3, 3, "Request letter for missing documents"); box(5, 3, "One-page client report");
    const midY = (lane) => by(lane) + bh / 2;
    arrow(s, bx(0) + bw, midY(0), cw - bw, 0, "a1");
    arrow(s, bx(1) + bw / 2, by(0) + bh, 0, by(1) - by(0) - bh, "a2");
    for (let c = 1; c < 5; c++) arrow(s, bx(c) + bw, midY(1), cw - bw, 0, "a" + (c + 2));
    arrow(s, bx(2) + bw / 2, by(1) + bh, 0, by(2) - by(1) - bh, "a7");
    arrow(s, bx(3) + bw / 2, by(1) + bh, 0, by(3) - by(1) - bh, "a8");
    arrowUp(s, bx(4) + bw / 2, by(1) + bh, by(2) - by(1) - bh, "a9");
    arrow(s, bx(5) + bw / 2, by(1) + bh, 0, by(2) - by(1) - bh, "a10");
    arrow(s, bx(5) + bw / 2, by(2) + bh, 0, by(3) - by(2) - bh, "a11");
    s.addText("The client sends the missing documents; the analysis updates and the gaps close.", tb({ x: bx(3) - 1.25, y: top + 4 * lh + 0.02, w: 6, h: 0.35, fontSize: 12, italic: true, color: C.accent6 }));
    s.addNotes("Dark boxes are automatic. Analyst steps are short: confirming values the engine is unsure of, setting Safe Capital's own tariff once, and signing the report. Nothing reaches a client without that signature.");
  }
  {
    const s = content("Documents", "What the client brings, and what each document can prove", "How it works");
    const head = ["Document", "What we read", "Proves", "Cannot prove", "Need"];
    const rows = [
      ["Portfolio / asset statement", "ISIN, quantity, price, value, currency, date, total", "Holdings at a date", "Fees", "Essential"],
      ["Annual cost & charges report", "Service costs, product costs, third-party payments", "Near-complete annual cost", "FX margins, if not listed", "Essential"],
      ["Fee advice / cash statement", "Fee type, period, base, rate, amount, VAT", "Every billed debit", "Costs inside products", "Essential*"],
      ["Mandate contract / tariff", "Rates, tiers, minimums, all-in scope, exclusions", "What was agreed", "What was billed", "Helpful"],
      ["Trade & FX confirmations", "Commission, third-party fees, stamp duty, FX rate", "Explicit trading cost", "Contract terms", "Helpful"],
      ["Fund KID (official)", "Share class, ongoing, transaction, entry/exit costs", "Product cost rates", "What the client paid", "We fetch"],
      ["Retrocession statement", "Payments from product providers, refunded or kept", "Conflicts and refunds", "Client cost directly", "Ask bank"],
      ["Insurance policy statement", "Policy value, wrapper charges, underlying funds", "Wrapper charges", "Underlying fund costs", "If wrapped"],
    ];
    const hdr = { bold: true, color: C.accent6, fill: { color: X.mutedSurface }, fontSize: 11 };
    const needKind = { Essential: [X.greenSoft, X.green], "Essential*": [X.greenSoft, X.green], Helpful: ["E6ECF4", X.navy], "We fetch": [X.tealSoft, X.teal], "Ask bank": [X.amberSoft, X.amber], "If wrapped": [X.mutedSurface, X.muted] };
    s.addTable([head.map((h) => ({ text: h.toUpperCase(), options: hdr }))].concat(rows.map((r) => r.map((c, ci) => ({
      text: c,
      options: ci === 0 ? { bold: true, fontSize: 13, color: C.text1 } : ci === 4 ? { bold: true, fontSize: 12, color: needKind[c][1], fill: { color: needKind[c][0] }, align: "center" } : { fontSize: 12, color: ci === 3 ? C.accent6 : C.text1 },
    })))), { x: 0.6, y: 1.6, w: 12.1, colW: [2.6, 3.9, 2.25, 2.15, 1.2], rowH: 0.52, border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0.04, 0.1, 0.04, 0.1], valign: "middle" });
    s.addText("* either the cost report or the fee advices. Accepted formats: PDF, scans or phone photos (OCR), Excel, CSV. Italian, German, French and English.", tb({ x: 0.6, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent6 }));
    s.addNotes("Full taxonomy of 31 document types with IT/DE/EN names is in data/taxonomy/document_types.csv. In Switzerland the annual cost report is often only provided on request, so the engine drafts that request.");
  }
  {
    const s = content("Real documents", "Real public documents, and the figures FeeLens takes from them", "How it works");
    const docs = [
      ["Bank price list", "Zürcher Kantonalbank", "Preisübersicht Anlagegeschäft · Sept 2025 · German", [
        ["Custody, Swiss-held securities", "0.30% p.a., min CHF 3/month", "p.1"],
        ["Custody, foreign-held securities", "0.40% p.a., min CHF 4/month", "p.1"],
        ["Brokerage, Swiss shares to 100k", "0.50% online · 1.00% other", "p.2"],
        ["FX spread, main currency < 50k", "up to 1.00%", "p.3"],
        ["Swiss stamp duty, shares", "0.075–0.150%", "p.5"]]],
      ["Bank price list", "Raiffeisenbank Locarno", "Dienstleistungspreise Anlegen · from 1 Jan 2025 · German", [
        ["Custody, securities account", "0.25% p.a.", "p.2"],
        ["Minimum", "CHF 12.50 per quarter", "p.2"],
        ["Surcharge, complex markets (e.g. USA)", "+0.10% p.a.", "p.2"],
        ["Low-priced securities", "CHF 5.00 per quarter, per position", "p.2"],
        ["Fund savings-plan account", "0.25% p.a., min CHF 5 per quarter", "p.2"]]],
      ["Fund KID (PRIIPs)", "iShares Core MSCI World UCITS ETF", "IE00B4L5Y983 · USD Acc · BlackRock · 3 Sep 2026", [
        ["Ongoing costs", "0.20% p.a.", "p.3"],
        ["Transaction costs", "0.00% p.a.", "p.3"],
        ["Entry / exit charge", "none / none", "p.3"],
        ["Performance fee", "none", "p.3"],
        ["Cost on USD 10'000, year 1", "USD 20", "p.3"]]],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1, d = docs[i];
      card(s, x, 1.6, 3.85, 4.75, X.bg, d[1]);
      chip(s, x + 0.25, 1.82, d[0], i === 2 ? "con" : "info", 1.75);
      s.addText(d[1], tb({ x: x + 0.25, y: 2.25, w: 3.4, h: 0.4, fontSize: 16, bold: true, color: C.text2 }));
      s.addText(d[2], tb({ x: x + 0.25, y: 2.65, w: 3.4, h: 0.5, fontSize: 11, color: C.accent6 }));
      d[3].forEach((r, j) => {
        const y = 3.25 + j * 0.6;
        s.addShape(pres.shapes.LINE, { x: x + 0.25, y: y - 0.05, w: 3.35, h: 0, line: { color: X.border, width: 0.5 }, objectName: "rr" + i + j });
        s.addText(r[0], tb({ x: x + 0.25, y, w: 2.9, h: 0.25, fontSize: 11, color: C.accent6 }));
        s.addText(r[1], tb({ x: x + 0.25, y: y + 0.24, w: 2.9, h: 0.3, fontSize: 13, bold: true }));
        s.addText(r[2], tb({ x: x + 3.15, y: y + 0.24, w: 0.45, h: 0.3, fontSize: 11, color: C.accent1, align: "right" }));
      });
    }
    s.addText("Figures quoted as printed by each issuer; every value keeps its page. Client statements in the demo stay synthetic for privacy. Fees change: FeeLens checks the document date and the issuing entity.", tb({ x: 0.6, y: 6.5, w: 12.1, h: 0.4, fontSize: 12, color: C.accent6 }));
    s.addNotes("Public sources, read on 6 Nov 2026. ZKB: zkb.ch/media/zkb/dokumente/legal/preisuebersichten/preisuebersicht_anlagegeschaeft_de_sept2025.pdf. Raiffeisenbank Locarno: raiffeisen.ch/content/dam/www/locarno/pdf/de-prezzi-servizi-2025/dienstleistungspreise-anlegen-ab-01-2025. KID for IE00B4L5Y983 (BlackRock Asset Management Ireland, created 3 Sep 2026), also confirmed by the iShares factsheet (TER 0.20%). Quoted for illustration only; no endorsement or comparison of these banks is implied. Example: CHF 1m of foreign-held securities at ZKB would cost 0.40% = CHF 4'000 a year in custody alone.");
  }
  {
    const s = content("Data", "Everything extracted becomes one of five kinds of data", "How it works");
    const ents = [
      ["LuLayers", "Positions", ["ISIN and share class", "Quantity, price, value", "Currency, valuation date", "Bank, account"]],
      ["LuReceipt", "Fees charged", ["Fee type and period", "Base and rate", "Amount, VAT", "Debit date"]],
      ["LuFileSignature", "Contract terms", ["Rates and tiers", "Minimums", "All-in scope", "Booking entity"]],
      ["LuPieChart", "Product costs", ["Ongoing charges", "Transaction costs", "Entry / exit (max)", "KID date and class"]],
      ["LuSearch", "Evidence", ["File and page", "Box on the page", "Original text", "Who confirmed it"]],
    ];
    for (let i = 0; i < 5; i++) {
      const x = 0.6 + i * 2.46;
      card(s, x, 1.65, 2.25, 3.9, i === 4 ? X.tealSoft : X.bg, ents[i][1]);
      await iconIn(s, x + 0.25, 1.9, 0.6, ents[i][0], X.white, i === 4 ? X.teal : X.navy, ents[i][1]);
      s.addText(ents[i][1], tb({ x: x + 0.25, y: 2.7, w: 1.9, h: 0.45, fontSize: 18, bold: true, color: C.text2 }));
      s.addText(ents[i][2].map((t, j) => ({ text: t, options: { breakLine: j < 3 } })), tb({ x: x + 0.25, y: 3.25, w: 1.9, h: 2.1, fontSize: 13, paraSpaceAfter: 8, color: C.text1 }));
    }
    s.addText("Every position, fee, term and product cost carries its evidence. Each one also gets a status: observed, contractual, estimated, not a paid cost, or not determined. A number with no evidence never reaches the cost total.", tb({ x: 0.6, y: 5.85, w: 12.1, h: 0.8, fontSize: 15 }));
    s.addNotes("This is the canonical data model in plain words. Bank-specific layouts all map onto these five kinds, which is what makes the tool generic for any bank.");
  }
  {
    const s = content("Cost layers", "Ten cost layers, in four places a client may never look", "How it works");
    const groups = [
      ["Debited from the account", X.navy, ["Service: management, advisory, all-in", "Custody and account", "Trading: brokerage, third-party", "Financing: Lombard interest", "Taxes: VAT, stamp duty"]],
      ["Inside product prices", X.teal, ["Funds and ETFs: ongoing and transaction costs", "Structured products: issuer and distribution margin"]],
      ["Inside execution rates", X.l2, ["FX margins and bid/ask spreads"]],
      ["Wrapper and one-off", X.amber, ["Insurance wrapper charges", "Switching: transfer, exit, sale costs"]],
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.08;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.65, w: 2.88, h: 0.62, rectRadius: 0.06, fill: { color: groups[i][1] }, line: { color: groups[i][1] }, objectName: groups[i][0] });
      s.addText(groups[i][0], tb({ x: x + 0.18, y: 1.65, w: 2.6, h: 0.62, fontSize: 15, bold: true, color: C.background1, valign: "middle" }));
      groups[i][2].forEach((t, j) => {
        card(s, x, 2.42 + j * 0.72, 2.88, 0.62, X.bg, t);
        s.addText(t, tb({ x: x + 0.18, y: 2.42 + j * 0.72, w: 2.6, h: 0.62, fontSize: 13, valign: "middle" }));
      });
    }
    card(s, 0.6, 6.05, 12.1, 0.7, X.amberSoft, "retro note");
    s.addText([{ text: "Beside the total, never inside it: ", options: { bold: true } }, { text: "retrocessions paid by product providers to the bank. They are already part of fund costs; only a refund to the client lowers the cost." }], tb({ x: 0.85, y: 6.05, w: 11.7, h: 0.7, fontSize: 14, valign: "middle" }));
    s.addNotes("The ten layers (L1 to L10) are defined in docs/research/FEE_TAXONOMY.md. Clients see the first column on statements; the second column is usually the surprise.");
  }
  {
    const s = content("Evidence", "Every cost carries a status, and only some are added up", "How it works");
    const st = [
      ["obs", "Observed", "Taken from a bank document", "Advisory fee, Bank Alpha", "CHF 25'600", "Counted"],
      ["con", "Contractual", "Calculated from an agreed tariff", "Safe Capital fee, proposal", "CHF 25'500", "Counted"],
      ["est", "Estimated", "Official rate × position value", "Global Equity Leaders, 1.08%", "CHF 9'720", "Counted"],
      ["na", "Not a paid cost", "A maximum or an illustration", "Entry charge, up to 3%", "CHF 27'000", "Shown, not added"],
      ["unk", "Not determined", "No document yet", "Bank Beta service fees", "?", "Never zero"],
    ];
    const hy = 1.65;
    ["STATUS", "MEANING", "EXAMPLE (P-1042)", "AMOUNT", "IN THE TOTAL"].forEach((h, i) => s.addText(h, tb({ x: [0.6, 3.0, 6.3, 9.4, 11.0][i], y: hy, w: 2.8, h: 0.3, fontSize: 11, bold: true, color: C.accent6, charSpacing: 1 })));
    for (let i = 0; i < 5; i++) {
      const y = 2.1 + i * 0.86;
      if (i) s.addShape(pres.shapes.LINE, { x: 0.6, y: y - 0.13, w: 12.1, h: 0, line: { color: X.border, width: 0.75 }, objectName: "rule " + i });
      chip(s, 0.6, y + 0.12, st[i][1], st[i][0], 2.0);
      s.addText(st[i][2], tb({ x: 3.0, y, w: 3.1, h: 0.55, fontSize: 15, valign: "middle" }));
      s.addText(st[i][3], tb({ x: 6.3, y, w: 3.0, h: 0.55, fontSize: 15, valign: "middle", color: C.accent6 }));
      s.addText(st[i][4], tb({ x: 9.4, y, w: 1.4, h: 0.55, fontSize: 17, bold: true, valign: "middle", color: st[i][0] === "unk" ? C.accent3 : st[i][0] === "na" ? C.accent6 : C.text1 }));
      s.addText(st[i][5], tb({ x: 11.0, y, w: 1.7, h: 0.55, fontSize: 15, bold: true, valign: "middle", color: st[i][0] === "unk" ? C.accent3 : st[i][0] === "na" ? C.accent6 : C.accent4 }));
    }
    s.addText("The fund's management fee (0.75%) is part of its 1.08% ongoing charge. It is shown as detail and not added a second time.", tb({ x: 0.6, y: 6.45, w: 12.1, h: 0.35, fontSize: 13, color: C.accent6 }));
    s.addNotes("Statuses follow the shared design system (icon plus label, never colour alone). The KID's illustrative amounts and maximum entry charges are visible for transparency but are not costs the client paid.");
  }
  {
    const s = content("Reconciliation", "Before trusting a number, documents are checked against each other", "How it works");
    const groups = [
      ["LuCalculator", "Do the numbers add up?", [["pass", "Alpha positions = printed total, 3'200'000"], ["pass", "Beta positions = printed total, 1'100'000"], ["pass", "All holdings valued on 30.09.2026"]]],
      ["LuFileSignature", "Is what was billed what was agreed?", [["pass", "Advisory fee = 3.2m × 0.80%"], ["pass", "Custody fee = 3.0m × 0.20%"], ["pass", "Quarterly debits × 4 = annual report, counted once"]]],
      ["LuShieldCheck", "Is the source valid for this client?", [["fail", "Beta price list is from its Luxembourg entity: rejected"], ["pass", "Fund costs from KIDs within 2.6% of the bank's estimate"], ["info", "Retrocessions CHF 3'900: inside fund costs, not added"]]],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.85, 4.6, X.bg, groups[i][1]);
      await iconIn(s, x + 0.3, 1.9, 0.6, groups[i][0], X.white, X.navy, groups[i][1]);
      s.addText(groups[i][1], tb({ x: x + 0.3, y: 2.65, w: 3.3, h: 0.75, fontSize: 18, bold: true, color: C.text2 }));
      groups[i][2].forEach(([k, t], j) => {
        const y = 3.55 + j * 0.85;
        chip(s, x + 0.3, y, k === "pass" ? "Pass" : k === "fail" ? "Rejected" : "Note", k, 1.05);
        s.addText(t, tb({ x: x + 1.5, y: y - 0.05, w: 2.2, h: 0.8, fontSize: 13 }));
      });
    }
    s.addText("Mismatches stay visible for the analyst. They are never silently forced to agree.", tb({ x: 0.6, y: 6.45, w: 12.1, h: 0.35, fontSize: 13, color: C.accent6 }));
    s.addNotes("These are the actual checks the demo engine ran on the synthetic P-1042 documents. A tariff from a different legal entity or country (here Luxembourg for a Swiss-booked account) is rejected automatically.");
  }

  // =====================================================================
  // SCREENS
  pres.addSection({ title: "The screens" });
  const screen = (kicker, title, file, notes) => {
    const s = content(kicker, title, "The screens");
    fitImage(s, IMG(file), { x: 0.6, y: 1.55, w: 12.1, h: 5.3 }, title);
    s.addNotes(notes);
    return s;
  };
  screen("Screen · costs", "The headline always comes with its coverage", "v2_overview.png",
    "Mockup in the shared design system, with the engine's synthetic P-1042 output. Known cost CHF 61'450 (1.43%), 65% observed in bank documents, 35% estimated from KIDs, five items not determined and shown as such. The bank-by-layer grid shows at a glance where evidence is missing.");
  screen("Screen · drill-down", "Click any number: formula, checks and source page", "v2_drill.png",
    "Every line opens a side panel with the amount, its status, the source page with the value highlighted, the formula and the cross-checks it passed. Overlaps (management fee inside ongoing charges) and maximums are shown but not added.");
  screen("Screen · review", "Scans and uncertain values get a human check", "v2_review.png",
    "The original page on the left, extracted values on the right. Values read by OCR from a scan are flagged; the analyst accepts, corrects or turns them into a question for the client. Keyboard shortcuts keep this fast.");
  screen("Screen · checks", "Gaps turn into a ready-to-send request letter", "v2_checks.png",
    "Reconciliation results and the documents still needed, ranked by impact. The request letter is drafted in the client's language (Italian here) and explains why each document matters.");

  // =====================================================================
  // RESULT
  pres.addSection({ title: "The result" });
  {
    const s = content("Compare", "Same holdings first, with every Safe Capital cost included", "The result");
    const labels = ["Today (comparable)", "Safe Capital, same holdings", "Safe Capital, new funds"];
    s.addChart(pres.charts.BAR, [
      { name: "Management / advisory", labels, values: [25600, 25500, 25500] },
      { name: "Custody, trading, FX", labels, values: [11390, 5140, 5140] },
      { name: "VAT", labels, values: [2559.6, 2389.5, 2389.5] },
      { name: "Fund costs inside prices", labels, values: [21290, 21290, 13110] },
    ], {
      x: 0.6, y: 1.55, w: 7.4, h: 5.25, barDir: "col", barGrouping: "stacked", barGapWidthPct: 70,
      chartColors: [X.navy, X.l2, X.l9, X.teal], showValue: false,
      catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", titleFontFace: "+mn-lt",
      catAxisLabelColor: X.muted, valAxisLabelColor: X.muted, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, valAxisLabelFormatCode: "#,##0",
      valGridLine: { color: "E5E2DA", size: 0.5 }, catGridLine: { style: "none" }, valAxisMaxVal: 70000,
      showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: X.muted,
      showTitle: true, title: "Annual cost, CHF (synthetic P-1042)", titleFontSize: 13, titleColor: X.muted,
    });
    const rows = [["Today, comparable", "CHF 60'840", "1.41%", C.text1], ["Safe Capital, same holdings", "CHF 54'320", "1.26%", C.accent1], ["Safe Capital, new funds", "CHF 46'140", "1.07%", C.accent6]];
    rows.forEach((r, i) => {
      const y = 1.6 + i * 0.85;
      s.addText(r[0], tb({ x: 8.4, y, w: 3.0, h: 0.3, fontSize: 13, color: C.accent6 }));
      s.addText(r[1], tb({ x: 8.4, y: y + 0.3, w: 2.8, h: 0.45, fontSize: 22, bold: true, color: r[3] }));
      s.addText(r[2], tb({ x: 11.3, y: y + 0.33, w: 1.4, h: 0.4, fontSize: 16, color: C.accent6, align: "right" }));
    });
    card(s, 8.4, 4.25, 4.3, 0.85, X.tealSoft, "saving");
    s.addText([{ text: "at least CHF 6'520 per year", options: { bold: true, color: C.accent1, fontSize: 18, breakLine: true } }, { text: "same holdings, like for like", options: { fontSize: 12, color: C.accent6 } }], tb({ x: 8.6, y: 4.3, w: 4.0, h: 0.75, valign: "middle" }));
    s.addText([
      { text: "\"At least\": Bank Beta's own fees are still unknown, so today's real cost is higher.", options: { bullet: true, breakLine: true } },
      { text: "Swiss stamp duty (CHF 610) is left out on both sides: it is due at any Swiss bank.", options: { bullet: true, breakLine: true } },
      { text: "New funds change risk and products: shown apart, never as a fee saving.", options: { bullet: true } },
    ], tb({ x: 8.4, y: 5.25, w: 4.3, h: 1.6, fontSize: 12, color: C.text1, paraSpaceAfter: 4 }));
    s.addNotes("Safe Capital is an external asset manager: client assets stay at a custodian bank, so the proposal adds Safe Capital's fee (tiered 0.70% / 0.50%) and the partner custodian's custody, trading and FX fees. VAT at 8.1% applies because the synthetic client is domiciled in Switzerland; it depends on domicile. All figures come from the demo engine and are synthetic.");
  }
  {
    const s = content("Year one", "Switching costs are counted, and paid back within months here", "The result");
    const tbl = [
      ["", "Same holdings", "New funds"],
      ["Annual difference, at least", "CHF 6'520.10", "CHF 14'700.10"],
      ["One-off switching costs", "– CHF 1'500.00", "– CHF 4'000.00"],
      ["Net in year one", "CHF 5'020.10", "CHF 10'700.10"],
      ["Payback", "2.8 months", "3.3 months"],
      ["Like for like?", "Yes", "No: products change"],
    ];
    const hdr = { bold: true, color: C.background1, fill: { color: X.navy }, fontSize: 14 };
    s.addTable(tbl.map((r, ri) => r.map((c, ci) => ({
      text: c,
      options: ri === 0 ? Object.assign({ align: ci ? "right" : "left" }, hdr) : { fontSize: 16, align: ci ? "right" : "left", bold: ri === 3 || ri === 4 || ci === 0, color: ri === 5 && ci === 2 ? C.accent2 : ri === 3 && ci ? C.accent1 : C.text1, fill: { color: ri % 2 ? X.white : X.bg } },
    }))), { x: 0.6, y: 1.65, w: 7.6, colW: [3.0, 2.3, 2.3], rowH: 0.62, border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0, 0.15, 0, 0.15], valign: "middle" });
    await iconIn(s, 8.8, 1.7, 0.7, "LuTimer", X.tealSoft, X.teal, "payback");
    s.addText("Payback = switching cost ÷ annual difference × 12", tb({ x: 8.8, y: 2.6, w: 3.9, h: 0.7, fontSize: 16, bold: true, color: C.text2 }));
    s.addText("Switching costs come from the banks' transfer fees and the positions sold. In this synthetic case they are small; with real prospects exit fees and taxes can change the picture, and the tool shows that honestly.", tb({ x: 8.8, y: 3.4, w: 3.9, h: 2.2, fontSize: 14 }));
    s.addText("Safe Capital's own margin on the prospect is calculated on a separate internal screen and never appears in client material.", tb({ x: 0.6, y: 6.0, w: 7.6, h: 0.6, fontSize: 13, color: C.accent6 }));
    s.addNotes("Engine output for P-1042: same holdings 1'500 transfer fees (Alpha 500, Beta estimate 1'000), payback 2.8 months; new funds 4'000 switching, payback 3.3 months. The internal view reports 'insufficient evidence' for an acquisition decision until Bank Beta's fees are known.");
  }
  {
    const s = content("Client report", "One page the client can read, approved before it leaves", "The result");
    const r = fitImage(s, IMG("v2_report.png"), { x: 0.6, y: 1.5, w: 6.4, h: 5.35 }, "Client report mockup");
    const pts = [
      ["LuCheckCircle2", X.green, X.greenSoft, "On the page", "Today vs Safe Capital, line by line, observed vs estimated"],
      ["LuAlertTriangle", X.amber, X.amberSoft, "Also on the page", "What is still missing, and the stamp duty exclusion, in plain words"],
      ["LuEyeOff", X.red, X.redSoft, "Never on the page", "Safe Capital's internal margin and analyst notes"],
      ["LuPenLine", X.navy, "E6ECF4", "Before it leaves", "An approver signs it off; the version is frozen and logged"],
    ];
    for (let i = 0; i < 4; i++) {
      const y = 1.65 + i * 1.25;
      await iconIn(s, 7.5, y, 0.6, pts[i][0], pts[i][2], pts[i][1], pts[i][3]);
      s.addText(pts[i][3], tb({ x: 8.3, y: y, w: 4.4, h: 0.35, fontSize: 16, bold: true }));
      s.addText(pts[i][4], tb({ x: 8.3, y: y + 0.38, w: 4.4, h: 0.7, fontSize: 14, color: C.accent6 }));
    }
    s.addNotes("PDF export from approved numbers only, in the client's language. States that it is not investment advice.");
  }

  // =====================================================================
  // DATA & PRIVACY
  pres.addSection({ title: "Data & privacy" });
  {
    const s = content("Hosting", "It runs on Safe Capital's own infrastructure by default", "Data & privacy");
    const opts = [
      ["LuLaptop", "A · In the office", "One secured machine at Safe Capital. Documents never leave the building.", "Recommended for the pilot", X.teal],
      ["LuServer", "B · Swiss private hosting", "Dedicated server at a Swiss provider, under a data-processing contract. For several users.", "Option for production", X.navy],
      ["LuCloud", "C · External AI services", "Only for hard pages, only with explicit approval, only on redacted excerpts.", "Off by default", X.amber],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.85, 3.6, X.bg, opts[i][1]);
      await iconIn(s, x + 0.3, 1.95, 0.7, opts[i][0], X.white, opts[i][4], opts[i][1]);
      s.addText(opts[i][1], tb({ x: x + 0.3, y: 2.85, w: 3.3, h: 0.45, fontSize: 19, bold: true, color: C.text2 }));
      s.addText(opts[i][2], tb({ x: x + 0.3, y: 3.35, w: 3.3, h: 1.2, fontSize: 14 }));
      s.addText(opts[i][3], tb({ x: x + 0.3, y: 4.7, w: 3.3, h: 0.35, fontSize: 14, bold: true, color: opts[i][4] }));
    }
    card(s, 0.6, 5.55, 12.1, 0.95, X.tealSoft, "egress");
    s.addText([{ text: "The only thing that goes online: ", options: { bold: true, color: C.accent1 } }, { text: "public fund codes (ISINs) to fetch official product documents. No names, no amounts, no statements." }], tb({ x: 0.9, y: 5.55, w: 11.6, h: 0.95, fontSize: 16, valign: "middle" }));
    s.addNotes("Swiss hosting helps but does not by itself make processing compliant; contracts, access control and retention matter as much. Final choice with Safe Capital's compliance officer.");
  }
  {
    const s = content("Privacy", "Client files stay confidential from upload to deletion", "Data & privacy");
    const tiles = [
      ["LuFileSignature", "Client consent", "A short signed authorisation before any upload"],
      ["LuFilter", "Only what is needed", "Names can be blacked out; costs need no identity"],
      ["LuLock", "Encrypted", "At rest and in transit; one space per prospect"],
      ["LuUserCheck", "Named access", "Personal logins, two-factor, every view logged"],
      ["LuBot", "No public AI on raw files", "Unless Safe Capital approves a provider"],
      ["LuTrash2", "Deleted on schedule", "Retention agreed up front, then erased"],
    ];
    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.6 + col * 4.1, y = 1.7 + row * 1.95;
      card(s, x, y, 3.85, 1.7, X.bg, tiles[i][1]);
      await iconIn(s, x + 0.3, y + 0.3, 0.6, tiles[i][0], X.white, X.teal, tiles[i][1]);
      s.addText(tiles[i][1], tb({ x: x + 1.1, y: y + 0.3, w: 2.6, h: 0.4, fontSize: 16, bold: true }));
      s.addText(tiles[i][2], tb({ x: x + 1.1, y: y + 0.75, w: 2.6, h: 0.8, fontSize: 13, color: C.accent6 }));
    }
    s.addText("Swiss Federal Act on Data Protection (revised, in force since 1 September 2023) applies. Bank-client confidentiality and outsourcing rules must be checked by Safe Capital's counsel; this is not legal advice.", tb({ x: 0.6, y: 5.75, w: 12.1, h: 0.7, fontSize: 13, color: C.accent6 }));
    s.addNotes("Pseudonymised data can still be personal data. A data-protection impact assessment may be needed; that decision belongs to Safe Capital and its counsel.");
  }

  // =====================================================================
  // NEXT STEPS
  pres.addSection({ title: "Next steps" });
  {
    const s = content("People and machine", "The engine reads and calculates; people decide", "Next steps");
    const cols = [
      [`Automatic, by ${NAME}`, X.tealSoft, X.teal, "LuSettings", ["Recognise each document, bank and language", "Extract positions, ISINs and fees with their page", "Fetch official fund cost documents", "Run the reconciliation checks", "Build the ledger and both scenarios", "Draft the request letter and the report"]],
      ["A person at Safe Capital", X.amberSoft, X.amber, "LuUserCheck", ["Enter Safe Capital's and the custodian's fees, once", "Confirm values the engine flags", "Decide whether a comparison is like for like", "Approve and sign the client report", "Present it and talk to the client"]],
    ];
    for (let i = 0; i < 2; i++) {
      const x = 0.6 + i * 6.15;
      card(s, x, 1.65, 5.95, 3.9, cols[i][1], cols[i][0]);
      await iconIn(s, x + 0.35, 1.95, 0.6, cols[i][3], X.white, cols[i][2], cols[i][0]);
      s.addText(cols[i][0], tb({ x: x + 1.15, y: 2.0, w: 4.5, h: 0.5, fontSize: 20, bold: true, color: cols[i][2] }));
      s.addText(cols[i][4].map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < cols[i][4].length - 1 } })), tb({ x: x + 0.35, y: 2.85, w: 5.3, h: 3.4, fontSize: 16, paraSpaceAfter: 10 }));
    }
    s.addNotes("Manual configuration is mostly one-time: Safe Capital's tariff, the custodian's terms and the report template. Per prospect, the human effort depends on document quality.");
  }
  {
    const s = content("Plan", "Delivery in phases, with a real pilot before production", "Next steps");
    const ph = [["Now", "Demo", "Working engine on synthetic documents; this deck"], ["Phase 1", "Pilot", "1–3 anonymised real prospects; measure accuracy and time"], ["Phase 2", "Harden", "More bank layouts, security review, user logins"], ["Phase 3", "Production", "Live at Safe Capital after compliance sign-off"]];
    s.addShape(pres.shapes.LINE, { x: 0.95, y: 2.3, w: 9.3, h: 0, line: { color: X.border, width: 2 }, objectName: "timeline" });
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.1;
      s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: 2.1, w: 0.4, h: 0.4, fill: { color: i === 0 ? X.teal : X.navy }, line: { color: X.white, width: 2 }, objectName: "milestone " + (i + 1) });
      s.addText(ph[i][0].toUpperCase(), tb({ x, y: 1.6, w: 2.8, h: 0.3, fontSize: 11, bold: true, charSpacing: 1, color: i === 0 ? C.accent1 : C.accent6 }));
      card(s, x, 2.85, 2.85, 2.2, X.bg, "phase " + (i + 1));
      s.addText(ph[i][1], tb({ x: x + 0.3, y: 3.1, w: 2.3, h: 0.5, fontSize: 22, bold: true, color: C.text2 }));
      s.addText(ph[i][2], tb({ x: x + 0.3, y: 3.7, w: 2.3, h: 1.2, fontSize: 15 }));
    }
    s.addText("Durations are set after the pilot, once we know how many bank layouts Safe Capital's prospects bring.", tb({ x: 0.6, y: 5.45, w: 12.1, h: 0.4, fontSize: 13, color: C.accent6 }));
    s.addNotes("No dates before seeing real documents: the number of bank layouts drives the effort.");
  }
  {
    const s = content("Decisions", "Six decisions to start the pilot", "Next steps");
    const dec = [
      ["One anonymised real case", "holdings, 12 months of fees, the contract"],
      ["Safe Capital's pricing", "advisory fee, partner custodian and its tariff"],
      ["Comparison policy", "same holdings only, or also a new-funds case"],
      ["Where it runs, who sees it", "office machine or Swiss hosting; named users"],
      ["Consent and retention", "authorisation wording; how long files are kept"],
      ["Name and legal entity", `confirm "${NAME}", the entity and licence to cite`],
    ];
    for (let i = 0; i < 6; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.6 + col * 6.15, y = 1.65 + row * 1.55;
      card(s, x, y, 5.95, 1.3, X.bg, "decision " + (i + 1));
      s.addText(String(i + 1).padStart(2, "0"), tb({ x: x + 0.3, y, w: 0.8, h: 1.3, fontSize: 28, bold: true, color: C.accent1, valign: "middle" }));
      s.addText(dec[i][0], tb({ x: x + 1.2, y: y + 0.25, w: 4.5, h: 0.42, fontSize: 18, bold: true, color: C.text2 }));
      s.addText(dec[i][1], tb({ x: x + 1.2, y: y + 0.7, w: 4.5, h: 0.4, fontSize: 14, color: C.accent6 }));
    }
    s.addNotes("Decision 6: Safe Capital Management SA (CHE-381.156.096, Lugano) is in the commercial register. Its website states FINMA authorisation with OSIF supervision; this has not yet been checked in the FINMA register, so nothing in client material should state it until confirmed. The product name also needs a trademark search.");
  }
  {
    const s = pres.addSlide({ masterName: "Dark", sectionTitle: "Next steps" });
    s.addText("Next: one real case", { placeholder: "title" });
    s.addText("No source, no verified figure · Missing is never zero · No comparable service, no savings claim", { placeholder: "body" });
    s.addNotes("Ask: one anonymised prospect file and Safe Capital's fee schedule. With those, every synthetic figure here becomes a real, source-linked one.");
  }

  // =====================================================================
  // DEEP DIVE
  pres.addSection({ title: "Deep dive" });
  {
    const s = content("Deep dive · cost layers", "The ten layers in detail", "Deep dive");
    const rows = [
      ["L1", "Service", "Management, advisory, all-in, EAM fee", "Mandate, fee advice, cost report", "Debit"],
      ["L2", "Custody & account", "Safekeeping (tiered, minimums), account fees", "Tariff, fee advice", "Debit"],
      ["L3", "Explicit trading", "Brokerage, ticket, third-party, FX commission", "Trade confirmations", "In net amount"],
      ["L4", "Funds & ETFs", "Ongoing, fund transaction, performance, entry/exit", "KID, factsheet", "Inside NAV"],
      ["L5", "Structured products", "Issuer margin, distribution fee", "KID, termsheet", "Inside price"],
      ["L6", "Implicit execution", "FX margin, bid/ask spread", "FX confirmations vs reference", "Inside rate"],
      ["L7", "Insurance wrapper", "Policy, admin, risk charges", "Policy statement, insurance KID", "Partly"],
      ["L8", "Financing", "Lombard interest, commitment fee", "Credit agreement, interest advice", "Debit"],
      ["L9", "Taxes & duties", "VAT on fees (by domicile), stamp duty", "Fee advice, confirmations", "Debit"],
      ["L10", "One-off & switching", "Transfer per position, exit, sale costs", "Tariff, transfer quote", "Once"],
    ];
    const hdr = { bold: true, color: C.accent6, fill: { color: X.mutedSurface }, fontSize: 11 };
    s.addTable([["", "LAYER", "WHAT", "EVIDENCE", "VISIBLE AS"].map((h) => ({ text: h, options: hdr }))].concat(rows.map((r) => r.map((c, ci) => ({ text: c, options: { fontSize: 12, bold: ci <= 1, color: ci === 0 ? C.accent1 : C.text1 } })))),
      { x: 0.6, y: 1.55, w: 12.1, colW: [0.6, 2.2, 4.4, 3.3, 1.6], rowH: 0.45, border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0.03, 0.1, 0.03, 0.1], valign: "middle" });
    s.addNotes("Source: docs/research/FEE_TAXONOMY.md and data/taxonomy/fee_taxonomy.csv (fee codes, overlap rules, default evidence status).");
  }
  {
    const s = content("Deep dive · pipeline", "From file to report: seven steps, each one traceable", "Deep dive");
    const st = [
      ["Intake", "hash, file type, size limits, quarantine, duplicates"],
      ["Classify", "bank, document type, period, language"],
      ["Extract", "text and tables with page boxes; OCR for scans"],
      ["Normalise", "Swiss/EU number formats, currencies, rates"],
      ["Reconcile", "totals, dates, tariffs, debits vs reports"],
      ["Ledger", "fee atoms, overlaps, statuses, Decimal arithmetic"],
      ["Scenarios", "current, same holdings, new funds, payback"],
    ];
    const w = 1.66, gap = 0.08;
    for (let i = 0; i < 7; i++) {
      const x = 0.6 + i * (w + gap);
      s.addShape(i ? pres.shapes.CHEVRON : pres.shapes.PENTAGON, { x, y: 1.75, w, h: 0.8, fill: { color: i % 2 ? X.teal : X.navy }, line: { color: X.white }, objectName: "pipe " + st[i][0] });
      s.addText(st[i][0], tb({ x: x + (i ? 0.42 : 0.15), y: 1.75, w: w - 0.62, h: 0.8, fontSize: 13, bold: true, color: C.background1, valign: "middle" }));
      s.addText(st[i][1], tb({ x: x + 0.05, y: 2.75, w: w - 0.15, h: 1.3, fontSize: 12, color: C.text1 }));
    }
    card(s, 0.6, 4.45, 5.95, 2.0, X.bg, "guardrails");
    s.addText([{ text: "Guardrails", options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
      { text: "AI output is a suggestion until code checks it against the page text", options: { bullet: true, breakLine: true } },
      { text: "No arithmetic by AI: a deterministic Decimal engine does the sums", options: { bullet: true, breakLine: true } },
      { text: "Document text is data, never instructions", options: { bullet: true } }], tb({ x: 0.85, y: 4.6, w: 5.5, h: 1.8, fontSize: 13, paraSpaceAfter: 4 }));
    card(s, 6.75, 4.45, 5.95, 2.0, X.bg, "audit");
    s.addText([{ text: "Audit trail", options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
      { text: "Every value keeps file, page, box and original text", options: { bullet: true, breakLine: true } },
      { text: "Every correction keeps who, when, why, before and after", options: { bullet: true, breakLine: true } },
      { text: "Approved reports are frozen versions", options: { bullet: true } }], tb({ x: 7.0, y: 4.6, w: 5.5, h: 1.8, fontSize: 13, paraSpaceAfter: 4 }));
    s.addNotes("This mirrors the demo engine's modules (extraction, engine/ledger, engine/scenarios, analysis).");
  }
  {
    const s = content("Deep dive · tools", "A local, open-source extraction stack", "Deep dive");
    const rows = [
      ["Born-digital PDF", "pdfplumber, Docling", "Words with coordinates, tables, reading order", "MIT"],
      ["Scans and photos", "OCRmyPDF + Tesseract", "Adds a text layer; Italian, German, French, English", "MPL-2.0 / Apache-2.0"],
      ["Excel and CSV", "openpyxl", "Sheet and cell as evidence", "MIT"],
      ["Page images", "pypdfium2, PDF.js", "Render pages and highlight boxes in the viewer", "Apache-2.0 / BSD"],
      ["Hard scans (later)", "PaddleOCR (local)", "Benchmark on real documents before adopting", "Apache-2.0"],
      ["Avoided", "PyMuPDF, cloud OCR", "AGPL licence; client data would leave the office", "—"],
    ];
    const hdr = { bold: true, color: C.accent6, fill: { color: X.mutedSurface }, fontSize: 11 };
    s.addTable([["INPUT", "TOOL", "WHAT IT DOES", "LICENCE"].map((h) => ({ text: h, options: hdr }))].concat(rows.map((r, ri) => r.map((c, ci) => ({ text: c, options: { fontSize: 13, bold: ci === 0, color: ri === 5 ? C.accent3 : C.text1 } })))),
      { x: 0.6, y: 1.6, w: 12.1, colW: [2.4, 2.8, 4.6, 2.3], rowH: 0.6, border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0.04, 0.12, 0.04, 0.12], valign: "middle" });
    s.addText("Accuracy is measured per field on a gold set of real anonymised documents in the pilot, not taken from vendor benchmarks.", tb({ x: 0.6, y: 6.1, w: 12.1, h: 0.4, fontSize: 13, color: C.accent6 }));
    s.addNotes("Source: docs/research/EXTRACTION_TOOLING.md. Versions are pinned in the backend.");
  }
  {
    const s = content("Deep dive · glossary", "Words used in this deck", "Deep dive");
    const g = [
      ["KID", "Key Information Document: the official cost sheet a fund must publish for each share class."],
      ["Ongoing charges (TER/OCF)", "Yearly running costs of a fund, taken from its price. Includes the management fee."],
      ["Retrocession", "Payment from a product provider to the bank or manager. Belongs to the client unless validly waived."],
      ["Custodian bank", "The bank that holds the assets. With an external manager, the client pays both."],
      ["EAM", "External asset manager, like Safe Capital: manages assets held at a custodian bank."],
      ["bps", "Basis points: 100 bps = 1% per year."],
      ["Like for like", "Same holdings, same service scope, so only fees differ."],
      ["Stamp duty", "Swiss federal tax on securities trades, due at any Swiss bank."],
    ];
    for (let i = 0; i < 8; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.6 + col * 6.15, y = 1.6 + row * 1.25;
      s.addText(g[i][0], tb({ x, y, w: 5.9, h: 0.38, fontSize: 16, bold: true, color: C.accent1 }));
      s.addText(g[i][1], tb({ x, y: y + 0.4, w: 5.9, h: 0.75, fontSize: 14 }));
    }
    s.addNotes("Retrocession ownership follows Swiss case law; marked 'to verify' in the research register until checked against the primary source.");
  }

  await pres.writeFile({ fileName: OUT });
  if (process.env.APPLY_THEME_JS) {
    const { applyTheme } = require(process.env.APPLY_THEME_JS);
    await applyTheme(OUT, THEME);
  }
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
