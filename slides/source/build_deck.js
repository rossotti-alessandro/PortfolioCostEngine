// Builds the FeeLens deck for Safe Capital (v3), in Italian or English from one source.
//   DECK_LANG=it node build_deck.js   -> ../FeeLens_Presentazione_IT.pptx
//   DECK_LANG=en node build_deck.js   -> ../FeeLens_Deck_EN.pptx
// Client figures are SYNTHETIC (demo prospect P-1042 from the app engine on branch claude/project-thread-steqtm).
// Bank and fund documents are REAL public documents, quoted as printed (see slides/README.md for URLs).
// Logos are cropped from those documents and used only to identify the source of each document.
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const NAME = process.env.PRODUCT_NAME || "FeeLens";
const LANG = (process.env.DECK_LANG || "it").toLowerCase() === "en" ? "en" : "it";
const T = (it, en) => (LANG === "it" ? it : en);
const OUT = path.resolve(__dirname, "..", LANG === "it" ? `${NAME}_Presentazione_IT.pptx` : `${NAME}_Deck_EN.pptx`);
const IMG = (n) => path.join(__dirname, "img", n);
const REAL = (n) => path.join(__dirname, "realpages", n);
const LOGO = (n) => path.join(__dirname, "logos", n);

const THEME = {
  name: NAME, headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "14202E", lt1: "FFFFFF", dk2: "0F2A4A", lt2: "F7F6F2", accent1: "0F766E", accent2: "B45309", accent3: "B42318", accent4: "1E7A46", accent5: "2F5D8A", accent6: "5B6676", hlink: "0F766E", folHlink: "2F5D8A" },
};
const X = {
  text: "14202E", navy: "0F2A4A", teal: "0F766E", tealSoft: "E3F2F0", amber: "B45309", amberSoft: "FDF3E2",
  red: "B42318", redSoft: "FDECEA", green: "1E7A46", greenSoft: "E7F4EC", muted: "5B6676", bg: "F7F6F2",
  mutedSurface: "EFEDE7", border: "DEDAD1", l2: "2F5D8A", l3: "6B8FB3", l9: "A3A3A3", white: "FFFFFF", infoSoft: "E6ECF4", paleNavy: "9FB3C8",
};

