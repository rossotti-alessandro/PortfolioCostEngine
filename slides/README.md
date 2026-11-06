# Executive deck: FeeLens for Safe Capital

Audience: Massimo (Safe Capital, Lugano), non-technical. 27 slides, English: 23 main slides and a 4-slide deep-dive appendix.
FeeLens is the product's working name, chosen by Ale on 6 Nov 2026. It still needs a trademark check.

- `FeeLens_Executive_Deck.pptx`: editable deck, with speaker notes and sections
- `FeeLens_Executive_Deck.pdf`: the same deck as a PDF
- `source/build_deck.js`: the generator (pptxgenjs). Edit this, not the PPTX, then rebuild. `PRODUCT_NAME=... node build_deck.js` renames everything.
- `source/mockups/app_v2.html`: app screen mockups in the shared design system (`docs/design/DESIGN_SYSTEM.md`). `?name=` sets the brand.
- `source/mockups/docs/`: page renders of the app's synthetic bank PDFs, used inside the mockups
- `source/img/v2_*.png`: screenshots of the mockups used in the deck. The v1 files `screens.html` and `img/*.png` without the v2 prefix are kept for reference.

## Storyline

1. Why: the problem (40'160 shown vs 61'450 real), what FeeLens does and its three rules (slides 1–3)
2. How it works (4–10):
   - swimlane workflow (client / FeeLens / analyst / output)
   - documents table: what we read, what it proves, what it cannot prove
   - real public documents (ZKB and Raiffeisen Locarno price lists, the iShares Core MSCI World KID) with the figures quoted as printed and the page of each
   - five kinds of data
   - ten cost layers in four places
   - evidence statuses
   - reconciliation checks
3. The screens (11–14): costs overview with coverage, drill-down to the source page, review of scans, checks and request letter
4. The result (15–17): stacked comparison, year one and payback, client report
5. Data & privacy (18–19): hosting options, confidentiality controls
6. Next steps (20–23): people vs machine, phases, six decisions, close
7. Deep dive (24–27): the ten layers in detail, the pipeline and guardrails, the extraction stack and licences, a glossary

## Every figure is synthetic

The numbers are the output of the demo engine (branch `claude/project-thread-steqtm`, `python3 -m pce.demo.offline data/synthetic/prospect_p1042`). The prospect is P-1042: CHF 4.3m, with Bank Alpha 3.2m and Bank Beta 1.1m, over the period 01.10.2025–30.09.2026.

| CHF per year | Today (comparable) | Safe Capital, same holdings | Safe Capital, new funds |
|---|---|---|---|
| Management / advisory | 25'600 | 25'500 (EAM, 70/50 bps tiers) | 25'500 |
| Custody, trading, FX | 11'390 | 5'140 (partner custodian) | 5'140 |
| VAT | 2'559.60 (8.1% on advisory + custody) | 2'389.50 (8.1%, CH domicile) | 2'389.50 |
| Fund costs inside prices | 21'290 | 21'290 | 13'110 |
| **Total** | **60'839.60** | **54'319.50** | **46'139.50** |

- Known current cost, including stamp duty of 610: 61'449.60 (143 bps). Of this, 65% is observed and 35% is estimated from KIDs.
- Five items are not determined and are never counted as zero.
- Stamp duty is excluded from both sides of the comparison.
- The saving is "at least" 6'520.10 for the same holdings and 14'700.10 for the new funds.
- Switching costs are 1'500 and 4'000. The payback is 2.8 and 3.3 months.
- The app thread fixed a synthetic-data bug on 6 Nov 2026: the current-side VAT was 486 and is now 2'559.60.

## Real public documents quoted (slide 6)

Read on 6 Nov 2026 as text, with figures quoted as printed. The PDFs are not stored in the repo.
- Zürcher Kantonalbank, *Preisübersicht Anlagegeschäft, Preise ab September 2025*: https://www.zkb.ch/media/zkb/dokumente/legal/preisuebersichten/preisuebersicht_anlagegeschaeft_de_sept2025.pdf
- Raiffeisenbank Locarno, *Dienstleistungspreise Anlegen, gültig ab 1. Januar 2025*: https://www.raiffeisen.ch/content/dam/www/locarno/pdf/de-prezzi-servizi-2025/dienstleistungspreise-anlegen-ab-01-2025
- BlackRock, PRIIPs KID for iShares Core MSCI World UCITS ETF USD (Acc), IE00B4L5Y983, created 3 Sep 2026 (copy hosted by LV 1871): https://fsl.lv1871.de/product/IE00B4L5Y983/kid. The iShares factsheet gives a TER of 0.20%.

## Facts the deck relies on, and what is not verified

- **Data protection.** The Swiss revised FADP has been in force since 1 September 2023. This is not legal advice; counsel must review it.
- **Safe Capital's model.** Safe Capital is an external asset manager. Every Safe Capital scenario therefore includes the custodian bank's fees. VAT depends on the client's domicile.
- **Commercial register.** Checked on 6 Nov 2026 in a secondary copy of Zefix:
  - Safe Capital Management SA (CHE-381.156.096), Lugano, active.
  - Safe Capital Holding SA (CHE-291.799.912), Lugano, active.
- **FINMA licence: not verified.** The website states FINMA authorisation with OSIF supervision. Decision 6 asks Safe Capital to confirm what to cite.
- **"Minutes" is a design target**, not a measured result.
- **Screens are mockups** fed with the engine's output. Replace them with real app screenshots when the UI lands.

## Rebuild

```bash
cd slides/source
npm install                                  # pinned versions in package.json
node build_deck.js                           # writes ../FeeLens_Executive_Deck.pptx
# optional theme colours: APPLY_THEME_JS=<pptx skill>/scripts/apply_theme.js NODE_PATH=$PWD/node_modules node build_deck.js
soffice --headless --convert-to pdf --outdir .. ../FeeLens_Executive_Deck.pptx
```

To re-shoot the mockups, open `mockups/app_v2.html?name=FeeLens` with Playwright at device scale 2. Screenshot the elements `#overview #drill #review #checks #report` to `img/v2_<id>.png`.
