---
id: SC-4.1
title: Secure upload: hash, MIME sniff, limits, quarantine, dedupe
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
  - intake
  - security
dependencies:
  - SC-3.2
parent_task_id: SC-4
priority: P0
paths_owned:
  - "backend/src/pce/intake/**"
  - "backend/tests/unit/intake/**"
spec_ref: docs/adr/0004-privacy-local-first.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Accept prospect files safely and exactly once, before anything parses them.

## Description

### Context

No intake.

### User Flow Impact

Analyst drops files; duplicates and unsafe files are explained, not silently dropped.

### Performance / Efficiency Impact

Hashing streams the file; no full read into memory for large PDFs.

### Proposed Approach

1. SHA-256 while streaming to content-addressed store
2. python-magic sniff vs extension
3. Size/page caps, encrypted-PDF and zip-bomb rejection
4. Same hash in same prospect = duplicate, linked not re-parsed

### Risks & Follow-ups

See `docs/adr/0004-privacy-local-first.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Uploading the same file twice yields one document and a duplicate notice
- [ ] #2 A renamed .exe as .pdf is rejected with a reason
- [ ] #3 Encrypted PDF without password goes to 'needs password', not to the parser

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
