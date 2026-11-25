---
id: SC-6.3
title: Holding type from public registers (FIRDS then OpenFIGI, ISIN only)
status: "Done"
assignee: []
owner: "Prove and raise accuracy on realistic portfolios"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-12ht53"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/70"
created_date: "2026-11-25 22:25"
updated_date: "2026-11-25 22:28"
labels:
  - instruments
  - privacy
dependencies: []
parent_task_id: SC-6
priority: P0
paths_owned:
  - "backend/src/pce/instruments/**"
  - "backend/src/pce/api.py"
  - "backend/tests/test_isin_registry.py"
  - "backend/tests/conftest.py"
spec_ref: docs/research/INSTRUMENT_DATA_SOURCES.md
rule_refs: [".claude/rules/privacy.md", ".claude/rules/extraction.md"]
---

> **One-liner**: Take each holding's type (share, fund, ETF, bond, structured) from ESMA FIRDS or OpenFIGI by ISIN, so a fund named like a company is no longer read as a share whose missing cost counts as none.

## Description

### Context
`analysis.infer_asset_class` guesses the type from the name. A fund named like a company ("Comgest Monde C")
without an uploaded KID is read as a share, and shares get no product-cost gap, so the report looks complete
while the fund's ongoing charge is missing (missing became zero). Swiss bonds without a bond word are read as
shares too. Ale approved on 2026-11-25 sending ISINs only to public registers. SC-6.1 (full catalog, share
class identity) stays open; this story only sets the type.

### User Flow Impact
Funds and bonds are recognised whatever their name; a fund without a KID shows "ongoing charge unknown,
upload the KID" instead of nothing.

### Performance / Efficiency Impact
One FIRDS request per new ISIN and one OpenFIGI request per 10 ISINs FIRDS lacks, at upload; answers cached
on disk (`instrument_types.json` in the data dir), so each ISIN is asked once. 137 ISINs: about 40 s cold.

### Proposed Approach
1. `pce/instruments/registry.py`: `resolve(isins)` → FIRDS CFI code, else OpenFIGI security type; cache;
   any network error returns nothing (name rule applies) and is retried next time.
2. `api.ingest`: positions without a stated class get `extra.asset_class` and `asset_class_source`.
3. `PCE_PUBLIC_ISIN_LOOKUP=0` switches it off; tests run with it off.

### Risks & Follow-ups
External call: ISIN only, two hosts, no client data (tested). An egress guard (SC-11.5) should wrap it later.
Share class identity and KID retrieval stay in SC-6.1 / SC-6.2.

## Acceptance Criteria

- [x] #1 Tests: FIRDS then OpenFIGI mapping, only ISINs sent to the two hosts, cached, offline falls back, switch off sends nothing
- [x] #2 A fund named like a company with no KID gets an unknown ongoing-charge atom (not nothing)
- [x] #3 Live check on the 137 public benchmark ISINs: types match

## Implementation Notes

## Outcome

- **Status**: completed

`pce.instruments.registry.resolve` sets each held ISIN's type from the FIRDS CFI code, else OpenFIGI, at
upload (`api._register_types`). Tests `backend/tests/test_isin_registry.py` (mock transport: mapping, only
ISINs sent to the two hosts, cache, offline fallback, switch off, fund-named-like-a-share gets an unknown
ongoing charge). Live check 2026-11-25 on the 137 public benchmark ISINs: 137/137 types right (108 FIRDS,
29 OpenFIGI).

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-12ht53 | 2e4122b | 2026-11-25 | holding type from FIRDS then OpenFIGI |