async function icon(name, color, size = 256) {
  const Cmp = lu[name] || lu.LuCircle;
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Cmp, { color: "#" + color, size: String(size), strokeWidth: 1.75 }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
function imgSize(file) { const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; }

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = T(`${NAME} · presentazione per Safe Capital`, `${NAME} · briefing for Safe Capital`);
  pres.author = `${NAME} project`; pres.company = NAME;
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "Dark", background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.7, w: 11.5, h: 1.5, fontFace: THEME.headFontFace, fontSize: 60, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.4, w: 11.5, h: 1.2, fontSize: 26, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Content", background: { color: C.background1 }, margin: [0.5, 0.6, 0.6, 0.6],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.62, w: 12.1, h: 0.75, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.text2, valign: "top", align: "left", margin: 0 }, text: "" } },
      { text: { text: T(`${NAME} · per Safe Capital · dati cliente sintetici, documenti pubblici reali`, `${NAME} · for Safe Capital · client figures synthetic, public documents real`), options: { x: 0.6, y: 7.02, w: 10, h: 0.28, fontSize: 10, color: C.accent6, margin: 0 } } },
    ],
    slideNumber: { x: 12.2, y: 7.02, w: 0.5, h: 0.28, fontSize: 10, color: C.accent6, align: "right" },
  });

  const tb = (o) => Object.assign({ isTextBox: true, margin: 0, fontSize: 16, color: C.text1, valign: "top" }, o);
  const content = (kicker, title, section) => {
    const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
    s.addText(kicker.toUpperCase(), tb({ x: 0.6, y: 0.35, w: 10, h: 0.25, fontSize: 11, bold: true, color: C.accent1, charSpacing: 2 }));
    s.addText(title, { placeholder: "title" });
    return s;
  };
  const card = (s, x, y, w, h, fill, name, line) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: fill || X.bg }, line: { color: line || fill || X.bg, width: line ? 0.75 : 0 }, objectName: name });
  const iconIn = async (s, x, y, d, name, bg, fg, objName) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: d, h: d, rectRadius: 0.08, fill: { color: bg }, line: { color: bg }, objectName: objName + " tile" });
    const p = d * 0.22;
    s.addImage({ data: await icon(name, fg), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, objectName: objName + " icon" });
  };
  const KIND = { obs: [X.greenSoft, X.green], con: [X.infoSoft, X.navy], est: [X.amberSoft, X.amber], unk: [X.redSoft, X.red], na: [X.mutedSurface, X.muted], pass: [X.greenSoft, X.green], fail: [X.redSoft, X.red], info: [X.infoSoft, X.navy], acc: [X.tealSoft, X.teal] };
  const chip = (s, x, y, text, kind, w, h = 0.3, fs = 11) => {
    const [bg, fg] = KIND[kind];
    const ww = w || Math.max(0.9, 0.09 * text.length + 0.35);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: ww, h, rectRadius: h / 2, fill: { color: bg }, line: { color: bg }, objectName: "chip " + text });
    s.addText(text, tb({ x, y, w: ww, h, fontSize: fs, bold: true, color: fg, align: "center", valign: "middle" }));
    return ww;
  };
  const fitImage = (s, file, box, name, frame = true, align = "center") => {
    const { w, h } = imgSize(file);
    const r = Math.min(box.w / w, box.h / h);
    const iw = w * r, ih = h * r;
    const x = align === "left" ? box.x : box.x + (box.w - iw) / 2;
    const rr = { x, y: box.y + (box.h - ih) / 2, w: iw, h: ih };
    s.addImage({ path: file, ...rr, objectName: name, altText: name });
    if (frame) s.addShape(pres.shapes.RECTANGLE, { ...rr, fill: { type: "none" }, line: { color: X.border, width: 0.75 }, objectName: name + " frame" });
    return rr;
  };
  const numBadge = (s, x, y, n, d = 0.32, fill = X.navy) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: "badge " + n });
    s.addText(String(n), tb({ x, y, w: d, h: d, fontSize: 12, bold: true, color: C.background1, align: "center", valign: "middle" }));
  };
  const note = (s, text, y = 6.5) => s.addText(text, tb({ x: 0.6, y, w: 12.1, h: 0.4, fontSize: 12, color: C.accent6 }));
  const fieldRows = (s, x, y, w, rows, rh = 0.46) => {
    // rows: [n, label, value, page, kind, kindLabel]
    rows.forEach((r, j) => {
      const yy = y + j * rh;
      if (j) s.addShape(pres.shapes.LINE, { x, y: yy - 0.03, w, h: 0, line: { color: X.border, width: 0.5 }, objectName: "fr" + j });
      numBadge(s, x, yy + (rh - 0.3) / 2 - 0.02, r[0], 0.3);
      s.addText(r[1], tb({ x: x + 0.45, y: yy, w: w * 0.36, h: rh - 0.06, fontSize: 12, color: C.accent6, valign: "middle" }));
      s.addText(r[2], tb({ x: x + 0.45 + w * 0.36, y: yy, w: w * 0.3, h: rh - 0.06, fontSize: 13, bold: true, valign: "middle" }));
      if (r[4]) chip(s, x + w - 1.95, yy + (rh - 0.28) / 2 - 0.02, r[5], r[4], 1.45, 0.28, 10);
      s.addText(r[3], tb({ x: x + w - 0.45, y: yy, w: 0.45, h: rh - 0.06, fontSize: 11, color: C.accent1, align: "right", valign: "middle" }));
    });
  };
  const logo = (s, file, x, y, h, name) => {
    const { w, h: ih } = imgSize(LOGO(file));
    s.addImage({ path: LOGO(file), x, y, w: (w / ih) * h, h, objectName: name + " logo", altText: name + " logo" });
    return (w / ih) * h;
  };
  const SEC = { why: T("Perché", "Why"), how: T("Come funziona", "How it works"), docs: T("Documenti reali", "Real documents"), check: T("Controlli", "Checks"), result: T("Risultato", "Result"), go: T("Avvio", "Getting started"), deep: T("Approfondimenti", "Deep dive") };

  // ===================================================================== WHY
  pres.addSection({ title: SEC.why });
  {
    const s = pres.addSlide({ masterName: "Dark", sectionTitle: SEC.why });
    s.addText(NAME, { placeholder: "title" });
    s.addText(T("Quanto costa davvero un portafoglio. In pochi minuti, con le prove.", "See what a portfolio really costs. In minutes, with proof."), { placeholder: "body" });
    s.addText(T("Presentazione per Massimo · Safe Capital, Lugano · novembre 2026", "Briefing for Massimo · Safe Capital, Lugano · November 2026"), tb({ x: 0.8, y: 4.4, w: 11, h: 0.4, fontSize: 16, color: X.paleNavy }));
    const steps = [["LuFileUp", T("Carica", "Upload")], ["LuListChecks", T("Verifica", "Verify")], ["LuScale", T("Confronta", "Compare")]];
    for (let i = 0; i < 3; i++) {
      const x = 0.8 + i * 2.3;
      s.addImage({ data: await icon(steps[i][0], "5FA8A0"), x, y: 5.35, w: 0.42, h: 0.42, objectName: "cover icon " + i });
      s.addText(steps[i][1], tb({ x: x + 0.55, y: 5.35, w: 1.6, h: 0.42, fontSize: 18, bold: true, color: C.background1, valign: "middle" }));
    }
    s.addText(T("Concetto e demo funzionante · dati cliente sintetici · documenti bancari pubblici reali", "Concept and working demo · synthetic client figures · real public bank documents"), tb({ x: 0.8, y: 6.6, w: 11, h: 0.35, fontSize: 12, color: X.paleNavy }));
    s.addNotes(T(`${NAME} legge i documenti bancari e dei prodotti di un potenziale cliente, trova ogni costo con la sua fonte e lo confronta in modo corretto con l'offerta di Safe Capital. Le cifre del cliente sono sintetiche (prospect demo P-1042); i documenti delle banche e dei fondi mostrati sono documenti pubblici reali.`, `${NAME} reads a prospect's bank and product documents, finds every cost with its source and compares it fairly with Safe Capital's offer. Client figures are synthetic (demo prospect P-1042); the bank and fund documents shown are real public documents.`));
  }
  {
    const s = content(T("Il problema", "The problem"), T("Più di un terzo dei costi non compare tra gli addebiti", "More than a third of the cost never shows up as a debit"), SEC.why);
    s.addText([{ text: "CHF 61'450", options: { fontSize: 60, bold: true, color: C.accent1, breakLine: true } }, { text: T("costo annuo reale, almeno", "real yearly cost, at least"), options: { fontSize: 18, color: C.accent6 } }], tb({ x: 0.6, y: 1.7, w: 6, h: 1.5 }));
    s.addText([{ text: "CHF 40'160", options: { fontSize: 40, bold: true, color: C.text2, breakLine: true } }, { text: T("quello che la banca indica come addebitato", "what the bank lists as charged"), options: { fontSize: 16, color: C.accent6 } }], tb({ x: 0.6, y: 3.45, w: 6, h: 1.2 }));
    const bx = 0.6, by = 5.0, bw = 6.0, bh = 0.55, tot = 61450;
    const vis = (40160 / tot) * bw;
    s.addShape(pres.shapes.RECTANGLE, { x: bx, y: by, w: vis, h: bh, fill: { color: X.navy }, line: { color: X.navy }, objectName: "bar visible" });
    s.addShape(pres.shapes.RECTANGLE, { x: bx + vis, y: by, w: bw - vis, h: bh, fill: { color: X.amber }, line: { color: X.amber }, objectName: "bar hidden" });
    s.addText(T("addebitato 65%", "debited 65%"), tb({ x: bx + 0.12, y: by, w: vis - 0.2, h: bh, fontSize: 13, bold: true, color: C.background1, valign: "middle" }));
    s.addText(T("nascosto 35%", "hidden 35%"), tb({ x: bx + vis + 0.1, y: by, w: bw - vis - 0.15, h: bh, fontSize: 13, bold: true, color: C.background1, valign: "middle" }));
    s.addText(T("CHF 21'290 sono costi dei fondi presi dentro il prezzo. E i costi propri della Banca Beta sono ancora sconosciuti.", "CHF 21'290 are fund costs taken inside the price. And Bank Beta's own fees are still unknown."), tb({ x: 0.6, y: 5.7, w: 6, h: 0.7, fontSize: 14, color: C.accent6 }));
    const items = [
      ["LuLandmark", T("Avvisi di addebito", "Fee advices"), T("gestione, custodia", "management, custody"), false],
      ["LuFileSignature", T("Contratti e tariffe", "Contracts and tariffs"), T("aliquote, scaglioni, minimi", "rates, tiers, minimums"), false],
      ["LuArrowLeftRight", T("Operazioni e cambi", "Trades and FX"), T("commissioni, margini FX", "commissions, FX margins"), false],
      ["LuPieChart", T("Prezzi dei fondi", "Fund prices"), T("costi correnti nel NAV", "ongoing charges in NAV"), true],
      ["LuBoxes", T("Prodotti strutturati", "Structured products"), T("margine dell'emittente", "issuer margin"), true],
      ["LuUmbrella", T("Polizze assicurative", "Insurance wrappers"), T("costi della polizza", "policy charges"), true],
    ];
    s.addText(T("Dove si trovano i costi", "Where the costs sit"), tb({ x: 7.2, y: 1.75, w: 5.5, h: 0.4, fontSize: 16, bold: true }));
    for (let i = 0; i < 6; i++) {
      const y = 2.3 + i * 0.68;
      await iconIn(s, 7.2, y, 0.5, items[i][0], items[i][3] ? X.amberSoft : X.bg, items[i][3] ? X.amber : X.navy, items[i][1]);
      s.addText(items[i][1], tb({ x: 7.9, y: y + 0.08, w: 2.6, h: 0.35, fontSize: 15, bold: true }));
      s.addText(items[i][2], tb({ x: 10.4, y: y + 0.1, w: 2.3, h: 0.35, fontSize: 12, color: C.accent6 }));
    }
    s.addText(T("In arancione: mai visibili come addebito.", "In orange: never visible as a debit."), tb({ x: 7.2, y: 6.45, w: 5.5, h: 0.3, fontSize: 12, color: C.accent2 }));
    s.addNotes(T("Cifre sintetiche dal motore demo (prospect P-1042, CHF 4,3 milioni su due banche). Costo noto CHF 61'449.60 (143 bps): addebitato 40'159.60, nei prezzi dei fondi 21'290. Il cliente vede solo gli addebiti; i costi dei fondi sono dentro il prezzo e non compaiono mai.", "Synthetic figures from the demo engine (prospect P-1042, CHF 4.3m at two banks). Known cost CHF 61'449.60 (143 bps): debited 40'159.60, inside fund prices 21'290. Clients see debits only; fund costs sit inside the price and never appear."));
  }
  {
    const s = content(T(`Cosa fa ${NAME}`, `What ${NAME} does`), T("Tre passi, un risultato che si può dimostrare", "Three steps, a result you can prove"), SEC.why);
    const cols = [
      ["LuFileUp", T("1 · Carica", "1 · Upload"), T("Estratti, rendiconti e contratti di qualsiasi banca: PDF, scansioni, Excel.", "Statements, cost reports and contracts from any bank: PDF, scans, Excel."), T("Documenti classificati per banca, tipo e periodo", "Documents sorted by bank, type and period")],
      ["LuListChecks", T("2 · Verifica", "2 · Verify"), T("Ogni costo viene estratto con la sua pagina, controllato con gli altri documenti ed etichettato.", "Every cost is extracted with its page, checked against other documents and labelled."), T("Registro dei costi con fonte e stato", "Cost ledger with source and status")],
      ["LuScale", T("3 · Confronta", "3 · Compare"), T("Stessi titoli con Safe Capital e la sua banca depositaria, costi di cambio inclusi.", "Same holdings with Safe Capital and its custodian bank, switching costs included."), T("Report di una pagina per il cliente", "One-page client report")],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.85, 3.95, X.bg, "step card " + i);
      await iconIn(s, x + 0.3, 1.95, 0.7, cols[i][0], X.white, X.teal, cols[i][1]);
      s.addText(cols[i][1], tb({ x: x + 0.3, y: 2.85, w: 3.3, h: 0.45, fontSize: 22, bold: true, color: C.text2 }));
      s.addText(cols[i][2], tb({ x: x + 0.3, y: 3.4, w: 3.3, h: 1.1, fontSize: 15 }));
      s.addShape(pres.shapes.LINE, { x: x + 0.3, y: 4.6, w: 3.25, h: 0, line: { color: X.border, width: 0.75 }, objectName: "sep " + i });
      s.addText([{ text: "OUTPUT  ", options: { bold: true, color: C.accent1, fontSize: 11, charSpacing: 1 } }, { text: cols[i][3], options: { bold: true, fontSize: 13 } }], tb({ x: x + 0.3, y: 4.7, w: 3.3, h: 0.75 }));
    }
    const rules = [T("Nessuna fonte, nessuna cifra verificata", "No source, no verified figure"), T("Mancante non vuol dire zero", "Missing is never zero"), T("Nessun servizio comparabile, nessun risparmio dichiarato", "No comparable service, no savings claim")];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      s.addImage({ data: await icon("LuShieldCheck", X.teal), x, y: 5.95, w: 0.4, h: 0.4, objectName: "rule " + i });
      s.addText(rules[i], tb({ x: x + 0.55, y: 5.9, w: 3.3, h: 0.55, fontSize: 15, bold: true, color: C.text2, valign: "middle" }));
    }
    s.addNotes(T("Le tre regole rendono il risultato difendibile davanti al cliente e alla compliance.", "The three rules make the result defensible in front of a client and compliance."));
  }

  // ===================================================================== HOW
  pres.addSection({ title: SEC.how });
  {
    const s = content(T("Il processo", "The process"), T("Sei passi: chi fa cosa e cosa esce da ogni passo", "Six steps: who does what, and what each step produces"), SEC.how);
    const steps = [
      ["LuFileSignature", T("Consenso e documenti", "Consent and documents"), "info", T("Cliente", "Client"), T("Autorizzazione firmata, file caricati", "Signed authorisation, files uploaded"), "~10 min"],
      ["LuSearch", T("Lettura automatica", "Automatic reading"), "acc", T("Automatico", "Automatic"), T("Posizioni e costi, ognuno con la sua pagina", "Positions and fees, each with its page"), T("secondi per pagina", "seconds per page")],
      ["LuListChecks", T("Controlli incrociati", "Cross-checks"), "acc", T("Automatico", "Automatic"), T("Esito per ogni controllo, lacune elencate", "Result per check, gaps listed"), T("secondi", "seconds")],
      ["LuUserCheck", T("Verifica dei valori incerti", "Confirm uncertain values"), "est", T("Analista", "Analyst"), T("Valori confermati o domande al cliente", "Values confirmed or questions to the client"), T("pochi minuti", "a few minutes")],
      ["LuCalculator", T("Costi e scenari", "Costs and scenarios"), "acc", T("Automatico", "Automatic"), T("Costo attuale, proposta, rientro", "Current cost, proposal, payback"), T("secondi", "seconds")],
      ["LuPenLine", T("Approvazione e report", "Approve and report"), "est", T("Analista", "Analyst"), T("Report cliente + lettera di richiesta", "Client report + request letter"), T("minuti", "minutes")],
    ];
    const w = 1.9, gap = 0.14;
    for (let i = 0; i < 6; i++) {
      const x = 0.6 + i * (w + gap);
      const strong = steps[i][2] === "acc";
      card(s, x, 1.65, w, 4.55, strong ? X.tealSoft : X.bg, "proc " + i);
      numBadge(s, x + 0.2, 1.85, i + 1, 0.4, strong ? X.teal : X.navy);
      s.addImage({ data: await icon(steps[i][0], strong ? X.teal : X.navy), x: x + w - 0.62, y: 1.85, w: 0.42, h: 0.42, objectName: "proc icon " + i });
      s.addText(steps[i][1], tb({ x: x + 0.2, y: 2.45, w: w - 0.35, h: 0.8, fontSize: 15, bold: true, color: C.text2 }));
      chip(s, x + 0.2, 3.3, steps[i][3], steps[i][2], w - 0.4, 0.3, 11);
      s.addText("OUTPUT", tb({ x: x + 0.2, y: 3.85, w: w - 0.35, h: 0.25, fontSize: 10, bold: true, color: C.accent1, charSpacing: 1 }));
      s.addText(steps[i][4], tb({ x: x + 0.2, y: 4.1, w: w - 0.35, h: 1.3, fontSize: 13 }));
      s.addImage({ data: await icon("LuTimer", X.muted), x: x + 0.2, y: 5.67, w: 0.25, h: 0.25, objectName: "clock " + i });
      s.addText(steps[i][5], tb({ x: x + 0.5, y: 5.63, w: w - 0.6, h: 0.32, fontSize: 12, color: C.accent6, valign: "middle" }));
      if (i < 5) s.addShape(pres.shapes.LINE, { x: x + w - 0.02, y: 2.05, w: gap + 0.04, h: 0, line: { color: X.muted, width: 1.25, endArrowType: "triangle" }, objectName: "pa " + i });
    }
    note(s, T("Verde: automatico. Grigio: una persona del cliente o di Safe Capital. Nulla arriva al cliente senza approvazione. I tempi sono obiettivi di progetto, da misurare nel pilota.", "Green: automatic. Grey: a person at the client or Safe Capital. Nothing reaches a client without approval. Times are design targets, to be measured in the pilot."), 6.35);
    s.addNotes(T("Se mancano documenti, al passo 3 FeeLens prepara una lettera alla banca; quando arrivano, l'analisi si aggiorna.", "If documents are missing, step 3 drafts a letter to the bank; when they arrive the analysis updates."));
  }
  {
    const s = content(T("Requisiti", "Requirements"), T("Cosa serve per partire", "What is needed to start"), SEC.how);
    const cols = [
      ["LuUser", T("Dal cliente, per ogni caso", "From the client, per case"), X.navy, [T("Estratto patrimoniale per banca", "Statement of assets per bank"), T("Rendiconto costi annuale oppure 12 mesi di avvisi di addebito", "Annual cost report, or 12 months of fee advices"), T("Contratto di mandato, se esiste", "Mandate contract, if any"), T("Consenso firmato", "Signed consent")]],
      ["LuLandmark", T("Da Safe Capital, una volta", "From Safe Capital, once"), X.amber, [T("Tariffa di consulenza o gestione", "Advisory or management tariff"), T("Banca depositaria partner e sua tariffa", "Partner custodian bank and its tariff"), T("Testo del consenso e durata di conservazione", "Consent wording and retention period"), T("Chi approva i report", "Who approves reports")]],
      ["LuServer", T("Tecnici", "Technical"), X.teal, [T("Un PC sicuro in ufficio (pilota) o un server in Svizzera", "One secured office PC (pilot) or a Swiss server"), T("Accessi nominativi con due fattori", "Named logins with two-factor"), T("Nessun servizio AI esterno sui file grezzi", "No external AI on raw files"), T("Internet solo per scaricare i KID pubblici", "Internet only to fetch public KIDs")]],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.85, 4.6, X.bg, cols[i][1]);
      await iconIn(s, x + 0.3, 1.9, 0.6, cols[i][0], X.white, cols[i][2], cols[i][1]);
      s.addText(cols[i][1], tb({ x: x + 1.05, y: 1.9, w: 2.7, h: 0.6, fontSize: 16, bold: true, color: C.text2, valign: "middle" }));
      for (let j = 0; j < 4; j++) {
        const y = 2.85 + j * 0.82;
        s.addImage({ data: await icon("LuCheckCircle2", cols[i][2]), x: x + 0.3, y: y + 0.02, w: 0.3, h: 0.3, objectName: "req " + i + j });
        s.addText(cols[i][3][j], tb({ x: x + 0.75, y, w: 2.9, h: 0.75, fontSize: 14 }));
      }
    }
    note(s, T("Le commissioni di gestione delle banche (UBS, Julius Baer) non sono pubbliche: arrivano solo dal contratto del cliente.", "Banks' mandate fees (UBS, Julius Baer) are not public: they only come from the client's contract."));
    s.addNotes(T("Configurazione una tantum: tariffa Safe Capital, banca depositaria, modello di report. Per ogni caso lo sforzo dipende dalla qualità dei documenti.", "One-time setup: Safe Capital tariff, custodian, report template. Per case, effort depends on document quality."));
  }
  {
    const s = content(T("Le fonti", "The sources"), T("Cosa pubblicano le banche, e cosa ha solo il cliente", "What banks publish, and what only the client has"), SEC.how);
    const logos = [["juliusbaer_doc.png", "Julius Baer"], ["zkb.png", "Zürcher Kantonalbank"], ["raiffeisen.png", "Raiffeisen"], ["ishares.png", "iShares by BlackRock"]];
    let lx = 0.6;
    for (const [f, n] of logos) { const w = logo(s, f, lx, 1.6, 0.42, n); lx += w + 0.55; }
    chip(s, lx, 1.66, T("Documenti pubblici usati", "Public documents used"), "obs", 2.4);
    const head = [T("DOCUMENTO", "DOCUMENT"), T("PUBBLICO?", "PUBLIC?"), T("COSA ABBIAMO TROVATO", "WHAT WE FOUND"), T("DA DOVE LO PRENDE FEELENS", "WHERE FEELENS GETS IT")];
    const rows = [
      [T("Tariffario della banca", "Bank price list"), [T("Sì", "Yes"), "obs"], T("Julius Baer Europe, ZKB, Raiffeisen Locarno. UBS ne pubblica uno ma blocca il download automatico", "Julius Baer Europe, ZKB, Raiffeisen Locarno. UBS publishes one but blocks automated download"), T("Sito della banca; data ed entità controllate", "Bank website; date and entity checked")],
      [T("KID del fondo", "Fund KID"), [T("Sì", "Yes"), "obs"], T("Ogni classe di quote, es. iShares Core MSCI World", "Every share class, e.g. iShares Core MSCI World"), T("Fonte ufficiale, per ISIN", "Official source, by ISIN")],
      [T("Commissione di gestione", "Mandate fee"), [T("No", "No"), "unk"], T("Julius Baer: «non fa parte di questo documento»; UBS Manage: nessuna tariffa", "Julius Baer: “not part of this document”; UBS Manage: no rates"), T("Contratto o avvisi del cliente", "Client's contract or fee advices")],
      [T("Estratto patrimoniale", "Statement of assets"), [T("No", "No"), "unk"], T("Nessun esempio pubblico da UBS o Julius Baer", "No public specimen from UBS or Julius Baer"), T("Il cliente", "The client")],
      [T("Rendiconto costi annuale", "Annual cost report"), [T("Su richiesta", "On request"), "est"], T("UBS: dettagli dei costi «su richiesta» al consulente", "UBS: cost details “on request” from the advisor"), T("Lettera alla banca preparata da FeeLens", "Letter to the bank drafted by FeeLens")],
    ];
    const hdr = { bold: true, color: C.accent6, fill: { color: X.mutedSurface }, fontSize: 11 };
    s.addTable([head.map((h) => ({ text: h, options: hdr }))].concat(rows.map((r) => [
      { text: r[0], options: { bold: true, fontSize: 13 } },
      { text: r[1][0], options: { bold: true, fontSize: 12, align: "center", color: KIND[r[1][1]][1], fill: { color: KIND[r[1][1]][0] } } },
      { text: r[2], options: { fontSize: 12 } },
      { text: r[3], options: { fontSize: 12, color: C.accent6 } },
    ])), { x: 0.6, y: 2.3, w: 12.1, colW: [2.4, 1.4, 5.0, 3.3], rowH: 0.7, border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0.04, 0.12, 0.04, 0.12], valign: "middle" });
    note(s, T("Loghi riprodotti dai documenti pubblici solo per identificarne la fonte; nessuna partnership o approvazione è implicata.", "Logos are reproduced from the public documents only to identify their source; no partnership or endorsement is implied."));
    s.addNotes(T("Verificato il 6 novembre 2026. Pagina FIDLEG di UBS Switzerland AG: i dettagli dei costi sono forniti su richiesta. Il tariffario UBS esiste ma il sito rifiuta lo scaricamento automatico: va scaricato a mano.", "Checked on 6 November 2026. UBS Switzerland AG FinSA page: cost details are provided on request. The UBS price list exists but the site refuses automated download: download it manually."));
  }

  // ===================================================================== REAL DOCUMENTS
  pres.addSection({ title: SEC.docs });
  const realDoc = async (o) => {
    const s = content(o.kicker, o.title, SEC.docs);
    logo(s, o.logo, 0.6, 1.62, 0.5, o.issuer);
    s.addText(o.docTitle, tb({ x: 0.6, y: 2.3, w: 4.2, h: 0.65, fontSize: 16, bold: true, color: C.text2 }));
    s.addText(o.meta, tb({ x: 0.6, y: 2.95, w: 4.2, h: 0.75, fontSize: 12, color: C.accent6 }));
    if (o.left) await o.left(s);
    const ch = o.cropH || 2.25;
    s.addText(T("PAGINA ORIGINALE, INGRANDITA", "ORIGINAL PAGE, ZOOMED IN"), tb({ x: 5.2, y: 1.62, w: 6, h: 0.25, fontSize: 10, bold: true, color: C.accent6, charSpacing: 1 }));
    fitImage(s, REAL(o.crop), { x: 5.2, y: 1.92, w: 7.5, h: ch }, o.title + " crop", true, "left");
    s.addText(T("DATI ESTRATTI", "EXTRACTED DATA"), tb({ x: 5.2, y: 2.08 + ch, w: 6, h: 0.25, fontSize: 10, bold: true, color: C.accent6, charSpacing: 1 }));
    fieldRows(s, 5.2, 2.4 + ch, 7.5, o.fields, o.rh || 0.44);
    s.addNotes(o.notes);
    return s;
  };
  await realDoc({
    kicker: T("Documento reale · tariffario", "Real document · price list"), title: T("Julius Baer: dal tariffario ai dati, campo per campo", "Julius Baer: from price list to data, field by field"),
    logo: "juliusbaer_doc.png", issuer: "Julius Baer", docTitle: "Schedule of prices and services, banking and custody",
    meta: T("Bank Julius Baer Europe S.A., Lussemburgo · PU00505EN · giugno 2025 · inglese · 9 pagine", "Bank Julius Baer Europe S.A., Luxembourg · PU00505EN · June 2025 · English · 9 pages"),
    crop: "jb_custody.png", cropH: 2.0,
    left: async (s) => {
      s.addText(T("COPERTINA, P.1", "COVER, P.1"), tb({ x: 0.6, y: 3.8, w: 4, h: 0.25, fontSize: 10, bold: true, color: C.accent6, charSpacing: 1 }));
      fitImage(s, REAL("jb_booked.png"), { x: 0.6, y: 4.1, w: 4.2, h: 0.45 }, "booked crop", true, "left");
      card(s, 0.6, 4.75, 4.2, 1.45, X.redSoft, "reject");
      s.addImage({ data: await icon("LuAlertTriangle", X.red), x: 0.8, y: 4.95, w: 0.4, h: 0.4, objectName: "warn" });
      s.addText(T("Valido solo per conti in Lussemburgo. Per un cliente con conto in Svizzera FeeLens scarta questa tariffa.", "Valid only for Luxembourg-booked accounts. For a Swiss-booked client FeeLens rejects this tariff."), tb({ x: 1.35, y: 4.9, w: 3.3, h: 1.2, fontSize: 13, bold: true, color: C.accent3 }));
    },
    fields: [
      [1, T("Custodia fino a 5 mln", "Custody up to 5m"), "0.300% p.a.", "p.3", "con", T("Contrattuale", "Contractual")],
      [2, T("Custodia 5–10 mln", "Custody 5–10m"), "0.250% p.a.", "p.3", "con", T("Contrattuale", "Contractual")],
      [3, T("Custodia 10–20 mln", "Custody 10–20m"), "0.200% p.a.", "p.3", "con", T("Contrattuale", "Contractual")],
      [4, T("Custodia oltre 20 mln", "Custody over 20m"), "0.150% p.a.", "p.3", "con", T("Contrattuale", "Contractual")],
      [5, T("Minimo per trimestre", "Minimum per quarter"), "EUR 360", "p.3", "con", T("Contrattuale", "Contractual")],
    ],
    notes: T("Fonte: juliusbaer.com/fileadmin/legal/schedule-of-prices-and-services-banking-and-custody.pdf, scaricato il 6.11.2026. I riquadri verdi sono i valori che FeeLens estrae, con la loro posizione sulla pagina. Lo stesso documento dà anche FX spot fino al 3% (p.6) e trasferimento EUR 100 per posizione (p.8), usati per stimare i costi di cambio banca.", "Source: juliusbaer.com/fileadmin/legal/schedule-of-prices-and-services-banking-and-custody.pdf, downloaded 6.11.2026. Green boxes are the values FeeLens extracts, with their position on the page. The same document also gives FX spot up to 3% (p.6) and transfer EUR 100 per position (p.8), used to estimate switching costs."),
  });
  await realDoc({
    kicker: T("Documento reale · KID del fondo", "Real document · fund KID"), title: T("Un KID ufficiale: i costi del fondo in cinque campi", "An official KID: the fund's costs in five fields"),
    logo: "ishares.png", issuer: "iShares", docTitle: "iShares Core MSCI World UCITS ETF · Basisinformationsblatt",
    meta: T("BlackRock Asset Management Ireland · IE00B4L5Y983 · USD Acc · 3 settembre 2026 · tedesco · pagina 3 di 3", "BlackRock Asset Management Ireland · IE00B4L5Y983 · USD Acc · 3 September 2026 · German · page 3 of 3"),
    crop: "kid_costs.png", cropH: 2.3, rh: 0.42,
    left: async (s) => {
      card(s, 0.6, 3.85, 4.2, 2.35, X.tealSoft, "calc");
      s.addText([
        { text: T("Come si usa", "How it is used"), options: { bold: true, fontSize: 15, color: C.accent1, breakLine: true } },
        { text: T("Costo stimato = costi correnti × valore della posizione", "Estimated cost = ongoing costs × position value"), options: { fontSize: 13, bold: true, breakLine: true } },
        { text: " ", options: { fontSize: 6, breakLine: true } },
        { text: T("Esempio: CHF 500'000 × 0,20% = CHF 1'000 all'anno, etichettato «Stimato».", "Example: CHF 500'000 × 0.20% = CHF 1'000 a year, labelled “Estimated”."), options: { fontSize: 13 } },
      ], tb({ x: 0.85, y: 4.0, w: 3.8, h: 2.1 }));
    },
    fields: [
      [1, T("Costi totali, 1 anno, su USD 10'000", "Total cost, 1 year, on USD 10'000"), "USD 20", "p.3", "na", T("Illustrazione", "Illustration")],
      [2, T("Costi di ingresso", "Entry charge"), T("nessuno", "none"), "p.3", "con", T("Contrattuale", "Contractual")],
      [3, T("Costi di uscita", "Exit charge"), T("nessuno", "none"), "p.3", "con", T("Contrattuale", "Contractual")],
      [4, T("Costi correnti", "Ongoing costs"), "0.20% p.a.", "p.3", "est", T("Stimato", "Estimated")],
      [5, T("Costi di transazione", "Transaction costs"), "0.00% p.a.", "p.3", "est", T("Stimato", "Estimated")],
    ],
    notes: T("Fonte: KID PRIIPs per IE00B4L5Y983, creato il 3.9.2026 (copia su fsl.lv1871.de). Il KID è pubblico per ogni fondo e FeeLens lo recupera tramite ISIN: l'unica informazione che va online è il codice ISIN pubblico.", "Source: PRIIPs KID for IE00B4L5Y983, created 3.9.2026 (copy at fsl.lv1871.de). KIDs are public for every fund and FeeLens fetches them by ISIN: the only thing that goes online is the public ISIN."),
  });
  {
    const s = content(T("Documenti reali · tariffari svizzeri", "Real documents · Swiss price lists"), T("Due banche svizzere, la stessa voce: la custodia", "Two Swiss banks, the same line: custody"), SEC.docs);
    const two = [
      ["zkb.png", "Zürcher Kantonalbank", T("Preisübersicht Anlagegeschäft · prezzi da ottobre 2025 · tedesco", "Preisübersicht Anlagegeschäft · prices from October 2025 · German"), "zkb_custody.png", [[1, T("Titoli custoditi in Svizzera", "Securities held in Switzerland"), T("0,30% p.a., min CHF 3/mese", "0.30% p.a., min CHF 3/month"), "p.1"], [2, T("Titoli custoditi all'estero", "Securities held abroad"), T("0,40% p.a., min CHF 4/mese", "0.40% p.a., min CHF 4/month"), "p.1"]]],
      ["raiffeisen.png", "Raiffeisenbank Locarno", T("Dienstleistungspreise Anlegen · dal 1° gennaio 2025 · tedesco", "Dienstleistungspreise Anlegen · from 1 January 2025 · German"), "raif_custody.png", [[1, T("Deposito titoli, tassa base", "Securities account, base fee"), "0.25% p.a.", "p.2"], [2, T("Minimo per trimestre", "Minimum per quarter"), "CHF 12.50", "p.2"]]],
    ];
    for (let i = 0; i < 2; i++) {
      const x = 0.6 + i * 6.15, w = 5.95, d = two[i];
      logo(s, d[0], x, 1.62, 0.45, d[1]);
      s.addText(d[2], tb({ x, y: 2.15, w, h: 0.35, fontSize: 12, color: C.accent6 }));
      fitImage(s, REAL(d[3]), { x, y: 2.55, w, h: 2.3 }, d[1] + " crop", true, "left");
      d[4].forEach((r, j) => {
        const y = 5.0 + j * 0.55;
        if (j) s.addShape(pres.shapes.LINE, { x, y: y - 0.04, w, h: 0, line: { color: X.border, width: 0.5 }, objectName: "l" + i + j });
        numBadge(s, x, y + 0.08, r[0], 0.3);
        s.addText(r[1], tb({ x: x + 0.45, y, w: 2.5, h: 0.48, fontSize: 12, color: C.accent6, valign: "middle" }));
        s.addText(r[2], tb({ x: x + 2.95, y, w: 2.5, h: 0.48, fontSize: 13, bold: true, valign: "middle" }));
        s.addText(r[3], tb({ x: x + w - 0.45, y, w: 0.45, h: 0.48, fontSize: 11, color: C.accent1, align: "right", valign: "middle" }));
      });
    }
    note(s, T("Esempio: CHF 1 mln di titoli esteri presso ZKB = CHF 4'000 all'anno di sola custodia, più IVA per clienti domiciliati in Svizzera.", "Example: CHF 1m of foreign securities at ZKB = CHF 4'000 a year in custody alone, plus VAT for Swiss-domiciled clients."));
    s.addNotes(T("Fonti: zkb.ch (Preisübersicht Anlagegeschäft, ottobre 2025) e raiffeisen.ch (Raiffeisenbank Locarno, gennaio 2025), scaricati il 6.11.2026. Mostrati come esempio di documento pubblico; nessun confronto tra banche è implicato.", "Sources: zkb.ch (Preisübersicht Anlagegeschäft, October 2025) and raiffeisen.ch (Raiffeisenbank Locarno, January 2025), downloaded 6.11.2026. Shown as examples of public documents; no comparison between banks is implied."));
  }

  // ===================================================================== CHECKS
  pres.addSection({ title: SEC.check });
  {
    const s = content(T("Dati", "Data"), T("Ogni valore estratto diventa uno di cinque tipi di dato", "Every extracted value becomes one of five kinds of data"), SEC.check);
    const ents = [
      ["LuLayers", T("Posizioni", "Positions"), [T("ISIN e classe", "ISIN and class"), T("Quantità, prezzo, valore", "Quantity, price, value"), T("Valuta, data", "Currency, date")]],
      ["LuReceipt", T("Costi addebitati", "Fees charged"), [T("Tipo e periodo", "Type and period"), T("Base e aliquota", "Base and rate"), T("Importo, IVA", "Amount, VAT")]],
      ["LuFileSignature", T("Condizioni", "Contract terms"), [T("Aliquote e scaglioni", "Rates and tiers"), T("Minimi", "Minimums"), T("Entità e validità", "Entity and validity")]],
      ["LuPieChart", T("Costi dei prodotti", "Product costs"), [T("Costi correnti", "Ongoing costs"), T("Costi di transazione", "Transaction costs"), T("Data del KID", "KID date")]],
      ["LuSearch", T("Prova", "Evidence"), [T("File e pagina", "File and page"), T("Riquadro sulla pagina", "Box on the page"), T("Chi l'ha confermato", "Who confirmed it")]],
    ];
    for (let i = 0; i < 5; i++) {
      const x = 0.6 + i * 2.46;
      card(s, x, 1.65, 2.25, 3.4, i === 4 ? X.tealSoft : X.bg, ents[i][1]);
      await iconIn(s, x + 0.25, 1.9, 0.6, ents[i][0], X.white, i === 4 ? X.teal : X.navy, ents[i][1]);
      s.addText(ents[i][1], tb({ x: x + 0.25, y: 2.7, w: 1.9, h: 0.45, fontSize: 17, bold: true, color: C.text2 }));
      s.addText(ents[i][2].map((t, j) => ({ text: t, options: { breakLine: j < 2 } })), tb({ x: x + 0.25, y: 3.25, w: 1.9, h: 1.6, fontSize: 13, paraSpaceAfter: 8 }));
    }
    s.addText(T("OGNI COSTO HA UNO STATO", "EVERY COST HAS A STATUS"), tb({ x: 0.6, y: 5.3, w: 6, h: 0.25, fontSize: 11, bold: true, color: C.accent6, charSpacing: 1 }));
    const st = [["obs", T("Osservato", "Observed")], ["con", T("Contrattuale", "Contractual")], ["est", T("Stimato", "Estimated")], ["na", T("Non è un costo pagato", "Not a paid cost")], ["unk", T("Non determinato", "Not determined")]];
    let cx = 0.6;
    st.forEach(([k, l]) => { cx += chip(s, cx, 5.65, l, k, null, 0.36, 12) + 0.15; });
    s.addText(T("I primi tre entrano nel totale. «Non determinato» non vale mai zero: per questo il risparmio è sempre «almeno».", "The first three count in the total. “Not determined” is never zero: that is why savings are always “at least”."), tb({ x: 0.6, y: 6.15, w: 12.1, h: 0.5, fontSize: 14 }));
    s.addNotes(T("Il modello dati è lo stesso per tutte le banche: per questo lo strumento è generico.", "The data model is the same for every bank: that is what makes the tool generic."));
  }
  {
    const s = content(T("Controlli incrociati", "Reconciliation"), T("Prima di fidarsi di un numero, i documenti vengono confrontati", "Before trusting a number, documents are checked against each other"), SEC.check);
    const groups = [
      ["LuCalculator", T("I numeri tornano?", "Do the numbers add up?"), [["pass", T("Posizioni Alpha = totale stampato, 3'200'000", "Alpha positions = printed total, 3'200'000")], ["pass", T("Posizioni Beta = totale stampato, 1'100'000", "Beta positions = printed total, 1'100'000")], ["pass", T("Tutto valutato al 30.09.2026", "All valued on 30.09.2026")]]],
      ["LuFileSignature", T("Addebitato = concordato?", "Billed = agreed?"), [["pass", T("Consulenza = 3,2 mln × 0,80%", "Advisory = 3.2m × 0.80%")], ["pass", T("Custodia = 3,0 mln × 0,20%", "Custody = 3.0m × 0.20%")], ["pass", T("Addebiti trimestrali × 4 = rendiconto, contati una volta", "Quarterly debits × 4 = annual report, counted once")]]],
      ["LuShieldCheck", T("La fonte vale per questo cliente?", "Is the source valid for this client?"), [["fail", T("Tariffa di un'entità lussemburghese per un conto svizzero: scartata", "Tariff of a Luxembourg entity for a Swiss account: rejected")], ["pass", T("Costi KID entro il 2,6% della stima della banca", "KID costs within 2.6% of the bank's estimate")], ["info", T("Retrocessioni CHF 3'900: già nei costi dei fondi, non sommate", "Retrocessions CHF 3'900: already in fund costs, not added")]]],
    ];
    const lab = { pass: T("Ok", "Pass"), fail: T("Scartato", "Rejected"), info: T("Nota", "Note") };
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.85, 4.6, X.bg, groups[i][1]);
      await iconIn(s, x + 0.3, 1.9, 0.6, groups[i][0], X.white, X.navy, groups[i][1]);
      s.addText(groups[i][1], tb({ x: x + 0.3, y: 2.65, w: 3.3, h: 0.75, fontSize: 18, bold: true, color: C.text2 }));
      groups[i][2].forEach(([k, t], j) => {
        const y = 3.55 + j * 0.85;
        chip(s, x + 0.3, y, lab[k], k, 1.05);
        s.addText(t, tb({ x: x + 1.5, y: y - 0.05, w: 2.2, h: 0.8, fontSize: 13 }));
      });
    }
    note(s, T("Le differenze restano visibili all'analista: non vengono mai forzate a tornare. Cifre del prospect sintetico P-1042.", "Mismatches stay visible to the analyst: never forced to agree. Figures from synthetic prospect P-1042."));
    s.addNotes(T("Sono i controlli effettivamente eseguiti dal motore demo sui documenti sintetici.", "These are the checks the demo engine actually ran on the synthetic documents."));
  }
  {
    const s = content(T("Lo schermo", "The screen"), T("Ogni numero si apre: formula, controlli e pagina di origine", "Every number opens up: formula, checks and source page"), SEC.check);
    fitImage(s, IMG("v2_drill.png"), { x: 0.6, y: 1.55, w: 12.1, h: 5.3 }, "drill-down mockup");
    s.addNotes(T("Mockup dell'app (in inglese) con i dati sintetici del motore. Selezionando una riga si vede l'importo, lo stato, la pagina sorgente evidenziata, la formula e i controlli superati.", "App mockup with the engine's synthetic data. Selecting a line shows amount, status, highlighted source page, formula and the checks passed."));
  }

  // ===================================================================== RESULT
  pres.addSection({ title: SEC.result });
  {
    const s = content(T("Il risultato", "The result"), T("Stessi titoli, ogni costo di Safe Capital incluso", "Same holdings, every Safe Capital cost included"), SEC.result);
    const labels = [T("Oggi", "Today"), T("Safe Capital, stessi titoli", "Safe Capital, same holdings"), T("Safe Capital, nuovi fondi", "Safe Capital, new funds")];
    s.addChart(pres.charts.BAR, [
      { name: T("Gestione / consulenza", "Management / advisory"), labels, values: [25600, 25500, 25500] },
      { name: T("Custodia, operazioni, cambi", "Custody, trading, FX"), labels, values: [11390, 5140, 5140] },
      { name: T("IVA", "VAT"), labels, values: [2559.6, 2389.5, 2389.5] },
      { name: T("Costi dei fondi nel prezzo", "Fund costs inside prices"), labels, values: [21290, 21290, 13110] },
    ], {
      x: 0.6, y: 1.55, w: 7.2, h: 5.3, barDir: "col", barGrouping: "stacked", barGapWidthPct: 70,
      chartColors: [X.navy, X.l2, X.l9, X.l3], showValue: false,
      catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", titleFontFace: "+mn-lt",
      catAxisLabelColor: X.muted, valAxisLabelColor: X.muted, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, valAxisLabelFormatCode: "#,##0",
      valGridLine: { color: "E5E2DA", size: 0.5 }, catGridLine: { style: "none" }, valAxisMaxVal: 70000,
      showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: X.muted,
      showTitle: true, title: T("Costo annuo, CHF (prospect sintetico P-1042)", "Annual cost, CHF (synthetic P-1042)"), titleFontSize: 13, titleColor: X.muted,
    });
    card(s, 8.2, 1.6, 4.5, 2.35, X.teal, "hero");
    s.addText([
      { text: T("ALMENO", "AT LEAST"), options: { fontSize: 13, bold: true, color: "CDEDE8", charSpacing: 2, breakLine: true } },
      { text: "CHF 6'520", options: { fontSize: 50, bold: true, color: C.background1, breakLine: true } },
      { text: T("in meno all'anno, stessi titoli", "less per year, same holdings"), options: { fontSize: 15, color: C.background1 } },
    ], tb({ x: 8.45, y: 1.75, w: 4.1, h: 2.1 }));
    const kp = [[T("Rientro dei costi di cambio", "Switching cost paid back in"), T("2,8 mesi", "2.8 months")], [T("Oggi", "Today"), "CHF 60'840 · 1.41%"], [T("Con Safe Capital", "With Safe Capital"), "CHF 54'320 · 1.26%"]];
    kp.forEach((k, i) => {
      const y = 4.15 + i * 0.55;
      s.addText(k[0], tb({ x: 8.2, y, w: 2.4, h: 0.45, fontSize: 13, color: C.accent6, valign: "middle" }));
      s.addText(k[1], tb({ x: 10.5, y, w: 2.2, h: 0.45, fontSize: 15, bold: true, align: "right", valign: "middle", color: i === 0 ? C.accent1 : C.text1 }));
    });
    s.addText([
      { text: T("«Almeno»: i costi propri della Banca Beta non sono ancora noti.", "“At least”: Bank Beta's own fees are still unknown."), options: { bullet: true, breakLine: true } },
      { text: T("Bollo svizzero (CHF 610) escluso da entrambi i lati.", "Swiss stamp duty (CHF 610) left out on both sides."), options: { bullet: true, breakLine: true } },
      { text: T("Nuovi fondi: mostrati a parte, non è un risparmio di commissioni.", "New funds: shown apart, not a fee saving."), options: { bullet: true } },
    ], tb({ x: 8.2, y: 5.85, w: 4.5, h: 1.05, fontSize: 11.5, color: C.accent6, paraSpaceAfter: 3 }));
    s.addNotes(T("Safe Capital è un gestore patrimoniale esterno: gli averi restano presso una banca depositaria, quindi la proposta include la commissione Safe Capital (0,70% / 0,50% a scaglioni) e custodia, operazioni e cambi della banca depositaria partner. IVA 8,1% perché il cliente sintetico è domiciliato in Svizzera; dipende dal domicilio. Risparmio esatto CHF 6'520.10; costo di cambio CHF 1'500. Con nuovi fondi: almeno CHF 14'700 all'anno, rientro in 3,3 mesi, ma non è un confronto a parità.", "Safe Capital is an external asset manager: assets stay at a custodian bank, so the proposal includes Safe Capital's fee (tiered 0.70% / 0.50%) and the partner custodian's custody, trading and FX. VAT 8.1% because the synthetic client lives in Switzerland; it depends on domicile. Exact saving CHF 6'520.10; switching cost CHF 1'500. New funds: at least CHF 14'700 a year, payback 3.3 months, but not like for like."));
  }
  {
    const s = content(T("Gli output", "The outputs"), T("Cosa si ottiene alla fine di ogni analisi", "What you get at the end of every analysis"), SEC.result);
    fitImage(s, IMG("v2_report.png"), { x: 0.6, y: 1.55, w: 5.4, h: 5.3 }, "client report mockup");
    const outs = [
      ["LuFileText", X.teal, X.tealSoft, T("Report per il cliente", "Client report"), T("Una pagina, nella lingua del cliente: oggi vs Safe Capital, riga per riga, cosa manca.", "One page in the client's language: today vs Safe Capital, line by line, what is missing.")],
      ["LuMail", X.navy, X.infoSoft, T("Lettera di richiesta alla banca", "Request letter to the bank"), T("Elenca i documenti mancanti e perché servono, già pronta da firmare.", "Lists the missing documents and why they matter, ready to sign.")],
      ["LuListChecks", X.navy, X.infoSoft, T("Registro dei costi con fonti", "Cost ledger with sources"), T("Ogni riga con documento, pagina, stato e controlli superati.", "Every line with document, page, status and checks passed.")],
      ["LuEyeOff", X.red, X.redSoft, T("Vista interna (solo staff)", "Internal view (staff only)"), T("Margine di Safe Capital sul prospect: mai nei materiali per il cliente.", "Safe Capital's margin on the prospect: never in client material.")],
    ];
    for (let i = 0; i < 4; i++) {
      const y = 1.6 + i * 1.3;
      await iconIn(s, 6.5, y, 0.62, outs[i][0], outs[i][2], outs[i][1], outs[i][3]);
      s.addText(outs[i][3], tb({ x: 7.3, y, w: 5.4, h: 0.38, fontSize: 17, bold: true, color: C.text2 }));
      s.addText(outs[i][4], tb({ x: 7.3, y: y + 0.4, w: 5.4, h: 0.75, fontSize: 14, color: C.accent6 }));
    }
    s.addNotes(T("Il report viene esportato solo da numeri approvati e indica che non è una consulenza d'investimento.", "The report is exported from approved numbers only and states it is not investment advice."));
  }
  {
    const s = content(T("Dati e privacy", "Data and privacy"), T("Gira sull'infrastruttura di Safe Capital; i file restano riservati", "Runs on Safe Capital's own infrastructure; files stay confidential"), SEC.result);
    const opts = [
      ["LuLaptop", T("In ufficio", "In the office"), T("Consigliato per il pilota", "Recommended for the pilot"), X.teal],
      ["LuServer", T("Hosting privato in Svizzera", "Swiss private hosting"), T("Opzione per la produzione", "Option for production"), X.navy],
      ["LuCloud", T("Servizi AI esterni", "External AI services"), T("Disattivati di default", "Off by default"), X.amber],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.85, 1.35, X.bg, opts[i][1]);
      await iconIn(s, x + 0.25, 1.9, 0.85, opts[i][0], X.white, opts[i][3], opts[i][1]);
      s.addText(opts[i][1], tb({ x: x + 1.3, y: 1.85, w: 2.45, h: 0.5, fontSize: 16, bold: true, color: C.text2, valign: "middle" }));
      s.addText(opts[i][2], tb({ x: x + 1.3, y: 2.35, w: 2.45, h: 0.4, fontSize: 13, bold: true, color: opts[i][3] }));
    }
    const tiles = [["LuFileSignature", T("Consenso del cliente", "Client consent")], ["LuFilter", T("Solo i dati necessari", "Only what is needed")], ["LuLock", T("Cifrato", "Encrypted")], ["LuUserCheck", T("Accessi nominativi, tracciati", "Named, logged access")], ["LuBot", T("Niente AI pubblica sui file", "No public AI on files")], ["LuTrash2", T("Cancellati a scadenza", "Deleted on schedule")]];
    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.6 + col * 4.1, y = 3.35 + row * 0.95;
      await iconIn(s, x, y, 0.6, tiles[i][0], X.tealSoft, X.teal, tiles[i][1]);
      s.addText(tiles[i][1], tb({ x: x + 0.8, y, w: 3.1, h: 0.6, fontSize: 15, bold: true, valign: "middle" }));
    }
    card(s, 0.6, 5.4, 12.1, 0.8, X.tealSoft, "egress");
    s.addText([{ text: T("L'unica cosa che va online: ", "The only thing that goes online: "), options: { bold: true, color: C.accent1 } }, { text: T("i codici ISIN pubblici, per scaricare i KID. Nessun nome, nessun importo.", "public ISIN codes, to fetch KIDs. No names, no amounts.") }], tb({ x: 0.85, y: 5.4, w: 11.7, h: 0.8, fontSize: 16, valign: "middle" }));
    note(s, T("Si applica la LPD svizzera riveduta (in vigore dal 1° settembre 2023). Segreto bancario e regole di outsourcing da verificare con il legale di Safe Capital; non è una consulenza legale.", "The revised Swiss FADP applies (in force since 1 September 2023). Banking secrecy and outsourcing rules to be checked by Safe Capital's counsel; this is not legal advice."));
    s.addNotes(T("L'hosting in Svizzera aiuta ma da solo non rende il trattamento conforme: contano anche contratti, accessi e conservazione.", "Swiss hosting helps but does not by itself make processing compliant: contracts, access and retention matter too."));
  }

  // ===================================================================== GETTING STARTED
  pres.addSection({ title: SEC.go });
  {
    const s = content(T("Il piano", "The plan"), T("Un pilota su casi reali prima della produzione", "A pilot on real cases before production"), SEC.go);
    const ph = [[T("OGGI", "NOW"), T("Demo", "Demo"), T("Motore funzionante su documenti sintetici e tariffari reali", "Working engine on synthetic documents and real price lists")], [T("FASE 1", "PHASE 1"), T("Pilota", "Pilot"), T("1–3 casi reali anonimizzati; misuriamo precisione e tempi", "1–3 anonymised real cases; measure accuracy and time")], [T("FASE 2", "PHASE 2"), T("Consolidamento", "Harden"), T("Più formati bancari, revisione di sicurezza, accessi", "More bank layouts, security review, logins")], [T("FASE 3", "PHASE 3"), T("Produzione", "Production"), T("In uso a Safe Capital dopo l'ok della compliance", "Live at Safe Capital after compliance sign-off")]];
    s.addShape(pres.shapes.LINE, { x: 0.95, y: 2.3, w: 9.3, h: 0, line: { color: X.border, width: 2 }, objectName: "timeline" });
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.1;
      s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: 2.1, w: 0.4, h: 0.4, fill: { color: i === 0 ? X.teal : i === 1 ? X.amber : X.navy }, line: { color: X.white, width: 2 }, objectName: "ms " + i });
      s.addText(ph[i][0], tb({ x, y: 1.6, w: 2.8, h: 0.3, fontSize: 11, bold: true, charSpacing: 1, color: i === 0 ? C.accent1 : i === 1 ? C.accent2 : C.accent6 }));
      card(s, x, 2.85, 2.85, 2.3, i === 1 ? X.amberSoft : X.bg, "phase " + i);
      s.addText(ph[i][1], tb({ x: x + 0.3, y: 3.1, w: 2.3, h: 0.5, fontSize: 22, bold: true, color: C.text2 }));
      s.addText(ph[i][2], tb({ x: x + 0.3, y: 3.7, w: 2.3, h: 1.3, fontSize: 15 }));
    }
    note(s, T("Le durate si fissano dopo il pilota, quando sappiamo quanti formati bancari portano i clienti di Safe Capital.", "Durations are set after the pilot, once we know how many bank layouts Safe Capital's prospects bring."), 5.5);
    s.addNotes(T("Niente date prima di vedere documenti reali.", "No dates before seeing real documents."));
  }
  {
    const s = pres.addSlide({ masterName: "Dark", sectionTitle: SEC.go });
    s.addText(T("PROSSIMO PASSO", "NEXT STEP"), tb({ x: 0.8, y: 0.7, w: 8, h: 0.35, fontSize: 14, bold: true, color: "5FA8A0", charSpacing: 3 }));
    s.addText(T("Facciamo il pilota su un caso reale", "Let's run the pilot on one real case"), tb({ x: 0.8, y: 1.1, w: 11.5, h: 0.9, fontSize: 40, bold: true, color: C.background1 }));
    const asks = [
      ["LuFolderOpen", T("Un caso reale anonimizzato", "One anonymised real case"), T("Estratti, 12 mesi di costi, il contratto", "Statements, 12 months of fees, the contract")],
      ["LuReceipt", T("Le tariffe di Safe Capital", "Safe Capital's tariffs"), T("Commissione e banca depositaria partner", "Fee and partner custodian")],
      ["LuShieldCheck", T("Due conferme", "Two confirmations"), T("Dove gira (ufficio o Svizzera) e testo del consenso", "Where it runs (office or Swiss) and consent wording")],
    ];
    s.addText(T("CI SERVE", "WE NEED"), tb({ x: 0.8, y: 2.3, w: 4, h: 0.3, fontSize: 12, bold: true, color: X.paleNavy, charSpacing: 2 }));
    for (let i = 0; i < 3; i++) {
      const x = 0.8 + i * 3.95;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.7, w: 3.7, h: 1.9, rectRadius: 0.06, fill: { color: "1B3A5C" }, line: { color: "1B3A5C" }, objectName: "ask " + i });
      s.addImage({ data: await icon(asks[i][0], "5FA8A0"), x: x + 0.3, y: 2.95, w: 0.5, h: 0.5, objectName: "ask icon " + i });
      s.addText(asks[i][1], tb({ x: x + 0.3, y: 3.55, w: 3.2, h: 0.45, fontSize: 17, bold: true, color: C.background1 }));
      s.addText(asks[i][2], tb({ x: x + 0.3, y: 4.0, w: 3.2, h: 0.5, fontSize: 13, color: X.paleNavy }));
    }
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.8, y: 5.0, w: 11.55, h: 1.15, rectRadius: 0.08, fill: { color: X.teal }, line: { color: X.teal }, objectName: "cta" });
    s.addText([{ text: T("IN CAMBIO  ", "IN RETURN  "), options: { bold: true, fontSize: 13, color: "CDEDE8", charSpacing: 2 } }, { text: T("il report FeeLens di quel caso: ogni costo con la sua fonte, e il confronto con Safe Capital.", "the FeeLens report for that case: every cost with its source, and the comparison with Safe Capital."), options: { bold: true, fontSize: 19, color: C.background1 } }], tb({ x: 1.1, y: 5.0, w: 11.0, h: 1.15, valign: "middle" }));
    s.addText(T("Nessuna fonte, nessuna cifra verificata · Mancante non vuol dire zero · Nessun servizio comparabile, nessun risparmio dichiarato", "No source, no verified figure · Missing is never zero · No comparable service, no savings claim"), tb({ x: 0.8, y: 6.55, w: 11.5, h: 0.35, fontSize: 12, color: X.paleNavy }));
    s.addNotes(T("Da confermare anche: entità legale e licenza da citare (Safe Capital Management SA, CHE-381.156.096, è nel registro di commercio; l'autorizzazione FINMA indicata sul sito non è ancora stata verificata nel registro FINMA) e una ricerca di marchio per il nome FeeLens.", "Also to confirm: legal entity and licence to cite (Safe Capital Management SA, CHE-381.156.096, is in the commercial register; the FINMA authorisation stated on its website is not yet checked in the FINMA register) and a trademark search for the name FeeLens."));
  }

  // ===================================================================== DEEP DIVE
  pres.addSection({ title: SEC.deep });
  {
    const s = content(T("Approfondimento · documenti", "Deep dive · documents"), T("Cosa porta il cliente e cosa prova ogni documento", "What the client brings and what each document proves"), SEC.deep);
    const head = [T("DOCUMENTO", "DOCUMENT"), T("COSA LEGGIAMO", "WHAT WE READ"), T("PROVA", "PROVES"), T("NON PROVA", "CANNOT PROVE"), T("SERVE", "NEED")];
    const rows = [
      [T("Estratto patrimoniale", "Statement of assets"), T("ISIN, quantità, prezzo, valore, valuta, data, totale", "ISIN, quantity, price, value, currency, date, total"), T("Posizioni a una data", "Holdings at a date"), T("Costi", "Fees"), [T("Essenziale", "Essential"), "obs"]],
      [T("Rendiconto costi annuale", "Annual cost report"), T("Costi di servizio, costi dei prodotti, pagamenti a terzi", "Service costs, product costs, third-party payments"), T("Costo annuo quasi completo", "Near-complete annual cost"), T("Margini FX non elencati", "FX margins not listed"), [T("Essenziale", "Essential"), "obs"]],
      [T("Avvisi di addebito", "Fee advices"), T("Tipo, periodo, base, aliquota, importo, IVA", "Type, period, base, rate, amount, VAT"), T("Ogni addebito", "Every debit"), T("Costi nei prodotti", "Costs inside products"), [T("Essenziale*", "Essential*"), "obs"]],
      [T("Contratto / tariffario", "Contract / price list"), T("Aliquote, scaglioni, minimi, perimetro, entità", "Rates, tiers, minimums, scope, entity"), T("Cosa è stato concordato", "What was agreed"), T("Cosa è stato addebitato", "What was billed"), [T("Utile", "Helpful"), "info"]],
      [T("Conferme di esecuzione", "Trade confirmations"), T("Commissione, terzi, bollo, cambio applicato", "Commission, third-party, stamp duty, FX rate"), T("Costi di negoziazione", "Trading costs"), T("Condizioni", "Contract terms"), [T("Utile", "Helpful"), "info"]],
      [T("KID del fondo", "Fund KID"), T("Costi correnti, transazione, ingresso/uscita", "Ongoing, transaction, entry/exit costs"), T("Aliquote di costo", "Cost rates"), T("Quanto ha pagato il cliente", "What the client paid"), [T("Recuperato", "Fetched"), "acc"]],
      [T("Retrocessioni", "Retrocessions"), T("Pagamenti dai fornitori, rimborsati o trattenuti", "Payments from providers, refunded or kept"), T("Conflitti, rimborsi", "Conflicts, refunds"), T("Costo diretto", "Direct cost"), [T("Da chiedere", "Ask bank"), "est"]],
    ];
    const hdr = { bold: true, color: C.accent6, fill: { color: X.mutedSurface }, fontSize: 11 };
    s.addTable([head.map((h) => ({ text: h, options: hdr }))].concat(rows.map((r) => r.map((c, ci) => ci === 4
      ? { text: c[0], options: { bold: true, fontSize: 12, align: "center", color: KIND[c[1]][1], fill: { color: KIND[c[1]][0] } } }
      : { text: c, options: ci === 0 ? { bold: true, fontSize: 13 } : { fontSize: 12, color: ci === 3 ? C.accent6 : C.text1 } }))),
      { x: 0.6, y: 1.6, w: 12.1, colW: [2.6, 3.9, 2.25, 2.15, 1.2], rowH: 0.58, border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0.04, 0.1, 0.04, 0.1], valign: "middle" });
    note(s, T("* oppure il rendiconto costi. Formati: PDF, scansioni, foto, Excel, CSV. Italiano, tedesco, francese, inglese.", "* or the cost report. Formats: PDF, scans, photos, Excel, CSV. Italian, German, French, English."));
    s.addNotes(T("Tassonomia completa di 31 tipi di documento in data/taxonomy/document_types.csv.", "Full taxonomy of 31 document types in data/taxonomy/document_types.csv."));
  }
  {
    const s = content(T("Approfondimento · strati di costo", "Deep dive · cost layers"), T("I dieci strati di costo", "The ten cost layers"), SEC.deep);
    const rows = [
      ["L1", T("Servizio", "Service"), T("Gestione, consulenza, all-in, commissione EAM", "Management, advisory, all-in, EAM fee"), T("Addebito", "Debit")],
      ["L2", T("Custodia e conto", "Custody and account"), T("Custodia (scaglioni, minimi), spese di conto", "Safekeeping (tiers, minimums), account fees"), T("Addebito", "Debit")],
      ["L3", T("Negoziazione", "Trading"), T("Courtage, ticket, terzi, commissione FX", "Brokerage, ticket, third-party, FX commission"), T("Nel netto", "In net amount")],
      ["L4", T("Fondi ed ETF", "Funds and ETFs"), T("Correnti, transazione, performance, ingresso/uscita", "Ongoing, transaction, performance, entry/exit"), T("Nel NAV", "Inside NAV")],
      ["L5", T("Prodotti strutturati", "Structured products"), T("Margine dell'emittente, distribuzione", "Issuer margin, distribution"), T("Nel prezzo", "Inside price")],
      ["L6", T("Esecuzione implicita", "Implicit execution"), T("Margine FX, spread denaro/lettera", "FX margin, bid/ask spread"), T("Nel tasso", "Inside rate")],
      ["L7", T("Polizza assicurativa", "Insurance wrapper"), T("Costi della polizza", "Policy charges"), T("In parte", "Partly")],
      ["L8", T("Finanziamento", "Financing"), T("Interessi lombard", "Lombard interest"), T("Addebito", "Debit")],
      ["L9", T("Imposte", "Taxes"), T("IVA (secondo domicilio), bollo", "VAT (by domicile), stamp duty"), T("Addebito", "Debit")],
      ["L10", T("Una tantum / cambio banca", "One-off / switching"), T("Trasferimento per posizione, uscita, vendita", "Transfer per position, exit, sale"), T("Una volta", "Once")],
    ];
    const hdr = { bold: true, color: C.accent6, fill: { color: X.mutedSurface }, fontSize: 11 };
    s.addTable([["", T("STRATO", "LAYER"), T("COSA", "WHAT"), T("VISIBILE COME", "VISIBLE AS")].map((h) => ({ text: h, options: hdr }))].concat(rows.map((r) => r.map((c, ci) => ({ text: c, options: { fontSize: 12, bold: ci <= 1, color: ci === 0 ? C.accent1 : C.text1 } })))),
      { x: 0.6, y: 1.55, w: 12.1, colW: [0.7, 2.8, 6.4, 2.2], rowH: 0.45, border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0.03, 0.1, 0.03, 0.1], valign: "middle" });
    s.addNotes(T("Fonte: docs/research/FEE_TAXONOMY.md. Le retrocessioni stanno a lato del totale: sono già nei costi dei fondi.", "Source: docs/research/FEE_TAXONOMY.md. Retrocessions sit beside the total: they are already inside fund costs."));
  }
  {
    const s = content(T("Approfondimento · tecnologia", "Deep dive · technology"), T("Strumenti locali e open source, con regole precise", "Local open-source tools, with clear rules"), SEC.deep);
    const rows = [
      [T("PDF digitali", "Born-digital PDF"), "pdfplumber, Docling", T("Parole con coordinate, tabelle", "Words with coordinates, tables"), "MIT"],
      [T("Scansioni e foto", "Scans and photos"), "OCRmyPDF + Tesseract", T("Testo da immagini; IT, DE, FR, EN", "Text from images; IT, DE, FR, EN"), "MPL-2.0 / Apache-2.0"],
      ["Excel, CSV", "openpyxl", T("Foglio e cella come prova", "Sheet and cell as evidence"), "MIT"],
      [T("Immagini delle pagine", "Page images"), "pypdfium2, PDF.js", T("Pagine con i riquadri evidenziati", "Pages with highlighted boxes"), "Apache-2.0 / BSD"],
      [T("Evitati", "Avoided"), T("PyMuPDF, OCR in cloud", "PyMuPDF, cloud OCR"), T("Licenza AGPL; i dati uscirebbero dall'ufficio", "AGPL licence; data would leave the office"), "—"],
    ];
    const hdr = { bold: true, color: C.accent6, fill: { color: X.mutedSurface }, fontSize: 11 };
    s.addTable([["INPUT", T("STRUMENTO", "TOOL"), T("COSA FA", "WHAT IT DOES"), T("LICENZA", "LICENCE")].map((h) => ({ text: h, options: hdr }))].concat(rows.map((r, ri) => r.map((c, ci) => ({ text: c, options: { fontSize: 13, bold: ci === 0, color: ri === 4 ? C.accent3 : C.text1 } })))),
      { x: 0.6, y: 1.6, w: 12.1, colW: [2.4, 2.8, 4.6, 2.3], rowH: 0.52, border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0.04, 0.12, 0.04, 0.12], valign: "middle" });
    const g = [T("L'AI propone, il codice verifica sul testo della pagina", "AI suggests; code checks it against the page text"), T("Nessun calcolo fatto dall'AI: somme deterministiche", "No arithmetic by AI: deterministic sums"), T("Ogni correzione registra chi, quando e perché", "Every correction records who, when and why")];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      s.addImage({ data: await icon("LuShieldCheck", X.teal), x, y: 5.15, w: 0.4, h: 0.4, objectName: "g" + i });
      s.addText(g[i], tb({ x: x + 0.55, y: 5.1, w: 3.4, h: 0.8, fontSize: 14, bold: true }));
    }
    s.addNotes(T("Fonte: docs/research/EXTRACTION_TOOLING.md. Precisione misurata campo per campo su casi reali anonimizzati nel pilota.", "Source: docs/research/EXTRACTION_TOOLING.md. Accuracy measured field by field on anonymised real cases in the pilot."));
  }
  {
    const s = content(T("Approfondimento · glossario", "Deep dive · glossary"), T("Le parole usate", "Words used"), SEC.deep);
    const g = [
      ["KID", T("Documento ufficiale con i costi di ogni classe di un fondo.", "Official cost sheet for each fund share class.")],
      [T("Costi correnti (TER/OCF)", "Ongoing charges (TER/OCF)"), T("Costi annui del fondo, presi dal prezzo. Includono la commissione di gestione.", "Yearly fund costs, taken from the price. Include the management fee.")],
      [T("Retrocessione", "Retrocession"), T("Pagamento di un fornitore di prodotti alla banca o al gestore.", "Payment from a product provider to the bank or manager.")],
      [T("Banca depositaria", "Custodian bank"), T("La banca che custodisce i titoli. Con un gestore esterno si pagano entrambi.", "The bank holding the assets. With an external manager the client pays both.")],
      ["EAM", T("Gestore patrimoniale esterno, come Safe Capital.", "External asset manager, like Safe Capital.")],
      ["bps", T("Punti base: 100 bps = 1% all'anno.", "Basis points: 100 bps = 1% a year.")],
      [T("A parità", "Like for like"), T("Stessi titoli, stesso servizio: cambiano solo i costi.", "Same holdings, same service: only fees differ.")],
      [T("Tassa di bollo", "Stamp duty"), T("Imposta federale sulle negoziazioni, dovuta presso ogni banca svizzera.", "Federal tax on trades, due at any Swiss bank.")],
    ];
    for (let i = 0; i < 8; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.6 + col * 6.15, y = 1.6 + row * 1.25;
      s.addText(g[i][0], tb({ x, y, w: 5.9, h: 0.38, fontSize: 16, bold: true, color: C.accent1 }));
      s.addText(g[i][1], tb({ x, y: y + 0.4, w: 5.9, h: 0.75, fontSize: 14 }));
    }
    s.addNotes(T("La titolarità delle retrocessioni segue la giurisprudenza svizzera; da verificare sulla fonte primaria.", "Retrocession ownership follows Swiss case law; to verify against the primary source."));
  }

  await pres.writeFile({ fileName: OUT });
  if (process.env.APPLY_THEME_JS) { const { applyTheme } = require(process.env.APPLY_THEME_JS); await applyTheme(OUT, THEME); }
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
