// Builds the FeeLens proposal deck for Safe Capital (Massimo): a visual tutorial of the app, honest accuracy,
// where it runs, personal data, pilot and price. One source, two languages:
//   DECK_LANG=it node build_proposal.js   -> ../FeeLens_Proposta_IT.pptx
//   DECK_LANG=en node build_proposal.js   -> ../FeeLens_Proposal_EN.pptx
// Screenshots: img/proposal/<lang>/, taken from main (after PR #43) plus the firm tariff branch (PR #40), 2026-11-13.
//   - Prospects P-1042 and P-2077 are SYNTHETIC (pinned in backend/tests/test_pipeline.py).
//   - "Public sample documents (real)" uses real public documents: AJ Bell demo client report, BlackRock iShares
//     KIDs (one re-scanned as an image to show OCR), Julius Baer Europe price list. URLs in slides/README.md.
// Accuracy figures: main re-run of 2026-11-13 (pce.evaluation, 62 pages / 896 fees), data/specimens/arena/RESULTS.md,
// data/specimens/statements/RESULTS.md.
// Prices: proposal from the pricing thread (doc "FeeLens pricing for Safe Capital", 2026-11-13), not yet approved.
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const LANG = (process.env.DECK_LANG || "it").toLowerCase() === "en" ? "en" : "it";
const T = (it, en) => (LANG === "it" ? it : en);
const OUT = path.resolve(__dirname, "..", LANG === "it" ? "FeeLens_Proposta_IT.pptx" : "FeeLens_Proposal_EN.pptx");
const SHOT = (n) => path.join(__dirname, "img", "proposal", LANG, n + ".jpg");

const X = {
  text: "14202E", navy: "0F2A4A", teal: "0F766E", tealSoft: "E3F2F0", amber: "B45309", amberSoft: "FDF3E2",
  red: "B42318", redSoft: "FDECEA", green: "1E7A46", greenSoft: "E7F4EC", muted: "5B6676", bg: "F7F6F2",
  border: "DEDAD1", white: "FFFFFF", infoSoft: "E6ECF4", paleNavy: "9FB3C8",
};

