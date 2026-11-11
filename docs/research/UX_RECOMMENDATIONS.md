# UX recommendations from the research

Input for the app and design threads, 2026-11-06. These follow from the cost and document findings, not from a visual design.

## Two audiences, two surfaces

| Surface | User | Job | Tone |
|---|---|---|---|
| **Analyst workspace** | Safe Capital staff | Upload, check extraction, resolve gaps, approve | Dense, keyboard-friendly, every number clickable to its source |
| **Client report** | Prospect, non-technical | Understand what they pay and what they could save | Few numbers, plain language, honest about estimates |

Never show internal margins or analyst notes on the client surface.

## Flow (5 steps, one per screen)

1. **New analysis**: prospect alias (no real name needed), base currency, client domicile (drives VAT), consent checkbox.
2. **Upload and checklist**: drop files; each is classified live; a checklist shows which of the top-6 documents (see `DOCUMENT_TAXONOMY.md`) are present, missing or partial. Primary CTA: "Analyse". Secondary: "Generate document request letter".
3. **Review extraction**: split view, PDF page with highlighted box on the left, extracted fields on the right; low-confidence fields first; accept / correct / reject. Holdings total vs statement total reconciliation shown at the top.
4. **Cost ledger**: table by layer (L1–L10), each row with amount CHF, bps, status chip (Observed / Contractual / Estimated / Public tariff / Unknown), source link. Overlaps (e.g. custody inside all-in) are shown indented and greyed, not summed.
5. **Comparison and report**: current vs Safe Capital on same holdings; one-off switching cost and payback; gaps list. Export to PDF.

## Key dashboard elements

- **Headline**: "Estimated all-in cost: CHF 41,200 per year (1.37%)" with a **coverage meter** next to it ("82% of expected cost categories evidenced"). Never a headline without coverage.
- **Stacked bar by evidence status**: proven, estimated, unknown (hatched, no fake length; show as a labelled gap).
- **Breakdown by layer**: service, custody, trading, products, implicit, wrapper. Product costs are usually the surprise for clients: give them their own colour.
- **Top cost drivers**: the five positions or fees that cost the most, with one-line explanations ("Fund X: TER 1.85% on CHF 270k = CHF 5,000/yr").
- **Gaps panel**: each unknown with the document that would close it and a "add to request letter" button.
- **Savings card**: annual difference, % change, payback months; footnote with assumptions and the same-holdings basis.

## Wording rules

- Say "estimated" whenever status is not Observed. Say "we could not determine" for unknowns; never show 0.
- Use the client's language (Italian first for Lugano prospects, then German, English).
- Explain jargon inline: TER, retrocession, custody fee, in one sentence each.

## Accessibility and best practice

Status is never conveyed by colour alone (chip text + icon). Numbers right-aligned with tabular figures and Swiss formatting (`1'234.50`) or locale. Keyboard navigation in the review table. Every chart has a table equivalent.
