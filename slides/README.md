# FeeLens deck for Safe Capital

Audience: Massimo (Safe Capital, Lugano), non-technical. One source, two languages, 21 slides each: 17 main slides and a 4-slide appendix.
FeeLens is the product's working name, chosen by Ale on 6 Nov 2026. It still needs a trademark check.

- `FeeLens_Presentazione_IT.pptx` / `.pdf`: Italian deck, with speaker notes and sections
- `FeeLens_Deck_EN.pptx` / `.pdf`: the same deck in English
- `source/build_deck.js`: the generator (pptxgenjs). Edit this, not the PPTX, then rebuild. Every text has its Italian and English form side by side (`T(it, en)`).
- `source/realpages/`: zoomed crops of real public documents. Each value FeeLens extracts has a box and a number that match the list on the slide.
- `source/logos/`: issuer logos cropped from those same documents. They are used only to identify where a document comes from; no partnership or endorsement is implied.
- `source/mockups/app_v2.html`: app screen mockups in the shared design system (`docs/design/DESIGN_SYSTEM.md`). `source/img/v2_*.png` are their screenshots.

Design rule from Ale (6 Nov 2026): as simple as possible. One idea per slide, plain words, emphasis only on key numbers (teal for the result, amber for hidden costs). Details go in the speaker notes and the appendix.

## Storyline

1. Why (1–3): cover; the problem (CHF 61'450 real cost vs 40'160 debited, 35% hidden); three steps with their outputs and the three rules
2. How it works (4–6): six-step process with who does it, output and time; requirements (client, Safe Capital, technical); what banks publish vs what only the client has, with source logos
3. Real documents (7–9): Julius Baer Europe price list field by field (and why its tariff is rejected for a Swiss client); the iShares Core MSCI World KID in five fields; ZKB and Raiffeisen Locarno custody lines
4. Checks (10–12): five kinds of data and five statuses; reconciliation; drill-down screen
5. Result (13–15): comparison with the "at least CHF 6'520" callout; the four outputs; data and privacy
6. Getting started (16–17): pilot plan; call to action (one anonymised real case, Safe Capital's tariffs, two confirmations)
7. Appendix (18–21): document table, ten cost layers, technology and licences, glossary

## Client figures are synthetic

They come from the demo engine (branch `claude/project-thread-steqtm`, `PYTHONPATH=backend/src python3 -m pce.demo.offline data/synthetic/prospect_p1042`). Every figure below was re-checked against that output on 6 Nov 2026. The prospect is P-1042: CHF 4.3m, with Bank Alpha 3.2m and Bank Beta 1.1m, over the period 01.10.2025–30.09.2026.

| CHF per year | Today (comparable) | Safe Capital, same holdings | Safe Capital, new funds |
|---|---|---|---|
| Management / advisory | 25'600 | 25'500 (EAM, 70/50 bps tiers) | 25'500 |
| Custody, trading, FX | 11'390 | 5'140 (partner custodian) | 5'140 |
| VAT | 2'559.60 | 2'389.50 (8.1%, CH domicile) | 2'389.50 |
| Fund costs inside prices | 21'290 | 21'290 | 13'110 |
| **Total** | **60'839.60** (1.41%) | **54'319.50** (1.26%) | **46'139.50** |

- Known current cost, including stamp duty of 610: 61'449.60 (142.9 bps). Debited 40'159.60 (65%); inside fund prices 21'290 (35%, estimated from KIDs).
- Five items are not determined and are never counted as zero, so savings are "at least".
- Stamp duty is excluded from both sides of the comparison.
- Saving: at least 6'520.10 (same holdings) and 14'700.10 (new funds, not like for like). Switching costs 1'500 and 4'000; payback 2.8 and 3.3 months.

## Real public documents (slides 6–9)

Downloaded on 6 Nov 2026; figures quoted as printed. The PDFs are not stored in the repo (copyright); only the small crops are.
- Bank Julius Baer Europe S.A. (Luxembourg), *Schedule of prices and services, banking and custody*, PU00505EN, June 2025, "for clients booked in Luxembourg only" (p.1), custody bands p.3: https://www.juliusbaer.com/fileadmin/legal/schedule-of-prices-and-services-banking-and-custody.pdf
- BlackRock, PRIIPs KID for iShares Core MSCI World UCITS ETF USD (Acc), IE00B4L5Y983, created 3 Sep 2026, costs on p.3 (copy hosted by LV 1871): https://fsl.lv1871.de/product/IE00B4L5Y983/kid
- Zürcher Kantonalbank, *Preisübersicht Anlagegeschäft*, prices from October 2025, custody on p.1: https://www.zkb.ch/media/zkb/dokumente/legal/preisuebersicht_anlagegeschaeft.pdf
- Raiffeisenbank Locarno, *Dienstleistungspreise Anlegen*, valid from 1 January 2025, custody on p.2: https://www.raiffeisen.ch/content/dam/www/locarno/pdf/de-prezzi-servizi-2025/dienstleistungspreise-anlegen-ab-01-2025 (the crop on slide 9 joins the label column and the "Wertschriftendepot" column; the dashed line marks the cut)
- UBS Switzerland AG, FinSA page (cost details "on request"): https://www.ubs.com/ch/en/collections/fidleg.html

Not reachable or not public: the UBS private-client price list (the site refuses automated download; download it by hand from https://www.ubs.com/content/dam/ubs/ch/swissbank/private/zahlen-und-sparen/konten/dienstleistungen-und-preise.pdf), any UBS or Julius Baer mandate fee rates, and any public specimen of a statement of assets or an ex-post cost report.

## Live versions (private until shared)

- Italian deck: https://claude.ai/artifact/CWsTBHgfGCQex6jbXeHbPM
- English deck: https://claude.ai/artifact/Hd88azNdk8C1CsnHaNwb1q
- Explorer page (details behind expanders): https://claude.ai/artifact/HAR2cwFgZU2QLeLrDCZrLZ

## Facts the deck relies on, and what is not verified

- **Data protection.** The Swiss revised FADP has been in force since 1 September 2023. This is not legal advice; counsel must review it.
- **Safe Capital's model.** Safe Capital is an external asset manager, so every Safe Capital scenario includes the custodian bank's fees. VAT depends on the client's domicile.
- **Commercial register.** Safe Capital Management SA (CHE-381.156.096), Lugano, active (secondary copy of Zefix, 6 Nov 2026).
- **FINMA licence: not verified.** The website states FINMA authorisation; the deck does not cite it.
- **Times ("minutes") are design targets**, not measured results.
- **Screens are mockups** fed with the engine's output (in English). Replace them with real app screenshots when the UI lands.

## Rebuild

```bash
cd slides/source
npm install                                   # pinned versions in package.json
DECK_LANG=it node build_deck.js               # ../FeeLens_Presentazione_IT.pptx
DECK_LANG=en node build_deck.js               # ../FeeLens_Deck_EN.pptx
# optional theme colours: APPLY_THEME_JS=<pptx skill>/scripts/apply_theme.js NODE_PATH=$PWD/node_modules
soffice --headless --convert-to pdf --outdir .. ../FeeLens_Presentazione_IT.pptx ../FeeLens_Deck_EN.pptx
```