async function icon(name, color, size = 256) {
  const Cmp = lu[name] || lu.LuCircle;
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Cmp, { color: "#" + color, size: String(size), strokeWidth: 1.75 }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
function imgSize(file) {
  const b = fs.readFileSync(file);
  // JPEG: walk the markers to the SOF frame
  let i = 2;
  while (i < b.length) {
    const m = b[i + 1], len = b.readUInt16BE(i + 2);
    if (m >= 0xc0 && m <= 0xc3) return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
    i += 2 + len;
  }
  throw new Error("no size " + file);
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
  pres.title = T("FeeLens · proposta per Safe Capital", "FeeLens · proposal for Safe Capital");
  pres.author = "FeeLens"; pres.company = "FeeLens";
  pres.theme = { headFontFace: "Calibri", bodyFontFace: "Calibri" };

  pres.defineSlideMaster({ title: "Dark", background: { color: X.navy }, objects: [] });
  pres.defineSlideMaster({
    title: "Content", background: { color: X.white },
    objects: [
      { text: { text: T("FeeLens · proposta per Safe Capital · clienti P-1042 e P-2077 sintetici, documenti pubblici reali", "FeeLens · proposal for Safe Capital · prospects P-1042 and P-2077 synthetic, public documents real"), options: { x: 0.5, y: 7.08, w: 10.5, h: 0.25, fontSize: 9, color: X.muted, margin: 0 } } },
    ],
    slideNumber: { x: 12.3, y: 7.08, w: 0.55, h: 0.25, fontSize: 9, color: X.muted, align: "right" },
  });

  const sections = new Set();
  const addSlide = pres.addSlide.bind(pres);
  pres.addSlide = (o) => {
    if (o && o.sectionTitle && !sections.has(o.sectionTitle)) { pres.addSection({ title: o.sectionTitle }); sections.add(o.sectionTitle); }
    return addSlide(o);
  };
  const tb = (o) => Object.assign({ margin: 0, fontSize: 14, color: X.text, valign: "top", fontFace: "Calibri" }, o);
  const content = (kicker, title, section) => {
    const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
    s.addText(kicker.toUpperCase(), tb({ x: 0.5, y: 0.32, w: 11, h: 0.25, fontSize: 11, bold: true, color: X.teal, charSpacing: 2 }));
    s.addText(title, tb({ x: 0.5, y: 0.58, w: 12.3, h: 0.7, fontSize: 26, bold: true, color: X.navy }));
    return s;
  };
  // Square white cards with a hairline border; a tinted fill becomes a thin rule of its colour on top.
  const RULE = { [X.tealSoft]: X.teal, [X.amberSoft]: X.amber, [X.redSoft]: X.red, [X.greenSoft]: X.green, [X.infoSoft]: X.navy };
  const card = (s, x, y, w, h, fill, line) => {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: X.white }, line: { color: line || X.border, width: 0.75 } });
    const rule = RULE[fill];
    if (rule) s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.06, fill: { color: rule }, line: { color: rule, width: 0 } });
  };
  const badge = (s, x, y, n, d = 0.34, fill = X.amber) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: X.white, width: 1.5 } });
    s.addText(String(n), tb({ x, y, w: d, h: d, fontSize: 13, bold: true, color: X.white, align: "center", valign: "middle" }));
  };
  const iconTile = async (s, x, y, d, name, bg, fg) => {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg } });
    const p = d * 0.22;
    s.addImage({ data: await icon(name, fg), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p });
  };
  const chip = (s, x, y, text, fg, bg, w) => {
    const ww = w || Math.max(0.8, 0.085 * text.length + 0.3);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: ww, h: 0.28, fill: { color: bg }, line: { color: bg } });
    s.addText(text, tb({ x, y, w: ww, h: 0.28, fontSize: 10.5, bold: true, color: fg, align: "center", valign: "middle" }));
    return ww;
  };
  // Places a screenshot into a box, keeps its ratio, frames it, returns the placed rectangle.
  const shot = (s, name, box, crop) => {
    const f = SHOT(name);
    const { w, h } = imgSize(f);
    const r = Math.min(box.w / w, box.h / h);
    const rr = { x: box.x + (box.w - w * r) / 2, y: box.y, w: w * r, h: h * r };
    s.addImage({ path: f, ...rr, altText: name });
    s.addShape(pres.shapes.RECTANGLE, { ...rr, fill: { type: "none" }, line: { color: X.border, width: 0.75 } });
    return rr;
  };
  // Callout badges at CSS pixel positions of a 1440 x 900 screenshot.
  const marks = (s, rr, pts, cssW = 1440) => pts.forEach(([n, cx, cy]) => {
    const k = rr.w / cssW;
    badge(s, rr.x + cx * k - 0.17, rr.y + cy * k - 0.17, n);
  });
  // Right column: numbered steps, each "what to do" (bold) + "why" (grey).
  const steps = (s, items, x = 9.15, y = 1.5, w = 3.7, gap = 0.2) => {
    let yy = y;
    const perLine = Math.floor((w - 0.48) * 13);
    for (const [n, what, why] of items) {
      badge(s, x, yy, n);
      s.addText(what, tb({ x: x + 0.48, y: yy - 0.02, w: w - 0.48, h: 0.5, fontSize: 13.5, bold: true, color: X.navy }));
      const lines = Math.ceil(why.length / perLine);
      s.addText(why, tb({ x: x + 0.48, y: yy + 0.42, w: w - 0.48, h: 0.25 * lines + 0.1, fontSize: 11.5, color: X.muted }));
      yy += 0.55 + 0.21 * lines + gap;
    }
  };
  const tutorial = (kicker, title, name, pts, items, notes, extra) => {
    const s = content(kicker, title, T("Tutorial", "Tutorial"));
    const rr = shot(s, name, { x: 0.5, y: 1.45, w: 8.4, h: 5.25 });
    marks(s, rr, pts);
    steps(s, items);
    if (extra) extra(s, rr);
    if (notes) s.addNotes(notes);
    return s;
  };
  const bigNum = (s, x, y, w, num, label, color = X.navy, sub) => {
    card(s, x, y, w, sub ? 1.75 : 1.55, X.white);
    s.addText(num, tb({ x: x + 0.2, y: y + 0.15, w: w - 0.4, h: 0.7, fontSize: 34, bold: true, color }));
    s.addText(label, tb({ x: x + 0.2, y: y + 0.85, w: w - 0.4, h: 0.55, fontSize: 12, color: X.text }));
    if (sub) s.addText(sub, tb({ x: x + 0.2, y: y + 1.4, w: w - 0.4, h: 0.28, fontSize: 10, color: X.muted }));
  };

  // ---------- 1 Title ----------
  {
    const s = pres.addSlide({ masterName: "Dark", sectionTitle: T("Introduzione", "Introduction") });
    s.addText("FeeLens", tb({ x: 0.8, y: 1.6, w: 11, h: 1.1, fontSize: 60, bold: true, color: X.white }));
    s.addText(T("Quanto costa davvero il portafoglio di un potenziale cliente, con la fonte di ogni cifra.",
      "What a prospect's portfolio really costs, with the source of every figure."),
      tb({ x: 0.8, y: 2.8, w: 11, h: 1, fontSize: 26, color: X.white }));
    s.addText(T("Proposta per Safe Capital · come funziona, quanto è affidabile, come si usa, dove gira, quanto costa",
      "Proposal for Safe Capital · how it works, how accurate it is, how to use it, where it runs, what it costs"),
      tb({ x: 0.8, y: 4.1, w: 11, h: 0.6, fontSize: 16, color: X.paleNavy }));
    s.addText(T("Lugano, novembre 2026", "Lugano, November 2026"), tb({ x: 0.8, y: 6.4, w: 6, h: 0.4, fontSize: 14, color: X.paleNavy }));
    s.addNotes(T("Obiettivo dell'incontro: mostrare l'app passo per passo, dire con onestà cosa è pronto e cosa no, e proporre un pilota supervisionato.",
      "Goal of the meeting: walk through the app step by step, say honestly what is ready and what is not, and propose a supervised pilot."));
  }

  // ---------- 2 In short ----------
  {
    const s = content(T("In breve", "In short"), T("Quattro cose da sapere", "Four things to know"), T("Introduzione", "Introduction"));
    const items = [
      ["LuFileSearch", T("Cosa fa", "What it does"), T("Legge estratti, rendiconti costi, tariffari e KID di qualsiasi banca. Calcola il costo annuo completo e lo confronta con la vostra proposta.", "Reads statements, cost reports, price lists and KIDs from any bank. Works out the all-in annual cost and compares it with your proposal.")],
      ["LuMousePointerClick", T("Ogni cifra ha la sua fonte", "Every figure has its source"), T("Un clic su un numero mostra il calcolo e il punto esatto della pagina da cui viene. Un costo mancante resta mancante, mai zero.", "One click on a number shows the calculation and the exact spot on the page it came from. A missing cost stays missing, never zero.")],
      ["LuUserCheck", T("Aiuta l'analista, non lo sostituisce", "It assists the analyst, it does not replace them"), T("Trova l'87% dei costi su pagine reali (91% su pagine mai viste). Una persona accetta ogni cifra prima che conti, e due persone controllano ogni rapporto.", "Finds 87% of fees on real pages (91% on pages it had never seen). A person accepts each figure before it counts, and two people check every report.")],
      ["LuFlag", T("Proposta: pilota di 3 mesi", "Proposal: a 3-month pilot"), T("Su un computer di Safe Capital, 10 potenziali clienti, CHF 3'000. Poi licenza annuale da CHF 9'000.", "On a Safe Capital machine, 10 prospects, CHF 3,000. Then an annual licence from CHF 9,000.")],
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.5 + (i % 2) * 6.2, y = 1.55 + Math.floor(i / 2) * 2.65;
      card(s, x, y, 6.0, 2.45, X.bg);
      await iconTile(s, x + 0.3, y + 0.3, 0.7, items[i][0], X.tealSoft, X.teal);
      s.addText(items[i][1], tb({ x: x + 1.2, y: y + 0.35, w: 4.6, h: 0.6, fontSize: 18, bold: true, color: X.navy }));
      s.addText(items[i][2], tb({ x: x + 1.2, y: y + 1.0, w: 4.6, h: 1.3, fontSize: 13.5 }));
    }
  }

  // ---------- 3 The problem ----------
  {
    const s = content(T("Il problema", "The problem"), T("I costi di un cliente sono sparsi in tre posti", "A client's costs sit in three places"), T("Introduzione", "Introduction"));
    const cols = [
      [T("Addebitati sul conto", "Debited from the account"), T("Gestione o consulenza, custodia, tenuta conto, IVA. Negli estratti conto e nel rendiconto annuale dei costi.", "Management or advisory, custody, account fees, VAT. In cash statements and the annual cost report."), "LuLandmark"],
      [T("Dentro i prodotti", "Inside the products"), T("Costi correnti di fondi ed ETF (TER/OCF), margine dei prodotti strutturati. Non si vedono sul conto: sono nel KID.", "Ongoing costs of funds and ETFs (TER/OCF), the margin in structured products. Never on the account: they are in the KID."), "LuPackage"],
      [T("Nelle operazioni", "In the trades"), T("Commissioni di borsa, cambi, bolli, costi di trasferimento. Nel tariffario della banca che tiene il conto.", "Brokerage, FX, stamp duty, transfer fees. In the price list of the bank that books the account."), "LuArrowLeftRight"],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.5 + i * 4.15;
      card(s, x, 1.6, 3.95, 3.3, X.bg);
      await iconTile(s, x + 0.3, 1.9, 0.65, cols[i][2], X.infoSoft, X.navy);
      s.addText(cols[i][0], tb({ x: x + 0.3, y: 2.75, w: 3.4, h: 0.5, fontSize: 18, bold: true, color: X.navy }));
      s.addText(cols[i][1], tb({ x: x + 0.3, y: 3.3, w: 3.4, h: 1.5, fontSize: 13.5 }));
    }
    card(s, 0.5, 5.2, 12.35, 1.45, X.tealSoft);
    s.addText(T("Oggi un analista impiega ore a mettere insieme questi pezzi, e un costo che non trova finisce spesso per valere zero. FeeLens li raccoglie, li cita e dice cosa manca.",
      "Today an analyst spends hours putting these pieces together, and a cost they cannot find often ends up as zero. FeeLens collects them, cites them and says what is missing."),
      tb({ x: 0.8, y: 5.4, w: 11.8, h: 1.1, fontSize: 16, color: X.navy, valign: "middle" }));
  }

  // ---------- 4 How it works ----------
  {
    const s = content(T("Come funziona", "How it works"), T("La vostra tariffa una volta, poi cinque passi per ogni cliente", "Your tariff once, then five steps for every client"), T("Introduzione", "Introduction"));
    const st = [
      ["LuPercent", T("Vostra tariffa", "Your tariff"), T("Una volta sola: commissioni, custodia, cambi, IVA di Safe Capital.", "Once only: Safe Capital's fees, custody, FX, VAT.")],
      ["LuUpload", T("Documenti", "Documents"), T("Caricate i PDF (anche scansioni) o Excel del cliente.", "Upload the client's PDFs (scans too) or Excel files.")],
      ["LuSearchCheck", T("Verifica valori", "Check values"), T("Ogni valore letto, con il riquadro sulla pagina. Accettate, correggete o scartate.", "Every value read, boxed on the page. Accept, correct or reject.")],
      ["LuCalculator", T("Costi", "Costs"), T("Costo annuo noto, cosa manca, punti da verificare.", "Known annual cost, what is missing, points to review.")],
      ["LuScale", T("Confronto", "Compare"), T("Stesse posizioni, con la vostra tariffa. Risparmio come limite minimo.", "Same holdings at your tariff. Saving as a lower bound.")],
      ["LuFileCheck", T("Rapporto", "Report"), T("Un senior approva, PDF in italiano o inglese.", "A senior approves; PDF in Italian or English.")],
    ];
    for (let i = 0; i < 6; i++) {
      const x = 0.5 + i * 2.07;
      card(s, x, 1.7, 1.92, 3.2, i === 0 ? X.tealSoft : X.bg);
      await iconTile(s, x + 0.22, 1.95, 0.62, st[i][0], X.tealSoft, X.teal);
      if (i) badge(s, x + 1.4, 1.95, i, 0.32, X.navy);
      s.addText(st[i][1], tb({ x: x + 0.22, y: 2.8, w: 1.6, h: 0.45, fontSize: 15, bold: true, color: X.navy }));
      s.addText(st[i][2], tb({ x: x + 0.22, y: 3.3, w: 1.6, h: 1.55, fontSize: 12 }));
    }
    const rules = [
      [T("Nessuna fonte, nessuna cifra verificata.", "No source, no verified figure."), X.navy],
      [T("Mancante non vuol dire zero.", "Missing is never zero."), X.red],
      [T("Nessun servizio comparabile, nessun risparmio dichiarato.", "No comparable service, no savings claim."), X.teal],
    ];
    rules.forEach(([t, c], i) => {
      card(s, 0.5 + i * 4.15, 5.25, 3.95, 1.0, X.white, X.border);
      s.addText(t, tb({ x: 0.7 + i * 4.15, y: 5.3, w: 3.6, h: 0.9, fontSize: 15, bold: true, color: c, valign: "middle" }));
    });
    s.addText(T("Le tre regole del prodotto", "The three product rules"), tb({ x: 0.5, y: 6.35, w: 6, h: 0.3, fontSize: 11, color: X.muted }));
  }

  // ---------- Tutorial ----------
  const R = T("Documenti pubblici reali", "Real public documents");
  const S = T("Cliente sintetico P-1042", "Synthetic prospect P-1042");
  const src = (s, text) => s.addText(text, tb({ x: 0.5, y: 6.75, w: 8.4, h: 0.25, fontSize: 9.5, italic: true, color: X.muted }));

  tutorial(T("Tutorial · 1 Clienti", "Tutorial · 1 Clients"), T("Si parte dai clienti: ogni relazione e a che punto è", "Start from your clients: every relationship and where it stands"), "01-crm",
    [[1, 90, 137], [2, 1272, 625], [3, 1250, 78]],
    [[1, T("«Analisi dei costi» nel menu", "\"Cost reviews\" in the menu"), T("Tutte le analisi in corso, con patrimonio, costo noto e risparmio.", "All cost reviews in progress, with assets, known cost and saving.")],
     [2, T("La scheda «Analisi costi»", "The \"Cost review\" chip"), T("Un clic apre l'analisi di quel cliente.", "One click opens that client's review.")],
     [3, T("«Nuovo contatto»", "\"New contact\""), T("Un potenziale cliente entra qui; il funnel mostra dove si perdono.", "A prospect starts here; the funnel shows where prospects drop out.")]],
    T("Il CRM è la pagina iniziale, come richiesto. I contatti mostrati sono sintetici.", "The CRM is the home page, as requested. The contacts shown are synthetic."));

  {
    const s = tutorial(T("Tutorial · 2 La vostra tariffa", "Tutorial · 2 Your tariff"), T("La tariffa di Safe Capital si inserisce una volta sola", "Safe Capital's tariff is entered once"), "02-firm-tariff",
      [[1, 80, 205], [2, 580, 390], [3, 970, 230], [4, 1287, 100]],
      [[1, T("«Tariffa della società» nel menu", "\"Firm tariff\" in the menu"), T("I vostri prezzi, validi per tutta la società.", "Your prices, for the whole firm.")],
       [2, T("Fasce della commissione di gestione", "Management fee bands"), T("Marginali o sull'intero patrimonio, come nel vostro contratto.", "Marginal or on the whole portfolio, as in your agreement.")],
       [3, T("Custodia, negoziazione, cambi, IVA", "Custody, trading, FX, VAT"), T("Con il minimo annuo della banca depositaria partner.", "With the partner custodian's annual minimum.")],
       [4, T("«Salva la tariffa»", "\"Save firm tariff\""), T("Solo un senior. Ogni nuova analisi parte da qui; un caso singolo si può ancora adattare.", "Seniors only. Every new review starts from it; one case can still be adjusted.")]],
      T("Prezzi mostrati: tariffa demo sintetica. Con il pilota inseriamo insieme la vostra tariffa reale.", "Prices shown: synthetic demo tariff. In the pilot we enter your real tariff together."));
    src(s, T("Prezzi dimostrativi, non la tariffa di Safe Capital.", "Demo prices, not Safe Capital's tariff."));
  }

  tutorial(T("Tutorial · 3 Nuova analisi", "Tutorial · 3 New review"), T("Nuova analisi: un codice, non un nome", "New review: a code, not a name"), "03-new-prospect",
    [[1, 720, 367], [2, 720, 562], [3, 826, 640]],
    [[1, T("Scrivete un codice, es. P-1043", "Type a code, e.g. P-1043"), T("Nomi, numeri di conto e IBAN non servono. Meno dati personali, meno rischio.", "Names, account numbers and IBANs are not needed. Less personal data, less risk.")],
     [2, T("Scegliete il domicilio fiscale", "Pick the tax domicile"), T("Decide se l'IVA svizzera dell'8.1% si applica ai costi proposti.", "Decides whether 8.1% Swiss VAT applies to the proposed fees.")],
     [3, T("«Crea e carica documenti»", "\"Create and upload documents\""), T("Si apre subito la pagina dei documenti.", "Opens the documents page straight away.")]]);

  {
    const s = tutorial(T("Tutorial · 4 Documenti", "Tutorial · 4 Documents"), T("Caricate tutto: una riga per file, con cosa è stato letto", "Upload everything: one line per file, with what was read"), "05-upload-done",
      [[1, 1090, 220], [2, 575, 458], [3, 942, 376], [4, 1193, 148]],
      [[1, T("«Scegli file» o trascinate", "\"Choose files\" or drag"), T("PDF digitali o scansionati (OCR in IT, DE, FR, EN) ed Excel. I duplicati vengono riconosciuti.", "Digital or scanned PDFs (OCR in IT, DE, FR, EN) and Excel. Duplicates are detected.")],
       [2, T("Tipo, banca, data, valori", "Type, bank, date, values"), T("Riconosciuti da soli: estratto, KID, tariffario... e quanti valori ha letto.", "Recognised on their own: statement, KID, price list... and how many values were read.")],
       [3, T("«Da verificare» in arancione", "\"Needs a check\" in amber"), T("Una scansione o un tariffario con più colonne chiede una conferma.", "A scan or a price list with several columns asks for a confirmation.")],
       [4, T("«Verifica i valori»", "\"Review extracted values\""), T("Il passo successivo.", "The next step.")]]);
    src(s, R + T(": rapporto demo AJ Bell, KID iShares (uno ri-scansionato come immagine), tariffario Julius Baer Europe.", ": AJ Bell demo report, iShares KIDs (one re-scanned as an image), Julius Baer Europe price list."));
  }

  {
    const s = tutorial(T("Tutorial · 4 Documenti", "Tutorial · 4 Documents"), T("«Cosa ci serve»: i documenti mancanti, banca per banca", "\"What we need\": the missing documents, bank by bank"), "06-documents",
      [[1, 1388, 322], [2, 1388, 520], [3, 1388, 595]],
      [[1, T("Spunta verde = documento presente", "Green tick = document present"), T("Estratto, rendiconto costi, estratto conto, tariffario per ogni banca, KID per ogni prodotto.", "Statement, cost report, cash statement, price list per bank, KID per product.")],
       [2, T("Cerchio arancione = manca", "Amber circle = missing"), T("Qui il rendiconto costi della seconda banca: quei costi restano «non determinati».", "Here the second bank's cost report: those costs stay \"not determined\".")],
       [3, T("«Entità errata»", "\"Wrong entity\""), T("Il tariffario è di un'altra sede della banca: le tariffe valgono solo dove il conto è registrato.", "The price list belongs to another entity of the bank: tariffs apply only where the account is booked.")]]);
    src(s, S);
  }

  {
    const s = tutorial(T("Tutorial · 5 Verifica valori", "Tutorial · 5 Check values"), T("Prima i valori che servono a voi, ognuno sulla sua pagina", "Values that need you come first, each on its page"), "07-check-kid",
      [[1, 1003, 212], [2, 740, 390], [3, 1182, 335], [4, 1332, 570]],
      [[1, T("«Serve a voi · 5»", "\"Needs you · 5\""), T("Prima i dubbi; i valori confermati dai controlli sono a parte.", "Doubts first; values the checks confirmed are kept apart.")],
       [2, T("Il riquadro sulla pagina", "The box on the page"), T("Mostra la riga esatta da cui viene il valore.", "Shows the exact row the value came from.")],
       [3, T("Valore e motivo", "Value and reason"), T("«Costi totali USD 7.00» è un importo su un esempio di USD 10'000, non un tasso. Etichetta e valore non concordano: decide l'analista.", "\"Costi totali USD 7.00\" is an amount on a USD 10,000 example, not a rate. Label and value disagree, so the analyst decides.")],
       [4, T("«Respingi»", "\"Reject\""), T("L'importo d'esempio non entra nei calcoli. Il tasso giusto, 0.07%, è sotto. Tasti: a, e, r, j/k.", "The example amount stays out of every total. The right rate, 0.07%, is below. Keys: a, e, r, j/k.")]],
      T("Un KID reale (iShares Core S&P 500, italiano). L'app tiene la valuta dell'importo e non lo tratta come un costo annuo: lo mette in dubbio e chiede a una persona.",
        "A real KID (iShares Core S&P 500, Italian). The app keeps the amount's currency and does not treat it as an annual cost: it flags it and asks a person."));
    src(s, R + ": KID iShares Core S&P 500 UCITS ETF (IT), BlackRock.");
  }

  {
    const s = tutorial(T("Tutorial · 5 Verifica valori", "Tutorial · 5 Check values"), T("Caso limite: una pagina scansionata", "Edge case: a scanned page"), "08-check-scan",
      [[1, 923, 166], [2, 1388, 494], [3, 745, 468]],
      [[1, T("«Scansionato · OCR»", "\"Scanned · OCR\""), T("Il testo è ricostruito dall'immagine, sul vostro computer, senza servizi esterni.", "The text is rebuilt from the image, on your machine, with no outside service.")],
       [2, T("Chi ha letto e con che sicurezza", "Who read it and how sure"), T("tesseract-ocr, 95%. Stato «stimato» finché una persona non conferma.", "tesseract-ocr, 95%. Status \"estimated\" until a person confirms.")],
       [3, T("Confrontate con l'immagine", "Compare with the image"), T("0.20%: corretto. Accettate e passate al successivo.", "0.20%: correct. Accept and move on.")]]);
    src(s, R + T(": KID iShares Core MSCI World (EN), stampato come immagine per simulare una scansione.", ": iShares Core MSCI World KID (EN), printed to an image to simulate a scan."));
  }

  tutorial(T("Tutorial · 6 Costi", "Tutorial · 6 Costs"), T("Prima la risposta, poi i documenti da chiedere", "The answer first, then the documents to ask for"), "11-costs",
    [[1, 548, 278], [2, 858, 318], [3, 1420, 348], [4, 525, 465]],
    [[1, T("Costo annuo noto", "Known annual cost"), T("CHF 61'450, 1.43% del patrimonio, «almeno».", "CHF 61,450, 1.43% of assets, \"at least\".")],
     [2, T("5 costi non determinati", "5 costs not determined"), T("Il costo vero è più alto: non lo inventiamo e non lo contiamo zero.", "The true cost is higher: we do not invent it or count it as zero.")],
     [3, T("Copertura delle evidenze", "Evidence coverage"), T("Quanta parte dei costi viene da un documento effettivo.", "How much of the cost comes from an actual document.")],
     [4, T("«Documenti da richiedere»", "\"Documents to ask for\""), T("Per priorità, con il patrimonio interessato. «Copia lettera di richiesta» per cliente o banca.", "By priority, with the assets affected. \"Copy request letter\" for the client or the bank.")]]);

  {
    const s = tutorial(T("Tutorial · 6 Costi", "Tutorial · 6 Costs"), T("Un clic su un numero: calcolo, fonte e chi l'ha controllato", "One click on a number: calculation, source and who checked it"), "13-trace-kid",
      [[1, 1140, 323], [2, 1140, 487], [3, 1140, 548], [4, 1140, 686], [5, 990, 800]],
      [[1, T("Il calcolo", "The calculation"), T("900'000 × 1.08%: valore della posizione per costo corrente del fondo.", "900,000 × 1.08%: holding value times the fund's ongoing cost.")],
       [2, T("Il tasso, letto dal KID", "The rate, read from the KID"), T("Con documento e pagina.", "With document and page.")],
       [3, T("La base, letta dall'estratto", "The basis, read from the statement"), T("Stessa posizione, stesso ISIN.", "Same holding, same ISIN.")],
       [4, T("Dove è scritto", "Where it is written"), T("Il ritaglio della pagina; «Mostra la pagina intera» per il contesto.", "The page crop; \"Show full page\" for context.")],
       [5, T("Traccia delle decisioni", "Decision trail"), T("Come è stato letto, quali controlli ha passato, chi l'ha accettato.", "How it was read, which checks passed, who accepted it.")]]);
    s.addNotes(T("Le commissioni di gestione dentro il costo corrente (OCF) contano una volta sola: 1.08%, non 1.08% + 0.75%. Vedi «Voci collegate (mostrate, non sommate)».",
      "The management fee inside the ongoing charge (OCF) counts once: 1.08%, not 1.08% + 0.75%. See \"Linked items (shown, not added)\"."));
  }

  {
    const s = content(T("Tutorial · 6 Costi", "Tutorial · 6 Costs"), T("Mancante non vuol dire zero: l'app chiede il documento", "Missing is never zero: the app asks for the document"), T("Tutorial"));
    const a = shot(s, "c-layer", { x: 0.5, y: 1.45, w: 6.0, h: 2.3 });
    shot(s, "c-missing", { x: 0.5, y: 1.6 + a.h, w: 6.0, h: 3.0 });
    steps(s, [
      [1, T("Le barre con «+ non determinato»", "Bars with \"+ not determined\""), T("Quella parte del costo non ha ancora un documento. Non è contata come zero.", "That part of the cost has no document yet. It is not counted as zero.")],
      [2, T("«Documenti da richiedere», per priorità", "\"Documents to ask for\", by priority"), T("Per ogni buco: quale documento serve e quanto patrimonio riguarda (es. CHF 1'100'000).", "For each gap: which document is needed and how much of the assets it affects (e.g. CHF 1,100,000).")],
      [3, T("«Copia lettera di richiesta»", "\"Copy request letter\""), T("Una lettera pronta per il cliente o la banca. «Segna come richiesto» tiene traccia.", "A ready letter for the client or the bank. \"Mark requested\" keeps track.")],
    ], 6.9, 1.6, 5.9);
    src(s, S);
  }

  {
    const s = content(T("Tutorial · casi limite", "Tutorial · edge cases"), T("Su documenti reali l'app si ferma e lo dice", "On real documents the app stops and says so"), T("Tutorial"));
    const rr = shot(s, "16-real-costs", { x: 0.5, y: 1.45, w: 6.6, h: 4.15 });
    marks(s, rr, [[1, 700, 280], [2, 262, 825]]);
    const v = shot(s, "c-validation", { x: 7.6, y: 1.45, w: 5.0, h: 1.8 });
    marks(s, v, [[3, 36, 80], [4, 36, 160]], 1170);
    steps(s, [
      [1, T("Costi non ancora calcolati", "Costs are not calculated yet"), T("L'estratto è in GBP senza cambio GBP/CHF nei documenti: nessun totale, invece di un totale sbagliato.", "The statement is in GBP with no GBP/CHF rate on the documents: no total, rather than a wrong one.")],
      [2, T("Nessun cambio inventato", "No invented FX rate"), T("Nessun tasso preso da Internet: si chiede la pagina con il cambio.", "No rate fetched from the internet: the page with the rate is requested.")],
      [3, T("Due persone nello stesso file", "Two people in one file"), T("Da pagina 16 compare un altro cliente. Caricate solo le sue pagine.", "Another client appears from page 16. Upload only your prospect's pages.")],
      [4, T("Riconciliazione", "Reconciliation"), T("Somma delle posizioni = totale stampato (660'273.45 GBP): superato.", "Sum of holdings = printed total (660,273.45 GBP): passed.")],
    ], 7.35, 3.4, 5.5, 0.04);
    src(s, R + T(": rapporto demo cliente AJ Bell (UK), 26 pagine, due clienti fittizi.", ": AJ Bell demo client report (UK), 26 pages, two fictitious clients."));
  }

  {
    const s = tutorial(T("Tutorial · 7 Confronto", "Tutorial · 7 Compare"), T("Confronto a parità di posizioni: il risparmio è un minimo", "Like-for-like comparison: the saving is a lower bound"), "18-compare",
      [[1, 1080, 176], [2, 1100, 228], [3, 1390, 228], [4, 1232, 390]],
      [[1, T("«Stesse posizioni»", "\"Same holdings\""), T("Stessi titoli, vostra tariffa. «Con modifiche ai prodotti» è un secondo scenario, separato.", "Same securities at your tariff. \"With product changes\" is a separate second scenario.")],
       [2, T("Risparmio «almeno» CHF 6'520", "Saving \"at least\" CHF 6,520"), T("Solo sui costi noti, con IVA e bolli trattati uguali sui due lati.", "On known costs only, with VAT and stamp duty treated the same on both sides.")],
       [3, T("Costo del cambio", "Switching cost"), T("CHF 1'500, ripagato in 2.8 mesi.", "CHF 1,500, paid back in 2.8 months.")],
       [4, T("Perché è un minimo", "Why it is a bound"), T("Spiegato in parole semplici, da dire al cliente.", "Explained in plain words you can repeat to the client.")]]);
    src(s, S);
  }

  {
    const s = tutorial(T("Tutorial · 7 Confronto", "Tutorial · 7 Compare"), T("Caso limite: quando la vostra proposta costa di più, lo dice", "Edge case: when your proposal costs more, it says so"), "20-compare-dearer",
      [[1, 1100, 190], [2, 916, 452]],
      [[1, T("«La proposta costa di più all'anno»", "\"Proposal costs more per year\""), T("Al massimo CHF 2'588. Mai mostrato come risparmio.", "At most CHF 2,588. Never shown as a saving.")],
       [2, T("Nessun risparmio sui costi noti", "No saving on known costs"), T("Utile prima dell'incontro: meglio saperlo voi che il cliente.", "Useful before the meeting: better you find out than the client.")]]);
    src(s, T("Cliente sintetico P-2077: banca italiana in EUR e broker USA in USD.", "Synthetic prospect P-2077: Italian bank in EUR and US broker in USD."));
  }

  {
    const s = content(T("Tutorial · 8 Rapporto", "Tutorial · 8 Report"), T("Il rapporto per il cliente: pronto da inviare, approvato da un senior", "The client report: ready to send, approved by a senior"), T("Tutorial"));
    const rr = shot(s, "21-report", { x: 0.5, y: 1.45, w: 7.0, h: 4.4 });
    marks(s, rr, [[1, 1305, 240], [2, 1305, 527], [3, 1180, 176], [4, 262, 717]]);
    const p = shot(s, "report-pdf", { x: 7.75, y: 1.45, w: 2.6, h: 3.7 });
    s.addText(T("Pagina 1 del PDF", "PDF page 1"), tb({ x: p.x, y: p.y + p.h + 0.05, w: p.w, h: 0.25, fontSize: 9.5, color: X.muted, align: "center" }));
    steps(s, [
      [1, T("«Pronto da inviare?»", "\"Ready to send?\""), T("Cosa manca ancora, con il link per farlo.", "What is still open, with a link to do it.")],
      [2, T("Approvazione", "Approval"), T("Solo un senior approva le cifre esatte mostrate.", "Only a senior approves the exact figures shown.")],
      [3, T("PDF in italiano o inglese", "PDF in Italian or English"), T("Lo stesso contenuto, nella lingua del cliente.", "The same content, in the client's language.")],
      [4, T("«Non ancora verificato»", "\"Not yet verified\""), T("I costi mancanti sono scritti nel rapporto, non nascosti.", "Missing costs are written in the report, not hidden.")],
    ], 10.55, 1.5, 2.35, 0.1);
    card(s, 0.5, 6.05, 7.0, 0.6, X.tealSoft);
    s.addText(T("Il vostro margine interno è in una pagina separata, solo per i senior, e non entra mai nel rapporto (verificato da test automatici).",
      "Your internal margin is on a separate page, for seniors only, and never enters the report (checked by automated tests)."),
      tb({ x: 0.7, y: 6.1, w: 6.7, h: 0.5, fontSize: 12, color: X.navy, valign: "middle" }));
  }

  // ---------- Edge cases summary ----------
  {
    const s = content(T("Casi limite", "Edge cases"), T("Cosa fa l'app, cosa fa l'analista", "What the app does, what the analyst does"), T("Tutorial"));
    const rows = [
      [T("Pagina scansionata", "Scanned page"), T("Legge con OCR in locale, segna «OCR», stato stimato", "Reads with local OCR, marks \"OCR\", status estimated"), T("Conferma ogni valore sull'immagine", "Confirms each value on the image")],
      [T("Costo mancante", "Missing cost"), T("«Non determinato», mai zero; totale «almeno»", "\"Not determined\", never zero; total \"at least\""), T("Chiede il documento (lettera pronta)", "Requests the document (ready letter)")],
      [T("Valore dubbio", "Doubtful value"), T("Nei «Punti da verificare», con il motivo", "In \"Points to review\", with the reason"), T("Accetta, corregge o respinge", "Accepts, corrects or rejects")],
      [T("Totale che non torna", "Total that does not add up"), T("Allarme di riconciliazione con la pagina", "Reconciliation alarm with the page"), T("Risolve prima di tutto il resto", "Resolves it before anything else")],
      [T("Due clienti in un file", "Two clients in one file"), T("Allarme «più di una persona»", "\"More than one person\" alarm"), T("Carica solo le pagine giuste", "Uploads only the right pages")],
      [T("Valuta senza cambio", "Currency with no FX rate"), T("Esclude l'importo, non inventa il cambio", "Leaves the amount out, never guesses a rate"), T("Fornisce la pagina con il cambio", "Provides the page with the rate")],
      [T("Tariffario di un'altra sede", "Price list of another entity"), T("«Entità errata»: la tariffa non si applica", "\"Wrong entity\": the tariff does not apply"), T("Chiede il tariffario giusto", "Requests the right price list")],
      [T("Commissione dentro il TER", "Fee inside the TER"), T("Contata una volta sola (1.08%, non 1.83%)", "Counted once (1.08%, not 1.83%)"), "—"],
    ];
    const hdr = [T("Situazione", "Situation"), T("L'app", "The app"), T("L'analista", "The analyst")];
    const cw = [3.0, 5.0, 4.35];
    const data = [hdr.map((h) => ({ text: h, options: { bold: true, color: X.white, fill: { color: X.navy } } }))]
      .concat(rows.map((r, i) => r.map((c, j) => ({ text: c, options: { bold: j === 0, color: j === 0 ? X.navy : X.text, fill: { color: i % 2 ? X.white : X.bg } } }))));
    s.addTable(data, { x: 0.5, y: 1.45, w: 12.35, colW: cw, fontSize: 12.5, fontFace: "Calibri", rowH: 0.56, border: { type: "solid", color: X.border, pt: 0.5 }, valign: "middle", margin: [0.04, 0.12, 0.04, 0.12] });
  }

  // ---------- Accuracy: method ----------
  // Numbers: main re-run of 2026-11-13, independently re-checked the same day (project file accuracy/accuracy-check-2026-11-13.md).
  const flowBox = (s, x, y, w, h, title, sub, strong) => {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: strong ? X.tealSoft : X.white }, line: { color: strong ? X.teal : X.border, width: strong ? 1.5 : 0.75 } });
    s.addText(title, tb({ x: x + 0.1, y: y + 0.12, w: w - 0.2, h: 0.32, fontSize: 13, bold: true, color: X.navy, align: "center" }));
    if (sub) s.addText(sub, tb({ x: x + 0.1, y: y + 0.44, w: w - 0.2, h: 0.4, fontSize: 10.5, color: X.muted, align: "center" }));
  };
  const arrow = (s, x1, y1, x2, y2, label, ly) => {
    s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, line: { color: X.muted, width: 1, endArrowType: "triangle" } });
    if (label) s.addText(label, tb({ x: Math.min(x1, x2), y: ly, w: Math.max(Math.abs(x2 - x1), 0.9), h: 0.25, fontSize: 10, color: X.muted, align: "center" }));
  };
  const table = (s, hdr, rows, opt) => {
    const data = [hdr.map((h, j) => ({ text: h, options: { bold: true, color: X.navy, align: opt.align[j], border: [{ type: "none" }, { type: "none" }, { type: "solid", color: X.navy, pt: 1 }, { type: "none" }] } }))]
      .concat(rows.map((r, i) => r.map((c, j) => ({ text: c, options: { bold: opt.boldLast && i === rows.length - 1, align: opt.align[j], color: j === 0 ? X.navy : X.text,
        border: [{ type: opt.boldLast && i === rows.length - 1 ? "solid" : "none", color: X.navy, pt: 0.75 }, { type: "none" }, { type: "solid", color: X.border, pt: 0.5 }, { type: "none" }] } }))));
    s.addTable(data, { x: opt.x, y: opt.y, w: opt.colW.reduce((a, b) => a + b, 0), colW: opt.colW, fontSize: opt.fontSize || 12, fontFace: "Calibri", rowH: opt.rowH || 0.4, valign: "middle", margin: [0.03, 0.08, 0.03, 0.08] });
  };
  const bullets = (items) => items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } }));
  {
    const s = content(T("Metodo", "Method"), T("Ogni cifra è letta due volte, oppure la controlla una persona", "Every figure is read twice, or a person checks it"), T("Accuratezza", "Accuracy"));
    const y = 1.55, h = 0.85, w = 2.05;
    flowBox(s, 0.5, y, w, h, T("Caricamento", "Upload"), T("più file insieme", "several files at once"));
    flowBox(s, 3.0, y, w, h, T("Lettura pagina", "Read each page"), T("testo, o OCR in locale", "text, or local OCR"));
    flowBox(s, 5.5, y, w, h, T("Ogni costo trovato", "Find every fee"), T("riga, colonna, riquadro", "row, column, page box"));
    s.addShape(pres.shapes.DIAMOND, { x: 8.0, y: y - 0.15, w: 2.0, h: 1.15, fill: { color: X.white }, line: { color: X.navy, width: 1 } });
    s.addText(T("Controlli superati?", "Checks pass?"), tb({ x: 8.0, y: y + 0.27, w: 2.0, h: 0.3, fontSize: 12, bold: true, color: X.navy, align: "center" }));
    flowBox(s, 10.8, y, w, h, T("Verificato", "Verified"), T("con pagina e riquadro", "with its page and box"), true);
    arrow(s, 2.55, y + h / 2, 3.0, y + h / 2); arrow(s, 5.05, y + h / 2, 5.5, y + h / 2); arrow(s, 7.55, y + h / 2, 8.0, y + h / 2);
    arrow(s, 10.0, y + h / 2, 10.8, y + h / 2, T("sì", "yes"), y + 0.1);
    s.addText(T("seconda lettura uguale, somme che tornano", "second reading agrees, sums tie"), tb({ x: 7.6, y: y + 1.05, w: 2.8, h: 0.25, fontSize: 10, italic: true, color: X.muted, align: "center" }));
    flowBox(s, 5.5, y + 1.55, w, h, T("Verifica valori", "Check values"), T("l'analista conferma sulla pagina", "analyst confirms on the page"));
    s.addShape(pres.shapes.LINE, { x: 9.0, y: y + 1.32, w: 0.001, h: 0.65, line: { color: X.muted, width: 1 } });
    arrow(s, 9.0, y + 1.97, 7.55, y + 1.97, T("in dubbio", "in doubt"), y + 1.68);
    flowBox(s, 5.5, y + 3.0, 7.35, 0.75, T("Registro dei costi e rapporto", "Cost ledger and client report"), T("ogni costo contato una volta (AMF dentro OCF); un costo ignoto non è mai 0", "each fee counted once (AMF inside OCF); an unknown cost is never shown as 0"));
    arrow(s, 6.525, y + 2.4, 6.525, y + 3.0); arrow(s, 11.825, y + h, 11.825, y + 3.0);
    s.addText(T("Come lo misuriamo", "How we measure it"), tb({ x: 0.5, y: 3.1, w: 4.6, h: 0.35, fontSize: 15, bold: true, color: X.navy }));
    s.addText(bullets([
      T("Un solo valutatore (pce.evaluation), stesse pagine per ogni versione.", "One scorer (pce.evaluation), the same pages for every version."),
      T("Trovato solo se il valore è identico e sulla riga giusta.", "Found only if the value is identical and on the right row."),
      T("Errore: cifra mostrata come verificata ma sbagliata. Una persona la accetta comunque prima che conti.", "Error: a figure shown as verified that is wrong. A person still accepts it before it counts."),
      T("Intervalli al 95%: 1'000 ricampionamenti per pagina; per documento il risultato è lo stesso.", "95% ranges: 1,000 resamples by page; by document gives the same range."),
      T("19 pagine annotate dopo aver fissato il lettore: nessun adattamento al test.", "19 pages labelled after the reader was frozen: no tuning to the test."),
    ]), tb({ x: 0.5, y: 3.5, w: 4.75, h: 1.9, fontSize: 11.5, paraSpaceAfter: 3 }));
    const sets = [
      ["813", T("costi distinti", "distinct fees"), T("62 pagine reali pubbliche, 11 scansionate", "62 real public pages, 11 scanned")],
      ["130", T("KID pubblici", "public KIDs"), T("costo corrente del fondo", "the fund's ongoing cost")],
      ["4", T("estratti reali", "real statements"), T("posizioni e patrimonio", "holdings and assets")],
      ["2", T("clienti sintetici", "synthetic prospects"), T("15 documenti, anche scansioni", "15 documents, scans too")],
    ];
    sets.forEach(([n, t, d], i) => {
      const x = 0.5 + i * 3.1;
      card(s, x, 5.5, 2.95, 1.15, X.white, X.border);
      s.addText(n, tb({ x: x + 0.15, y: 5.62, w: 1.05, h: 0.6, fontSize: 26, bold: true, color: X.teal }));
      s.addText(t, tb({ x: x + 1.2, y: 5.62, w: 1.7, h: 0.3, fontSize: 12.5, bold: true, color: X.navy }));
      s.addText(d, tb({ x: x + 1.2, y: 5.92, w: 1.7, h: 0.65, fontSize: 10.5, color: X.muted }));
    });
    s.addNotes(T("Dettagli: «FeeLens accuracy study» e il controllo indipendente del 13.11.2026. Tutti i dati sono pubblici o sintetici. 896 righe annotate = 813 costi distinti (alcune scansioni duplicano pagine digitali).",
      "Details: \"FeeLens accuracy study\" and the independent re-check of 13 Nov 2026. All data is public or synthetic. 896 labelled rows = 813 distinct fees (some scans duplicate digital pages)."));
  }

  // ---------- Test documents ----------
  {
    const s = content(T("Su cosa lo proviamo", "What we test on"), T("414 documenti pubblici reali, nessuno di un cliente", "414 real public documents, none from a client"), T("Accuratezza", "Accuracy"));
    const rows = [
      [T("Tariffari e tariffe di custodia", "Bank price lists, custody tariffs"), "87", "48 / 20", T("Buono · 38 banche svizzere", "Good · 38 Swiss banks")],
      [T("KID di fondi, ETF, prodotti svizzeri", "Fund, ETF and Swiss KIDs"), "146", "15 / 5", T("Buono", "Good")],
      [T("Prodotti strutturati, assicurativi", "Structured products, insurance"), "62", "19 / 16", T("Buono", "Good")],
      [T("Costi ex-ante, retrocessioni", "Ex-ante costs, retrocessions"), "27", "11 / 2", T("Buono", "Good")],
      [T("Contratti di mandato", "Mandate contracts"), "6", "4 / 2", T("Solo modelli", "Templates only")],
      [T("Factsheet, prospetti", "Factsheets, prospectuses"), "57", "8 / 1", T("Solo controllo incrociato", "Cross-check only")],
      [T("Guide di lettura, specifiche", "Reading guides, specs"), "15", "6 / 2", T("Solo impaginazione", "Layout only")],
      [T("Estratti con posizioni", "Holdings statements"), "5", "0 / 0", T("Lacuna", "Gap")],
      [T("Rendiconti costi ex-post", "Ex-post cost reports"), "7", "0 / 1", T("Lacuna", "Gap")],
      [T("Avvisi di operazione e di costo", "Trade and fee advices"), "2", "0 / 0", T("Lacuna", "Gap")],
    ];
    table(s, [T("Tipo di documento", "Document type"), T("File", "Files"), T("CH / IT", "CH / IT"), T("Copertura", "Coverage")], rows,
      { x: 0.5, y: 1.5, colW: [3.6, 0.9, 1.1, 2.6], align: ["left", "right", "right", "left"], rowH: 0.44 });
    s.addText(T("Ogni file scaricato dalla fonte pubblica, con impronta SHA-256. BancaStato e UBS bloccano l'accesso automatico: non lo aggiriamo.",
      "Every file downloaded from its public source and fingerprinted (SHA-256). BancaStato and UBS block automated access: we do not get around it."),
      tb({ x: 0.5, y: 6.4, w: 8.2, h: 0.4, fontSize: 10.5, color: X.muted }));
    card(s, 9.05, 1.5, 3.8, 4.8, X.amberSoft);
    s.addText(T("Cosa vuol dire", "What this means"), tb({ x: 9.3, y: 1.65, w: 3.4, h: 0.35, fontSize: 15, bold: true, color: X.navy }));
    s.addText(bullets([
      T("Prezzi delle banche e costi dei prodotti: ben coperti, anche in italiano e per il Ticino.", "Bank prices and product costs: well covered, in Italian and for Ticino too."),
      T("Estratti e rendiconti costi con cifre vere: le banche svizzere e italiane non li pubblicano.", "Statements and cost reports with real figures: Swiss and Italian banks do not publish them."),
      T("Per questi usiamo copie sintetiche con risposte esatte, e il pilota sui vostri documenti, sul vostro computer.", "For those we use synthetic look-alikes with exact answers, and the pilot on your documents, on your machine."),
    ]), tb({ x: 9.3, y: 2.1, w: 3.4, h: 4.1, fontSize: 12.5, paraSpaceAfter: 8 }));
  }

  // ---------- Accuracy: results ----------
  {
    const s = content(T("Accuratezza", "Accuracy"), T("Oggi: trova l'87% dei costi, e una persona conferma prima che contino", "Today: 87% of fees found, and a person confirms them before they count"), T("Accuratezza", "Accuracy"));
    bigNum(s, 0.5, 1.5, 3.0, "87%", T("dei costi trovati su 62 pagine reali", "of fees found on 62 real pages"), X.teal, T("intervallo 80–92%", "range 80 to 92%"));
    bigNum(s, 3.6, 1.5, 3.0, "91%", T("su pagine mai viste prima", "on pages it had never seen"), X.teal, T("19 pagine annotate dopo", "19 pages labelled later"));
    bigNum(s, 6.7, 1.5, 3.0, "7.3%", T("delle cifre segnate verificate sono sbagliate", "of figures marked verified are wrong"), X.amber, T("intervallo 4.6–10.5%", "range 4.6 to 10.5%"));
    bigNum(s, 9.8, 1.5, 3.05, "91%", T("costi correnti letti da soli su 130 KID", "fund ongoing costs read automatically, 130 KIDs"), X.teal, T("nessuno sbagliato", "none wrong"));
    s.addText(T("Cosa sono le cifre «sbagliate» (controllo del 13.11, 51 cifre)", "What the \"wrong\" figures are (13 Nov check, 51 figures)"), tb({ x: 0.5, y: 3.45, w: 7.2, h: 0.35, fontSize: 15, bold: true, color: X.navy }));
    table(s, [T("Tipo", "Kind"), T("Cifre", "Figures"), T("Cosa facciamo", "What we do")], [
      [T("Non sono costi (importo d'esempio, limiti carta, prezzo massimo)", "Not fees (example amount, card limit, 52-week high)"), "22", T("Le filtriamo (prossimo lavoro)", "Filter them out (next piece of work)")],
      [T("Costi veri che mancano nelle risposte attese", "Real fees missing from the answer key"), "26", T("Aggiungerle: l'errore vero è più basso", "Add them: the true error is lower")],
      [T("Letture davvero sbagliate (es. «0 ,20%» letto 20)", "True misreads (e.g. \"0 ,20%\" read as 20)"), "3", T("Le ferma la verifica di una persona", "Stopped by a person's check")],
    ], { x: 0.5, y: 3.85, colW: [3.9, 0.8, 2.5], align: ["left", "right", "left"], rowH: 0.5, fontSize: 11.5 });
    s.addText(T("Trovati per tipo: tariffari e custodia 91%, KID 90%, estratti e rendiconti 74%, scansioni 54% (70% con il lettore RapidOCR opzionale).",
      "Found by type: price lists and custody 91%, KIDs 90%, statements and cost reports 74%, scans 54% (70% with the optional RapidOCR reader)."),
      tb({ x: 0.5, y: 5.95, w: 7.2, h: 0.5, fontSize: 11.5, color: X.muted }));
    card(s, 8.1, 3.45, 4.75, 3.2, X.amberSoft);
    s.addText(T("Cosa vuol dire per voi", "What this means for you"), tb({ x: 8.35, y: 3.6, w: 4.3, h: 0.35, fontSize: 15, bold: true, color: X.navy }));
    s.addText(bullets([
      T("Solo il 5% circa dei costi entra nei totali senza che nessuno lo guardi: su quelli, nessun errore trovato.", "Only about 5% of fees enter totals with nobody looking: on those, no errors found."),
      T("Il resto è mostrato con la sua pagina: l'analista conferma invece di cercare. Un senior approva ogni rapporto.", "The rest is shown on its page: the analyst confirms instead of searching. A senior approves every report."),
      T("Estratti svizzeri e italiani non sono pubblici: il pilota misura sui vostri.", "Swiss and Italian statements are not public: the pilot measures on yours."),
    ]), tb({ x: 8.35, y: 4.05, w: 4.3, h: 2.5, fontSize: 12, paraSpaceAfter: 6 }));
    s.addNotes(T("Esecuzione di main del 14.11.2026 (dopo il miglioramento del 13 sera), stesso metodo ricontrollato in modo indipendente il 13.11: nessuna contaminazione. «87%» conta ogni cifra che l'app mostra, anche quelle che una persona deve ancora accettare. Il 90% citato prima veniva dal laboratorio, non dall'app.",
      "Run of main on 14 Nov 2026 (after the 13 Nov evening improvement), same method independently re-checked on 13 Nov: no leakage. \"87%\" counts every figure the app shows, including those a person must still accept. The 90% quoted before came from the lab harness, not the app."));
  }

  // ---------- Accuracy: last week ----------
  {
    const s = content(T("Progressi", "Progress"), T("In una settimana: dal 4% all'87% dei costi trovati", "In one week: from 4% to 87% of fees found"), T("Accuratezza", "Accuracy"));
    const labels = [T("11 nov", "11 Nov"), T("13 nov, mattina", "13 Nov, morning"), T("14 nov, oggi", "14 Nov, today")];
    const chartOpts = (title, max, fmt) => ({
      x: 0, y: 0, w: 0, h: 0, barDir: "col", barGapWidthPct: 70, chartColors: [X.paleNavy, X.teal, "7FB8B0"], showValue: true, dataLabelFormatCode: fmt,
      dataLabelColor: X.navy, dataLabelFontSize: 13, dataLabelFontBold: true, dataLabelPosition: "outEnd",
      catAxisLabelColor: X.text, catAxisLabelFontSize: 11, catAxisLineShow: true, catAxisLineColor: X.border,
      valAxisHidden: true, valGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: max,
      showTitle: true, title, titleFontSize: 13, titleColor: X.navy, titleFontFace: "Calibri", showLegend: false, varyColors: true,
    });
    s.addChart(pres.charts.BAR, [{ name: "recall", labels, values: [4, 82, 87] }],
      { ...chartOpts(T("Costi trovati (%)", "Fees found (%)"), 100, "0\"%\""), x: 0.5, y: 1.45, w: 4.1, h: 3.6 });
    s.addChart(pres.charts.BAR, [{ name: "wrong", labels, values: [14.5, 7.3, 7.3] }],
      { ...chartOpts(T("Verificate ma sbagliate (%, meno è meglio)", "Verified but wrong (%, lower is better)"), 16, "0.0\"%\""), x: 4.75, y: 1.45, w: 4.1, h: 3.6 });
    s.addText(T("Stesse 62 pagine controllate a mano ogni volta, sempre l'app vera. Intervalli oggi: 87% (80–92), 7.3% (4.6–10.5). Su 19 pagine mai viste: 91%.",
      "The same 62 hand-checked pages each time, always the real app. Ranges today: 87% (80 to 92), 7.3% (4.6 to 10.5). On 19 unseen pages: 91%."),
      tb({ x: 0.5, y: 5.1, w: 8.35, h: 0.5, fontSize: 10.5, color: X.muted }));
    const log = [
      [T("13 nov", "13 Nov"), T("Lettore di scansioni RapidOCR (opzionale): scansioni dal 54% al 70%", "Optional RapidOCR scan reader: scans from 54% to 70%")],
      [T("13 nov", "13 Nov"), T("Vocabolario dei costi e titoli delle tabelle: dall'82% all'87%", "Fee vocabulary and table headings: from 82% to 87%")],
      [T("13 nov", "13 Nov"), T("Più documenti letti insieme: 29 file in 12 s invece di 43 s", "Several documents read at once: 29 files in 12 s instead of 43 s")],
      [T("13 nov", "13 Nov"), T("Ricontrollo indipendente: stessi numeri, nessuna contaminazione", "Independent re-check: same numbers, no leakage")],
      [T("12 nov", "12 Nov"), T("Estratti: Fidelity USA 34 posizioni su 34; 0 errori di patrimonio silenziosi", "Statements: Fidelity US 34 of 34 holdings; 0 silent asset errors")],
      [T("12 nov", "12 Nov"), T("Lettore che segue righe e colonne: dal 4% all'82%", "Reader that follows rows and columns: from 4% to 82%")],
    ];
    s.addText(T("Cosa è cambiato", "What changed"), tb({ x: 9.2, y: 1.5, w: 3.65, h: 0.35, fontSize: 15, bold: true, color: X.navy }));
    log.forEach(([d, t], i) => {
      const y = 1.95 + i * 0.62;
      s.addShape(pres.shapes.LINE, { x: 9.2, y: y - 0.08, w: 3.65, h: 0, line: { color: X.border, width: 0.5 } });
      s.addText(d, tb({ x: 9.2, y, w: 0.8, h: 0.3, fontSize: 11, bold: true, color: X.teal }));
      s.addText(t, tb({ x: 10.0, y, w: 2.85, h: 0.6, fontSize: 11 }));
    });
    card(s, 0.5, 5.75, 12.35, 0.85, X.tealSoft);
    s.addText([
      { text: T("Prossimo passo: ", "Next step: "), options: { bold: true, color: X.navy } },
      { text: T("togliere i numeri che non sono costi, un lettore di tabelle per le tariffe a scaglioni, RapidOCR nell'installazione standard, migliorare i rendiconti costi. Nel pilota misuriamo con lo stesso valutatore sulle vostre pagine.",
        "drop numbers that are not fees, a table reader for tiered tariffs, RapidOCR in the standard install, better cost reports. In the pilot we measure with the same scorer on your pages.") },
    ], tb({ x: 0.75, y: 5.8, w: 11.9, h: 0.75, fontSize: 12.5, valign: "middle" }));
  }

  // ---------- Speed ----------
  {
    const s = content(T("Velocità", "Speed"), T("Più documenti letti insieme: un fascicolo completo in secondi", "Several documents read at once: a full client pack in seconds"), T("Accuratezza", "Accuracy"));
    const labels = [T("29 file sintetici (digitali e scansioni)", "29 synthetic files (digital and scans)"), T("8 PDF pubblici lunghi (51–116 pagine)", "8 long public PDFs (51 to 116 pages)")];
    s.addChart(pres.charts.BAR, [
      { name: T("Prima, un file alla volta", "Before, one file at a time"), labels, values: [43, 215] },
      { name: T("Ora, in parallelo", "Now, in parallel"), labels, values: [12, 67] },
    ], {
      x: 0.5, y: 1.45, w: 7.4, h: 4.3, barDir: "col", barGapWidthPct: 60, chartColors: ["C9D3DE", X.teal], showValue: true, dataLabelFormatCode: "0\" s\"",
      dataLabelColor: X.navy, dataLabelFontSize: 13, dataLabelFontBold: true, dataLabelPosition: "outEnd",
      catAxisLabelColor: X.text, catAxisLabelFontSize: 11.5, catAxisLineShow: true, catAxisLineColor: X.border,
      valAxisHidden: true, valGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: 240,
      showLegend: true, legendPos: "t", legendFontSize: 11.5, legendColor: X.text,
      showTitle: true, title: T("Secondi per leggere tutto (meno è meglio)", "Seconds to read everything (lower is better)"), titleFontSize: 13, titleColor: X.navy, titleFontFace: "Calibri",
    });
    s.addText(T("Misurato su un computer con 4 core, stesso lettore e stessi risultati prima e dopo.", "Measured on a 4-core machine, same reader and same results before and after."),
      tb({ x: 0.5, y: 5.85, w: 7.4, h: 0.3, fontSize: 10.5, color: X.muted }));
    bigNum(s, 8.3, 1.5, 4.55, "12 s", T("per un fascicolo cliente di 29 file (prima 43 s)", "for a 29-file client pack (was 43 s)"), X.teal);
    card(s, 8.3, 3.25, 4.55, 3.4, X.tealSoft);
    s.addText(T("Come funziona", "How it works"), tb({ x: 8.55, y: 3.4, w: 4.1, h: 0.35, fontSize: 15, bold: true, color: X.navy }));
    s.addText(bullets([
      T("Ogni file è letto su un core diverso; le pagine scansionate di un file anche.", "Each file is read on its own core; the scanned pages of one file too."),
      T("L'avanzamento si vede file per file: si può iniziare a verificare il primo.", "Progress shows file by file: you can start checking the first one."),
      T("Tutto in locale. Basta un PC con 4 core; la demo pubblica gratuita ne ha 1 e non accelera.", "All local. A 4-core PC is enough; the free public demo has 1 and does not speed up."),
    ]), tb({ x: 8.55, y: 3.85, w: 4.1, h: 2.7, fontSize: 12.5, paraSpaceAfter: 8 }));
  }

  // ---------- Readiness ----------
  {
    const s = content(T("È pronto?", "Is it ready?"), T("Pronto per un pilota supervisionato, non per l'uso senza controllo", "Ready for a supervised pilot, not for unchecked use"), T("Accuratezza", "Accuracy"));
    const ready = [
      T("Legge estratti, KID, tariffari, rendiconti, più file insieme; scansioni con OCR", "Reads statements, KIDs, price lists, cost reports, several at once; scans with OCR"),
      T("Fonte e riquadro per ogni cifra; traccia delle decisioni", "Source and box for every figure; decision trail"),
      T("Allarmi: totali, due persone, cambio mancante, entità errata", "Alarms: totals, two people, missing FX, wrong entity"),
      T("Confronto a parità di posizioni, rapporto PDF IT/EN con approvazione", "Like-for-like comparison, IT/EN PDF report with approval"),
      T("Nessun dato esce dal computer (nessuna IA esterna)", "No data leaves the machine (no outside AI)"),
    ];
    const todo = [
      [T("Accesso personale con doppia verifica (MFA)", "Personal sign-in with two-factor (MFA)"), T("noi", "us")],
      [T("Cancellazione su richiesta del cliente", "Delete on the client's request"), T("noi", "us")],
      [T("Disco cifrato, backup provato, conservazione", "Encrypted disk, tested backup, retention"), T("noi", "us")],
      [T("Registro di chi vede e scarica cosa", "Log of who views and downloads what"), T("noi", "us")],
      [T("Dove gira il pilota", "Where the pilot runs"), "Safe Capital"],
      [T("Valutazione d'impatto (DPIA), consenso, ok compliance", "Impact assessment (DPIA), consent, compliance sign-off"), "Safe Capital"],
    ];
    card(s, 0.5, 1.5, 6.05, 5.1, X.greenSoft);
    s.addText(T("Pronto oggi", "Ready today"), tb({ x: 0.75, y: 1.65, w: 5.5, h: 0.4, fontSize: 17, bold: true, color: X.green }));
    ready.forEach((t, i) => {
      s.addText("✓", tb({ x: 0.75, y: 2.2 + i * 0.8, w: 0.3, h: 0.4, fontSize: 16, bold: true, color: X.green }));
      s.addText(t, tb({ x: 1.1, y: 2.2 + i * 0.8, w: 5.2, h: 0.7, fontSize: 13.5 }));
    });
    card(s, 6.8, 1.5, 6.05, 5.1, X.amberSoft);
    s.addText(T("Prima del primo documento reale", "Before the first real document"), tb({ x: 7.05, y: 1.65, w: 5.6, h: 0.4, fontSize: 17, bold: true, color: X.amber }));
    todo.forEach(([t, who], i) => {
      s.addText("○", tb({ x: 7.05, y: 2.2 + i * 0.68, w: 0.3, h: 0.4, fontSize: 15, color: X.amber }));
      s.addText(t, tb({ x: 7.4, y: 2.2 + i * 0.68, w: 3.9, h: 0.6, fontSize: 13.5 }));
      chip(s, 11.4, 2.22 + i * 0.68, who, who === "Safe Capital" ? X.navy : X.teal, who === "Safe Capital" ? X.infoSoft : X.tealSoft, 1.25);
    });
    s.addNotes(T("Riferimento: docs/READINESS.md, porte G2-G9. La demo pubblica su Render non va mai usata con documenti di clienti.",
      "Reference: docs/READINESS.md, gates G2 to G9. The public demo on Render is never used with client documents."));
  }

  // ---------- Where it runs ----------
  {
    const s = content(T("Dove gira", "Where it runs"), T("Il codice gira da voi o in Svizzera, mai su un servizio pubblico", "The code runs at your office or in Switzerland, never on a public service"), T("Dati e sicurezza", "Data and security"));
    const opts = [
      ["LuMonitor", T("A · Un computer di Safe Capital", "A · A Safe Capital computer"), T("Consigliato per il pilota", "Recommended for the pilot"), X.teal, X.tealSoft,
        [T("Tutto resta nel vostro ufficio", "Everything stays in your office"), T("Disco cifrato, backup sui vostri sistemi", "Encrypted disk, backups on your systems"), T("Un PC esistente basta; nuovo: CHF 1'500-2'500", "An existing PC is enough; new: CHF 1,500 to 2,500")]],
      ["LuServer", T("B · Server in Svizzera", "B · Server in Switzerland"), T("Dopo il pilota, per più utenti", "After the pilot, for more users"), X.navy, X.infoSoft,
        [T("Infomaniak o Exoscale (data center svizzeri)", "Infomaniak or Exoscale (Swiss data centres)"), T("Azure Svizzera se usate Microsoft 365", "Azure Switzerland if you use Microsoft 365"), T("Accesso personale con MFA, database, backup", "Personal sign-in with MFA, database, backups")]],
      ["LuGlobe", T("C · Demo pubblica", "C · Public demo"), T("Mai per dati di clienti", "Never for client data"), X.red, X.redSoft,
        [T("Solo dati sintetici, per mostrare l'app", "Synthetic data only, to show the app"), T("Si azzera a ogni riavvio", "Resets on every restart"), T("Non è un'opzione per il lavoro vero", "Not an option for real work")]],
    ];
    for (let i = 0; i < 3; i++) {
      const [ic, t, sub, c, bg, pts] = opts[i];
      const x = 0.5 + i * 4.15;
      card(s, x, 1.5, 3.95, 4.3, bg);
      await iconTile(s, x + 0.3, 1.75, 0.7, ic, X.white, c);
      s.addText(t, tb({ x: x + 0.3, y: 2.6, w: 3.4, h: 0.5, fontSize: 17, bold: true, color: c }));
      s.addText(sub, tb({ x: x + 0.3, y: 3.1, w: 3.4, h: 0.35, fontSize: 12.5, italic: true, color: X.text }));
      s.addText(pts.map((p, j) => ({ text: p, options: { bullet: true, breakLine: j < pts.length - 1 } })), tb({ x: x + 0.3, y: 3.55, w: 3.4, h: 2.1, fontSize: 13, paraSpaceAfter: 6 }));
    }
    card(s, 0.5, 6.0, 12.35, 0.65, X.bg);
    s.addText(T("In tutti i casi: la lettura dei documenti avviene sul computer stesso. Nessun testo, nessuna immagine e nessun numero viene mandato a ChatGPT, a un OCR in cloud o ad altri servizi.",
      "In every case: documents are read on the machine itself. No text, image or number is sent to ChatGPT, a cloud OCR or any other service."),
      tb({ x: 0.75, y: 6.03, w: 11.9, h: 0.6, fontSize: 13, color: X.navy, valign: "middle" }));
  }

  // ---------- Personal data ----------
  {
    const s = content(T("Dati personali", "Personal data"), T("Come trattiamo i dati dei vostri clienti", "How we treat your clients' data"), T("Dati e sicurezza", "Data and security"));
    const rules = [
      ["LuHash", T("Codici, non nomi", "Codes, not names"), T("L'analisi usa un codice (P-1043). Nomi, IBAN e numeri di conto non servono.", "A review uses a code (P-1043). Names, IBANs and account numbers are not needed.")],
      ["LuShieldCheck", T("Solo in locale", "Local only"), T("Nessuna IA esterna. Le ricerche pubbliche, se attivate, inviano solo ISIN.", "No outside AI. Public lookups, if switched on, send ISINs only.")],
      ["LuKeyRound", T("Utenti con nome e MFA", "Named users with MFA"), T("Ogni analista ha il suo accesso; chi lascia viene tolto lo stesso giorno.", "Every analyst has their own sign-in; leavers are removed the same day.")],
      ["LuTrash2", T("Cancellazione e conservazione", "Deletion and retention"), T("Su richiesta subito; altrimenti dopo 90 giorni senza mandato (proposta, decidete voi).", "On request at once; otherwise 90 days after the meeting with no mandate (proposal, you decide).")],
      ["LuScrollText", T("Registro", "Audit log"), T("Chi carica, vede, corregge, approva, scarica. I log non contengono testo dei documenti.", "Who uploads, views, corrects, approves, downloads. Logs never hold document text.")],
      ["LuFileSignature", T("Consenso e DPIA", "Consent and DPIA"), T("Il cliente consegna i documenti per questo scopo, con consenso scritto. Safe Capital firma la DPIA.", "The client hands over documents for this purpose, with written consent. Safe Capital signs the DPIA.")],
    ];
    for (let i = 0; i < 6; i++) {
      const x = 0.5 + (i % 3) * 4.15, y = 1.5 + Math.floor(i / 3) * 2.35;
      card(s, x, y, 3.95, 2.15, X.bg);
      await iconTile(s, x + 0.25, y + 0.25, 0.6, rules[i][0], X.tealSoft, X.teal);
      s.addText(rules[i][1], tb({ x: x + 1.0, y: y + 0.3, w: 2.8, h: 0.5, fontSize: 15, bold: true, color: X.navy }));
      s.addText(rules[i][2], tb({ x: x + 0.25, y: y + 1.0, w: 3.5, h: 1.1, fontSize: 12.5 }));
    }
    s.addText(T("Riferimenti da confermare con il vostro legale: LPD (nLPD) art. 7, 8, 19, 24; LIsFi art. 69 (segreto); Guida FINMA 08/2024 sull'IA. Non è un parere legale.",
      "To confirm with your counsel: Swiss FADP arts. 7, 8, 19, 24; FinIA art. 69 (secrecy); FINMA Guidance 08/2024 on AI. Not legal advice."),
      tb({ x: 0.5, y: 6.3, w: 12.35, h: 0.4, fontSize: 11, color: X.muted }));
    s.addNotes(T("Accesso con MFA, cancellazione, cifratura/backup e registro delle visualizzazioni sono da completare prima del pilota (slide precedente).",
      "MFA sign-in, deletion, encryption/backup and the view log are still to be finished before the pilot (see the readiness slide)."));
  }

  // ---------- How Safe Capital uses it ----------
  {
    const s = content(T("Come usarlo", "How to use it"), T("Un'analisi tipo in Safe Capital", "A typical review at Safe Capital"), T("Uso e pilota", "Use and pilot"));
    const flow = [
      [T("Primo incontro", "First meeting"), T("Il cliente firma il consenso e consegna estratti, rendiconto costi, tariffari.", "The client signs consent and hands over statements, cost report, price lists."), T("Consulente", "Adviser")],
      [T("Caricamento", "Upload"), T("Codice, domicilio, file. Pochi minuti.", "Code, domicile, files. A few minutes."), T("Analista", "Analyst")],
      [T("Controllo", "Check"), T("Prima il patrimonio (allarmi), poi ogni cifra del costo: conferma, correggi o «sconosciuto».", "Assets first (alarms), then every cost figure: confirm, correct or \"unknown\"."), T("Analista", "Analyst")],
      [T("Documenti mancanti", "Missing documents"), T("Lettera di richiesta al cliente o alla banca.", "Request letter to the client or the bank."), T("Analista", "Analyst")],
      [T("Quattro occhi", "Four eyes"), T("Un secondo controlla totale, risparmio, base del confronto e approva.", "A second person checks total, saving and comparison basis, then approves."), T("Senior", "Senior")],
      [T("Secondo incontro", "Second meeting"), T("Il rapporto approvato, nella lingua del cliente.", "The approved report, in the client's language."), T("Consulente", "Adviser")],
    ];
    flow.forEach(([t, d, who], i) => {
      const x = 0.5 + i * 2.07;
      card(s, x, 1.6, 1.92, 3.6, i === 2 || i === 4 ? X.tealSoft : X.bg);
      badge(s, x + 0.2, 1.8, i + 1, 0.36, X.navy);
      s.addText(t, tb({ x: x + 0.2, y: 2.3, w: 1.6, h: 0.6, fontSize: 14.5, bold: true, color: X.navy }));
      s.addText(d, tb({ x: x + 0.2, y: 2.95, w: 1.6, h: 1.7, fontSize: 11.5 }));
      chip(s, x + 0.2, 4.75, who, X.teal, X.white, 1.5);
    });
    card(s, 0.5, 5.5, 12.35, 1.1, X.white, X.border);
    s.addText([
      { text: T("Obiettivo: ", "Target: "), options: { bold: true, color: X.navy } },
      { text: T("meno di 2 ore di lavoro dell'analista per cliente, ogni cifra controllata. Oggi un confronto completo richiede probabilmente 6-10 ore (nostra stima: da misurare con voi su un caso reale).",
        "under 2 hours of analyst time per prospect, every figure checked. A full comparison today probably takes 6 to 10 hours (our estimate: to be timed with you on a real case).") },
    ], tb({ x: 0.75, y: 5.55, w: 11.9, h: 1.0, fontSize: 14, valign: "middle" }));
  }

  // ---------- Pilot ----------
  {
    const s = content(T("Pilota", "Pilot"), T("Pilota supervisionato: 10 clienti o 3 mesi", "Supervised pilot: 10 prospects or 3 months"), T("Uso e pilota", "Use and pilot"));
    const phases = [
      [T("Prima", "Before"), [T("Installazione su un vostro computer", "Install on one of your computers"), T("Mezza giornata di formazione", "Half-day training"), T("Analisti e revisore nominati", "Analysts and reviewer named"), T("Consenso e DPIA firmati", "Consent and DPIA signed")]],
      [T("Durante", "During"), [T("Solo documenti consegnati per questo scopo", "Only documents handed over for this purpose"), T("Ogni cifra controllata, ogni correzione registrata", "Every figure checked, every correction recorded"), T("Noi rivediamo i rapporti con l'analista", "We review the reports with the analyst")]],
      [T("Dopo", "After"), [T("Rapporto del pilota (solo numeri, nessun nome)", "Pilot report (numbers only, no names)"), T("Decisione: estendere, correggere o fermarsi", "Decision: widen, fix or stop")]],
    ];
    phases.forEach(([t, pts], i) => {
      const x = 0.5 + i * 4.15;
      card(s, x, 1.5, 3.95, 2.75, X.bg);
      s.addText(t, tb({ x: x + 0.25, y: 1.65, w: 3.4, h: 0.4, fontSize: 17, bold: true, color: X.teal }));
      s.addText(pts.map((p, j) => ({ text: p, options: { bullet: true, breakLine: j < pts.length - 1 } })), tb({ x: x + 0.25, y: 2.1, w: 3.5, h: 2.1, fontSize: 13, paraSpaceAfter: 4 }));
    });
    s.addText(T("Criteri per passare all'uso pieno (proposta)", "Criteria to move to full use (proposal)"), tb({ x: 0.5, y: 4.45, w: 12, h: 0.4, fontSize: 16, bold: true, color: X.navy }));
    const crit = [
      ["0", T("cifre sbagliate in un rapporto consegnato", "wrong figures in any delivered report")],
      ["8 / 10", T("clienti con costo annuo entro il 5% già prima del controllo", "prospects with annual cost within 5% even before review")],
      ["10 / 10", T("clienti con patrimonio entro l'1%", "prospects with assets within 1%")],
      ["< 2 h", T("di lavoro dell'analista per cliente", "of analyst time per prospect")],
    ];
    crit.forEach(([n, t], i) => {
      const x = 0.5 + i * 3.1;
      card(s, x, 4.9, 2.95, 1.55, X.white, X.border);
      s.addText(n, tb({ x: x + 0.2, y: 5.0, w: 2.6, h: 0.6, fontSize: 28, bold: true, color: X.teal }));
      s.addText(t, tb({ x: x + 0.2, y: 5.6, w: 2.6, h: 0.8, fontSize: 12 }));
    });
    s.addText(T("Il pilota si ferma subito a ogni incidente sui dati o a ogni cifra sbagliata trovata in un rapporto già consegnato.",
      "The pilot stops at once on any data incident or any wrong figure found in a report already delivered."),
      tb({ x: 0.5, y: 6.55, w: 12.35, h: 0.3, fontSize: 11, color: X.muted }));
  }

  // ---------- Price ----------
  {
    const s = content(T("Prezzo", "Price"), T("Quanto costa: un pilota, poi una licenza annuale", "What it costs: a pilot, then an annual licence"), T("Prezzo", "Price"));
    chip(s, 10.15, 0.33, T("PROPOSTA · DA CONFERMARE", "PROPOSAL · TO CONFIRM"), X.amber, X.amberSoft, 2.7);
    const tiers = [
      [T("Pilota", "Pilot"), "CHF 3'000", T("una volta, 3 mesi", "once, 3 months"), [T("Fino a 10 clienti", "Up to 10 prospects"), T("Installazione da voi e formazione", "Install at your office and training"), T("Rivediamo i rapporti con voi", "We review reports with you"), T("Rapporto del pilota", "Pilot report"), T("Scalato al 100% dal primo anno", "100% credited to year 1")], X.teal, X.tealSoft],
      ["Essential", "CHF 9'000", T("all'anno (CHF 750 al mese)", "a year (CHF 750 a month)"), [T("3 utenti, 40 analisi all'anno", "3 users, 40 analyses a year"), T("Hosting svizzero o vostro computer", "Swiss hosting or your machine"), T("Aggiornamenti, nuove banche, backup, supporto", "Updates, new bank layouts, backups, support"), T("Analisi extra CHF 200", "Extra analysis CHF 200")], X.navy, X.infoSoft],
      ["Professional", "CHF 18'000", T("all'anno (CHF 1'500 al mese)", "a year (CHF 1,500 a month)"), [T("10 utenti, 150 analisi all'anno", "10 users, 150 analyses a year"), T("Stessi servizi, supporto prioritario", "Same services, priority support"), T("Analisi extra CHF 120", "Extra analysis CHF 120")], X.navy, X.bg],
    ];
    tiers.forEach(([t, p, per, pts, c, bg], i) => {
      const x = 0.5 + i * 4.15;
      card(s, x, 1.5, 3.95, 4.15, bg);
      s.addText(t, tb({ x: x + 0.3, y: 1.7, w: 3.4, h: 0.4, fontSize: 17, bold: true, color: c }));
      s.addText(p, tb({ x: x + 0.3, y: 2.15, w: 3.4, h: 0.7, fontSize: 32, bold: true, color: X.navy }));
      s.addText(per, tb({ x: x + 0.3, y: 2.85, w: 3.4, h: 0.3, fontSize: 12, color: X.muted }));
      s.addText(pts.map((q, j) => ({ text: q, options: { bullet: true, breakLine: j < pts.length - 1 } })), tb({ x: x + 0.3, y: 3.3, w: 3.45, h: 2.3, fontSize: 12.5, paraSpaceAfter: 4 }));
    });
    card(s, 0.5, 5.85, 12.35, 0.85, X.white, X.border);
    s.addText([
      { text: T("Avvio dopo il pilota: ", "Setup after the pilot: "), options: { bold: true, color: X.navy } },
      { text: T("CHF 5'000 una volta (utenti con MFA, vostre tariffe e modelli, logo, rapporti IT/EN); metà prezzo per Safe Capital. ", "CHF 5,000 once (users with MFA, your tariffs and templates, logo, IT/EN reports); half price for Safe Capital. ") },
      { text: T("Cliente fondatore: ", "Founding customer: "), options: { bold: true, color: X.navy } },
      { text: T("-25% il primo anno e prezzo bloccato 2 anni, in cambio di referenza e numeri anonimi del pilota. Prezzi IVA 8.1% esclusa.", "25% off year 1 and price held for 2 years, for a reference and anonymised pilot numbers. Prices exclude 8.1% VAT.") },
    ], tb({ x: 0.75, y: 5.9, w: 11.9, h: 0.75, fontSize: 12.5, valign: "middle" }));
    s.addNotes(T("Fonte: documento «FeeLens pricing for Safe Capital» (13.11.2026). Prezzi proposti, non ancora approvati da Ale. Un'analisi = un cliente, tutti i suoi documenti, fino al rapporto approvato; rifarla entro 12 mesi è gratis.",
      "Source: doc \"FeeLens pricing for Safe Capital\" (13 Nov 2026). Proposed prices, not yet approved by Ale. One analysis = one prospect, all their documents, until the report is approved; re-running it within 12 months is free."));
  }

  {
    const s = content(T("Prezzo", "Price"), T("Perché questo prezzo è giusto", "Why this price is fair"), T("Prezzo", "Price"));
    bigNum(s, 0.5, 1.5, 4.0, "~CHF 225", T("per analisi con Essential", "per analysis on Essential"), X.teal, T("CHF 9'000 / 40 analisi", "CHF 9,000 / 40 analyses"));
    bigNum(s, 4.67, 1.5, 4.0, "0.45%", T("di commissione su un solo mandato di CHF 2 mln paga la licenza annuale", "fee on one CHF 2m mandate pays the yearly licence"), X.navy, T("CHF 9'000 / CHF 2'000'000", "CHF 9,000 / CHF 2,000,000"));
    bigNum(s, 8.85, 1.5, 4.0, "< 2 h", T("di lavoro dell'analista per cliente, ogni cifra controllata", "of analyst time per prospect, every figure checked"), X.navy, T("obiettivo; oggi stimiamo 6–10 h, da misurare con voi", "target; today we estimate 6 to 10 h, to time with you"));
    s.addText(T("Perché non un prezzo per documento", "Why not a price per document"), tb({ x: 0.5, y: 3.55, w: 6, h: 0.4, fontSize: 16, bold: true, color: X.navy }));
    s.addText([
      { text: T("Spinge a lasciare fuori documenti: i costi nascosti restano nascosti.", "It pushes people to leave documents out: hidden costs stay hidden."), options: { bullet: true, breakLine: true } },
      { text: T("Un cliente con 30 PDF costerebbe 6 volte uno ordinato.", "A prospect with 30 PDFs would cost 6 times a tidy one."), options: { bullet: true, breakLine: true } },
      { text: T("Si paga l'analisi: un cliente, tutti i suoi documenti.", "You pay per analysis: one prospect, all their documents."), options: { bullet: true } },
    ], tb({ x: 0.5, y: 4.0, w: 6.0, h: 2.0, fontSize: 13.5, paraSpaceAfter: 6 }));
    s.addText(T("Confronti di mercato", "Market anchors"), tb({ x: 6.85, y: 3.55, w: 6, h: 0.4, fontSize: 16, bold: true, color: X.navy }));
    s.addText([
      { text: T("InvestGlass (CRM, Ginevra): CHF 100-500 per utente al mese.", "InvestGlass (CRM, Geneva): CHF 100 to 500 per user a month."), options: { bullet: true, breakLine: true } },
      { text: T("Non abbiamo trovato uno strumento svizzero che pubblichi un prezzo per questo lavoro.", "We found no Swiss tool that publishes a price for this job."), options: { bullet: true, breakLine: true } },
      { text: T("Per noi il costo di calcolo per analisi è quasi zero: nessuna IA a pagamento.", "Our computing cost per analysis is near zero: no paid AI."), options: { bullet: true } },
    ], tb({ x: 6.85, y: 4.0, w: 6.0, h: 2.4, fontSize: 13.5, paraSpaceAfter: 6 }));
    s.addText(T("Fonte: investglass.com, consultato il 13.11.2026. Le altre cifre sono calcoli dai prezzi proposti.", "Source: investglass.com, opened 13 Nov 2026. The other figures are arithmetic on the proposed prices."), tb({ x: 0.5, y: 6.55, w: 12, h: 0.3, fontSize: 10, color: X.muted }));
  }

  // ---------- Next steps ----------
  {
    const s = content(T("Prossimi passi", "Next steps"), T("Cosa serve da voi per partire", "What we need from you to start"), T("Prossimi passi", "Next steps"));
    const qs = [
      T("Quante analisi al mese prevedete? (sceglie Essential o Professional)", "How many cost reviews a month do you expect? (picks Essential or Professional)"),
      T("Quanto dura oggi un confronto dei costi, in ore? (cronometriamo un caso)", "How long does a cost comparison take today, in hours? (we time one case)"),
      T("Pilota su un vostro computer o subito su un server svizzero? Usate Microsoft 365?", "Pilot on your computer or straight on a Swiss server? Do you use Microsoft 365?"),
      T("Chi sono l'analista e il secondo revisore (quattro occhi)?", "Who are the analyst and the second reviewer (four eyes)?"),
      T("Chi firma DPIA, testo di consenso e periodo di conservazione?", "Who signs the DPIA, the consent text and the retention period?"),
      T("Il secondo family office vuole partecipare al pilota?", "Does the second family office want to join the pilot?"),
    ];
    qs.forEach((q, i) => {
      const y = 1.5 + i * 0.78;
      badge(s, 0.5, y + 0.05, i + 1, 0.4, X.navy);
      s.addText(q, tb({ x: 1.1, y, w: 7.3, h: 0.7, fontSize: 15, valign: "middle" }));
    });
    card(s, 8.8, 1.5, 4.05, 4.6, X.tealSoft);
    s.addText(T("Calendario proposto", "Proposed timeline"), tb({ x: 9.05, y: 1.7, w: 3.6, h: 0.4, fontSize: 17, bold: true, color: X.teal }));
    s.addText([
      { text: T("Settimane 1-3: ", "Weeks 1-3: "), options: { bold: true } }, { text: T("completiamo accesso MFA, cancellazione, cifratura e registro; voi DPIA e consenso.", "we finish MFA sign-in, deletion, encryption and log; you do DPIA and consent."), options: { breakLine: true } },
      { text: T("Settimana 4: ", "Week 4: "), options: { bold: true } }, { text: T("installazione e formazione.", "install and training."), options: { breakLine: true } },
      { text: T("Mesi 2-4: ", "Months 2-4: "), options: { bold: true } }, { text: T("pilota su 10 clienti.", "pilot on 10 prospects."), options: { breakLine: true } },
      { text: T("Fine: ", "End: "), options: { bold: true } }, { text: T("rapporto e decisione insieme.", "report and joint decision.") },
    ], tb({ x: 9.05, y: 2.2, w: 3.6, h: 3.8, fontSize: 13.5, paraSpaceAfter: 10 }));
    s.addNotes(T("Il calendario è una stima: dipende dalla data di firma della DPIA e dalla scelta del computer.", "The timeline is an estimate: it depends on when the DPIA is signed and which machine is chosen."));
  }

  // ---------- Closing ----------
  {
    const s = pres.addSlide({ masterName: "Dark", sectionTitle: T("Prossimi passi", "Next steps") });
    s.addText(T("Ogni cifra con la sua fonte.", "Every figure with its source."), tb({ x: 0.8, y: 2.2, w: 11.5, h: 1.0, fontSize: 40, bold: true, color: X.white }));
    s.addText(T("Ciò che manca resta visibile. Il risparmio è un minimo, mai una promessa.", "What is missing stays visible. The saving is a floor, never a promise."), tb({ x: 0.8, y: 3.3, w: 11.5, h: 0.8, fontSize: 22, color: X.paleNavy }));
    s.addText(T("Proposta: pilota supervisionato di 3 mesi, CHF 3'000.", "Proposal: 3-month supervised pilot, CHF 3,000."), tb({ x: 0.8, y: 4.6, w: 11.5, h: 0.6, fontSize: 20, bold: true, color: X.white }));
  }

  // ---------- Appendix: sources ----------
  {
    const s = content(T("Appendice", "Appendix"), T("Da dove vengono i numeri e le immagini", "Where the numbers and pictures come from"), T("Appendice", "Appendix"));
    const lines = [
      [T("Schermate", "Screenshots"), T("App FeeLens, versione principale del 13.11.2026 con la tariffa della società, eseguita in locale. Clienti P-1042 e P-2077 sintetici (banche, ISIN e importi inventati).", "FeeLens app, main version of 13 Nov 2026 with the firm tariff, run locally. Prospects P-1042 and P-2077 are synthetic (banks, ISINs and amounts invented).")],
      [T("Documenti reali", "Real documents"), T("AJ Bell, rapporto demo cliente (investcentre.co.uk); BlackRock, KID iShares Core S&P 500 (IT) e Core MSCI World (EN); Julius Baer Europe, tariffario custodia (2025). Documenti pubblici, clienti fittizi.", "AJ Bell demo client report (investcentre.co.uk); BlackRock iShares Core S&P 500 (IT) and Core MSCI World (EN) KIDs; Julius Baer Europe custody price list (2025). Public documents, fictitious clients.")],
      [T("Accuratezza", "Accuracy"), T("62 pagine reali, 813 costi distinti controllati a mano; main rimisurato il 14.11.2026 (metodo ricontrollato in modo indipendente il 13.11); 130 KID pubblici; 4 estratti pubblici (Fidelity USA e UK, AJ Bell, Edward Jones). Velocità: 4 core, 13.11.2026.", "62 real pages, 813 distinct fees checked by hand; main re-run on 14 Nov 2026 (method independently re-checked on 13 Nov); 130 public KIDs; 4 public statements (Fidelity US and UK, AJ Bell, Edward Jones). Speed: 4 cores, 13 Nov 2026.")],
      [T("Prezzi", "Prices"), T("Documento «FeeLens pricing for Safe Capital», 13.11.2026: proposta da confermare. Riferimento di mercato: investglass.com.", "Doc \"FeeLens pricing for Safe Capital\", 13 Nov 2026: proposal to confirm. Market reference: investglass.com.")],
      [T("Limiti", "Limits"), T("Campione scelto per coprire i tipi di documento, un solo annotatore; estratti svizzeri e italiani non pubblici: il pilota è la prova vera.", "Sample chosen to cover document types, one annotator; Swiss and Italian statements are not public: the pilot is the real test.")],
    ];
    lines.forEach(([h, t], i) => {
      const y = 1.5 + i * 1.02;
      s.addText(h, tb({ x: 0.5, y, w: 2.4, h: 0.9, fontSize: 14, bold: true, color: X.navy }));
      s.addText(t, tb({ x: 2.9, y, w: 9.95, h: 0.95, fontSize: 12.5 }));
    });
  }

  await pres.writeFile({ fileName: OUT });
  console.log("wrote", OUT);
})();
