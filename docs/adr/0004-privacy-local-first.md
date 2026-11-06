# ADR 0004 — Privacy: local-first, no client content to external AI by default

Status: Accepted, 2026-11-06. Engineering policy, not legal advice; Safe Capital's compliance officer and
counsel must confirm before any real-data pilot. Research input: `docs/research/DATA_PRIVACY_AND_HOSTING.md`.

## Context

Prospect documents hold names, addresses, account numbers, IBANs, full holdings and transactions:
personal data under the Swiss FADP, and covered by the portfolio manager's professional secrecy. A
prospect is not yet a client. The whole value of the tool depends on the prospect trusting the analysis.

## Decision

1. **Default deployment is local** (research option A): the app and all extraction run on Safe Capital's
   own machine or office server. Swiss-hosted private server (option B) is the multi-user path.
2. **`PCE_ALLOW_EXTERNAL_AI=false` by default.** No document text, image or derived personal data goes to
   an external AI/OCR/search service. Turning it on requires a recorded organisational decision (DPIA,
   processor contract, zero-retention terms) and then only redacted page regions are sent (option C).
   Option D (raw documents to a public AI) is never allowed.
3. **Public lookups send ISINs only** (KID/factsheet retrieval, identifier mapping), to an allowlist of
   hosts, never quantities, values or client identifiers. Local catalog first.
4. **Data handling**: content-addressed storage outside the repo, encrypted at rest when deployed;
   retention limit configurable (default proposal 90 days after the meeting without mandate); deletion
   removes originals and derived facts; audit log of views and changes.
5. **Logs and traces** carry ids, hashes, counts and timings only.
6. **Tenant scope**: every row has `org_id` and `prospect_id`; queries are scoped; a negative test proves isolation.
7. **Client report** never contains internal margin or analyst notes (tested).
8. **Dev and demo use synthetic data only**; real documents never enter git (pre-commit hook blocks
   documents outside fixture folders).

## Consequences

- OCR accuracy on hard scans depends on local engines; if not good enough, option C is a business
  decision with a paper trail, not a config flip by a developer.
- The demo runs fully offline, which is also the strongest sales argument for a Swiss family office.

## Alternatives rejected

- Cloud-first with "we pseudonymise": pseudonymised portfolios are still personal data, and holdings alone
  can identify a person.
