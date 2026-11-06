---
description: Cost engine invariants. Money, evidence states, inclusion graph, scenarios.
paths:
  - "backend/src/pce/finance/**"
  - "backend/src/pce/scenarios/**"
  - "backend/src/pce/validation/**"
  - "backend/tests/**/test_*finance*"
---

# Finance rules (regret if forgotten)

These hold for every line of the cost engine. A PR that breaks one is not mergeable, whatever else it fixes.

## Arithmetic

- Money and rates are `decimal.Decimal`, built from strings (`Decimal("0.0025")`), never from floats.
  No `float()` on an amount anywhere in `finance/`, `scenarios/`, `validation/`.
- Rounding happens once, at presentation, with an explicit `quantize` and rounding mode. Keep full
  precision in the ledger.
- An LLM never does arithmetic and never writes into the ledger. Models propose candidate facts; code
  validates and computes.
- Rates carry their basis: `rate_bps` plus the denominator (`end_value`, `average_aum`, `assets_in_scope`,
  `transaction_value`). If the source does not define the denominator, the atom goes to human review.

## Evidence and status

- Every fee atom has a `status` in `observed | contractual | estimated | illustrative | unknown | not_applicable`
  and at least one evidence reference (document + page + bbox, or sheet + cell, or URL + anchor),
  except `unknown`, which carries the reason and the document that would resolve it.
- **Missing is not zero.** `unknown` amounts are `None`, never `Decimal(0)`. Totals that include an unknown
  are reported as "at least X" plus the list of unknowns, never as a plain total.
- `not_applicable` (we know the fee does not exist) and `unknown` (we could not find it) are different.
- A KID "costs over time" example is `illustrative`. It is never an `observed` paid fee.

## No double counting

- Fees form an inclusion graph. A child (`included_in_parent_atom_id`) is shown, never summed.
  Canonical test: a KID with OCF 1.08% that states the AMF 0.75% is included gives 1.08% economic cost,
  not 1.83%.
- An all-in or wrap fee that includes custody or brokerage replaces those lines, not adds to them.
- The same charge seen in the annual cost report and in a cash posting is one atom with two evidences.
- Embedded product costs (in the NAV) are economic cost. They are never subtracted again from billed bank fees.

## Jurisdiction and dates

- A tariff applies only to its booking entity and validity dates. A Luxembourg tariff on a Swiss-booked
  account is rejected, not approximated.
- Product costs match the exact ISIN and share class, dated. No match on fund name alone.

## Scenarios

- `same_holdings` (same ISINs, new service/custody fees) and `changed_holdings` (instrument switch) are
  separate results. A saving from changed holdings is never labelled a pure fee saving.
- First-year view = annual saving minus one-off switching costs (exit fees, transfer, taxes) with payback.
- Internal margin is computed in its own module and is never serialised into a client-facing report.
  A test asserts the client report payload has no internal-margin fields.

## Tests every finance PR keeps green

bps and percent conversion, marginal vs whole-base tiers, minimum and cap, proration by days, FX at a
dated rate, AMF-inside-OCF, KID illustrative vs actual, duplicate report-vs-cash, missing stays unknown,
negative saving shown as negative, jurisdiction mismatch rejected, client report has no margin.
