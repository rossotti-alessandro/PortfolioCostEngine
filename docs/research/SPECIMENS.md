# Specimen corpus: real public documents

72 real, public, official PDFs used to test FeeLens extraction against real layouts instead of
synthetic ones. Collected 2026-11-06 (story SC-2.3).

- **Manifest:** [`data/reference/specimen_corpus.csv`](../../data/reference/specimen_corpus.csv), one row per file:
  source URL, SHA-256, retrieval date, issuer, taxonomy code, language, jurisdiction, ISINs, licence
  and robots note, `expected` values read from the page text, category, title, document date, pages, encryption flag.
  The first 11 columns match `data/reference/public_corpus.csv` (demo thread) so the two can be merged.
- **The PDFs are not in git.** They are third-party copyrighted documents. Fetch them on demand:
  `python3 data/specimens/tools/fetch.py` (stdlib only) downloads into the git-ignored `var/specimens/`
  and checks every SHA-256. `--check` verifies without network.
- **Pipeline run:** `cd backend && uv run python ../data/specimens/tools/evaluate.py` calls
  `pce.extraction.parsers.extract` (the entry point the upload API uses) on every file and writes
  [`data/specimens/RESULTS.md`](../../data/specimens/RESULTS.md) (committed) and
  `artifacts/specimens/results.json` (git-ignored, contains snippets).

## What is in it

| Category | Files | Languages | Examples |
|---|---|---|---|
| ETF KID (PRIIPs) | 16 | en 5, de 3, it 4, fr 4 | iShares, Vanguard, Xtrackers, Amundi, SPDR, Invesco, WisdomTree |
| Active fund KID (PRIIPs) | 6 | de, it, en | DWS, Eurizon, Fidelity, JPMorgan |
| Fund/ETF KID (Swiss FinSA) | 3 | de, fr | Swisscanto Gold ETF, Swisscanto Portfolio, Gerifonds (BCV) |
| Fund factsheet | 6 | fr, it, en, de | Carmignac, Anima, JPMorgan, Swisscanto, BlackRock |
| Bank tariff CH | 12 | de, it, fr | ZKB, LUKB, BEKB, UKB, BCV, Raiffeisen Locarno (de + it), Cler, AEK, PostFinance, Cornèr, Migros Bank |
| Bank tariff IT | 7 | it | BancoPosta, UniCredit, BNL, Crédit Agricole Italia, Sparkasse Bolzano, Passadore, Banca Profilo |
| Bank tariff EU/other | 5 | en, de, fr | Julius Baer Europe (LU), HSBC Private Bank (LU), ING-DiBa, Trade Republic, BoursoBank |
| Cost disclosure (FinSA/MiFID ex-ante) | 5 | fr, it, de, en | BCV LSFin brochure, XTB, Postbank, Deutsche Bank Luxembourg, Nexent |
| Structured product termsheet | 7 | de, fr, en | BCV, ZKB, Raiffeisen Switzerland, Leonteq, Vontobel |
| Structured product KID | 3 | de, en, fr | Julius Baer tracker, BNP Paribas autocall, CIC autocall |
| Insurance KID | 2 | it | Genertellife, Eurovita (unit-linked, 87-page pack) |

58 issuers. 27 German, 20 Italian, 14 English, 11 French. 7 files carry owner-password encryption
(permissions only; text extracts), which is a useful intake edge case.

`cost_disclosure` is not yet a code in `data/taxonomy/document_types.csv` (it has the ex-post
`annual_cost_report` only). Proposed addition: `fees,cost_disclosure_ex_ante`, owned by SC-2.1.

## How each file was validated

Starts with `%PDF`; `pdfinfo` opens it; `pdftotext` on pages 1-3 returns at least 200 characters that
name the issuer (and the ISIN for product documents); the document is what the row claims (cost section
in a KID, a fee or TER figure in a factsheet, rates and minimums in a tariff); SHA-256 recorded; exact
duplicates dropped (the Julius Baer LU schedule was found twice). Document dates come from the text;
where a document prints only a month the day is set to the 1st, and where it prints no date the field is
empty and `notes` says where the date clue came from.

