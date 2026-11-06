# Executive deck: Portfolio Cost Engine for Safe Capital

Audience: Massimo (Safe Capital, Lugano), non-technical. 21 slides, English.

- `PortfolioCostEngine_Executive_Deck.pptx`: editable deck with speaker notes
- `PortfolioCostEngine_Executive_Deck.pdf`: same deck as PDF
- `source/build_deck.js`: generator (pptxgenjs); edit this, not the PPTX, then rebuild
- `source/mockups/screens.html`: HTML mockups of the app screens and the synthetic bank statement
- `source/img/*.png`: screenshots of those mockups used in the deck

## Storyline

1. Why: the problem, the offer (slides 1–3)
2. How it works: five steps, what the client brings, the three cost layers, reading documents (4–7)
3. The screens: upload, review, fund costs via KID, no double counting / missing ≠ zero, cost dashboard (8–12)
4. The result: comparison, year-one payback, client report (13–15)
5. Data & privacy: where it runs, confidentiality controls (16–17)
6. Next steps: human vs automatic, phases, six decisions, close (18–21)

## Every figure is synthetic

Numbers come from the handoff kit's `data/synthetic_cost_inputs.json` (AUM CHF 4.0m):

| Line | Today | Same holdings | New portfolio |
|---|---|---|---|
| Management / advisory | 17'100 | 15'200 | 15'200 |
| Custody | 5'700 | 3'040 | 3'040 |
| Brokerage | 2'300 | 1'800 | 1'800 |
| FX | 1'200 | 700 | 700 |
| Structured products | 1'600 | 1'600 | 0 |
| Fund products (in NAV) | 10'200 | 10'200 | 3'000 |
| **Total** | **38'100 (0.95%)** | **32'540 (0.81%)** | **23'740 (0.59%)** |

Switching cost CHF 8'000 (synthetic). Payback = 8'000 / annual difference × 12: about 17 months (same holdings), about 7 months (new portfolio).
The fund cost split (8'640 + 490 + 1'070 = 10'200) and the KID example (OCF 1.08% including AMF 0.75%) are invented for the demo, as are Banca Alfa / Banca Beta, PROSPECT-001 and the `ZZDEMO…` identifiers (deliberately not valid ISINs).

## Facts the deck relies on, and what is not verified

- Swiss revised FADP in force since 1 September 2023 (slide 17). Not legal advice; counsel must review.
- Commercial register (secondary copy of Zefix, checked 6 Nov 2026): Safe Capital Management SA (CHE-381.156.096) and Safe Capital Holding SA (CHE-291.799.912), Via Serafino Balestra 5, Lugano, both active. **FINMA licence and supervisory organisation not verified**, so the deck asks Safe Capital to confirm what to cite (decision 6) instead of stating it.
- "Ready in minutes" is the design target for the automatic first draft, not a measured result.
- Screens are mockups, not the running app. When the app lands, replace `source/img/*.png` with real screenshots and check every figure against the live engine.

## Rebuild

```bash
cd slides/source
npm install                      # pinned versions in package.json
node build_deck.js               # writes ../PortfolioCostEngine_Executive_Deck.pptx
# optional: APPLY_THEME_JS=<path to pptx skill>/scripts/apply_theme.js NODE_PATH=$PWD/node_modules node build_deck.js
#           writes the theme colours into the file so PowerPoint's colour pickers match
soffice --headless --convert-to pdf --outdir .. ../PortfolioCostEngine_Executive_Deck.pptx
```

To re-shoot mockups after editing `screens.html`, screenshot the elements `#statement #upload #review #costs #report` at device scale 2 with Playwright.
