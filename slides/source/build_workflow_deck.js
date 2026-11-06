// Builds the Italian technical deck "FeeLens · Come funziona il sistema".
//   node build_workflow_deck.js  ->  ../FeeLens_Workflow_IT.pptx
// Screens are real screenshots of the FeeLens app (branch claude/project-thread-steqtm, PR #5), Italian UI,
// filled with SYNTHETIC demo data. Extraction metrics are the real 72-PDF corpus results (PR #7,
// data/specimens/RESULTS.md, extractor pce-rules-0.1, parser 3834590).
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const NAME = "FeeLens";
const OUT = path.resolve(__dirname, "..", `${NAME}_Workflow_IT.pptx`);
const IMG = (n) => path.join(__dirname, "img", n);
const THEME = {
  name: NAME, headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "14202E", lt1: "FFFFFF", dk2: "0F2A4A", lt2: "F7F6F2", accent1: "0F766E", accent2: "B45309", accent3: "B42318", accent4: "1E7A46", accent5: "2F5D8A", accent6: "5B6676", hlink: "0F766E", folHlink: "2F5D8A" },
};
const X = {
  navy: "0F2A4A", teal: "0F766E", tealSoft: "E3F2F0", amber: "B45309", amberSoft: "FDF3E2", red: "B42318", redSoft: "FDECEA",
  green: "1E7A46", greenSoft: "E7F4EC", muted: "5B6676", bg: "F7F6F2", mutedSurface: "EFEDE7", border: "DEDAD1", white: "FFFFFF",
  infoSoft: "E6ECF4", paleNavy: "9FB3C8", panel: "1B3A5C", tealLight: "5FA8A0",
};
async function icon(name, color) {
  const Cmp = lu[name] || lu.LuCircle;
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Cmp, { color: "#" + color, size: "256", strokeWidth: 1.75 }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}
function imgSize(file) { const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; }

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = `${NAME} · come funziona il sistema`;
  pres.author = `${NAME} project`; pres.company = NAME;
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  pres.defineSlideMaster({
    title: "Dark", background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.5, w: 11.5, h: 1.7, fontFace: THEME.headFontFace, fontSize: 48, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.4, w: 11.5, h: 1.0, fontSize: 22, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Content", background: { color: C.background1 }, margin: [0.5, 0.6, 0.6, 0.6],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.62, w: 12.1, h: 0.75, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.text2, valign: "top", align: "left", margin: 0 }, text: "" } },
      { text: { text: `${NAME} · come funziona il sistema · dati dei clienti sintetici, metriche da 72 PDF pubblici reali`, options: { x: 0.6, y: 7.02, w: 10, h: 0.28, fontSize: 10, color: C.accent6, margin: 0 } } },
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
  const card = (s, x, y, w, h, fill, name) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: fill }, line: { color: fill }, objectName: name });
  const iconIn = async (s, x, y, d, name, bg, fg, objName) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: d, h: d, rectRadius: 0.08, fill: { color: bg }, line: { color: bg }, objectName: objName + " tile" });
    const p = d * 0.22;
    s.addImage({ data: await icon(name, fg), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, objectName: objName + " icon" });
  };
  const KIND = { obs: [X.greenSoft, X.green], con: [X.infoSoft, X.navy], est: [X.amberSoft, X.amber], unk: [X.redSoft, X.red], na: [X.mutedSurface, X.muted], acc: [X.tealSoft, X.teal] };
  const chip = (s, x, y, text, kind, w, h = 0.3, fs = 11) => {
    const [bg, fg] = KIND[kind];
    const ww = w || Math.max(0.9, 0.09 * text.length + 0.35);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: ww, h, rectRadius: h / 2, fill: { color: bg }, line: { color: bg }, objectName: "chip " + text });
    s.addText(text, tb({ x, y, w: ww, h, fontSize: fs, bold: true, color: fg, align: "center", valign: "middle" }));
    return ww;
  };
  const badge = (s, x, y, n, d = 0.34, fill = X.navy) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: "badge " + n });
    s.addText(String(n), tb({ x, y, w: d, h: d, fontSize: 12, bold: true, color: C.background1, align: "center", valign: "middle" }));
  };
  const note = (s, text, y = 6.5) => s.addText(text, tb({ x: 0.6, y, w: 12.1, h: 0.4, fontSize: 12, color: C.accent6 }));
  const shot = (s, file, box, name) => {
    const { w, h } = imgSize(IMG(file));
    const r = Math.min(box.w / w, box.h / h), iw = w * r, ih = h * r;
    const rr = { x: box.x, y: box.y, w: iw, h: ih };
    s.addImage({ path: IMG(file), ...rr, objectName: name, altText: name });
    s.addShape(pres.shapes.RECTANGLE, { ...rr, fill: { type: "none" }, line: { color: X.border, width: 0.75 }, objectName: name + " frame" });
    return rr;
  };
  // A screen slide: screenshot left, three numbered points right, a "where" chip.
  const screenSlide = (kicker, title, section, file, where, points, notes) => {
    const s = content(kicker, title, section);
    const r = shot(s, file, { x: 0.6, y: 1.6, w: 7.7, h: 4.85 }, where);
    s.addText(`Nell'app: ${where}`, tb({ x: 0.6, y: r.y + r.h + 0.1, w: 7.7, h: 0.3, fontSize: 11, color: C.accent6 }));
    points.forEach((p, i) => {
      const y = 1.65 + i * 1.6;
      badge(s, 8.7, y, i + 1);
      s.addText(p[0], tb({ x: 9.2, y: y - 0.02, w: 3.5, h: 0.4, fontSize: 16, bold: true, color: C.text2 }));
      s.addText(p[1], tb({ x: 9.2, y: y + 0.4, w: 3.5, h: 1.1, fontSize: 13, color: C.accent6 }));
    });
    s.addNotes(notes);
    return s;
  };
  const table = (s, head, rows, o) => {
    const hdr = { bold: true, color: C.accent6, fill: { color: X.mutedSurface }, fontSize: 11 };
    s.addTable([head.map((h) => ({ text: h, options: hdr }))].concat(rows.map((r) => r.map((c) => (typeof c === "string" ? { text: c, options: { fontSize: o.fs || 12 } } : c)))),
      Object.assign({ border: { type: "solid", color: X.border, pt: 0.5 }, margin: [0.04, 0.1, 0.04, 0.1], valign: "middle" }, o));
  };

  const S = { intro: "In breve", pipe: "La pipeline", ai: "AI e agenti", gen: "Ogni documento", res: "Risultati reali", next: "Prossimi passi", app: "Approfondimenti" };

  // ============================================================ IN BREVE
  pres.addSection({ title: S.intro });
  {
    const s = pres.addSlide({ masterName: "Dark", sectionTitle: S.intro });
    s.addText("Come funziona FeeLens", { placeholder: "title" });
    s.addText("Dal documento bancario al confronto verificato: la pipeline, dove entra l'AI, e come si vede nell'app.", { placeholder: "body" });
    s.addText("Presentazione tecnica · novembre 2026", tb({ x: 0.8, y: 4.6, w: 11, h: 0.4, fontSize: 16, color: X.paleNavy }));
    const t = [["LuFileStack", "8 passi"], ["LuShieldCheck", "ogni numero con la sua prova"], ["LuFlaskConical", "testato su 72 PDF reali"]];
    for (let i = 0; i < 3; i++) {
      const x = 0.8 + i * 3.6;
      s.addImage({ data: await icon(t[i][0], X.tealLight), x, y: 5.45, w: 0.42, h: 0.42, objectName: "c" + i });
      s.addText(t[i][1], tb({ x: x + 0.55, y: 5.45, w: 3.0, h: 0.42, fontSize: 17, bold: true, color: C.background1, valign: "middle" }));
    }
    s.addText("Schermate reali dell'app con dati sintetici · metriche reali su documenti pubblici", tb({ x: 0.8, y: 6.6, w: 11, h: 0.35, fontSize: 12, color: X.paleNavy }));
    s.addNotes("Questa è la presentazione tecnica, separata da quella per il cliente. In alto ogni slide dice una cosa sola; i dettagli sono nelle note e negli approfondimenti in fondo.");
  }
  {
    const s = content("L'idea in una slide", "Regole prima, AI dopo, e ogni numero si può controllare", S.intro);
    const cols = [
      ["LuSearch", "Leggere", "Il sistema legge ogni pagina e trova posizioni e costi. Ogni valore porta con sé file, pagina e riquadro.", X.teal],
      ["LuListChecks", "Controllare", "I documenti vengono confrontati tra loro. Quello che non torna resta visibile e va a una persona.", X.navy],
      ["LuScale", "Confrontare", "Costi di oggi e proposta Safe Capital, sugli stessi titoli. Ciò che manca non vale mai zero.", X.navy],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.85, 3.0, X.bg, cols[i][1]);
      await iconIn(s, x + 0.3, 1.9, 0.7, cols[i][0], X.white, cols[i][3], cols[i][1]);
      s.addText(cols[i][1], tb({ x: x + 1.2, y: 2.0, w: 2.5, h: 0.5, fontSize: 22, bold: true, color: C.text2, valign: "middle" }));
      s.addText(cols[i][2], tb({ x: x + 0.3, y: 2.85, w: 3.3, h: 1.6, fontSize: 15 }));
    }
    card(s, 0.6, 4.95, 12.1, 1.3, X.tealSoft, "principle");
    s.addText([
      { text: "Il principio  ", options: { bold: true, color: C.accent1, fontSize: 13, charSpacing: 1 } },
      { text: "l'AI può proporre un valore, ma lo accetta solo il codice: il numero deve comparire nel testo della pagina, nel suo riquadro, e i conti devono tornare.", options: { bold: true, fontSize: 18, color: C.text2 } },
    ], tb({ x: 0.9, y: 4.95, w: 11.5, h: 1.3, valign: "middle" }));
    note(s, "Oggi il motore funziona senza modelli linguistici: regole, OCR locale e controlli. I modelli AI sono un'aggiunta misurata, non la base.");
    s.addNotes("Il motore attuale si chiama pce-rules-0.1: estrazione a regole con coordinate, OCR locale, controlli deterministici. Questo è il motivo per cui ogni numero è tracciabile.");
  }

  // ============================================================ LA PIPELINE
  pres.addSection({ title: S.pipe });
  {
    const s = content("La pipeline", "Otto passi: sei automatici, due con una persona", S.pipe);
    const st = [
      ["LuUpload", "Caricamento", "auto", "File registrato con impronta SHA-256"],
      ["LuTextSelect", "Lettura", "auto", "Testo e coordinate di ogni parola"],
      ["LuTags", "Classificazione", "auto", "Tipo, banca, lingua, giurisdizione"],
      ["LuUserCheck", "Revisione", "person", "Valori accettati, corretti o respinti"],
      ["LuGitCompare", "Riconciliazione", "auto", "Esito di ogni controllo incrociato"],
      ["LuLayers", "Costi per livello", "auto", "Registro dei costi con stato e prova"],
      ["LuScale", "Confronto", "auto", "Oggi vs proposta, rientro"],
      ["LuStamp", "Approvazione e rapporto", "person", "Rapporto per il cliente, firmato"],
    ];
    const w = 2.85, h = 2.15, gx = 0.233;
    for (let i = 0; i < 8; i++) {
      const col = i % 4, row = Math.floor(i / 4);
      const x = 0.6 + col * (w + gx), y = 1.65 + row * (h + 0.35);
      const auto = st[i][2] === "auto";
      card(s, x, y, w, h, auto ? X.tealSoft : X.amberSoft, "step " + i);
      badge(s, x + 0.2, y + 0.2, i + 1, 0.38, auto ? X.teal : X.amber);
      s.addImage({ data: await icon(st[i][0], auto ? X.teal : X.amber), x: x + w - 0.6, y: y + 0.18, w: 0.4, h: 0.4, objectName: "si" + i });
      s.addText(st[i][1], tb({ x: x + 0.2, y: y + 0.72, w: w - 0.4, h: 0.4, fontSize: 17, bold: true, color: C.text2 }));
      s.addText(auto ? "Automatico" : "Una persona", tb({ x: x + 0.2, y: y + 1.12, w: w - 0.4, h: 0.28, fontSize: 11, bold: true, color: auto ? C.accent1 : C.accent2 }));
      s.addText(st[i][3], tb({ x: x + 0.2, y: y + 1.42, w: w - 0.4, h: 0.65, fontSize: 13, color: C.accent6 }));
      if (col < 3) s.addShape(pres.shapes.LINE, { x: x + w, y: y + h / 2, w: gx, h: 0, line: { color: X.muted, width: 1.25, endArrowType: "triangle" }, objectName: "a" + i });
    }
    note(s, "Le persone intervengono solo ai passi 4 e 8. Ogni modifica ricalcola tutto il resto in pochi secondi.", 6.55);
    s.addNotes("Gli stessi otto passi sono nella pagina «Come funziona» dell'app. Il passo 4 riguarda solo i valori segnalati (scansioni, bassa affidabilità, conflitti); il passo 8 è l'approvazione di un revisore senior.");
  }
  {
    const s = content("Passi 1–3 · ingresso", "Qualsiasi formato entra, ogni pagina viene letta nel modo giusto", S.pipe);
    const lanes = [
      ["LuFileText", "PDF digitale", "pdfplumber legge parole e coordinate", "Secondi", X.teal],
      ["LuScanLine", "Scansione o foto", "OCR locale (Tesseract) in IT, DE, FR, EN, poi come sopra", "Secondi per pagina", X.amber],
      ["LuSheet", "Excel o CSV", "Foglio e cella diventano la prova", "Istantaneo", X.navy],
    ];
    for (let i = 0; i < 3; i++) {
      const y = 1.7 + i * 1.12;
      card(s, 0.6, y, 5.6, 0.95, X.bg, lanes[i][1]);
      await iconIn(s, 0.75, y + 0.15, 0.65, lanes[i][0], X.white, lanes[i][4], lanes[i][1]);
      s.addText(lanes[i][1], tb({ x: 1.6, y: y + 0.12, w: 2.4, h: 0.35, fontSize: 15, bold: true, color: C.text2 }));
      s.addText(lanes[i][2], tb({ x: 1.6, y: y + 0.47, w: 4.4, h: 0.45, fontSize: 12, color: C.accent6 }));
    }
    s.addText("POI, PER OGNI DOCUMENTO", tb({ x: 0.6, y: 5.15, w: 5.6, h: 0.25, fontSize: 10, bold: true, color: C.accent6, charSpacing: 1 }));
    const lines = ["Tipo: estratto, rendiconto costi, conto, tariffario, KID, termsheet", "Banca emittente, lingua, periodo e giurisdizione", "Tipo incerto: «sconosciuto», lo sceglie una persona"];
    for (let j = 0; j < 3; j++) {
      s.addImage({ data: await icon(j === 2 ? "LuHelpCircle" : "LuCheckCircle2", j === 2 ? X.amber : X.teal), x: 0.6, y: 5.5 + j * 0.42, w: 0.28, h: 0.28, objectName: "l" + j });
      s.addText(lines[j], tb({ x: 1.0, y: 5.47 + j * 0.42, w: 5.2, h: 0.36, fontSize: 13 }));
    }
    const r = shot(s, "app_it_documents.png", { x: 6.6, y: 1.7, w: 6.1, h: 4.6 }, "Schermata Documenti");
    s.addText("Nell'app: Documenti. Tipo, emittente, periodo e motore di lettura per ogni file.", tb({ x: 6.6, y: r.y + r.h + 0.1, w: 6.1, h: 0.45, fontSize: 11, color: C.accent6 }));
    s.addNotes("I file sono dati non fidati: tipo MIME controllato, limiti di dimensione e pagine, PDF cifrati respinti. L'OCR gira come processo separato perché importarlo modifica il lettore PDF (bug documentato e coperto da un test). PyMuPDF è escluso per la licenza AGPL.");
  }
  screenSlide("Passo 4 · la prova", "Ogni valore estratto si vede sulla sua pagina", S.pipe, "app_it_review.png", "Verifica evidenze", [
    ["Riquadro sulla pagina", "Il valore selezionato è evidenziato nel PDF originale, alla sua posizione esatta."],
    ["Accetta, correggi, respingi", "La persona decide; ogni correzione registra chi, quando e perché."],
    ["Solo ciò che serve", "Vanno in revisione scansioni, valori incerti e conflitti, non tutto."],
  ], "Schermata reale dell'app (prospect sintetico P-1042). Senza riquadro un valore non entra nel registro dei costi: è una regola del codice, non una convenzione.");
  {
    const s = content("Passo 5 · riconciliazione", "Prima di fidarsi di un numero, i documenti si controllano a vicenda", S.pipe);
    const ck = [
      ["LuCalculator", "I numeri tornano", "Somma delle posizioni = totale stampato. Stessa data di valutazione su tutti gli estratti."],
      ["LuFileSignature", "Addebitato = concordato", "La commissione addebitata corrisponde alla tariffa: 3,2 mln × 0,80% = 25'600."],
      ["LuCopy", "Contato una volta", "Quattro addebiti trimestrali e il rendiconto annuale sono lo stesso costo: collegati, non sommati."],
      ["LuMapPin", "Fonte valida", "Una tariffa lussemburghese non vale per un conto svizzero: scartata."],
      ["LuGitMerge", "Prodotti coerenti", "Costi dai KID entro il 2,6% della stima della banca."],
      ["LuMailQuestion", "Lacune", "Ogni documento mancante diventa una richiesta, pronta da inviare alla banca."],
    ];
    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.6 + col * 4.1, y = 1.65 + row * 2.3;
      card(s, x, y, 3.85, 2.05, i === 3 ? X.redSoft : X.bg, ck[i][1]);
      await iconIn(s, x + 0.25, y + 0.25, 0.55, ck[i][0], X.white, i === 3 ? X.red : X.navy, ck[i][1]);
      s.addText(ck[i][1], tb({ x: x + 0.95, y: y + 0.3, w: 2.8, h: 0.45, fontSize: 16, bold: true, color: i === 3 ? C.accent3 : C.text2, valign: "middle" }));
      s.addText(ck[i][2], tb({ x: x + 0.25, y: y + 0.95, w: 3.4, h: 1.0, fontSize: 13 }));
    }
    note(s, "Controlli eseguiti dal motore sui documenti sintetici di P-1042. Un controllo fallito non blocca: resta visibile e abbassa la copertura delle evidenze.", 6.35);
    s.addNotes("Nell'app questi esiti sono nella pagina Costi attuali, sezione «Validazione e riconciliazione», e nell'elenco «Cosa ci serve» della pagina Documenti.");
  }
  {
    const s = content("Passo 6 · il registro dei costi", "Ogni costo diventa un «atomo», contato una volta sola", S.pipe);
    // left: atom card
    card(s, 0.6, 1.65, 5.2, 4.6, X.bg, "atom");
    s.addText("UN ATOMO DI COSTO · ESEMPIO", tb({ x: 0.85, y: 1.85, w: 4.8, h: 0.25, fontSize: 10, bold: true, color: C.accent6, charSpacing: 1 }));
    s.addText("Fondo Global Equity · costi correnti", tb({ x: 0.85, y: 2.15, w: 4.8, h: 0.4, fontSize: 17, bold: true, color: C.text2 }));
    const f = [["Importo", "CHF 9'720 (1,08% × 900'000)"], ["Livello", "L4 · fondi ed ETF"], ["Stato", "Stimato, da KID datato"], ["Dove sta", "Dentro il prezzo (NAV)"], ["Prova", "KID, pagina 2, riquadro"], ["Ruolo", "Contato"]];
    f.forEach((r, j) => {
      const y = 2.7 + j * 0.55;
      s.addText(r[0], tb({ x: 0.85, y, w: 1.4, h: 0.45, fontSize: 13, color: C.accent6, valign: "middle" }));
      s.addText(r[1], tb({ x: 2.3, y, w: 3.4, h: 0.45, fontSize: 14, bold: true, valign: "middle" }));
    });
    // right: inclusion rules
    s.addText("LE REGOLE CHE EVITANO I DOPPI CONTEGGI", tb({ x: 6.2, y: 1.7, w: 6.5, h: 0.25, fontSize: 10, bold: true, color: C.accent6, charSpacing: 1 }));
    const rules = [
      ["Incluso nel genitore", "La commissione di gestione (0,75%) è già dentro i costi correnti (1,08%): si mostra, non si somma. Totale 1,08%, non 1,83%.", "na"],
      ["Corrobora", "Addebito sul conto e rendiconto annuale descrivono lo stesso costo: uno conta, l'altro conferma.", "con"],
      ["Non è un costo pagato", "Massimi (ingresso fino al 3%) ed esempi illustrativi del KID: visibili, mai nel totale.", "est"],
      ["Non determinato", "Il costo esiste ma manca la prova: resta nell'elenco, mai zero. Per questo il risparmio è «almeno».", "unk"],
    ];
    rules.forEach((r, j) => {
      const y = 2.05 + j * 1.05;
      chip(s, 6.2, y + 0.05, r[0], r[2], 2.2, 0.32, 11);
      s.addText(r[1], tb({ x: 8.6, y, w: 4.1, h: 0.95, fontSize: 13 }));
    });
    note(s, "Dieci livelli di costo (L1–L10) e otto stati di misura. Elenco completo negli approfondimenti.", 6.45);
    s.addNotes("Nel codice: finance/ledger.py, con i campi layer, measurement, incidence, role, included_in, corroborates ed evidence_fact_ids. Il totale è un risultato strutturato: subtotale noto per stato più l'elenco dei costi non determinati, con is_complete=false.");
  }
  screenSlide("Passo 6 · nell'app", "Costi attuali: il totale, e quanto è davvero provato", S.pipe, "app_it_costs.png", "Costi attuali", [
    ["Totale con la sua copertura", "CHF 61'450, di cui il 65% rilevato su documenti e il resto stimato."],
    ["Costi per livello", "Gestione, custodia, negoziazione, fondi, imposte: ogni barra si apre fino alla pagina."],
    ["Mappa delle lacune", "Per banca e livello: rilevato, stimato o mancante (tratteggio)."],
  ], "Schermata reale, prospect sintetico P-1042. I numeri coincidono con quelli della presentazione per il cliente.");
  screenSlide("Passo 7 · confronto", "Stessi titoli, ogni costo della proposta incluso", S.pipe, "app_it_compare.png", "Confronto", [
    ["A parità di condizioni", "Stesso patrimonio, stesso volume di negoziazione, stesso periodo."],
    ["Proposta completa", "Commissione Safe Capital più custodia e operazioni della banca depositaria."],
    ["Almeno CHF 6'520", "Rientro dei costi di trasferimento in 2,8 mesi. Bollo escluso da entrambi i lati."],
  ], "Il pulsante «Con modifiche ai prodotti» mostra lo scenario con nuovi fondi, sempre etichettato come non a parità.");
  screenSlide("Passo 8 · rapporto", "Il rapporto parte solo dopo l'approvazione", S.pipe, "app_it_report.png", "Rapporto per il cliente", [
    ["Solo numeri approvati", "Un revisore senior approva una versione congelata, con la sua impronta."],
    ["Cosa manca, scritto", "Il rapporto elenca i costi non ancora verificati, in chiaro."],
    ["Margine interno separato", "Visibile solo ai revisori senior; mai nel rapporto né nell'API del cliente."],
  ], "Il PDF si scarica dalla stessa pagina. Il test E2E 07 verifica che un analista non veda l'economia interna e che l'API del cliente non contenga i parametri interni.");

  // ============================================================ AI E AGENTI
  pres.addSection({ title: S.ai });
  {
    const s = content("AI e agenti", "Dove entra l'AI: tre livelli, dal più sicuro al più potente", S.ai);
    const lv = [
      ["OGGI · IN USO", "Regole + OCR locale", "Parole con coordinate, vocabolario in 4 lingue, controlli deterministici.", "Testato su 72 PDF reali", "obs", X.teal, "LuCpu"],
      ["PROSSIMO · DA MISURARE", "Modelli locali di layout", "Docling per tabelle complesse; un modello visivo locale (es. PaddleOCR-VL) per scansioni difficili. Girano sul server, nessun dato esce.", "Si adottano solo se migliorano la misura campo per campo", "est", X.amber, "LuServer"],
      ["OPZIONALE · CON OK PRIVACY", "LLM e agenti", "Un modello linguistico propone valori su testo già strutturato e scrive bozze (lettere, sintesi).", "Spento di default; richiede una decisione documentata", "unk", X.red, "LuBot"],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1;
      card(s, x, 1.65, 3.85, 3.65, X.bg, lv[i][1]);
      s.addText(lv[i][0], tb({ x: x + 0.3, y: 1.85, w: 3.3, h: 0.28, fontSize: 10, bold: true, color: lv[i][5], charSpacing: 1 }));
      await iconIn(s, x + 0.3, 2.25, 0.6, lv[i][6], X.white, lv[i][5], lv[i][1]);
      s.addText(lv[i][1], tb({ x: x + 1.05, y: 2.25, w: 2.7, h: 0.6, fontSize: 17, bold: true, color: C.text2, valign: "middle" }));
      s.addText(lv[i][2], tb({ x: x + 0.3, y: 3.05, w: 3.3, h: 1.4, fontSize: 13 }));
      chip(s, x + 0.3, 4.6, lv[i][3], lv[i][4], 3.25, 0.5, 10.5);
    }
    card(s, 0.6, 5.55, 12.1, 0.8, X.tealSoft, "guard");
    s.addText([{ text: "In tutti e tre i casi  ", options: { bold: true, color: C.accent1, fontSize: 13 } }, { text: "l'AI propone, il codice verifica sulla pagina, nessun calcolo fatto dall'AI, decide una persona.", options: { bold: true, fontSize: 16, color: C.text2 } }], tb({ x: 0.9, y: 5.55, w: 11.6, h: 0.8, valign: "middle" }));
    s.addNotes("ADR 0003 (estrazione) e ADR 0004 (privacy). PCE_ALLOW_EXTERNAL_AI=false è il default. Con l'interruttore acceso si inviano solo regioni di pagina oscurate, mai documenti grezzi a un'AI pubblica. La scelta del modello è empirica: decide la misura sul corpus, non i benchmark dei fornitori.");
  }
  {
    const s = content("AI e agenti · proposta", "Come lavorerebbero gli agenti, ognuno con un compito stretto", S.ai);
    chip(s, 10.4, 0.42, "Proposta, non ancora costruita", "est", 2.3, 0.3, 10);
    // orchestrator
    card(s, 0.6, 1.7, 3.0, 4.4, X.navy, "orch");
    s.addImage({ data: await icon("LuWorkflow", X.tealLight), x: 0.85, y: 1.95, w: 0.5, h: 0.5, objectName: "orch icon" });
    s.addText("Orchestratore", tb({ x: 0.85, y: 2.6, w: 2.6, h: 0.45, fontSize: 18, bold: true, color: C.background1 }));
    s.addText("Codice normale, non un modello. Decide l'ordine, chiama gli agenti solo dove le regole non bastano, raccoglie gli esiti.", tb({ x: 0.85, y: 3.1, w: 2.55, h: 2.0, fontSize: 13, color: X.paleNavy }));
    const ag = [
      ["LuTags", "Classificatore", "Quando le regole esitano su tipo o banca", "Proposta di tipo, con motivazione"],
      ["LuSearch", "Estrattore per famiglia", "Layout nuovo o tabella complessa", "Campi dello schema, ognuno con pagina e riquadro"],
      ["LuShieldCheck", "Verificatore", "Sempre, su ogni proposta", "Il valore è nel testo? ISIN valido? I conti tornano?"],
      ["LuMail", "Redattore", "Lacune e rapporto", "Bozza della lettera alla banca e della sintesi"],
    ];
    for (let i = 0; i < 4; i++) {
      const y = 1.7 + i * 1.12;
      s.addShape(pres.shapes.LINE, { x: 3.6, y: y + 0.48, w: 0.4, h: 0, line: { color: X.muted, width: 1.25, endArrowType: "triangle" }, objectName: "ar" + i });
      const ver = i === 2;
      card(s, 4.0, y, 8.7, 0.96, ver ? X.tealSoft : X.bg, ag[i][1]);
      await iconIn(s, 4.15, y + 0.18, 0.6, ag[i][0], X.white, ver ? X.teal : X.navy, ag[i][1]);
      s.addText(ag[i][1], tb({ x: 4.95, y: y + 0.1, w: 2.6, h: 0.4, fontSize: 15, bold: true, color: C.text2 }));
      s.addText(ver ? "Codice deterministico" : "Modello AI", tb({ x: 4.95, y: y + 0.52, w: 2.6, h: 0.3, fontSize: 11, bold: true, color: ver ? C.accent1 : C.accent2 }));
      s.addText([{ text: "Quando: ", options: { color: C.accent6 } }, { text: ag[i][2], options: { breakLine: true } }, { text: "Produce: ", options: { color: C.accent6 } }, { text: ag[i][3] }], tb({ x: 7.7, y: y + 0.1, w: 4.9, h: 0.8, fontSize: 12, valign: "middle" }));
    }
    note(s, "Il testo dei documenti è sempre trattato come dato, mai come istruzione per un agente. Gli agenti non toccano i calcoli né l'approvazione.", 6.3);
    s.addNotes("Proposta coerente con la ricerca (EXTRACTION_TOOLING.md, punto 4: LLM solo su testo strutturato, dietro l'interruttore privacy, numeri ricontrollati dal codice). Il Verificatore è il pezzo che rende sicuro tutto il resto e si può costruire subito, anche senza agenti.");
  }

  // ============================================================ OGNI DOCUMENTO
  pres.addSection({ title: S.gen });
  {
    const s = content("Generalizzare", "Non un programma per banca: famiglie di documenti con uno schema", S.gen);
    const fam = [
      ["LuWallet", "Estratto patrimoniale", "ISIN, quantità, valore, data, totale"],
      ["LuReceipt", "Rendiconto costi ed estratto conto", "Tipo di costo, periodo, importo, IVA"],
      ["LuFileSignature", "Tariffario e contratto", "Aliquota di custodia, courtage, minimi, entità"],
      ["LuPieChart", "KID di fondi ed ETF", "ISIN, costi correnti, transazione, ingresso, uscita"],
      ["LuBoxes", "Termsheet di strutturati", "ISIN, costo di ingresso, distribuzione"],
      ["LuHelpCircle", "Sconosciuto", "Lo dice apertamente; il tipo lo sceglie una persona"],
    ];
    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.6 + col * 4.1, y = 1.65 + row * 1.55;
      const unk = i === 5;
      card(s, x, y, 3.85, 1.35, unk ? X.amberSoft : X.bg, fam[i][1]);
      await iconIn(s, x + 0.2, y + 0.2, 0.55, fam[i][0], X.white, unk ? X.amber : X.teal, fam[i][1]);
      s.addText(fam[i][1], tb({ x: x + 0.9, y: y + 0.15, w: 2.85, h: 0.6, fontSize: 15, bold: true, color: C.text2, valign: "middle" }));
      s.addText(fam[i][2], tb({ x: x + 0.9, y: y + 0.78, w: 2.85, h: 0.5, fontSize: 12, color: C.accent6 }));
    }
    const flow = [["Un documento qualsiasi", "LuFile"], ["Una famiglia", "LuFolderTree"], ["I campi chiave della famiglia", "LuListChecks"], ["Lo stesso registro dei costi", "LuLayers"]];
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.1;
      s.addImage({ data: await icon(flow[i][1], X.navy), x, y: 5.0, w: 0.4, h: 0.4, objectName: "f" + i });
      s.addText(flow[i][0], tb({ x: x + 0.5, y: 4.95, w: 2.2, h: 0.5, fontSize: 14, bold: true, valign: "middle" }));
      if (i < 3) s.addShape(pres.shapes.LINE, { x: x + 2.65, y: 5.2, w: 0.35, h: 0, line: { color: X.muted, width: 1.25, endArrowType: "triangle" }, objectName: "fl" + i });
    }
    card(s, 0.6, 5.7, 12.1, 0.7, X.tealSoft, "goal");
    s.addText([{ text: "L'obiettivo  ", options: { bold: true, color: C.accent1, fontSize: 13 } }, { text: "una banca nuova richiede parole chiave e test, non un nuovo programma. Il vocabolario copre italiano, tedesco, francese e inglese.", options: { fontSize: 15, bold: true, color: C.text2 } }], tb({ x: 0.9, y: 5.7, w: 11.6, h: 0.7, valign: "middle" }));
    s.addNotes("Tassonomia completa: 31 tipi di documento (data/taxonomy/document_types.csv) raggruppati nelle sei famiglie che il motore riconosce oggi. Factsheet e prospetti non hanno ancora un parser: il sistema li riconosce come tali e consiglia di usare il KID per i costi.");
  }

  // ============================================================ RISULTATI REALI
  pres.addSection({ title: S.res });
  {
    const s = content("Risultati reali", "Messo alla prova su 72 PDF pubblici di 58 emittenti", S.res);
    const big = [["0", "errori bloccanti", "su 72 file", X.teal], ["63/72", "tipo riconosciuto", "il resto: «sconosciuto», detto apertamente", X.navy], ["189/189", "valori con riquadro", "ogni valore estratto ha la sua posizione", X.teal], ["26/31", "valori attesi corretti", "letti da una persona sulla pagina", X.navy]];
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.075;
      card(s, x, 1.65, 2.85, 1.85, X.bg, big[i][1]);
      s.addText(big[i][0], tb({ x: x + 0.25, y: 1.8, w: 2.5, h: 0.75, fontSize: 38, bold: true, color: big[i][3] }));
      s.addText(big[i][1], tb({ x: x + 0.25, y: 2.55, w: 2.5, h: 0.35, fontSize: 15, bold: true }));
      s.addText(big[i][2], tb({ x: x + 0.25, y: 2.9, w: 2.5, h: 0.5, fontSize: 11.5, color: C.accent6 }));
    }
    // per family: files with >=1 value
    const fam = [["KID di fondi ed ETF", 23, 25], ["Tariffari bancari", 14, 24], ["Informative sui costi", 3, 5], ["Strutturati (KID e termsheet)", 4, 10], ["Factsheet", 0, 6], ["KID assicurativi", 0, 2]];
    s.addText("FILE CON ALMENO UN VALORE ESTRATTO, PER FAMIGLIA", tb({ x: 0.6, y: 3.8, w: 7, h: 0.25, fontSize: 10, bold: true, color: C.accent6, charSpacing: 1 }));
    fam.forEach((f, j) => {
      const y = 4.12 + j * 0.38, bw = 3.6, r = f[1] / f[2];
      s.addText(f[0], tb({ x: 0.6, y, w: 2.8, h: 0.34, fontSize: 12.5, valign: "middle" }));
      s.addShape(pres.shapes.RECTANGLE, { x: 3.45, y: y + 0.07, w: bw, h: 0.2, fill: { color: X.mutedSurface }, line: { color: X.mutedSurface }, objectName: "bb" + j });
      if (r > 0) s.addShape(pres.shapes.RECTANGLE, { x: 3.45, y: y + 0.07, w: bw * r, h: 0.2, fill: { color: r > 0.8 ? X.teal : r > 0.4 ? X.navy : X.amber }, line: { type: "none" }, objectName: "bf" + j });
      s.addText(`${f[1]}/${f[2]}`, tb({ x: 7.15, y, w: 0.8, h: 0.34, fontSize: 12.5, bold: true, valign: "middle" }));
    });
    card(s, 8.3, 3.8, 4.4, 2.55, X.amberSoft, "weak");
    s.addImage({ data: await icon("LuAlertTriangle", X.amber), x: 8.5, y: 3.98, w: 0.36, h: 0.36, objectName: "warn" });
    s.addText("Il punto debole: i tariffari", tb({ x: 8.95, y: 3.95, w: 3.6, h: 0.4, fontSize: 15, bold: true, color: C.accent2 }));
    s.addText([
      { text: "Scaglioni di courtage ZKB letti come custodia", options: { bullet: true, breakLine: true } },
      { text: "Un «-2» preso da una nota a piè di pagina", options: { bullet: true, breakLine: true } },
      { text: "Investimenti minimi letti come commissioni minime", options: { bullet: true, breakLine: true } },
      { text: "Factsheet, polizze, strutturati: quasi nulla", options: { bullet: true } },
    ], tb({ x: 8.5, y: 4.45, w: 4.05, h: 1.85, fontSize: 12.5, paraSpaceAfter: 3 }));
    note(s, "Corpus del 6.11.2026 (PR #7), motore pce-rules-0.1. Prima delle correzioni nate da questo test: 45/72 tipi giusti e 13/31 valori attesi.", 6.6);
    s.addNotes("Le metriche sono oneste: nessun caso reale di cliente è ancora stato misurato. I 72 PDF sono documenti pubblici (KID in 4 lingue, tariffari CH/IT/UE, informative FinSA/MiFID, termsheet, KID assicurativi); i file non sono nel repository, un manifest li riscarica e ne verifica l'impronta.");
  }

  // ============================================================ PROSSIMI PASSI
  pres.addSection({ title: S.next });
  {
    const s = content("Semplificare", "Come teniamo il sistema semplice, anche quando cresce", S.next);
    const p = [
      ["LuFolderTree", "Famiglie, non banche", "Sei schemi di campi coprono tutti i documenti; una banca nuova è vocabolario e test."],
      ["LuCpu", "Regole prima, AI dopo", "L'AI interviene solo dove le regole non bastano, e solo se migliora le misure."],
      ["LuUserCheck", "Persone solo sulle eccezioni", "Revisione dei valori segnalati e approvazione finale. Il resto è automatico."],
      ["LuMonitor", "Una schermata per passo", "Ogni passo della pipeline ha la sua pagina nell'app, con la prova a un clic."],
    ];
    for (let i = 0; i < 4; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.6 + col * 6.15, y = 1.65 + row * 2.3;
      card(s, x, y, 5.95, 2.05, X.bg, p[i][1]);
      await iconIn(s, x + 0.3, y + 0.3, 0.7, p[i][0], X.white, X.teal, p[i][1]);
      s.addText(p[i][1], tb({ x: x + 1.25, y: y + 0.32, w: 4.5, h: 0.5, fontSize: 19, bold: true, color: C.text2, valign: "middle" }));
      s.addText(p[i][2], tb({ x: x + 1.25, y: y + 0.9, w: 4.5, h: 1.0, fontSize: 14 }));
    }
    s.addNotes("Il criterio di ogni aggiunta: deve migliorare una misura del corpus o togliere lavoro alla persona, senza aggiungere schermate.");
  }
  {
    const s = content("Prossimi passi tecnici", "Cinque passi, in ordine di valore", S.next);
    const r = [
      ["Precisione dei tariffari", "Distinguere custodia da courtage e ignorare note e minimi d'investimento. Test su ogni caso del corpus.", "Subito"],
      ["Verificatore come servizio", "Il controllo «il valore è sulla pagina» diventa il cancello unico per regole, modelli e agenti.", "Subito"],
      ["Docling come seconda opinione", "Sulle tabelle complesse; i disaccordi vanno in revisione, non a una scelta silenziosa.", "Dopo"],
      ["Benchmark di un modello visivo locale", "Solo sulle scansioni difficili, misurato campo per campo.", "Dopo"],
      ["Casi reali anonimizzati", "Da 1 a 3 casi di Safe Capital: la vera misura di precisione e tempi.", "Pilota"],
    ];
    r.forEach((x, j) => {
      const y = 1.65 + j * 0.92;
      if (j) s.addShape(pres.shapes.LINE, { x: 0.6, y: y - 0.06, w: 12.1, h: 0, line: { color: X.border, width: 0.5 }, objectName: "rl" + j });
      badge(s, 0.6, y + 0.2, j + 1, 0.4, j < 2 ? X.teal : j < 4 ? X.navy : X.amber);
      s.addText(x[0], tb({ x: 1.25, y: y + 0.08, w: 3.8, h: 0.6, fontSize: 17, bold: true, color: C.text2, valign: "middle" }));
      s.addText(x[1], tb({ x: 5.1, y: y + 0.05, w: 6.0, h: 0.75, fontSize: 13.5, valign: "middle" }));
      chip(s, 11.4, y + 0.22, x[2], j < 2 ? "acc" : j < 4 ? "con" : "est", 1.3, 0.34, 11);
    });
    s.addNotes("I primi due passi sono lavoro di codice senza nuove dipendenze. Il terzo e il quarto richiedono installazioni più pesanti (PyTorch) e si fanno solo se il corpus dimostra un guadagno.");
  }
  {
    const s = pres.addSlide({ masterName: "Dark", sectionTitle: S.next });
    s.addText("IN SINTESI", tb({ x: 0.8, y: 0.7, w: 8, h: 0.35, fontSize: 14, bold: true, color: X.tealLight, charSpacing: 3 }));
    s.addText("Un motore semplice e verificabile, pronto per un caso reale", tb({ x: 0.8, y: 1.1, w: 11.5, h: 1.0, fontSize: 36, bold: true, color: C.background1 }));
    const k = [["Funziona oggi", "Otto passi, app in italiano e inglese, 14 test end-to-end superati."], ["Misurato", "72 PDF reali: tipi 63/72, valori attesi 26/31, punto debole noto."], ["Sicuro per costruzione", "Locale, nessuna AI esterna di default, ogni numero con la sua prova."]];
    for (let i = 0; i < 3; i++) {
      const x = 0.8 + i * 3.95;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.6, w: 3.7, h: 1.9, rectRadius: 0.06, fill: { color: X.panel }, line: { color: X.panel }, objectName: "k" + i });
      s.addText(k[i][0], tb({ x: x + 0.3, y: 2.85, w: 3.1, h: 0.45, fontSize: 19, bold: true, color: C.background1 }));
      s.addText(k[i][1], tb({ x: x + 0.3, y: 3.4, w: 3.1, h: 1.0, fontSize: 14, color: X.paleNavy }));
    }
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.8, y: 4.95, w: 11.55, h: 1.1, rectRadius: 0.08, fill: { color: X.teal }, line: { color: X.teal }, objectName: "cta" });
    s.addText([{ text: "PROSSIMO PASSO  ", options: { bold: true, fontSize: 13, color: "CDEDE8", charSpacing: 2 } }, { text: "correggere i tariffari e misurare il sistema su un primo caso reale anonimizzato.", options: { bold: true, fontSize: 19, color: C.background1 } }], tb({ x: 1.1, y: 4.95, w: 11.0, h: 1.1, valign: "middle" }));
    s.addNotes("Test E2E: 14 superati il 6.11.2026 sul branch dell'app (CRM, caricamento, riquadri, costi, confronto, rapporto PDF, ruoli, isolamento tra società, interfaccia italiana).");
  }

  // ============================================================ APPROFONDIMENTI
  pres.addSection({ title: S.app });
  {
    const s = content("Approfondimento · strumenti", "Gli strumenti di lettura e le loro licenze", S.app);
    table(s, ["BISOGNO", "STRUMENTO", "LICENZA", "NOTA"], [
      ["Parole e tabelle semplici, PDF digitali", "pdfplumber 0.11", "MIT", "Fonte dei riquadri"],
      ["Rendering delle pagine", "pypdfium2 5.15", "Apache-2.0 / BSD", "Immagini per OCR e visore"],
      ["Layout e tabelle complesse", "Docling 2.148 (opzionale)", "MIT", "Seconda opinione"],
      ["Scansioni", "OCRmyPDF 17 + Tesseract 5", "MPL-2.0 / Apache-2.0", "Processo separato, IT DE FR EN"],
      ["Excel, CSV", "openpyxl, xlrd, pandas", "MIT / BSD", "Foglio e cella come prova"],
      ["ISIN", "python-stdnum", "LGPL-2.1+", "Cifra di controllo"],
      ["Visore nel browser", "PDF.js", "Apache-2.0", ""],
      ["Scansioni difficili", "PaddleOCR-VL (candidato)", "Apache-2.0", "Solo dopo benchmark"],
      [{ text: "Escluso", options: { fontSize: 12, bold: true, color: X.red } }, { text: "PyMuPDF, OCR in cloud", options: { fontSize: 12, color: X.red } }, { text: "AGPL / dati fuori", options: { fontSize: 12, color: X.red } }, { text: "ADR 0003 e 0004", options: { fontSize: 12, color: X.red } }],
    ], { x: 0.6, y: 1.6, w: 12.1, colW: [3.6, 3.3, 2.4, 2.8], rowH: 0.48 });
    s.addNotes("Fonte: docs/adr/0003-document-extraction-and-ocr.md e backend/src/pce/extraction/toolchain.py (controllo dello stato: python -m pce.extraction.toolchain).");
  }
  {
    const s = content("Approfondimento · regole", "Le regole fisse dell'estrazione", S.app);
    const r = [
      ["Ogni valore ha la sua prova", "Impronta del documento, pagina e riquadro (o foglio e cella). Senza riquadro non entra nel registro."],
      ["Mai coordinate inventate", "Se un motore non le dà, il valore va in revisione."],
      ["I file non sono fidati", "Tipo MIME controllato, limiti di dimensione e pagine, PDF cifrati respinti, nessun contenuto eseguito."],
      ["Il testo è un dato", "Niente di ciò che c'è in un documento è un'istruzione per un modello o un agente."],
      ["ISIN controllati", "Formato e cifra di controllo. Un ISIN valido non prova che la riga sia un fondo."],
      ["Online solo ISIN", "Le ricerche pubbliche (KID) inviano solo ISIN, a siti autorizzati. Mai importi o nomi."],
      ["Log senza contenuti", "Solo identificativi, impronte, conteggi e tempi."],
    ];
    r.forEach((x, j) => {
      const y = 1.6 + j * 0.68;
      if (j) s.addShape(pres.shapes.LINE, { x: 0.6, y: y - 0.05, w: 12.1, h: 0, line: { color: X.border, width: 0.5 }, objectName: "x" + j });
      s.addText(x[0], tb({ x: 0.6, y, w: 3.6, h: 0.58, fontSize: 15, bold: true, color: C.text2, valign: "middle" }));
      s.addText(x[1], tb({ x: 4.3, y, w: 8.4, h: 0.58, fontSize: 13.5, valign: "middle" }));
    });
    s.addNotes("Fonte: .claude/rules/extraction.md sul branch dell'app.");
  }
  {
    const s = content("Approfondimento · stati", "Otto stati di misura, e cosa entra nel totale", S.app);
    table(s, ["STATO", "SIGNIFICA", "NEL TOTALE"], [
      [{ text: "Rilevato", options: { bold: true, color: X.green, fontSize: 12 } }, "Addebitato e documentato (estratto, avviso, rendiconto)", "Sì"],
      [{ text: "Contrattuale", options: { bold: true, color: X.navy, fontSize: 12 } }, "Dal contratto o tariffario del cliente, non visto addebitato", "Sì"],
      [{ text: "Tariffa pubblica", options: { bold: true, color: X.navy, fontSize: 12 } }, "Prezzo di listino della banca: prova debole per questo cliente", "Sì, segnalato"],
      [{ text: "Stimato", options: { bold: true, color: X.amber, fontSize: 12 } }, "Da un'informativa datata, es. costi correnti del KID × valore", "Sì"],
      [{ text: "Illustrativo", options: { bold: true, color: X.muted, fontSize: 12 } }, "Esempio ipotetico dell'emittente", "No"],
      [{ text: "Massimo", options: { bold: true, color: X.muted, fontSize: 12 } }, "Limite dichiarato, es. ingresso fino al 3%", "No"],
      [{ text: "Non determinato", options: { bold: true, color: X.red, fontSize: 12 } }, "Il costo esiste ma manca la prova", "Mai zero: elencato a parte"],
      [{ text: "Non applicabile", options: { bold: true, color: X.muted, fontSize: 12 } }, "La categoria non esiste per questo cliente", "No"],
    ], { x: 0.6, y: 1.6, w: 12.1, colW: [2.6, 6.8, 2.7], rowH: 0.52 });
    note(s, "Ruoli di un atomo: contato, incluso nel genitore, corrobora, non determinato, non applicabile, non è un costo pagato, una tantum.", 6.45);
    s.addNotes("Fonte: backend/src/pce/finance/ledger.py (Measurement, Incidence, Layer, AtomRole).");
  }
  {
    const s = content("Approfondimento · corpus", "Risultati per categoria, 72 PDF", S.app);
    const rows = [
      ["KID fondi attivi", "6", "6/6", "6/6", "16", "4/5"],
      ["KID ETF", "16", "16/16", "14/16", "27", "15/17"],
      ["KID svizzeri (FIDLEG)", "3", "3/3", "3/3", "6", "1/3"],
      ["Tariffari CH", "12", "8/12", "6/12", "58", "3/3"],
      ["Tariffari UE e altri", "5", "5/5", "4/5", "41", "3/3"],
      ["Tariffari IT", "7", "7/7", "4/7", "23", "–"],
      ["Informative sui costi", "5", "3/5", "3/5", "14", "–"],
      ["Factsheet", "6", "5/6", "0/6", "0", "–"],
      ["KID assicurativi", "2", "2/2", "0/2", "0", "–"],
      ["KID strutturati", "3", "2/3", "2/3", "2", "–"],
      ["Termsheet strutturati", "7", "6/7", "2/7", "2", "–"],
      [{ text: "Totale", options: { bold: true, fontSize: 12 } }, { text: "72", options: { bold: true, fontSize: 12 } }, { text: "63/72", options: { bold: true, fontSize: 12 } }, { text: "44/72", options: { bold: true, fontSize: 12 } }, { text: "189", options: { bold: true, fontSize: 12 } }, { text: "26/31", options: { bold: true, fontSize: 12 } }],
    ];
    table(s, ["CATEGORIA", "FILE", "TIPO GIUSTO", "≥1 VALORE", "VALORI", "ATTESI GIUSTI"], rows, { x: 0.6, y: 1.55, w: 12.1, colW: [3.9, 1.3, 1.8, 1.8, 1.5, 1.8], rowH: 0.37 });
    note(s, "Fonte: data/specimens/RESULTS.md (PR #7). «Tipo giusto» per i factsheet significa che il sistema ha risposto «sconosciuto», come previsto.", 6.55);
    s.addNotes("Tempi: la maggior parte dei file in meno di un secondo; il più lento 16,6 secondi (tariffario con una pagina in OCR).");
  }
  {
    const s = content("Approfondimento · privacy", "Dove gira e cosa non esce mai", S.app);
    const r = [
      ["LuLaptop", "Locale per default", "App ed estrazione sul PC o server di Safe Capital. Un server privato in Svizzera per più utenti."],
      ["LuCloudOff", "Nessuna AI esterna", "Spenta di default. Accenderla richiede una decisione documentata; anche allora solo regioni oscurate."],
      ["LuLock", "Dati protetti", "Archivio cifrato, conservazione limitata (proposta: 90 giorni), cancellazione completa, registro degli accessi."],
      ["LuUsers", "Separazione", "Ogni riga ha società e prospect; un test prova che un'altra società non può leggere."],
    ];
    for (let i = 0; i < 4; i++) {
      const y = 1.65 + i * 1.15;
      await iconIn(s, 0.6, y, 0.7, r[i][0], X.tealSoft, X.teal, r[i][1]);
      s.addText(r[i][1], tb({ x: 1.55, y: y + 0.02, w: 3.4, h: 0.65, fontSize: 17, bold: true, color: C.text2, valign: "middle" }));
      s.addText(r[i][2], tb({ x: 5.0, y: y + 0.02, w: 7.7, h: 0.65, fontSize: 14, valign: "middle" }));
    }
    note(s, "Politica tecnica (ADR 0004), non consulenza legale: la compliance di Safe Capital deve confermarla prima di usare dati reali.", 6.4);
    s.addNotes("Fonte: docs/adr/0004-privacy-local-first.md.");
  }

  await pres.writeFile({ fileName: OUT });
  if (process.env.APPLY_THEME_JS) { const { applyTheme } = require(process.env.APPLY_THEME_JS); await applyTheme(OUT, THEME); }
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
