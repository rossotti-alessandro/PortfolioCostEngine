# Source register

Checked 2026-11-06. **Status** values: `read` = text fetched and read in this pass; `partial` = fetched but only part readable; `listed` = URL found, content not read; `failed` = could not fetch (reason given); `kit-only` = cited by the ChatGPT kit, not re-checked here. Nothing marked `listed`, `failed` or `kit-only` should be quoted to a client.

## Client and regulator

| id | Issuer | What | URL | Status | Key facts used | Caveat |
|---|---|---|---|---|---|---|
| SRC-SC-WEB | Safe Capital Management SA | Website: home, history, team, wealth management, contact | https://safecapital.ch/it/ | read | "Società di gestione patrimoniale indipendente"; footer "authorized by FINMA and Supervised by OSIF"; AUM 1 Bn at 31.12.2025; 50+ partner custodians/insurers; manager for life insurers; "PMS Integrato" with cost monitoring | Self-declared marketing |
| SRC-MH-SCM | Moneyhouse (SOGC data) | Safe Capital Management SA register entry | https://www.moneyhouse.ch/en/company/safe-capital-management-sa-19662715911 | read | UID CHE-381.156.096; registered 06.04.2012; capital CHF 250'000; Lugano; purpose includes asset management, investment advice, portfolio analysis | Secondary aggregator of official SOGC data |
| SRC-MH-SCH | Moneyhouse (SOGC data) | Safe Capital Holding SA | https://www.moneyhouse.ch/en/company/safe-capital-holding-sa-13971358531 | read | UID CHE-291.799.912; registered 08.10.2013; former names Galafin Suisse SA, Safe Asset Management SA | |
| SRC-FINMA-VVTR | FINMA | List of portfolio managers and trustees licensed by FINMA (PDF, updated 27.10.2026, 69 pages; XLSX also published) | https://www.finma.ch/en/~/media/finma/dokumente/bewilligungstraeger/pdf/vvtr.pdf | partial | Pages A–N read; "S" pages not reachable by our tools | **Safe Capital's licence not independently confirmed.** Open the XLSX and search "Safe Capital" (5 minutes, manual) |
| SRC-FINMA-PUBLIC | FINMA | Authorised institutions search | https://www.finma.ch/en/finma-public/authorised-institutions-individuals-and-products/ | partial | Dynamic search; not run | Manual check |
| SRC-BDO-FINMA-RS | BDO Switzerland | Commentary on FINMA circular "Verhaltenspflichten nach FIDLEG/FIDLEV" (draft 15 May 2024) | https://www.bdo.ch/de-ch/publikationen/finma-rundschreiben-%C2%ABverhaltenspflichten-nach-fidleg-fidlev-e2e9211f3ef54b798cd507501dc0b880 | read | Info duties Art. 8 FinSA / Art. 7 FinSO; retrocessions Art. 26 FinSA / Art. 29 FinSO; pro-forma waiver insufficient; parameters and bandwidths in contract; detailed statement free on request | Commentary on a consultation draft, not the final circular |
| SRC-FINSA | Swiss Confederation | FinSA SR 950.1 / FinSO SR 950.11 | https://www.fedlex.admin.ch/eli/cc/2019/758/en | failed | Fedlex returns a JavaScript shell to our tools | Article quotes must be checked in a browser |
| SRC-FADP | Swiss Confederation | FADP SR 235.1 / O-FADP | https://www.fedlex.admin.ch/eli/cc/2022/491/en | failed | Same | Same |
| SRC-STG | Swiss Confederation | Stamp Duty Act SR 641.10 | https://www.fedlex.admin.ch/eli/cc/1974/11_11_11/de | failed | Same; rates in taxonomy are from domain knowledge | To verify |
| SRC-MWSTG | Swiss Confederation | VAT Act SR 641.20 | https://www.fedlex.admin.ch/eli/cc/2009/615/de | failed | Same | To verify |
| SRC-FDPIC-AI | FDPIC | AI and data protection (24 Sep 2025) | https://www.edoeb.admin.ch/en/ai-and-data-protection | read | FADP "directly applicable to AI-supported data processing"; transparency on purpose and data sources; DPIA "in high-risk cases" | |
| SRC-FDPIC-ADEQ | FDPIC | Adequacy | https://www.edoeb.admin.ch/en/adequacy | read | Federal Council decides adequacy (Art. 16 para. 1 FADP); list in Annex 1 O-FADP | US status not on this page |
| SRC-FDPIC-CLOUD | FDPIC | Cloud processing; outsourcing | https://www.edoeb.admin.ch/en/data-processing-in-the-cloud | kit-only | Controller stays responsible for processor | |

