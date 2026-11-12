# Design system

Decision: [ADR 0002](../adr/0002-design-system.md). Implementation: `frontend/src/styles/tokens.css`
(CSS variables, mapped to Tailwind v4 with `@theme`), `frontend/src/components/ui/` (shadcn/ui),
`frontend/src/components/` (house components). UX flow: `docs/research/UX_RECOMMENDATIONS.md`.

Character: a Swiss private bank's annual report, not a fintech app. Calm surfaces, strong type, precise
numbers, colour only where it carries meaning.

## 1. Colour tokens

| Token | Light value | Use |
|---|---|---|
| `--color-bg` | `#F7F6F2` | app background (warm off-white) |
| `--color-surface` | `#FFFFFF` | cards, tables, panels |
| `--color-surface-muted` | `#EFEDE7` | table headers, sidebars, disabled |
| `--color-border` | `#DEDAD1` | hairlines (1px) |
| `--color-text` | `#14202E` | primary text |
| `--color-text-muted` | `#5B6676` | labels, captions |
| `--color-primary` | `#0F2A4A` | navy: primary buttons, active nav, headings accents |
| `--color-primary-fg` | `#FFFFFF` | text on primary |
| `--color-accent` | `#0F766E` | teal: links, focus ring, selected rows, Safe Capital scenario series |
| `--color-accent-soft` | `#E3F2F0` | selected background, highlight fill (25% opacity in viewer) |
| `--color-warning` | `#B45309` | amber: estimated, needs review, partial coverage |
| `--color-warning-soft` | `#FDF3E2` | warning background |
| `--color-danger` | `#B42318` | red: unknown material cost, blocked, destructive |
| `--color-danger-soft` | `#FDECEA` | danger background |
| `--color-success` | `#1E7A46` | observed and reconciled |
| `--color-success-soft` | `#E7F4EC` | success background |

Contrast: every text/background pair above meets WCAG 2.2 AA (≥ 4.5:1 for body text). Verify any new pair.

### Evidence status (fixed mapping, never colour alone)

| Status | Label (en / it) | Icon (lucide) | Colour |
|---|---|---|---|
| observed | Observed / Rilevato | `check-circle-2` | success |
| contractual | Contractual / Contrattuale | `file-signature` | primary |
| estimated | Estimated / Stimato | `gauge` | warning |
| illustrative | Illustrative / Illustrativo | `flask-conical` | text-muted |
| unknown | Not determined / Non determinato | `circle-help` | danger |
| not_applicable | Not applicable / Non applicabile | `minus-circle` | text-muted |

### Chart palette (cost layers, in this order)

Service/advisory `#0F2A4A` · Custody `#2F5D8A` · Trading/FX `#6B8FB3` · Product (TER/OCF) `#0F766E` ·
Product transaction costs `#5FA8A0` · Implicit/spreads `#B7C9D9` · Wrapper/insurance `#8C6D46` ·
Taxes and duties `#A3A3A3` · Unknown: hatched pattern with label, no fake length.

## 2. Typography

- UI: **Inter** (self-hosted), `font-feature-settings: "tnum" 1, "cv11" 1` on numeric cells.
- Code/ids/ISIN: **IBM Plex Mono**.
- Scale (rem): 0.75 caption · 0.875 body-sm/table · 1 body · 1.125 lead · 1.5 h3 · 1.875 h2 · 2.25 h1 · 3 hero figure.
- Weights: 400 body, 500 labels/table headers, 600 headings, 700 hero figures only.

## 3. Space, shape, elevation

- Spacing: 4 px base (`1 = 4px`). Page padding 24/32, card padding 20, table cell 8×12, compact 6×10.
- Radius: square look. 4 px controls (`--radius-control`: buttons, inputs, selects), 6 px cards
  (`--radius-card`), 3 px badges and chips; full circles only for dots and step numbers. Elevation:
  hairline borders, no card shadows; one shadow level for popovers/dialogs only.
- Layout: left nav 240 px (collapsible to 64), content max-width 1440, review screen full-bleed split 55/45.

## 4. Numbers

- One formatter for the whole app: `formatMoney(value: string | null, ccy, locale)`.
  Default `de-CH` grouping: `CHF 1'234'567.50`. `null` → "Not determined" (never 0, never "-").
