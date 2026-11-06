---
description: Frontend conventions. Design system, accessibility, numbers, client vs analyst surfaces.
paths:
  - "frontend/**"
---

# Frontend rules

Decision records: [0001 stack](../../docs/adr/0001-stack.md), [0002 design system](../../docs/adr/0002-design-system.md).
Tokens and components: [docs/design/DESIGN_SYSTEM.md](../../docs/design/DESIGN_SYSTEM.md). UX input: `docs/research/UX_RECOMMENDATIONS.md`.

- Use the tokens; no raw hex colours or ad-hoc spacing in components. Reuse `src/components/ui/*`
  (shadcn) and the house components before adding new ones.
- Numbers: right-aligned, `font-variant-numeric: tabular-nums`, Swiss grouping by default (`1'234.50`)
  through the one shared formatter. Show currency code. Show bps next to percentages on cost screens.
- Status is never colour alone: every evidence status chip has text and an icon
  (Observed, Contractual, Estimated, Illustrative, Unknown, Not applicable).
- Unknown is shown as "Not determined" with the document that would resolve it, never as 0 or a dash.
- Every number on a cost screen is clickable to its evidence (page + highlight, or sheet + cell).
- Every chart has a table equivalent. Keyboard works in the review table (j/k, a accept, e edit, r reject).
- No inert controls: a visible button does something real or is not rendered.
- The client report route never fetches internal-margin endpoints. The analyst workspace and the client
  report are separate layouts.
- Copy: plain language, Italian first for Lugano prospects (i18n keys from day one), then German, English.
- Money arrives from the API as strings. The frontend formats; it never re-computes totals.
