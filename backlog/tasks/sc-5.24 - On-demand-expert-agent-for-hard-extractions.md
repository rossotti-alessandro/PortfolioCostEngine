---
id: SC-5.24
title: On-demand expert agent for hard extractions
status: "In Progress"
assignee: []
owner: "Build expert agent for hard extractions"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-1i20qh"
pr: ""
created_date: "2026-11-26 23:40"
updated_date: "2026-11-26 23:24"
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

- [ ] #1 Proposal accuracy and recovered misses reported on the realistic benchmark and the ocrbench pages
- [ ] #2 Tests prove: no proposal changes a value or enters totals, unpinned numbers are dropped, a hosted URL is refused without the privacy flag and masking

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
