# Production readiness: go-live gates and pilot protocols

Status on 2026-11-12, story SC-11.10. Engineering assessment, not legal advice: Safe Capital's compliance
officer and counsel confirm the legal points. The going-live plan with hosting, sign-in and law research is
the project document "FeeLens: going live with client data" (2026-11-12); this page is the checklist and the
operating rules that follow from it. Update it in the same PR as any change to a gate.

## 1. Verdict

**Not yet for real client data. Ready for a supervised pilot once gates G1 to G9 below are closed.**

- The pipeline is good enough to *assist* an analyst, not to produce a figure nobody checks. On 63 real public
  pages (899 hand-checked fees) the best workflow finds 90% of fees, and about 5 to 6% of the figures it does
  not flag are wrong (section 3). A cost report uses dozens of figures, so an unchecked report would almost
  certainly contain an error. Hence the analyst review protocol (section 5) is mandatory, not optional.
- Until 2026-11-12 `main` found about 4% of fees on real documents. The finder + verify work that raises this
  to about 90% (#15, #17, #21, #27) was merged on 2026-11-12 on Ale's instruction.
- The two things that drive every client percentage, holdings and AUM, are measured only on synthetic
  prospects. Real statement layouts are untested (SC-9.6). This is the largest open accuracy risk.
- Privacy controls that the plan requires before the first real upload (named users with MFA, deletion on
  request, retention, encrypted storage and backup, DPIA, consent) are not built or not signed.

## 2. Go-live gates

All must be closed before the first real prospect document is uploaded. Owner "Ale" or "Safe Capital" means a
decision or signature, not code.

| # | Gate | Owner | Status 2026-11-12 | Closes with |
|---|---|---|---|---|
| G1 | Extraction stack merged: #17, then #15, #16, #21, #27 (#26 independent) | Ale (rule 9) | **Closed 2026-11-12**: all merged on Ale's instruction, after the combined tree passed the full gate (section 3.3) | Done |
| G2 | Accuracy on real statements measured (holdings, AUM, statement fees) | Engineering | Partial 2026-11-12: 4 public statements checked, no silent AUM error left; Fidelity US 34 of 34 holdings with exact AUM after SC-5.16; AJ Bell overview cash and policies read after SC-5.17, so its AUM matches its account totals exactly; two-client files raise an alarm (`data/specimens/statements/RESULTS.md`); Swiss statements only in the pilot | SC-9.6, SC-5.16 |
| G3 | Where the pilot runs: Safe Capital machine (recommended) or Swiss host | Ale + Massimo | Open decision | SC-11.6 (local) or SC-11.2 (hosted) |
| G4 | Named users with MFA and roles; no shared admin password | Engineering, Ale approves (rule 9) | Open. Only one env-seeded admin exists | SC-11.7 |
| G5 | Delete a prospect and everything derived on request | Engineering | Open. No delete endpoint on main | SC-11.11 |
| G6 | Encrypted storage, backup with tested restore, retention deletion | Engineering | Open | SC-11.6 |
| G7 | Audit log of views, downloads, exports, deletions | Engineering | Partial. Writes are audited on main; views and downloads are not | SC-11.8 |
| G8 | No path for client content to leave the machine | Engineering, Ale approves (rule 9) | Holds by construction today (no outbound call except the demo's public corpus fetch); `PCE_ALLOW_EXTERNAL_AI` is declared but nothing reads it | SC-11.5 before any outbound feature |
| G9 | DPIA written and signed, consent text agreed, processing record, compliance sign-off | Safe Capital (DPIA owner to name) | Open | SC-11.1 AC #1 |

Not gates for the pilot (needed before several users or hosting): Postgres and multi-user hosting (SC-11.2),
redaction at exits (SC-11.4) and the PII model (SC-11.9) only if anything is ever exported outside Safe
Capital or sent to an outside service, the multi-document job queue (SC-5.15), scans embedded in digital
pages (SC-5.12).

The public demo (`feelens-demo.onrender.com`, Render free plan, Frankfurt) is **never** used for client
documents, before or after these gates. On 2026-11-12 it still deploys branch `claude/project-thread-steqtm`
(no sign-in) and accepts uploads from anyone. Until Ale sets `PCE_ADMIN_PASSWORD` and `PCE_SECRET_KEY` and
switches the service to `main`, nobody should be pointed at it except for the seeded synthetic demo.

## 3. Accuracy evidence and why the numbers differ

### 3.1 The numbers

| Measure | Value | Set | Source |
|---|---|---|---|
| Fees found, main today | 4% | 63 pages, 899 fees | `data/specimens/arena/RESULTS.md`, "App before SC-5.8" |
| Fees found, finder + verify | 90% (86 to 93%) | same | same, "Finder + verify" |
| Wrong among figures not sent to review, finder + verify | 5.9% (3.4 to 9.3%) | same | same |
| Same, inside the app after PR #15 (parsers + finder) | 7.2% wrong, 23% to review | same | same, "App after SC-5.8" |
| Same, full revalidation graph with local critic (PR #27) | 4.6% wrong, 29 to 34% to review, ~41 s/page | same | PR #27 |
| Two independent readers must agree | 0 wrong, 62% to review, ~59 s/page | 23 pages, 401 fees | arena |
| Label + value pairing in tables, best engine | 68% | lab pages | OCR lab |
| Synthetic prospects, digital | 100%, totals exact | P-1042, P-2077 | `pce.evaluation` |
| Synthetic prospects, scanned copy | a holdings page lost: AUM CHF 3.7m instead of 4.3m, alarm raised | P-1042 | `pce.evaluation --variant scan` |

### 3.2 Why reports quote different "wrong" rates

They are different sets, not contradictions. PR #15's 8.0% was measured on the first 44 lab pages with the
first gold file; the arena's 5.9% is on the grown set of 63 pages with the corrected gold; 4.9% is the same
workflow on the held-out pages only; 7.2% is the app path (parsers plus finder), which also keeps parser
values. An audit of the 44-page errors found about half were omissions in the gold file, not reading errors,
so the real rate is probably lower than quoted. All intervals overlap. Quote "about 5 to 6% of accepted
figures, real documents, small sample" and the source row.

### 3.3 The open PRs together (run 2026-11-12, this audit)

No one had tested the open PRs as one tree. Merged in order #17, #15, #16, #21, #27, #26, #29 on top of
`main` 87f02a4: no conflicts; full gate (OCR tests included) 204 passed, 3 skipped; the one failure was a
missing `qpdf` system package in the container, passing once installed. Accuracy protocol on the synthetic
prospects, digital and scan, with and without `PCE_REVALIDATE=1`, identical to `main`: P-1042 and P-2077
digital 100% with exact totals and no wrong value; scanned copies 85.5% and 96.2% with no wrong value (the
P-1042 holdings page is still lost on the scan, and the alarm still fires). So the stack introduces no
regression, but the synthetic prospects no longer tell strategies apart: only real pages do.

### 3.4 More tests: which ones and why

Running the same 63 pages again will not change the decision. The useful next tests are:

1. **Real statement layouts** (SC-9.6): started 2026-11-12 on the 4 usable public statements
   (`data/specimens/statements/RESULTS.md`). It found wrong currency on US rows, unread bonds and shorts, section
   subtotals summed as the total, and a 20% AUM shortfall with no alarm: all fixed or alarmed (SC-5.16). Public Swiss and Italian statements barely exist, so the pilot
   is the real test.
2. **The supervised pilot itself** (section 4): every figure checked by an analyst gives a real error rate on
   real documents at no extra labelling cost.
3. Bigger held-out set for the agentic critic before it is switched on by default (23 held-out pages today).

## 4. Pilot protocol (SC-11.1)

Purpose: measure accuracy and time on real documents while no unchecked figure reaches a client.

1. **Before**: gates G1 to G9 closed; the analysts named; the prospect's written consent on file (G9 text).
2. **Scope**: the first 10 prospects, or 3 months, whichever comes first. Only documents the prospect handed
   over for this purpose. No upload from personal devices or e-mail forwarding chains.
3. **Run**: upload, let FeeLens extract, then the analyst follows section 5 for every figure. The analyst
   records each correction in the app (the review action keeps before, after and who).
4. **Measure per prospect** (pilot report `docs/PILOT_REPORT.md`, numbers only, no client names): figures
   extracted, figures corrected, figures missed and added by hand, AUM difference before and after review,
   all-in cost difference before and after review, analyst minutes.
5. **Acceptance to widen use** (proposal for Ale): on 10 consecutive prospects, after review, zero wrong
   figures in any client report; before review, the all-in annual cost within 5% of the reviewed figure on at
   least 8 of 10 and AUM within 1% on all 10; analyst time per prospect under 2 hours. Miss any one: keep the
   pilot supervised and file stories for the causes.
6. **Stop the pilot** at once on any data incident (section 6) or any wrong figure found in a report already
   given to a prospect.

## 5. Analyst review protocol (every report, pilot and after)

FeeLens assists; the analyst signs.

1. Holdings first: the statement's printed total and FeeLens's AUM must agree; a reconciliation alarm is
   resolved before anything else.
2. Every figure that feeds the all-in cost is opened from the cost page and checked against its source crop:
   confirm, correct, or mark unknown. Unknown stays unknown; never type 0 for a missing fee.
3. Every review point and missing-document request is answered or left visibly open in the report.
4. Product costs: OCF and AMF come from the KID of the exact ISIN and share class. AMF inside OCF counts once.
5. A second person (four eyes) checks the total, the saving and the comparison basis before approval. The
   approval records who approved the snapshot.
6. Only the approved snapshot is given to the prospect. Internal margin and analyst notes never appear in it
   (enforced by tests; check the PDF anyway during the pilot).

## 6. Data handling and incident procedure

Applies to every real document from the first upload. Engineering notes; Safe Capital's own policies win.

- **Intake**: documents arrive only from the prospect, for this analysis, with consent on file. Store only in
  FeeLens, not in mailboxes, shared drives or chat. Never in git, issues, screenshots, or prompts to any AI
  service (`.claude/rules/privacy.md`). Support questions use synthetic copies.
- **Access**: named users only (G4). Leavers are removed the same day.
- **Retention**: delete 90 days after the meeting when no mandate follows (proposal in ADR 0004; Safe Capital
  sets the number). On request, delete at once (G5) and confirm to the prospect.
- **Incident** (lost device, wrong recipient, unauthorised access, data on the public demo, a leak found in a
  log): (1) stop use and preserve the audit log; (2) tell Ale and Safe Capital's compliance officer the same
  day; (3) scope who and what from the audit log; (4) Safe Capital decides on notification: the FADP requires
  notifying the FDPIC as soon as possible when the breach is likely to cause a high risk to the persons
  concerned (art. 24 FADP, to confirm with counsel), and FINMA or the supervisory organisation may also need
  to be informed; (5) write a short incident note (facts, cause, fix) without personal data.

## 7. Decisions needed

| # | Decision | Who | Unblocks |
|---|---|---|---|
| D1 | Whether page arithmetic (`PCE_REVALIDATE`) is on by default (the PRs themselves were merged 2026-11-12) | Ale | accuracy |
| D2 | Who labels statement pages, and whether an external AI may draft labels on public documents; keep the two Raiffeisen Locarno files | Ale | G2, corpus |
| D3 | Pilot on a Safe Capital machine or on a Swiss host; does Safe Capital use Microsoft 365 (sign-in choice) | Ale + Massimo | G3, G4 |
| D4 | Who at Safe Capital owns and signs the DPIA, consent text and retention period | Massimo | G9, G6 |
| D5 | Pilot acceptance thresholds in section 4.5 | Ale | SC-11.1 |
| D6 | Lock the public demo: set the two Render secrets and switch it to `main` | Ale | demo safety |
| D7 | Safe Capital's FINMA licence and supervisory organisation: manual check in the FINMA register before the deck uses the claim | Ale | deck, D4 |