## Access rules followed

- robots.txt checked for every host; result recorded per row in `licence_note`. No login, paywall,
  CAPTCHA, WAF challenge or disclaimer gate was bypassed, no browser was spoofed.
- Never touched: ubs.com, credit-suisse.com, bancastato.ch, swissfunddata.ch (forbids scraping). A UBS
  ETF KID found on a third-party host was dropped to keep UBS out entirely.
- Skipped because of robots or blocks: comdirect (`Disallow: /*.pdf`), VR Bank GL, derinet.vontobel.ch
  (`Disallow: /`), products.swisscanto.com (`/*.pdf`), kid.baloise.lu, dl.avl-investmentfonds.de
  (disallows AI crawlers), Leonteq site (403), Raiffeisen structured products (401), am.pictet.com,
  am.vontobel.com, fidelityinternational.com, BBVA Italia, Trading 212 (403).
- **Judgement call, flagged for Ale:** raiffeisen.ch's robots.txt blocks its PDF store with patterns that
  need a `.pdf` suffix or `pdfs` in the path. The two Raiffeisen Locarno URLs match neither, so they are
  allowed by the letter of the file but arguably not by its intent. The demo thread already uses the
  German one. Drop both rows if we follow intent.
- Third-party hosts used where the issuer had no plain-GET PDF: docs.extraetf.com, fsl.lv1871.de,
  assets.finanzfluss.de, app.allfunds.com, api.kneip.com, data.payoff.ch (Swiss termsheet mirror).
  Each is noted per row.

## Re-download check (2026-11-06)

A fresh `fetch.py` run into an empty folder got 70/72 with matching hashes. UniCredit returned 403 to
the script's user agent (curl had worked) and ING-DiBa closed the connection. Neither was retried with a
different user agent. Publishers update KIDs monthly and price lists yearly, so expect `CHANGED` rows
over time; the script keeps the new copy beside the old one for a human to refresh the row.

## Extraction results (summary)

Full tables: [`data/specimens/RESULTS.md`](../../data/specimens/RESULTS.md). Two runs on the same 72 files:

| Metric | Parser at eb4b412 | After fixes at 3834590 |
|---|---|---|
| Crashes | 0 | 0 |
| Document type right | 45/72 | 63/72 |
| Files with at least one fact | 31/72 | 44/72 |
| Facts extracted | 99 | 189 |
| Facts with page + bbox inside the page | 99/99 | 189/189 |
| Page-read values matched (`expected`) | 13/31 | 26/31 |
| KID ongoing cost right | 5/20 | 15/20 |

The fixes between the two runs (wrapped KID labels, Italian labels, curly apostrophe, tariff keywords,
factsheets to `unknown`) were made by the demo thread from this corpus's bug report.

**Honest caveats.**

- Bounding boxes are always present and inside the page, but "inside the page" is a sanity check, not
  proof the box covers the right figure.
- Recall is measured on 31 values only: 23 KID ongoing costs that Claude read from each KID's text layer
  (`pdftotext -layout`, cost table on page 2 or 3) and the demo thread's 3 files. No human has re-checked them yet.
  The other facts are unverified.
- **Tariff precision is the main open risk.** A manual spot check of the new tariff facts found values
  with the wrong fee code or that are not fees at all: ZKB brokerage tiers labelled as custody; BNL and
  Passadore trading and corporate-action commissions labelled as custody; Banca Profilo `-2` taken from
  a footnote marker; UKB minimum investment amounts taken as fee minimums; an LUKB foreign-custody
  surcharge taken as the custody rate. Wrong values are worse than missing ones, so tariff facts must
  stay "needs review" until section headings drive the fee code. Sent to the demo thread.
- Not handled yet: factsheets (no parser, honestly `unknown`), insurance KIDs (0 facts), structured
  products (2 facts across 10 files), ex-ante cost disclosures from DB Luxembourg and XTB (`unknown`).
