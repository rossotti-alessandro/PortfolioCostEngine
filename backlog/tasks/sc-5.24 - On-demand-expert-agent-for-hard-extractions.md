---
id: SC-5.24
title: On-demand expert agent for hard extractions
status: "Done"
assignee: []
owner: "Build expert agent for hard extractions"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-1i20qh"
pr: ""
created_date: "2026-11-26 23:40"
updated_date: "2026-11-27 01:21"
labels:
  - extraction
  - privacy
dependencies: []
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/expert.py"
  - "backend/src/pce/evaluation/expert_bench.py"
  - "backend/tests/test_expert.py"
  - "backend/src/pce/api.py"
  - "docs/research/EXPERT_AGENT.md"
  - "frontend/src/**"
  - "backend/tests/test_api.py"
  - ".env.example"
spec_ref: docs/research/REVALIDATION_PROTOCOL.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
  - ".claude/rules/finance.md"
---

> **One-liner**: An expert agent, called only for the figures the pipeline is unsure about or may have missed, reasons over the page with deterministic tools and proposes cited values that a person confirms.

## Description

### Context

The app runs a fixed finder + verify pipeline (SC-5.8). Figures it doubts go to review; fee-looking lines
with no value are listed as possible misses. The agentic revalidation graph (SC-5.14) only confirms or
flags and never looks for a better reading. Ale (2026-11-26) asked for a proper agentic workflow: an expert
agent used when needed.

### User Flow Impact

On a document with review points the analyst can ask the expert. Each doubtful figure and each possible
miss gets a proposal (confirm, corrected value, new fee, not a fee, or "cannot tell") with the quoted line
and its box on the page. Nothing enters the totals until the analyst confirms it.

### Performance / Efficiency Impact

Runs only on escalated items, on demand. Local 4B model on CPU: to measure per item.

### Proposed Approach

1. `pce/extraction/expert.py`: escalation (needs_review facts, possible misses), a small tool loop over an
   OpenAI-compatible chat endpoint (local llama.cpp / Ollama by default), tools for page lines and Decimal
   arithmetic, proposals as Pydantic models.
2. Deterministic guards after the model: the proposed number must be printed on the cited page (pinned to a
   word box) or it is dropped; no proposal changes a value; abstain keeps the doubt; zero needs a printed 0.
3. Hosted endpoint only with `PCE_ALLOW_EXTERNAL_AI=true`, and only through the PII masking of thread
   "Mask client names and addresses"; refuses otherwise.
4. API `POST /api/documents/{did}/expert`, audit entry, proposals stored on the fact, shown in review.
5. Benchmark on the realistic statements and the ocrbench pages.

### Risks & Follow-ups

Local model quality on CPU; prompt injection from document text (text is data, guards are deterministic).

## Acceptance Criteria

- [x] #1 Proposal accuracy and recovered misses reported on the realistic benchmark and the ocrbench pages
- [x] #2 Tests prove: no proposal changes a value or enters totals, unpinned numbers are dropped, a hosted URL is refused without the privacy flag and masking

## Implementation Notes

- `extraction/expert.py`: escalation (needs_review fees first, then possible misses, then holdings), one
  JSON "action" protocol for tools (`lines`, `reread`, `sum`) and answers, max 4 steps.
- Guards: the figure must be printed on the item's own row (or its reread); the app parses value and box;
  zero needs a printed zero; holdings cannot be "not a fee"; nothing changes a value or a total.
- Hosted: refused unless `PCE_ALLOW_EXTERNAL_AI=true` and `pce.pii.names_available()` (SC-11.9, PR #90);
  `pce.pii.LeakError` refuses the call. Off unless `PCE_EXPERT_URL` is set (`/api/health` says so).
- API `POST /api/documents/{did}/expert` (background task, status in `document.profile.expert`, audit
  counts only). Review rail: button, progress, suggestion with quoted line, "Use this value" prefills
  the correction dialog.
- Benchmark `pce.evaluation.expert_bench` (realistic, ocrbench). First run exposed the model writing
  `{"tool": "confirm"}`; fixed by the single action key.

## Outcome

- **Status**: completed
- Local Qwen3-4B on CPU, ~20 s per item. Realistic hardest conditions, 95 items: 86% of answers right
  (69 right confirmations, 6 wrong confirmations, 3 wrong corrections, 2 fees called not a cost), 15
  no answer, 0 of 9 missed fees recovered. Corpus fee pages: only 15 items escalated, 5 right, 2 wrong,
  8 no answer, 0 misses recovered (pipeline misses are silent). Details: docs/research/EXPERT_AGENT.md.
- Not good enough to accept anything automatically; kept as suggestions. Next: stronger model (hosted
  after the privacy decision, or local 8B+ on GPU), whole-page sweep for silent misses, quantity x price
  check for holdings.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-1i20qh | 35382fb | 2026-11-26 | feat(extraction): on-demand expert agent with cited proposals |
| claude/project-thread-1i20qh | 0c51532 | 2026-11-26 | feat(review): ask the expert from review, proposals by values |
| claude/project-thread-1i20qh | 8a8e864 | 2026-11-27 | fix(extraction): one action key for tools and answers |