- Percent with 2 decimals plus bps on cost screens: `1.08% (108 bps)`.
- Right-aligned, tabular numerals, currency code always visible on totals.
- Negative savings shown with a minus sign and danger colour, never hidden.
- A figure is one unit and never wraps (`.money`, `td.num`). In a figure card the currency code is small and
  muted before the figure (`Money` in `components/ui.tsx`).
- Figure cards (`Kpi`): sentence-case label on one line, figure 26 px semibold, one line of context at the
  bottom, equal height in a row. Rows of cards use `StatGrid` (auto-fit, min 220 px) so they reflow to
  fewer columns instead of squeezing the figure.

## 5. House components

| Component | Purpose / rule it enforces |
|---|---|
| `Money`, `Bps` | the formatter above; `null` renders the Unknown chip |
| `StatusChip` | evidence status with icon + label + colour from § 1 |
| `EvidenceLink` | wraps any number; click opens `SourceViewer` at page + bbox or sheet + cell |
| `SourceViewer` | PDF.js page + highlight rectangle (accent-soft fill, accent 2px border), zoom, page nav; sheet grid for XLSX |
| `EvidencePanel` | right side panel opened by any number (`components/Trace.tsx`), non-modal: the page stays usable and another click replaces the content. Formula → inputs → `SourceCrop` → `DecisionTrail` |
| `SourceCrop` | the cited row cropped from the page at readable size, context dimmed, one box with the value tag; "Show full page" opens `SourceViewer` in focus mode (only the cited box until "Show all values") |
| `DecisionTrail` | read (text, OCR or cell, engine, confidence) → automatic checks (fact review: readers, checks, reasons) → person (accept / correct old → new / reject, who, when) → used in. A step with no data says so; never an invented check (`lib/trail.ts`) |
| `CoverageMeter` | "82% of expected cost categories evidenced"; mandatory next to every headline total |
| `GapCard` | an unknown cost + the document that would resolve it + "Add to request letter" |
| `CostWaterfall` | stacked/waterfall by layer with unknown hatched; table twin toggle |
| `ScenarioCompare` | current vs same-holdings vs changed-holdings, with comparability badge |
| `StepBar` | Documents → Check values → Costs → Compare → Report across the top of the prospect header (`components/Shell.tsx`), always visible; done tick per step, count of values still to check; Internal economics as a lock link at the right end |
| `AccountMenu` | bottom of the sidebar: user, language and demo role; opens language switch, role picker and sign-out. The sidebar itself holds only places: Clients, Cost reviews, Library |
| `ReviewTable` | keyboard: j/k move, a accept, e edit, r reject, Enter open source |
| `DemoWatermark` | "SYNTHETIC DEMO" on every page and export when the dataset is synthetic |

## 6. Screens (analyst workspace and client report)

1. **Prospects**: list with AUM, banks, documents, analysis status, last activity. CTA "New analysis".
2. **Intake**: alias, base currency, domicile, consent; drop zone; live classification; required-documents checklist. CTA "Analyse", secondary "Request missing documents".
3. **Review**: split screen, low-confidence first, reconciliation banner at top.
4. **Costs**: headline total + CoverageMeter, layer breakdown, top cost drivers, gaps panel.
5. **Compare**: scenarios side by side, editable proposal tariff, one-off costs, payback, comparability badge.
6. **Internal** (analyst-only route, separate layout): contribution margin, decision gates.
7. **Report**: client-safe one-pager + appendix, PDF export, approved figures only, DemoWatermark when synthetic.

## 7. Calls to action

One primary button per screen (navy, filled, `Button` default), secondary outlined (`outline`, or `accent`
= teal outline for a positive secondary such as "Load synthetic demo"), tertiary text (`ghost`). Verb-first labels
("Analyse documents", "Approve figures", "Export report"). Destructive actions red and confirmed. No
disabled-without-reason buttons: show why in a tooltip.

## 8. Accessibility checklist (per PR touching UI)

Keyboard path works · focus visible (2 px accent ring) · status not colour-only · chart has table twin ·
contrast checked · `aria-live` for job progress · screen titles unique · text resizes to 200% without loss.
