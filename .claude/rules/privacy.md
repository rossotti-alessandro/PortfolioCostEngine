---
description: Client data handling. Applies everywhere, read before touching uploads, logs, fixtures or any external call.
paths:
  - "**"
---

# Privacy rules

Decision record: [docs/adr/0004-privacy-local-first.md](../../docs/adr/0004-privacy-local-first.md).
Background research: `docs/research/DATA_PRIVACY_AND_HOSTING.md`. This is engineering policy, not legal advice.

- Real prospect documents never enter git, issues, PR descriptions, screenshots, Slack or chat. Demo and
  test data are synthetic and say so (file name or a visible "SYNTHETIC" mark).
- Default is local-only: `PCE_ALLOW_EXTERNAL_AI=false`. No client content goes to any external AI, OCR or
  search service unless the organisation recorded a decision and the call sends a redacted page region.
- Public lookups send ISINs only. Never quantities, values, names, account numbers or IBANs.
- Logs and traces: ids, hashes, counts, timings. Never document text or personal data.
- Client-facing outputs never contain internal margin, analyst notes or other prospects' data.
- Every query is scoped by organisation and prospect. A test proves one tenant cannot read another's rows.
