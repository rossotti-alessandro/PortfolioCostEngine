---
description: Decks and demo material. Generators, EN + IT, synthetic figures, real screenshots, unverified claims.
paths:
  - "slides/**"
---

# Deck rules

Audience and storyline: [slides/README.md](../../slides/README.md).

- **Generators only.** Edit `slides/source/*.js` (pptxgenjs) and rebuild; never edit a PPTX or PDF by hand.
  Every text has its Italian and English form side by side; both decks are rebuilt in the same PR.
- **Figures come from the engine.** Client figures are the SYNTHETIC prospects (P-1042, P-2077) as the
  engine computes them on `main`; they are pinned in `backend/tests/test_pipeline.py`. Change the engine,
  re-check every quoted figure. Missing stays "not determined"; savings stay "at least".
- **Screens are real.** Screenshots come from the app on `main` with a SYNTHETIC prospect, in the deck's
  language (Playwright, `deviceScaleFactor: 2`). A mockup is labelled as a mockup.
- **Accuracy and speed claims** quote the number, the corpus, the date and what the number counts
  (`docs/READINESS.md` §3). "Minutes" or other targets are labelled as targets, not results.
- **Unverified facts are not claims.** Regulatory status (for example a FINMA licence), trademarks and
  partner names stay out until verified; list them under "not verified" in `slides/README.md`.
- **Real public documents** appear only as small crops with their source URL and date; full PDFs are never
  committed. No real client document, name or account ever appears, even blurred.
- Simplicity rule: one idea per slide, plain words, emphasis only on the key numbers, details in the
  speaker notes or appendix.
