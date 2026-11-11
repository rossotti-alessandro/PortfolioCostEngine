# Data privacy and hosting

Technical research notes, 2026-11-06. **Not legal advice.** Safe Capital's compliance officer and counsel must confirm. Sources: [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md).

## The data

A prospect's bank documents contain name, address, account and IBAN numbers, full holdings, transactions and sometimes tax and family information. Under the Swiss FADP (in force since 1 Sep 2023, `SRC-FDPIC-AI`) this is personal data, and financial details make it high-risk in practice. Safe Capital is the **controller**: it decides why and how the data is processed. Any software or AI vendor is a **processor** and needs a contract. As a FINMA-licensed portfolio manager, Safe Capital also has a statutory confidentiality duty for client information (FinIA professional secrecy, to verify the article), which is stricter than general privacy law. Note that a prospect is not yet a client, so consent and a deletion promise are needed at upload.

## What the law points to (to verify with counsel)

- **Transparency.** Tell the prospect what is processed, why, by whom, and where. FDPIC: AI processing must make purpose, functionality and data sources transparent (`SRC-FDPIC-AI`).
- **DPIA.** Required "in high-risk cases" (`SRC-FDPIC-AI`). Systematic analysis of full portfolios with AI is a likely candidate. Doing one is cheap insurance.
- **Cross-border disclosure.** Sending data to a country without adequate protection needs safeguards. The Federal Council keeps the adequacy list (Annex 1 O-FADP, `SRC-FDPIC-ADEQ`). US status depends on the Swiss-US Data Privacy Framework certification of the specific vendor (to verify).
- **Processors.** Controller stays responsible for its processors (`SRC-FDPIC-CLOUD`).
- **Breach notification** to the FDPIC when high risk (to verify article).

## Options for where it runs

| Option | How | Privacy | Effort | Fit |
|---|---|---|---|---|
| A. **Local on Safe Capital's machine** | App runs on a laptop or office server; extraction with local libraries; no cloud AI | Best: nothing leaves the office | Low for a demo; needs an IT owner later | **Recommended for the pilot** |
| B. **Swiss-hosted private server** | Same app on a Swiss cloud VM (e.g. a Swiss provider or a hyperscaler's Swiss region), encrypted storage, Safe Capital controls keys | Good, with a processor contract | Medium | Production with several users |
| C. **Hybrid with cloud AI** | Local extraction first; only hard pages, redacted, go to a cloud model under a zero-retention contract | Acceptable only after DPIA and contract | Medium | Later, if local accuracy is not enough |
| D. Plain cloud AI on raw PDFs | Upload full statements to a public AI service | Not acceptable | Low | Never for real client data |

Facts behind option C: OpenAI's EEA+Switzerland data region and zero-data-retention controls are not self-service; they "are subject to prior approval", and abuse-monitoring logs are kept "up to 30 days" by default (`SRC-OPENAI-DATA`). We could not fetch Anthropic's terms in this pass; check them before choosing a vendor.

## Redaction before anything leaves the machine

Pseudonymised data is still personal data. But redaction cuts risk a lot. Before any external call: replace client name, address, account numbers, IBANs and the bank relationship number with tokens; never send the whole portfolio, only the page region that failed local extraction. ISIN lookups to external services (OpenFIGI, data vendors) leak portfolio composition: look up in the local catalog first, and never send quantities or values.

## Minimum controls for a real-data pilot

Written prospect consent at upload · retention limit (e.g. delete 90 days after the meeting if no mandate) · encryption at rest and in transit · access only for named staff · no client data in logs · audit trail of who saw and changed what · documented DPIA · compliance officer sign-off on the client report template.
