---
description: Frontend conventions. Simplicity, design system, EN + IT, accessibility, numbers, client vs analyst surfaces.
paths:
  - "frontend/**"
---

# Frontend rules

Decision records: [0001 stack](../../docs/adr/0001-stack.md), [0002 design system](../../docs/adr/0002-design-system.md).
Tokens and components: [docs/design/DESIGN_SYSTEM.md](../../docs/design/DESIGN_SYSTEM.md). UX input: `docs/research/UX_RECOMMENDATIONS.md`.

## Simplicity first (Ale's rule)

- Every screen answers its question first: the key number or the next action, in one line, at the top.
- Emphasis only on the key numbers. Everything else is quiet: details behind an (i) icon, an expander,
  a row that opens, or a dropdown. Plain words, clear headers, no jargon without a tooltip.
- One primary action per screen. No inert controls: a visible button does something real or is not rendered.
- Before adding a component, panel or setting, check whether an existing one can carry it. Removing UI
  is a valid fix.

## Languages

- English and Italian, always both, in the same PR. English strings are the keys (`src/lib/i18n.ts`);
  Italian lives in `src/lib/it.ts`; server messages shown to users are translated too.
- Check the Italian screen for overflow and truncation: Italian runs about 20% longer.
- German and French are not product languages yet (documents are read in them, the UI is EN + IT).

## Design system and components

- Use the tokens; no raw hex colours or ad-hoc spacing in components. Reuse `src/components/ui/*`
  (shadcn) and the house components before adding new ones.
- Third-party UI/UX skills or style guides are input; `docs/design/DESIGN_SYSTEM.md` and this file win.

## Numbers and evidence

- Numbers: right-aligned, `font-variant-numeric: tabular-nums`, Swiss grouping by default (`1'234.50`)
  through the one shared formatter (`src/lib/format.ts`). Show currency code. Show bps next to
  percentages on cost screens.
- Status is never colour alone: every evidence status chip has text and an icon.
- Unknown is shown as "Not determined" with the document that would resolve it, never as 0, "CHF 0" or a dash.
- Every number on a cost screen is clickable to its evidence (page + highlight, or sheet + cell).
- Money arrives from the API as strings. The frontend formats; it never re-computes totals.

## Accessibility

- Every chart has a table equivalent. Keyboard works in the review table (j/k, a accept, e edit, r reject).
- Visible focus, labels on every input and icon button, contrast AA on text.

## Surfaces

- The client report route never fetches internal-margin endpoints. The analyst workspace and the client
  report are separate layouts.
- The CRM is the home page.

## Evidence in the PR

- Before/after screenshots on a SYNTHETIC prospect, EN and IT, for every visible change.
- A screen used in a deck (`slides/source/img/`) changed? Say so in the PR; the deck owner regenerates it
  (`.claude/rules/deck.md`).