## Banks and custodians

| id | Issuer | What | URL | Status | Key facts used | Caveat |
|---|---|---|---|---|---|---|
| SRC-JB-LUX | Bank Julius Baer Europe S.A. | Schedule of prices, banking and custody, June 2025 (PU00505EN) | https://www.juliusbaer.com/fileadmin/legal/schedule-of-prices-and-services-banking-and-custody.pdf | read | Custody 0.300/0.250/0.200/0.150% cumulative bands by EUR 5/10/20m, month-end average, min EUR 360/quarter; equity brokerage 1.5% (EU/CH/US, ≤50k) down to 0.4% (>1m), min EUR 200; FX spot up to 3.0%; structured products up to 5.0%; transfer out EUR 100/position; all fees ex VAT | **"For clients booked in Luxembourg only."** Use as a schema example, never as Swiss pricing |
| SRC-SQ-FEES | Swissquote | Account fees | https://www.swissquote.com/en-ch/private/trade/pricing/commissions/account-fees | read | Custody CHF 20–50 per quarter by bracket, +0.0075%/quarter above CHF 1m; "The VAT of 8.1% is applied to custody fees"; transfer out CHF 50/position electronic; tax statement CHF 85 | Retail online bank list price |
| SRC-SQ-COMM | Swissquote | Trading commissions overview | https://www.swissquote.com/en-ch/private/trade/pricing/commissions | read | Stocks/ETFs from CHF 3; funds and structured products from CHF 9; FX from 0.95% | Headline "from" prices only |
| SRC-BS-TARIFF | BancaStato (Ticino) | Servizi e prezzi, valid from 1 Oct 2026 | https://www.bancastato.ch/DMS/prodottieservizi/PUBLIC-ServiziPrezziBancaStato.pdf | partial | "I prezzi sono indicati IVA esclusa"; FX differential on payments 2.30% up to CHF 5'000 falling to 0.25% above CHF 1m; "Differenziale del 2% sul tasso di mercato" on FX cash; securities custody and brokerage not in this document | Securities tariff is a separate sheet |
| SRC-BS-MANDATE | BancaStato | Discretionary mandate page | https://www.bancastato.ch/clienti-individuali/investimenti/servizi/gestione-patrimoniale | read | Mandate is all-inclusive: flat quarterly fee "include tutte le spese necessarie quali commissioni di borsa, commissione di gestione e tasse di custodia"; minimum CHF 50'000 (fund-only) / 200'000 | Rate not published |
| SRC-UBS-GUIDE | UBS Switzerland | How to read your UBS statement | (long URL, see kit `sources/official_sources.csv`) | kit-only | Kit says quarterly current-account fees are excluded from the securities transaction list | Re-check before quoting |
| SRC-UBS-WEB | UBS Switzerland | UBS Manage / UBS Advice pages | https://www.ubs.com/ch/en/services/investments/manage-overview.html | read | No public fee figures | UBS mandate pricing is not public online |
| SRC-UBS-PSN | UBS | PSN Light CSV format description v3.2 (2024) | (kit) | kit-only | MT535/536/590/940 feed formats | For authorised external asset managers |
| SRC-LGT-PRO | LGT | SmartBanking Pro | https://www.lgt.com/global-en/lgt-smartbanking-pro | kit-only (our fetch failed) | PDF + XML index; SFTP e-data | |
| SRC-IBKR | Interactive Brokers | Reporting | https://www.interactivebrokers.com/en/whyib/reporting.php | kit-only | Flex queries XML | Contrast case |

## Product cost data

