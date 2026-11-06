---
id: SC-9.2
title: Threat model and security negative tests
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
labels:
  - security
  - qa
dependencies:
  - SC-4.1
  - SC-3.2
parent_task_id: SC-9
priority: P0
paths_owned:
  - "docs/THREAT_MODEL.md"
  - "backend/tests/security/**"
spec_ref: docs/adr/0004-privacy-local-first.md
rule_refs:
  - ".claude/rules/privacy.md"
---

> **One-liner**: Prove the obvious attacks and leaks fail: cross-tenant reads, malicious files, prompt injection, PII in logs.

## Description

### Context

No threat model.

### User Flow Impact

No direct change.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. STRIDE-style model
2. Tenant isolation tests
3. Malicious PDF/zip fixtures
4. Log scrubber test
5. Egress allowlist test

### Risks & Follow-ups

See `docs/adr/0004-privacy-local-first.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Cross-tenant read returns 404/403 in tests
- [ ] #2 Logs from a full synthetic run contain no names/IBANs (scan)

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
