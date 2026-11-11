# Safe Capital: who the tool is for

Checked 2026-11-06. Sources: `SRC-SC-WEB`, `SRC-MH-SCM`, `SRC-MH-SCH`, `SRC-FINMA-VVTR` in [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md).

## Facts

| Item | Value | Source |
|---|---|---|
| Legal entity | Safe Capital Management SA (società anonima) | Register via Moneyhouse |
| UID | CHE-381.156.096 | Moneyhouse |
| Registered | 6 April 2012, Ticino commercial register, seat Lugano | Moneyhouse |
| Share capital | CHF 250'000 | Moneyhouse |
| Address | Via Serafino Balestra 5, 6900 Lugano | Website, register |
| Group | Safe Capital Holding SA (CHE-291.799.912, registered 2013; formerly Galafin Suisse SA, Safe Asset Management SA) | Moneyhouse |
| Business | Independent asset manager (gestione patrimoniale indipendente). Private clients and families (mainly HNWI), corporates, institutional investors; manages assets for life-insurance companies | Website |
| Size claim | "AUM 1 Bn" at 31 Dec 2025 (currency not stated) | Website |
| Network | "More than 50 institutional partners (custodian banks, insurers and asset managers)"; access to many custodian banks in Switzerland and abroad | Website |
| Regulatory claim | "Safe Capital Management SA is authorized by FINMA and Supervised by OSIF". History page: FINMA licence under FinIA and OSIF affiliation in 2022; earlier member of the Ticino trustees' self-regulatory body (OAD FCT) from 2012 | Website |
| Regulatory check | **Not independently confirmed.** The FINMA list (updated 27.10.2026) was only partly readable (A–N). Search the FINMA XLSX for "Safe Capital" before quoting this in a presentation | FINMA |
| Internal tooling | Website mentions an integrated PMS that handles execution with custodians, "monitoraggio dei costi", reconciliations, AML monitoring | Website |

## What this means for the product

1. **Safe Capital is an external asset manager (EAM), not a bank.** The client's assets stay at a custodian bank. So the proposed scenario is always *Safe Capital fee + custodian's fees + product costs*. The engine needs a "proposed custodian" input; Safe Capital's fee alone is not a fair comparison.
2. **Prospects are often Italian or Italian-speaking.** Lugano EAMs serve many Italian residents. Expect Italian bank documents (MiFID II *rendiconto costi e oneri*), Italian insurance wrappers (*polizze unit-linked*, *polizze vita* — the ChatGPT ISIN list is 60% funds from one Italian unit-linked policy), and Swiss bank documents in Italian or German. VAT also differs: Swiss VAT on fees generally applies to Swiss-domiciled clients only (to verify).
3. **Insurance work is a real line of business.** Safe Capital manages money for life insurers. The wrapper layer (L7 in the fee taxonomy) is not an edge case; it should be in the first demo.
4. **The output is comparative advertising.** A report saying "you pay X at your bank, you would pay Y with us" is a comparison with competitors. Swiss unfair competition law forbids comparisons that are incorrect or misleading (UWG Art. 3 para. 1 lit. e, to verify with counsel), and FinSA conduct rules require fair information. That is why the engine separates proven, estimated and unknown costs, and why the same-holdings comparison is the default.
5. **Safe Capital's own retrocession policy must be stated.** If Safe Capital receives or refunds retrocessions, the proposal must say so, or the comparison is not like-for-like.
6. **Brand naming.** The ChatGPT kit uses "3MC" and "Safe Capital" interchangeably. "3MC" does not appear on the Safe Capital site. Confirm with Massimo which name goes on the client report, and whether the second family office he works with should be a separate tenant (Ale asked for a generic tool).

## Questions for Massimo

1. Two or three anonymised real prospect files (statements, fee advices, contracts), even blacked out, to test the taxonomy.
2. Safe Capital's standard fee grid and the custodian tariffs it usually negotiates.
3. Who runs the analysis: relationship manager in the meeting, or back office before the meeting?
4. Where data may be processed (office machine only, Swiss cloud, any cloud with contract).
5. How long prospect documents may be kept if the prospect does not sign.
6. Brand and legal entity on the report; who signs off on its content (compliance officer).
