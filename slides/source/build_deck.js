// Builds slides/PortfolioCostEngine_Executive_Deck.pptx
// All financial figures are SYNTHETIC demo values (see data notes in slides/README.md).
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const SKILL_THEME = process.env.APPLY_THEME_JS; // path to apply_theme.js (optional)
const OUT = path.resolve(__dirname, "..", "PortfolioCostEngine_Executive_Deck.pptx");
const IMG = (n) => path.join(__dirname, "img", n);

const THEME = {
  name: "Portfolio Cost Engine",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2433", lt1: "FFFFFF", dk2: "13233F", lt2: "F3F5F8",
    accent1: "0E7C72", accent2: "B7791F", accent3: "B42318", accent4: "3D5A80",
    accent5: "7FD1C7", accent6: "5B6678", hlink: "0E7C72", folHlink: "3D5A80",
  },
};
const H = THEME.colors; // hex, for hex-only options
const NAVY = H.dk2, TEAL = H.accent1, AMBER = H.accent2, RED = H.accent3, MUTED = H.accent6, MINT = H.accent5;

// ---------- icons ----------
async function icon(name, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(fa[name], { color: "#" + color, size: String(size) })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

function imgSize(file) {
  // read PNG width/height from IHDR
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.title = "Portfolio Cost Engine — briefing for Safe Capital";
  pres.author = "Portfolio Cost Engine project";
  pres.company = "Portfolio Cost Engine";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const W = 13.333;

  // ---------- layouts ----------
  pres.defineSlideMaster({
    title: "Dark title",
    background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.2, w: 10.5, h: 1.9, fontFace: THEME.headFontFace, fontSize: 44, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.3, w: 10.5, h: 1.2, fontSize: 20, color: C.accent5, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Content",
    background: { color: C.background1 },
    margin: [0.5, 0.6, 0.6, 0.6],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.95, fontFace: THEME.headFontFace, fontSize: 28, bold: true, color: C.text2, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { text: { text: "Portfolio Cost Engine · concept for Safe Capital · all figures are synthetic demo values", options: { x: 0.6, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: C.accent6, margin: 0 } } },
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
  });

  const tb = (o) => Object.assign({ isTextBox: true, margin: 0, fontSize: 16, color: C.text1, valign: "top" }, o);
  const content = (title, section) => {
    const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
    s.addText(title, { placeholder: "title" });
    return s;
  };
  const card = (s, x, y, w, h, fill, name) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || C.background2 }, line: { color: fill || C.background2 }, objectName: name });
  const circleIcon = async (s, x, y, d, iconName, bg, fg, name) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg }, objectName: name + " circle" });
    const pad = d * 0.25;
    s.addImage({ data: await icon(iconName, fg), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: name + " icon" });
  };
  const fitImage = (s, file, box, name) => {
    const { w, h } = imgSize(file);
    const r = Math.min(box.w / w, box.h / h);
    const iw = w * r, ih = h * r;
    s.addImage({ path: file, x: box.x + (box.w - iw) / 2, y: box.y + (box.h - ih) / 2, w: iw, h: ih, objectName: name, altText: name });
    return { x: box.x + (box.w - iw) / 2, y: box.y + (box.h - ih) / 2, w: iw, h: ih };
  };
  const frame = (s, r) => s.addShape(pres.shapes.RECTANGLE, { x: r.x, y: r.y, w: r.w, h: r.h, fill: { type: "none" }, line: { color: "D5DBE3", width: 1 }, objectName: "screenshot frame" });

  // =====================================================================
  // 1. Title
  pres.addSection({ title: "Why" });
  {
    const s = pres.addSlide({ masterName: "Dark title", sectionTitle: "Why" });
    s.addText("A free portfolio cost check, ready in minutes", { placeholder: "title" });
    s.addText("How the Portfolio Cost Engine would work for Safe Capital\nBriefing for Massimo · November 2026", { placeholder: "body" });
    s.addText("Concept and demo · every figure in this deck is synthetic", tb({ x: 0.8, y: 6.5, w: 8, h: 0.4, fontSize: 14, color: C.background1, transparency: 25 }));
    await circleIcon(s, 11.4, 0.8, 1.2, "FaSearchDollar", TEAL, "FFFFFF", "title");
    s.addNotes("Purpose of this deck: show, without technical detail, how a prospect's bank documents become a clear, evidence-backed cost picture and a fair comparison with Safe Capital. Everything shown is a concept with synthetic data; no real client, bank or saving is represented.");
  }

  // 2. Problem
  {
    const s = content("Clients rarely know what their portfolio really costs", "Why");
    card(s, 0.6, 1.6, 4.6, 4.9, C.text2, "quote card");
    s.addImage({ data: await icon("FaQuoteLeft", MINT), x: 0.95, y: 1.95, w: 0.55, h: 0.45, objectName: "quote mark" });
    s.addText("“My bank charges me about half a percent… I think. I’ve never added it all up.”", tb({ x: 0.95, y: 2.6, w: 3.95, h: 2.4, fontFace: THEME.headFontFace, fontSize: 22, italic: true, color: C.background1 }));
    s.addText("Typical prospect remark (illustrative, not a real quote)", tb({ x: 0.95, y: 5.6, w: 3.95, h: 0.6, fontSize: 12, color: C.accent5 }));
    s.addText("The costs are spread over many documents, and some are never shown as a charge", tb({ x: 5.7, y: 1.6, w: 7.0, h: 0.8, fontSize: 18, bold: true, color: C.text2 }));
    const items = [
      ["FaUniversity", "Bank fee statement", "management and custody debits"],
      ["FaFileContract", "Mandate & tariff", "rates, tiers, minimums, VAT"],
      ["FaExchangeAlt", "Trades & FX", "brokerage, third-party, FX margin"],
      ["FaChartPie", "Fund prices", "ongoing charges taken inside the price"],
      ["FaCubes", "Structured notes", "margins built into the issue price"],
      ["FaUmbrella", "Insurance wrappers", "policy fees on top of the funds"],
    ];
    for (let i = 0; i < items.length; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 5.7 + col * 3.55, y = 2.65 + row * 1.3;
      await circleIcon(s, x, y, 0.7, items[i][0], col ? "FBF1DE" : "E3F2F0", col ? AMBER : TEAL, items[i][1]);
      s.addText(items[i][1], tb({ x: x + 0.85, y: y + 0.02, w: 2.6, h: 0.35, fontSize: 16, bold: true }));
      s.addText(items[i][2], tb({ x: x + 0.85, y: y + 0.38, w: 2.6, h: 0.6, fontSize: 13, color: C.accent6 }));
    }
    s.addNotes("The core problem: no single bank document shows the all-in cost. A holdings statement does not show fees; fund costs are deducted inside the fund price and never appear as a debit; structured products and insurance wrappers add their own layers. Prospects therefore usually underestimate what they pay.");
  }

  // 3. Value proposition
  {
    const s = content("Our offer: an evidence-based cost check, free for the prospect", "Why");
    const cols = [
      ["FaFileUpload", "1. The client hands over documents", "Statements, fee reports and contracts from one or more banks: PDF, scans or Excel."],
      ["FaStopwatch", "2. A cost picture within minutes", "The engine reads the documents and builds a first draft of the annual all-in cost. An analyst checks it."],
      ["FaBalanceScale", "3. A fair comparison with Safe Capital", "Same holdings, Safe Capital's fee plus the custodian bank's fees, switching costs included. On one page."],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.8, 3.6, C.background2, "value card " + (i + 1));
      await circleIcon(s, x + 0.35, 1.95, 0.9, cols[i][0], TEAL, "FFFFFF", "value " + (i + 1));
      s.addText(cols[i][1], tb({ x: x + 0.35, y: 3.05, w: 3.1, h: 0.75, fontSize: 18, bold: true, color: C.text2 }));
      s.addText(cols[i][2], tb({ x: x + 0.35, y: 3.85, w: 3.1, h: 1.3, fontSize: 14, color: C.text1 }));
    }
    card(s, 0.6, 5.55, 12.1, 1.05, C.text2, "principle band");
    s.addText([
      { text: "Three rules we never break:  ", options: { bold: true, color: C.accent5 } },
      { text: "every number links to its source page · a missing cost is never counted as zero · no saving is claimed unless the service is comparable", options: { color: C.background1 } },
    ], tb({ x: 0.9, y: 5.62, w: 11.5, h: 0.9, fontSize: 16, valign: "middle" }));
    s.addNotes("'Minutes' is the design target for the automatic first draft, not a measured result yet. The analyst review adds time depending on how complete the documents are. The three rules are what make the result defensible in front of a client.");
  }

  // 4. Five steps
  pres.addSection({ title: "How it works" });
  {
    const s = content("Five steps from a pile of documents to a client-ready report", "How it works");
    const steps = [
      ["FaFileUpload", "Upload", "Files go into a private, encrypted workspace for this prospect"],
      ["FaSearch", "Read & check", "Positions, ISINs and fees are extracted, each tied to its page"],
      ["FaBook", "Find product costs", "Official fund documents give each fund's ongoing cost"],
      ["FaCalculator", "Calculate", "Annual cost per layer: proven, estimated, missing"],
      ["FaBalanceScale", "Compare & report", "Safe Capital scenario, payback, one-page report"],
    ];
    const w = 2.3, gap = 0.15;
    for (let i = 0; i < 5; i++) {
      const x = 0.6 + i * (w + gap);
      s.addShape(i === 0 ? pres.shapes.PENTAGON : pres.shapes.CHEVRON, { x, y: 1.75, w, h: 0.9, fill: { color: i % 2 ? C.accent1 : C.text2 }, line: { color: C.background1 }, objectName: "step arrow " + (i + 1) });
      s.addText(steps[i][1], tb({ x: x + (i ? 0.55 : 0.25), y: 1.75, w: w - 0.75, h: 0.9, fontSize: 15, bold: true, color: C.background1, valign: "middle" }));
      await circleIcon(s, x + w / 2 - 0.45, 3.0, 0.9, steps[i][0], "E3F2F0", TEAL, "step " + (i + 1));
      s.addText(steps[i][2], tb({ x: x + 0.1, y: 4.05, w: w - 0.2, h: 1.2, fontSize: 14, align: "center" }));
    }
    card(s, 0.6, 5.5, 12.1, 1.1, "FBF1DE", "human band");
    await circleIcon(s, 0.85, 5.68, 0.75, "FaUserCheck", AMBER, "FFFFFF", "human");
    s.addText("A Safe Capital analyst checks flagged values after step 2 and approves the report after step 5. Nothing reaches the client without a person signing it off.", tb({ x: 1.85, y: 5.55, w: 10.6, h: 1.0, fontSize: 16, valign: "middle" }));
    s.addNotes("Steps 2 to 4 are automatic. The software never sends anything to a client by itself; it prepares, a person decides.");
  }

  // 5. What the client brings
  {
    const s = content("What the client brings: three essentials, the rest makes it sharper", "How it works");
    card(s, 0.6, 1.6, 5.8, 5.0, "E3F2F0", "essentials");
    s.addText("Essential", tb({ x: 0.95, y: 1.85, w: 5, h: 0.5, fontSize: 20, bold: true, color: C.accent1 }));
    const ess = [
      ["FaListAlt", "Holdings / portfolio valuation", "per bank, recent date"],
      ["FaReceipt", "Fees charged in the last 12 months", "fee statement or annual cost report"],
      ["FaFileSignature", "Mandate or advisory contract", "the agreed rates and what they cover"],
    ];
    for (let i = 0; i < 3; i++) {
      const y = 2.6 + i * 1.25;
      await circleIcon(s, 0.95, y, 0.75, ess[i][0], TEAL, "FFFFFF", ess[i][1]);
      s.addText(ess[i][1], tb({ x: 1.9, y: y, w: 4.3, h: 0.4, fontSize: 16, bold: true }));
      s.addText(ess[i][2], tb({ x: 1.9, y: y + 0.4, w: 4.3, h: 0.4, fontSize: 14, color: C.accent6 }));
    }
    card(s, 6.8, 1.6, 5.9, 5.0, C.background2, "helpful");
    s.addText("Helpful", tb({ x: 7.15, y: 1.85, w: 5, h: 0.5, fontSize: 20, bold: true, color: C.text2 }));
    const help = [
      "Custody and trading tariff",
      "Transaction list (12 months)",
      "FX confirmations",
      "Rebate / retrocession disclosure",
      "Structured product termsheets",
      "Insurance policy, if funds sit in a wrapper",
    ];
    s.addText(help.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < help.length - 1 } })), tb({ x: 7.15, y: 2.5, w: 5.3, h: 2.9, fontSize: 16, paraSpaceAfter: 8 }));
    s.addText("Accepted: PDF, scans or phone photos, Excel, CSV. If something is missing, the engine drafts the request for the client.", tb({ x: 7.15, y: 5.5, w: 5.3, h: 0.9, fontSize: 14, color: C.accent6 }));
    s.addNotes("With only the three essentials we can already show bank-level costs and fund costs. The helpful documents turn estimates into proven figures, especially for trading, FX and rebates.");
  }

  // 6. Three layers
  {
    const s = content("Costs sit in three layers, and only the top one shows up as a debit", "How it works");
    const layers = [
      ["Bank & service layer", "Management or advisory fee, custody, brokerage, FX", "Visible: debited from the account", TEAL, "FFFFFF", 9.0],
      ["Product layer", "Fund ongoing charges, fund trading costs, structured note margins", "Hidden: taken inside the product price", AMBER, "FFFFFF", 7.4],
      ["Wrapper & one-off layer", "Insurance policy fees, entry or exit fees, transfer costs, stamp duty", "Occasional or contract-specific", NAVY, "FFFFFF", 5.8],
    ];
    for (let i = 0; i < 3; i++) {
      const [t, d, v, col, fg, w] = layers[i];
      const y = 1.7 + i * 1.6, x = 0.6 + (9.0 - w) / 2;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 1.35, rectRadius: 0.08, fill: { color: col }, line: { color: col }, objectName: t });
      s.addText([{ text: t, options: { bold: true, fontSize: 18, breakLine: true } }, { text: d, options: { fontSize: 14 } }], tb({ x: x + 0.3, y, w: w - 0.6, h: 1.35, color: fg, valign: "middle", align: "center" }));
      s.addText(v, tb({ x: 9.95, y: y + 0.2, w: 2.8, h: 1.0, fontSize: 15, bold: i === 1, color: i === 1 ? C.accent2 : C.text1, valign: "middle" }));
    }
    s.addText("The product layer is the one most clients never see, and often the largest after the management fee.", tb({ x: 0.6, y: 6.5, w: 12, h: 0.4, fontSize: 14, italic: true, color: C.accent6 }));
    s.addNotes("This is the central idea for clients. Fund costs are not wrong or hidden on purpose, they are simply deducted inside the fund price, so they never appear on a bank statement. The engine makes them visible using the official product documents.");
  }

  // 7. Statement reading
  {
    const s = content("Every number keeps a link to the page it came from", "How it works");
    const r = fitImage(s, IMG("statement.png"), { x: 0.6, y: 1.5, w: 7.3, h: 5.35 }, "Synthetic bank statement with highlighted values");
    frame(s, r);
    const pts = [
      ["1", "Security recognised", "The ISIN identifies the exact fund and share class.", TEAL],
      ["2", "Position value", "Used to turn a fund's cost percentage into francs.", TEAL],
      ["3", "Fee actually billed", "Proven cost: date, period and amount kept with the page reference.", AMBER],
    ];
    for (let i = 0; i < 3; i++) {
      const y = 1.7 + i * 1.45;
      s.addShape(pres.shapes.OVAL, { x: 8.3, y, w: 0.6, h: 0.6, fill: { color: pts[i][3] }, line: { color: pts[i][3] }, objectName: "badge " + pts[i][0] });
      s.addText(pts[i][0], tb({ x: 8.3, y, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" }));
      s.addText(pts[i][1], tb({ x: 9.1, y: y - 0.02, w: 3.6, h: 0.4, fontSize: 17, bold: true }));
      s.addText(pts[i][2], tb({ x: 9.1, y: y + 0.4, w: 3.6, h: 0.8, fontSize: 14, color: C.accent6 }));
    }
    s.addText("Example is a synthetic facsimile. Real bank layouts differ by bank and language; each new layout is tested before use.", tb({ x: 8.3, y: 6.0, w: 4.4, h: 0.8, fontSize: 12, italic: true, color: C.accent6 }));
    s.addNotes("Born-digital PDFs are read directly; scans and photos go through OCR (text recognition) and are flagged for a human check. Every extracted value remembers its file, page and position so anyone can click it and see the original.");
  }

  // 8. Upload screen
  pres.addSection({ title: "The screens" });
  {
    const s = content("Step 1 · Upload: the checklist shows at once what is still missing", "The screens");
    const r = fitImage(s, IMG("upload.png"), { x: 0.6, y: 1.45, w: 12.1, h: 5.4 }, "Upload screen mockup with document checklist");
    frame(s, r);
    s.addNotes("Mockup with synthetic data. Each file is recognised automatically (valuation, fee statement, contract, scan). The checklist on the right tells the analyst which documents to ask for before the meeting ends.");
  }

  // 9. Review screen
  {
    const s = content("Step 2 · Review: the analyst confirms values next to the original page", "The screens");
    const r = fitImage(s, IMG("review.png"), { x: 0.6, y: 1.45, w: 12.1, h: 5.4 }, "Review screen mockup with source document and extracted facts");
    frame(s, r);
    s.addNotes("Left: the original document with the value highlighted. Right: what the engine extracted. Uncertain values (here, VAT not stated) are flagged and need one click to confirm, correct, or turn into a question for the client. Every correction is logged with who, when and why.");
  }

  // 10. KID
  {
    const s = content("Fund costs come from the official KID of the exact share class", "The screens");
    const flow = [
      ["FaBarcode", "ISIN on the statement", "ZZDEMO000011"],
      ["FaLayerGroup", "Exact share class", "Global Equity Fund A, R-acc"],
      ["FaBook", "Official KID / factsheet", "issuer's document, dated"],
      ["FaPercent", "Ongoing cost", "1.08% per year"],
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.1;
      card(s, x, 1.65, 2.7, 2.1, C.background2, "kid step " + (i + 1));
      await circleIcon(s, x + 0.95, 1.85, 0.8, flow[i][0], TEAL, "FFFFFF", flow[i][1]);
      s.addText(flow[i][1], tb({ x: x + 0.15, y: 2.75, w: 2.4, h: 0.4, fontSize: 15, bold: true, align: "center" }));
      s.addText(flow[i][2], tb({ x: x + 0.15, y: 3.15, w: 2.4, h: 0.45, fontSize: 13, color: C.accent6, align: "center" }));
      if (i < 3) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.75, y: 2.5, w: 0.3, h: 0.4, fill: { color: "C5CCD8" }, line: { color: "C5CCD8" }, objectName: "kid arrow " + (i + 1) });
    }
    card(s, 0.6, 4.15, 7.4, 2.05, "FBF1DE", "worked example");
    s.addText("Worked example (synthetic)", tb({ x: 0.9, y: 4.35, w: 6.8, h: 0.4, fontSize: 16, bold: true, color: C.accent2 }));
    s.addText([
      { text: "Ongoing charges 1.08%, of which management fee 0.75%", options: { bullet: true, breakLine: true } },
      { text: "The 0.75% is already inside the 1.08%: counted once", options: { bullet: true, breakLine: true } },
      { text: "CHF 800'000 × 1.08% = CHF 8'640 per year, marked estimated", options: { bullet: true, bold: true } },
    ], tb({ x: 0.9, y: 4.85, w: 6.9, h: 1.6, fontSize: 15, paraSpaceAfter: 6 }));
    s.addText([
      { text: "Why the exact class matters", options: { bold: true, breakLine: true, color: C.text2 } },
      { text: "The same fund can have several share classes with different costs. If the class can't be confirmed, the engine marks the cost as missing instead of guessing.", options: {} },
    ], tb({ x: 8.4, y: 4.2, w: 4.3, h: 2.4, fontSize: 15 }));
    s.addNotes("KID = Key Information Document, the official cost sheet funds must publish. Only the client's ISIN is looked up, never their name or amounts. The KID's example amounts are illustrations, not what the client actually paid, so we use the percentage applied to the client's real position value and label it 'estimated'.");
  }

  // 11. Double counting & missing
  {
    const s = content("Each cost is counted once, and a missing cost is never treated as zero", "The screens");
    card(s, 0.6, 1.6, 5.9, 4.4, C.background2, "counted once");
    await circleIcon(s, 0.9, 1.85, 0.75, "FaLink", TEAL, "FFFFFF", "counted once");
    s.addText("Counted once", tb({ x: 1.85, y: 1.95, w: 4.4, h: 0.5, fontSize: 20, bold: true, color: C.text2 }));
    const once = [
      "A fund's management fee is part of its ongoing charges",
      "An all-in fee may already include custody",
      "A KID's total is the sum of its parts, not an extra",
      "A rebate counts only if it was actually paid back",
    ];
    s.addText(once.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < once.length - 1 } })), tb({ x: 0.9, y: 2.85, w: 5.4, h: 3.5, fontSize: 16, paraSpaceAfter: 10 }));

    card(s, 6.8, 1.6, 5.9, 4.4, "FCE8E6", "missing");
    await circleIcon(s, 7.1, 1.85, 0.75, "FaExclamationTriangle", RED, "FFFFFF", "missing");
    s.addText("Missing ≠ zero", tb({ x: 8.05, y: 1.95, w: 4.4, h: 0.5, fontSize: 20, bold: true, color: C.accent3 }));
    s.addText("Gaps are shown in red, and the engine drafts the request:", tb({ x: 7.1, y: 2.85, w: 5.3, h: 0.5, fontSize: 15 }));
    s.addShape(pres.shapes.RECTANGLE, { x: 7.1, y: 3.45, w: 5.3, h: 2.25, fill: { color: "FFFFFF" }, line: { color: "E8B4AE", width: 1 }, objectName: "request letter" });
    s.addText([
      { text: "Please ask Banca Beta for:", options: { bold: true, breakLine: true } },
      { text: "Rebate (retrocession) disclosure 2026", options: { bullet: true, breakLine: true } },
      { text: "FX confirmations, last 12 months", options: { bullet: true, breakLine: true } },
      { text: "Why: without them, FX and rebates stay estimated, so the saving shown is a range, not a firm figure.", options: { italic: true, color: C.accent6 } },
    ], tb({ x: 7.35, y: 3.6, w: 4.85, h: 2.0, fontSize: 14, paraSpaceAfter: 4 }));
    s.addNotes("These two rules protect Safe Capital's credibility. Adding a fund's management fee on top of its ongoing charges would overstate the client's cost; treating an unknown FX margin as zero would understate it. Both would make the comparison unfair.");
  }

  // 12. Costs dashboard
  {
    const s = content("Step 3 · Costs: the full picture, split into proven and estimated", "The screens");
    const r = fitImage(s, IMG("costs.png"), { x: 0.6, y: 1.45, w: 12.1, h: 5.4 }, "Cost dashboard mockup");
    frame(s, r);
    s.addNotes("Synthetic prospect with CHF 4 million across two banks. Known annual cost CHF 38'100 (0.95%). CHF 25'100 is proven by billed fees; CHF 13'000 is estimated from official fund documents and tariffs; two items remain unquantified and are shown, not hidden. Clicking any line opens the source page.");
  }

  // 13. Comparison chart
  pres.addSection({ title: "The result" });
  {
    const s = content("Step 4 · Compare: same holdings first, a new portfolio kept apart", "The result");
    s.addChart(pres.charts.BAR, [
      { name: "Advisory, custodian bank & trading fees", labels: ["Today", "Safe Capital, same holdings", "Safe Capital, new portfolio"], values: [26300, 20740, 20740] },
      { name: "Product costs (funds, notes)", labels: ["Today", "Safe Capital, same holdings", "Safe Capital, new portfolio"], values: [11800, 11800, 3000] },
    ], {
      x: 0.6, y: 1.55, w: 7.6, h: 5.2, barDir: "col", barGrouping: "stacked", barGapWidthPct: 60,
      chartColors: [TEAL, AMBER], showValue: true, dataLabelPosition: "ctr", dataLabelColor: "FFFFFF", dataLabelFontSize: 12, dataLabelFormatCode: "#,##0",
      dataLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", titleFontFace: "+mn-lt",
      catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, valAxisLabelFormatCode: "#,##0",
      valGridLine: { color: "E2E6EC", size: 0.5 }, catGridLine: { style: "none" },
      showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: MUTED,
      showTitle: true, title: "Annual cost, CHF (synthetic)", titleFontSize: 14, titleColor: MUTED,
    });
    const rows = [
      ["Today", "CHF 38'100", "0.95%", C.text1],
      ["Same holdings", "CHF 32'540", "0.81%", C.accent1],
      ["New portfolio", "CHF 23'740", "0.59%", C.accent2],
    ];
    for (let i = 0; i < 3; i++) {
      const y = 1.7 + i * 1.05;
      s.addText(rows[i][0], tb({ x: 8.6, y, w: 2.0, h: 0.45, fontSize: 15, color: C.accent6 }));
      s.addText(rows[i][1], tb({ x: 8.6, y: y + 0.38, w: 2.4, h: 0.5, fontSize: 22, bold: true, color: rows[i][3] }));
      s.addText(rows[i][2], tb({ x: 11.2, y: y + 0.38, w: 1.5, h: 0.5, fontSize: 18, color: C.accent6, align: "right" }));
    }
    card(s, 8.6, 4.95, 4.1, 1.75, "FBF1DE", "caveat");
    s.addText("Safe Capital columns include the custodian bank's fees: assets stay at a bank, Safe Capital manages them. The new-portfolio case changes products and risk, so it is not a like-for-like saving.", tb({ x: 8.8, y: 5.05, w: 3.75, h: 1.55, fontSize: 13, valign: "middle" }));
    s.addNotes("Safe Capital is an external asset manager: the client's assets stay at a custodian bank, so every Safe Capital scenario adds Safe Capital's fee AND the custodian bank's custody, trading and FX fees. VAT on fees depends on the client's domicile. Same-holdings comparison: identical positions, Safe Capital's advisory fee plus the custodian's terms. This is the fair headline. The new-portfolio case (e.g. cheaper share classes or ETFs) can show a larger difference but needs a suitability review and must never be presented as a pure fee saving. Figures are synthetic.");
  }

  // 14. First year & payback
  {
    const s = content("Year one: switching costs are included, so the payback is honest", "The result");
    const tbl = [
      ["", "Same holdings", "New portfolio"],
      ["Annual difference", "CHF 5'560", "CHF 14'360"],
      ["One-off switching costs", "– CHF 8'000", "– CHF 8'000"],
      ["Net result in year one", "– CHF 2'440", "+ CHF 6'360"],
      ["Payback", "about 17 months", "about 7 months"],
    ];
    const hdr = { bold: true, color: C.background1, fill: { color: C.text2 }, fontSize: 15 };
    s.addTable(tbl.map((r, ri) => r.map((c, ci) => ({
      text: c,
      options: ri === 0 ? Object.assign({ align: ci ? "right" : "left" }, hdr) : {
        fontSize: 16, align: ci ? "right" : "left", bold: ri === 3 || ci === 0,
        color: ri === 3 && ci === 1 ? C.accent3 : ri === 3 && ci === 2 ? C.accent1 : C.text1,
        fill: { color: ri % 2 ? C.background1 : C.background2 },
      },
    }))), { x: 0.6, y: 1.7, w: 7.6, colW: [3.2, 2.2, 2.2], rowH: 0.65, border: { type: "solid", color: "E2E6EC", pt: 0.75 }, margin: [0, 0.15, 0, 0.15], valign: "middle" });
    await circleIcon(s, 8.75, 1.75, 0.8, "FaHandshake", TEAL, "FFFFFF", "honest");
    s.addText("Why show a negative year one?", tb({ x: 8.75, y: 2.75, w: 3.95, h: 0.5, fontSize: 18, bold: true, color: C.text2 }));
    s.addText("Because a client will find out anyway. Showing the switching cost and the payback period up front makes the recommendation credible, and the saving from year two onward speaks for itself.", tb({ x: 8.75, y: 3.3, w: 3.95, h: 2.2, fontSize: 15 }));
    s.addText("Switching costs (transfer, exit, taxes) come from the banks' quotes; here they are a synthetic placeholder. VAT on fees depends on the client's domicile and is applied per client.", tb({ x: 0.6, y: 5.25, w: 7.6, h: 0.8, fontSize: 13, italic: true, color: C.accent6 }));
    s.addNotes("Payback = one-off switching cost ÷ annual difference × 12. Same holdings: 8'000 ÷ 5'560 × 12 ≈ 17 months. New portfolio: 8'000 ÷ 14'360 × 12 ≈ 7 months. All synthetic. Safe Capital's own margin on the prospect is computed on a separate internal screen and never appears in client material.");
  }

  // 15. Client report
  {
    const s = content("Step 5 · Report: one page for the client, the margin stays internal", "The result");
    const r = fitImage(s, IMG("report.png"), { x: 0.6, y: 1.45, w: 7.9, h: 5.4 }, "Client report mockup");
    frame(s, r);
    const pts = [
      ["FaCheckCircle", TEAL, "On the page", "Today vs Safe Capital, the breakdown, what is proven and what is estimated"],
      ["FaExclamationTriangle", AMBER, "Also on the page", "What is still missing, in plain words"],
      ["FaEyeSlash", RED, "Never on the page", "Safe Capital's internal margin and profitability view"],
      ["FaSignature", NAVY, "Before it leaves", "An approver signs it off; the version is frozen"],
    ];
    for (let i = 0; i < 4; i++) {
      const y = 1.6 + i * 1.3;
      await circleIcon(s, 8.85, y, 0.65, pts[i][0], pts[i][1], "FFFFFF", pts[i][2]);
      s.addText(pts[i][2], tb({ x: 9.7, y: y - 0.02, w: 3.0, h: 0.35, fontSize: 15, bold: true }));
      s.addText(pts[i][3], tb({ x: 9.7, y: y + 0.35, w: 3.0, h: 0.85, fontSize: 13, color: C.accent6 }));
    }
    s.addNotes("The report is a PDF generated from approved numbers only. It states that it is not investment advice. The internal profitability screen uses separate permissions.");
  }

  // 16. Where it runs
  pres.addSection({ title: "Data & privacy" });
  {
    const s = content("Where it runs: on Safe Capital's own infrastructure by default", "Data & privacy");
    const opts = [
      ["FaLaptop", "A · In the office", "One secured computer or server at Safe Capital. Simplest for a pilot: documents never leave the building.", "Recommended for the pilot", TEAL],
      ["FaServer", "B · Swiss private hosting", "A dedicated server with a Swiss provider under a data-processing contract. For several users and offices.", "Option for production", NAVY],
      ["FaCloud", "C · External AI services", "Only for hard-to-read pages, only with explicit approval, and only on redacted excerpts.", "Off by default", AMBER],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.6, 3.8, 3.75, C.background2, opts[i][1]);
      await circleIcon(s, x + 0.3, 1.85, 0.8, opts[i][0], opts[i][4], "FFFFFF", opts[i][1]);
      s.addText(opts[i][1], tb({ x: x + 0.3, y: 2.8, w: 3.3, h: 0.45, fontSize: 18, bold: true, color: C.text2 }));
      s.addText(opts[i][2], tb({ x: x + 0.3, y: 3.3, w: 3.3, h: 1.4, fontSize: 14 }));
      s.addText(opts[i][3], tb({ x: x + 0.3, y: 4.8, w: 3.3, h: 0.4, fontSize: 14, bold: true, color: opts[i][4] }));
    }
    card(s, 0.6, 5.6, 12.1, 1.0, "E3F2F0", "what leaves");
    s.addText([
      { text: "The only thing that goes to the internet: ", options: { bold: true, color: C.accent1 } },
      { text: "public fund codes (ISINs) to fetch official product documents. No names, no amounts, no statements.", options: {} },
    ], tb({ x: 0.9, y: 5.6, w: 11.5, h: 1.0, fontSize: 16, valign: "middle" }));
    s.addNotes("Hosting in Switzerland helps but does not by itself make the processing compliant; contracts, access control and retention matter as much. The final choice should be made with Safe Capital's compliance officer.");
  }

  // 17. Privacy
  {
    const s = content("Client files stay confidential from upload to deletion", "Data & privacy");
    const tiles = [
      ["FaFileSignature", "Client consent", "The client signs a short authorisation before any upload"],
      ["FaFilter", "Only what is needed", "Names can be blacked out; costs need no identity"],
      ["FaLock", "Encrypted", "In storage and in transit; separate space per prospect"],
      ["FaUserShield", "Named access", "Personal logins, two-factor, every view logged"],
      ["FaRobot", "No public AI on raw files", "Unless Safe Capital explicitly approves a provider"],
      ["FaTrashAlt", "Deleted on schedule", "Retention period agreed up front, then erased"],
    ];
    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.6 + col * 4.1, y = 1.7 + row * 1.9;
      card(s, x, y, 3.8, 1.6, C.background2, tiles[i][1]);
      await circleIcon(s, x + 0.25, y + 0.3, 0.7, tiles[i][0], TEAL, "FFFFFF", tiles[i][1]);
      s.addText(tiles[i][1], tb({ x: x + 1.1, y: y + 0.3, w: 2.55, h: 0.45, fontSize: 16, bold: true }));
      s.addText(tiles[i][2], tb({ x: x + 1.1, y: y + 0.78, w: 2.55, h: 1.0, fontSize: 13, color: C.accent6 }));
    }
    s.addText("Swiss Federal Act on Data Protection (revised, in force since 1 September 2023) applies. Bank-client confidentiality and outsourcing rules must be checked by Safe Capital's counsel; this slide is not legal advice.", tb({ x: 0.6, y: 5.55, w: 12.1, h: 0.7, fontSize: 13, italic: true, color: C.accent6 }));
    s.addNotes("Pseudonymised data can still be personal data. A data-protection impact assessment may be needed; that decision belongs to Safe Capital with its counsel.");
  }

  // 18. Human vs machine
  pres.addSection({ title: "Next steps" });
  {
    const s = content("The engine reads and calculates; people make the judgements", "Next steps");
    card(s, 0.6, 1.6, 5.9, 4.3, "E3F2F0", "automatic");
    await circleIcon(s, 0.9, 1.85, 0.75, "FaCogs", TEAL, "FFFFFF", "automatic");
    s.addText("Automatic", tb({ x: 1.85, y: 1.95, w: 4, h: 0.5, fontSize: 20, bold: true, color: C.accent1 }));
    const auto = ["Recognise each document and bank", "Extract positions, ISINs and fees", "Fetch official fund cost documents", "Calculate costs in CHF and %", "Flag gaps and draft the client request", "Produce the report draft"];
    s.addText(auto.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < auto.length - 1 } })), tb({ x: 0.9, y: 2.8, w: 5.4, h: 3.6, fontSize: 16, paraSpaceAfter: 8 }));
    card(s, 6.8, 1.6, 5.9, 4.3, "FBF1DE", "human");
    await circleIcon(s, 7.1, 1.85, 0.75, "FaUserCheck", AMBER, "FFFFFF", "human");
    s.addText("A person at Safe Capital", tb({ x: 8.05, y: 1.95, w: 4.4, h: 0.5, fontSize: 20, bold: true, color: C.accent2 }));
    const hum = ["Enter Safe Capital's and the custodian's fees (once)", "Confirm values the engine flags", "Decide if a comparison is like-for-like", "Approve and sign the client report", "Present it and talk to the client"];
    s.addText(hum.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < hum.length - 1 } })), tb({ x: 7.1, y: 2.8, w: 5.4, h: 3.6, fontSize: 16, paraSpaceAfter: 8 }));
    s.addNotes("Manual configuration is mostly one-time: Safe Capital's tariff, custodian terms and the report template. Per prospect, the human effort depends on document quality.");
  }

  // 19. Phases
  {
    const s = content("Delivery in phases, with a real pilot case before any production use", "Next steps");
    const ph = [
      ["Now", "Demo", "Working concept on synthetic documents; this deck"],
      ["Phase 1", "Pilot", "1–3 anonymised real prospects; measure accuracy and time"],
      ["Phase 2", "Harden", "More bank layouts, security review, user logins"],
      ["Phase 3", "Production", "Live at Safe Capital after compliance sign-off"],
    ];
    s.addShape(pres.shapes.LINE, { x: 1.3, y: 2.55, w: 9.3, h: 0, line: { color: "C5CCD8", width: 3 }, objectName: "timeline" });
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.1;
      s.addShape(pres.shapes.OVAL, { x: x + 0.35, y: 2.2, w: 0.7, h: 0.7, fill: { color: i === 0 ? TEAL : NAVY }, line: { color: "FFFFFF", width: 2 }, objectName: "milestone " + (i + 1) });
      s.addText(ph[i][0], tb({ x, y: 1.6, w: 2.8, h: 0.4, fontSize: 14, bold: true, color: i === 0 ? C.accent1 : C.accent6 }));
      card(s, x, 3.2, 2.8, 2.0, C.background2, "phase " + (i + 1));
      s.addText(ph[i][1], tb({ x: x + 0.25, y: 3.4, w: 2.3, h: 0.5, fontSize: 20, bold: true, color: C.text2 }));
      s.addText(ph[i][2], tb({ x: x + 0.25, y: 4.0, w: 2.3, h: 1.6, fontSize: 15 }));
    }
    s.addText("Durations are set after the pilot, once we know how many bank formats Safe Capital's prospects bring.", tb({ x: 0.6, y: 5.6, w: 12.1, h: 0.5, fontSize: 13, italic: true, color: C.accent6 }));
    s.addNotes("We deliberately do not promise dates before seeing real documents: the number of different bank layouts drives the effort.");
  }

  // 20. Decisions
  {
    const s = content("Six decisions we need from Safe Capital to start the pilot", "Next steps");
    const dec = [
      ["One anonymised real case", "holdings, 12 months of fees, the contract"],
      ["Safe Capital's pricing", "advisory fee, custodian partner and their tariffs"],
      ["Comparison policy", "same holdings only, or also a new-portfolio case"],
      ["Where it runs and who sees it", "office machine or Swiss hosting; named users"],
      ["Client consent and retention", "wording of the authorisation; how long we keep files"],
      ["Legal entity on client material", "which Safe Capital entity and licence to cite"],
    ];
    for (let i = 0; i < 6; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.6 + col * 6.15, y = 1.65 + row * 1.6;
      card(s, x, y, 5.95, 1.35, C.background2, "decision " + (i + 1));
      s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.3, w: 0.75, h: 0.75, fill: { color: NAVY }, line: { color: NAVY }, objectName: "decision number " + (i + 1) });
      s.addText(String(i + 1), tb({ x: x + 0.25, y: y + 0.3, w: 0.75, h: 0.75, fontSize: 20, bold: true, color: C.background1, align: "center", valign: "middle" }));
      s.addText(dec[i][0], tb({ x: x + 1.2, y: y + 0.22, w: 4.55, h: 0.45, fontSize: 17, bold: true, color: C.text2 }));
      s.addText(dec[i][1], tb({ x: x + 1.2, y: y + 0.68, w: 4.55, h: 0.5, fontSize: 14, color: C.accent6 }));
    }
    s.addNotes("Decision 6: the public commercial register lists Safe Capital Management SA and Safe Capital Holding SA in Lugano. Safe Capital's website states FINMA authorisation with OSIF supervision, but this has not yet been checked in the FINMA register; Safe Capital should confirm exactly what to cite before anything goes to a client.");
  }

  // 21. Close
  {
    const s = pres.addSlide({ masterName: "Dark title", sectionTitle: "Next steps" });
    s.addText("Next step: run one anonymised real case", { placeholder: "title" });
    s.addText("No source, no verified figure · Missing is never zero · No comparable service, no savings claim", { placeholder: "body" });
    await circleIcon(s, 11.4, 0.8, 1.2, "FaFlagCheckered", TEAL, "FFFFFF", "close");
    s.addNotes("Ask: one anonymised prospect file and Safe Capital's fee schedule. With those we can run the pilot and replace every synthetic figure in this deck with a real, source-linked one.");
  }

  await pres.writeFile({ fileName: OUT });
  if (SKILL_THEME) {
    const { applyTheme } = require(SKILL_THEME);
    await applyTheme(OUT, THEME);
  }
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