| id | Issuer | What | URL | Status | Key facts used | Caveat |
|---|---|---|---|---|---|---|
| SRC-PRIIPS-653 | European Union | Delegated Reg. (EU) 2017/653, consolidated 01/01/2023 | https://eur-lex.europa.eu/eli/reg_del/2017/653/oj | read (Art. 5) | Composition of costs: one-off (entry/exit), recurring (portfolio transaction costs; other recurring), incidental (performance fees, carried interest), all in % | Annex VI/VII not read verbatim |
| SRC-SSPA-COST | SSPA | Guideline on calculation and disclosure of costs of structured products (16 Oct 2019, in force 21 Nov 2019) | https://sspa.ch/wp-content/uploads/2020/08/20191016-svsp-ter-kostenkonzept-richtlinie_finalversion.pdf | read | Entry cost = price minus fair value; exit costs usually only before maturity; most products have no incidental costs; issuers publish daily cost data free on a website (ISIN, entry/exit ex post, ongoing ex post) | No explicit "distribution fee" wording |
| SRC-SSPA-MAP | SSPA | Swiss Derivative Map 2026 | https://sspa.ch/wp-content/uploads/2026/01/de_sspaswissmap_2026.pdf | listed | Product type codes (e.g. 1230 Barrier Reverse Convertible) | No cost data; useful for classification |
| SRC-AMAS-TER | AMAS | TER guideline, valid from 1 Jan 2022 | https://www.am-switzerland.ch/de/selbstregulierung/richtlinien-gueltig-ab-1-januar-2022 | partial | Guideline exists | PDF not retrieved; TER scope to verify (commonly excludes transaction costs) |
| SRC-SFD | SIX Financial Information | swissfunddata.ch | https://www.swissfunddata.ch/sfdpub/anlagefonds | read | Free FINMA-recognised publication platform for fund documents; professional data vendors may not "systematisch extrahieren, scrapen oder kommerziell verwerten" without SIX consent | **No automated scraping for a commercial tool** |
| SRC-OPENFIGI | Bloomberg / OpenFIGI | API docs | https://www.openfigi.com/api/documentation | read | Identity mapping only, no costs; 25 req/min without key, 250 with key | Sending a client's ISIN list leaks portfolio composition to a third party; batch with decoys or use catalog first |
| SRC-FINDATEX | FinDatEx | EMT / EPT templates | https://www.findatex.eu | partial | EMT V4.x carries MiFID cost fields; EPT carries PRIIPs data | Access via data vendors or manufacturers; field list to read |
| SRC-ESMA-QA | ESMA | MiFID II investor protection Q&A on ex-post cost disclosure | https://www.esma.europa.eu/publications-data/questions-answers/2024 | kit-only | EU annual aggregated costs in amount and % | EU, design reference only |
| SRC-KID-TRP | T. Rowe Price via swissfunddata | Example PRIIPs KID LU0860350064 | https://swissfunddata.ch/sfdpub/docs/prp-83400_01_05-20260218-en.pdf | kit-only | Example of share-class cost table | |

## Technology

| id | Project | Version seen | License | URL | Status |
|---|---|---|---|---|---|
| SRC-DOCLING | Docling | 2.148.0 (5 Nov 2026) | MIT | https://pypi.org/project/docling/ | read |
| SRC-PYMUPDF | PyMuPDF | 2.0 | **AGPL-3.0** or commercial (Artifex) | https://pypi.org/project/PyMuPDF/ | read |
| SRC-PDFPLUMBER | pdfplumber | 0.11.10 | MIT | https://pypi.org/project/pdfplumber/ | read |
| SRC-CAMELOT | camelot-py | 2.0.0 (4 Jun 2026) | MIT | https://pypi.org/project/camelot-py/ | read |
| SRC-PADDLE | PaddleOCR (PP-StructureV3, PaddleOCR-VL-1.6) | 3.7.0 (11 Jun 2026) | Apache-2.0 | https://pypi.org/project/paddleocr/ | read |
| SRC-TESSERACT | Tesseract | 5.x | Apache-2.0 | https://github.com/tesseract-ocr/tesseract | read |
| SRC-OCRMYPDF | OCRmyPDF | not captured | MPL-2.0 | https://github.com/ocrmypdf/OCRmyPDF | read |
| SRC-MARKER | Marker | not captured | Code Apache-2.0; **weights OpenRAIL-M, free only under USD 5M revenue/funding** | https://github.com/datalab-to/marker | read |
| SRC-MINERU | MinerU | 4.x (summary) | Apache-2.0 + extra terms (attribution for online services; MAU/revenue caps) | https://github.com/opendatalab/MinerU | read |
| SRC-UNSTRUCTURED | Unstructured | not captured | Apache-2.0 | https://github.com/Unstructured-IO/unstructured | read |
| SRC-OPENAI-DATA | OpenAI | API data controls | https://developers.openai.com/api/docs/guides/your-data | read | EEA+Switzerland region and zero retention need OpenAI approval; abuse logs kept up to 30 days by default |

## Open verification list

1. Safe Capital in the FINMA list (XLSX) and OSIF member list. **Owner: Ale or Massimo, manual.**
2. FinSA Art. 8, 16, 26 and FinSO Art. 7, 29 wording (Fedlex in a browser).
3. Stamp duty rates and split (StG Art. 13–17) and VAT treatment of custody vs asset management for Swiss vs foreign clients (MWSTG Art. 8, 21; ESTV MWST-Branchen-Info 14).
4. AMAS TER scope (transaction costs, performance fee).
5. Anthropic commercial terms on data retention and region (our fetch failed).
6. Real anonymised client documents from Massimo (the only way to validate the document taxonomy against Safe Capital's actual prospects).
