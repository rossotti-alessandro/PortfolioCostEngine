<!-- Protocol: AGENTS.md and docs/WORKFLOW.md. Keep the attribution block (if any) as the first lines. -->

## Summary

<!-- What changed for the analyst or the team, and why, in one or two sentences. -->

**Story:** SC-___ (one story per PR)
**Type:** feat / fix / refactor / test / chore / docs / deps
**Needs Ale's approval (AGENTS.md rule 9):** no / yes, because <!-- finance formula, privacy/auth, new dependency + licence, real data, rule 9 -->
**Shared contracts touched (rule 4):** none / <!-- paths -->

## Change loop

- [ ] Verified the gap or reproduced the bug before writing code
- [ ] A test failed before the change and passes after (or N/A for docs/chore)
- [ ] Self-reviewed the diff (ponytail-review + the rules for these paths)
- [ ] `./scripts/local-gate.sh` prints GATE PASSED with `origin/main` merged in (paste the last lines below)
- [ ] Story file closed in this PR: status, progress, Outcome, Branch & Commits; board regenerated

## Cross-cutting

- [ ] Only touched paths my story owns (or got the owner's OK in the story notes)
- [ ] Money: `Decimal` only, every figure keeps its evidence and status, missing stays unknown (`.claude/rules/finance.md`), or N/A
- [ ] Extraction: accuracy before/after pasted (`docs/EVALUATION_PROTOCOL.md`), or N/A
- [ ] UI: EN and IT screenshots on a SYNTHETIC prospect; details behind (i), one primary action, or N/A
- [ ] No client data, secrets or real names in code, fixtures, logs or screenshots
- [ ] Behaviour or decision change → spec / ADR / HANDOFF updated in this PR; deck figures or screens affected → said here
- [ ] Headline number changed → project memory, docs and published artifacts refreshed (AGENTS.md § Results stay fresh), or N/A

**Issues found this session:** <!-- new story ids, or "none" -->

## Verification

<!-- Commands and output, accuracy tables, screenshots (synthetic data only), how a reviewer reproduces it. -->
