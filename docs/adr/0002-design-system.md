# ADR 0002 — Design system

Status: Accepted, 2026-11-06.

## Context

Two audiences (`docs/research/UX_RECOMMENDATIONS.md`): analysts who need density, keyboard speed and a
source for every number; and prospects who need a few honest numbers in plain language. The look must
read as a Swiss private bank: calm, precise, trustworthy. Several agents will build screens in parallel,
so components and tokens must be decided once.

## Decision

- **Tokens first**: colours, type, spacing, radii and elevation are CSS variables defined once in
  `frontend/src/styles/tokens.css` and exposed to Tailwind v4 via `@theme`. Spec: `docs/design/DESIGN_SYSTEM.md`.
- **Components**: shadcn/ui (copied into `frontend/src/components/ui/`, owned by us, built on Radix for
  accessibility) plus a small set of house components that encode the product rules: `Money`, `Bps`,
  `StatusChip`, `EvidenceLink`, `CoverageMeter`, `GapCard`, `Stepper`, `CostWaterfall`, `SourceViewer`.
- **Typography**: Inter (UI, tabular numerals on), IBM Plex Mono for ids and ISINs. Self-hosted, no font CDN.
- **Palette**: navy primary, teal accent, warm off-white surfaces; amber and red only for real alerts.
  Evidence statuses have fixed colour + icon + label.
- **Light theme first** (print-friendly client report); dark theme tokens defined but not a pilot goal.
- **Accessibility**: WCAG 2.2 AA contrast, focus rings visible, status never colour-only, every chart
  has a table twin, full keyboard support in review screens.
- **i18n**: all copy through translation keys (`it`, `de`, `en`, `fr`), Italian first for Lugano.

## Consequences

- Any screen built from these pieces looks consistent without design review per screen.
- House components are where product rules live (e.g. `Money` renders `None` as "Not determined"), so
  rules are enforced once.

## Alternatives rejected

- MUI / Ant Design: heavier, recognisable "admin template" look, harder to make feel bespoke.
- A custom component library from scratch: slow; Radix gives tested accessibility.
