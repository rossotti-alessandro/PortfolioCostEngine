"""SYNTHETIC PII set for measuring a detector (SC-11.9 acceptance #1).

Every person, number and address is invented.

Pages imitate the text pdfplumber or OCR returns from a private-banking statement, cover letter or KYC
page in IT, DE, FR and EN. Each page carries gold spans for what a redactor must hide, built while the text
is written, so offsets are exact. Hard cases are deliberate: identifiers broken across lines, numbers
without a label, national phone formats, OCR letter/digit swaps, surnames alone in a salutation, joint
holders. Distractors that must stay visible: ISINs, valor numbers, amounts, dates, rates, the bank's own
BIC.

    uv run python -m tests.evaluation.pii_set     # scores pce.pii (rules) on the set
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from stdnum import ean, iban, luhn

KINDS = ("name", "address", "iban", "ahv", "card", "account", "phone", "email", "birth_date")


@dataclass
class Page:
    lang: str
    text: str = ""
    gold: list[tuple[str, int, int]] = field(default_factory=list)

    def put(self, s: str, kind: str | None = None) -> None:
        if kind:
            self.gold.append((kind, len(self.text), len(self.text) + len(s)))
        self.text += s


FIRST = [
    "Marco",
    "Laura",
    "Ursula",
    "Jean-Luc",
    "Chiara",
    "Thomas",
    "Élodie",
    "Olena",
    "Mehmet",
    "Li",
    "Sarah",
]
LAST = [
    "Bernasconi",
    "Brunner-Keller",
    "Favre",
    "Rezzonico",
    "Müller",
    "Kovalenko",
    "Yılmaz",
    "Wei",
    "O'Connor",
    "Pedrazzini",
    "Schaller",
]
STREETS = {
    "it": ["Via Nassa", "Via Cantonale", "Corso Pestalozzi", "Viale Stefano Franscini"],
    "de": ["Bahnhofstrasse", "Seefeldstrasse", "Rämistrasse", "Hauptgasse"],
    "fr": ["Rue du Rhône", "Avenue de la Gare", "Chemin des Vignes", "Rue de Bourg"],
    "en": ["Kings Road", "Baker Street", "Elm Grove", "Harbour View"],
}
TOWNS = {
    "it": [("6900", "Lugano"), ("6600", "Locarno"), ("6500", "Bellinzona")],
    "de": [("8001", "Zürich"), ("6300", "Zug"), ("4051", "Basel")],
    "fr": [("1204", "Genève"), ("1003", "Lausanne"), ("2000", "Neuchâtel")],
    "en": [("SW3 4LY", "London"), ("EH1 1YZ", "Edinburgh"), ("6900", "Lugano")],
}
WORDS = {
    "it": {
        "title": "Estratto patrimoniale al 31.12.2025",
        "holder": "Titolare",
        "acct": ["Relazione n. ", "Conto n. ", "Rapporto ", "Portafoglio n. ", "Codice cliente "],
        "iban": "IBAN ",
        "tel": "Tel. ",
        "mail": "E-mail: ",
        "dob": "Data di nascita: ",
        "ahv": "N. AVS: ",
        "dear": "Gentile Signor ",
        "card": "Carta di credito ",
        "value": "Valore di mercato",
        "fee": "Commissione di gestione 0.85% p.a.",
        "valor": "N. valore",
    },
    "de": {
        "title": "Vermögensausweis per 31.12.2025",
        "holder": "Inhaber",
        "acct": ["Konto-Nr. ", "Depot-Nr. ", "Stammnummer ", "Kontonummer: ", "Kunden-Nr. "],
        "iban": "IBAN ",
        "tel": "Telefon ",
        "mail": "E-Mail: ",
        "dob": "Geburtsdatum: ",
        "ahv": "AHV-Nr.: ",
        "dear": "Sehr geehrter Herr ",
        "card": "Kreditkarte ",
        "value": "Marktwert",
        "fee": "Verwaltungsgebühr 0.85% p.a.",
        "valor": "Valoren-Nr.",
    },
    "fr": {
        "title": "Relevé de fortune au 31.12.2025",
        "holder": "Titulaire",
        "acct": ["Compte n° ", "Dossier ", "Numéro de compte ", "Portefeuille n° ", "Client n° "],
        "iban": "IBAN ",
        "tel": "Tél. ",
        "mail": "E-mail : ",
        "dob": "Date de naissance : ",
        "ahv": "N° AVS : ",
        "dear": "Cher Monsieur ",
        "card": "Carte de crédit ",
        "value": "Valeur de marché",
        "fee": "Commission de gestion 0.85% p.a.",
        "valor": "N° de valeur",
    },
    "en": {
        "title": "Portfolio statement as at 31.12.2025",
        "holder": "Account holder",
        "acct": ["Account no. ", "Portfolio ", "Relationship number ", "Client number: ", "Acct "],
        "iban": "IBAN ",
        "tel": "Phone ",
        "mail": "Email: ",
        "dob": "Date of birth: ",
        "ahv": "AHV/AVS no.: ",
        "dear": "Dear Mr ",
        "card": "Credit card ",
        "value": "Market value",
        "fee": "Management fee 0.85% p.a.",
        "valor": "Valor no.",
    },
}
# Public fund ISINs and the bank's own BIC: must stay visible.
ISINS = ["IE00B4L5Y983", "LU0274208692", "CH0012032048", "IE00B5BMR087", "LU1681043599"]


def _iban(rng: random.Random, country: str) -> str:
    bban = {"CH": 17, "LI": 17, "DE": 18, "IT": 23}[country]
    body = "".join(rng.choice("0123456789") for _ in range(bban))
    if country == "IT":
        body = rng.choice("ABCDEFGHIJ") + body[1:]
    raw = country + iban.calc_check_digits(country + "00" + body) + body
    return " ".join(raw[i : i + 4] for i in range(0, len(raw), 4))


def _ahv(rng: random.Random) -> str:
    d = "756" + "".join(rng.choice("0123456789") for _ in range(9))
    d += ean.calc_check_digit(d)
    return f"{d[:3]}.{d[3:7]}.{d[7:11]}.{d[11:]}"


def _card(rng: random.Random) -> str:
    d = rng.choice("45") + "".join(rng.choice("0123456789") for _ in range(14))
    d += luhn.calc_check_digit(d)
    return " ".join(d[i : i + 4] for i in range(0, 16, 4))


def _account(rng: random.Random) -> str:
    n = lambda k: "".join(rng.choice("0123456789") for _ in range(k))  # noqa: E731
    return rng.choice(
        [f"{n(4)}-{n(6)}.{n(2)}", f"{n(3)}.{n(3)}.{n(3)}", f"{n(7)}-{n(2)}", f"CH-{n(8)}", n(10)]
    )


def _phone(rng: random.Random, lang: str) -> str:
    """A phone number, international or Swiss national form."""
    n = lambda k: "".join(rng.choice("0123456789") for _ in range(k))  # noqa: E731
    if lang == "en" and rng.random() < 0.5:
        return f"+44 20 {n(4)} {n(4)}"
    area = {"it": "091", "de": "044", "fr": "022", "en": "091"}[lang]
    if rng.random() < 0.5:
        return f"+41 {area[1:]} {n(3)} {n(2)} {n(2)}"
    return f"{area} {n(3)} {n(2)} {n(2)}"


def _ocr_noise(s: str, rng: random.Random) -> str:
    """One letter/digit swap of the kind OCR makes (0->O, 1->l, 5->S)."""
    idx = [i for i, c in enumerate(s) if c in "015"]
    if not idx:
        return s
    i = rng.choice(idx)
    return s[:i] + {"0": "O", "1": "l", "5": "S"}[s[i]] + s[i + 1 :]


def make_page(seed: int, lang: str) -> Page:
    rng = random.Random(seed)  # noqa: S311 - reproducible test data, not a secret
    w = WORDS[lang]
    p = Page(lang)
    first, last = rng.choice(FIRST), rng.choice(LAST)
    street, (plz, town) = rng.choice(STREETS[lang]), rng.choice(TOWNS[lang])
    p.put("SYNTHETIC - Banca Esempio SA, Via Bank 1, 6900 Lugano, BIC BEXACH22XXX\n")
    p.put(f"{w['title']}\n\n")
    joint = rng.random() < 0.25
    p.put(f"{w['holder']}: ")
    if joint:
        first2 = rng.choice([f for f in FIRST if f != first])
        p.put(f"{first} {last}", "name")
        p.put(" & ")
        p.put(f"{first2} {last}", "name")
    else:
        p.put(f"{first} {last}", "name")
    p.put("\n")
    p.put(f"{street} {rng.randint(1, 120)}", "address")
    p.put("\n")
    p.put(f"{plz} {town}", "address")
    p.put("\n")
    label = rng.choice(w["acct"])
    acct = _account(rng)
    p.put(label)
    p.put(acct, "account")
    p.put("\n")
    ib = _iban(rng, rng.choice(["CH", "CH", "LI", "DE", "IT"]))
    style = rng.random()
    p.put(w["iban"])
    if style < 0.15:  # broken across two lines, as a narrow PDF column returns it
        cut = ib.index(" ", 9)
        p.put(ib[:cut], "iban")
        p.put("\n")
        p.put(ib[cut + 1 :], "iban")
    elif style < 0.3:
        p.put(_ocr_noise(ib, rng), "iban")
    elif style < 0.45:
        p.put(ib.replace(" ", ""), "iban")
    else:
        p.put(ib, "iban")
    p.put("\n")
    if rng.random() < 0.6:
        p.put(w["dob"])
        p.put(f"{rng.randint(1, 28):02d}.{rng.randint(1, 12):02d}.{rng.randint(1940, 1995)}", "birth_date")
        p.put("\n")
    if rng.random() < 0.5:
        p.put(w["ahv"])
        p.put(_ahv(rng), "ahv")
        p.put("\n")
    tel = _phone(rng, lang)
    p.put(w["tel"])
    p.put(tel, "phone")
    p.put("   ")
    p.put(w["mail"])
    local = unicodedata.normalize("NFKD", f"{first}.{last}".lower()).encode("ascii", "ignore").decode()
    p.put(f"{local.replace(chr(39), '')}@example.ch", "email")
    p.put("\n\n")
    # Holdings table: none of this is personal data.
    p.put(f"{w['valor']}    ISIN            {w['value']} CHF\n")
    for isin in rng.sample(ISINS, 3):
        value = f"{rng.randint(10, 900)}'{rng.randint(100, 999)}.{rng.randint(10, 99)}"
        p.put(f"{rng.randint(1000000, 99999999)}    {isin}    {value}\n")
    p.put(f"{w['fee']}\n\n")
    # Harder cases: number repeated without its label (page header of page 2), unlabelled national phone,
    # surname alone in a salutation, a card number in a transaction line.
    p.put(f"{last.upper()} {first.upper()[0]}.", "name")
    p.put("   ")
    p.put(acct, "account")
    p.put("   2/3\n")
    if rng.random() < 0.5:
        p.put(f"{w['card']}")
        p.put(_card(rng), "card")
        p.put("  -1'250.00\n")
    p.put(f"{w['dear']}")
    p.put(last, "name")
    p.put(",\n")
    if rng.random() < 0.5:
        other = _phone(rng, lang)
        p.put(other, "phone")
        p.put("\n")
    return p


def pages(n_per_lang: int = 25) -> list[Page]:
    return [make_page(1000 * i + j, lang) for j, lang in enumerate(WORDS) for i in range(n_per_lang)]


def _covered(spans: Iterable[tuple[int, int]], text: str, start: int, end: int) -> bool:
    """True when every non-space character of [start, end) is inside some predicted span."""
    hit = [False] * (end - start)
    for s, e in spans:
        for i in range(max(s, start), min(e, end)):
            hit[i - start] = True
    return all(h or text[start + i].isspace() for i, h in enumerate(hit))


def score(predict: Callable[[str], list[tuple[str, int, int]]], ps: list[Page]) -> dict:
    """Per gold kind: fully hidden / total. Precision: predicted spans that overlap any gold span."""
    found: dict[str, list[int]] = {k: [0, 0] for k in KINDS}
    pred_ok = pred_all = 0
    false_pos: list[str] = []
    for p in ps:
        pred = predict(p.text)
        spans = [(s, e) for _, s, e in pred]
        for kind, s, e in p.gold:
            found[kind][1] += 1
            found[kind][0] += _covered(spans, p.text, s, e)
        for kind, s, e in pred:
            pred_all += 1
            if any(s < ge and gs < e for _, gs, ge in p.gold):
                pred_ok += 1
            elif len(false_pos) < 20:
                false_pos.append(f"{kind}: {re.sub(r'[0-9]', '9', p.text[s:e])}")
    total = [sum(v[0] for v in found.values()), sum(v[1] for v in found.values())]
    return {
        "recall": {k: tuple(v) for k, v in found.items() if v[1]},
        "overall": tuple(total),
        "precision": (pred_ok, pred_all),
        "false_positive_shapes": false_pos,
    }


def rules(text: str) -> list[tuple[str, int, int]]:
    from pce import pii

    return [(s.kind, s.start, s.end) for s in pii.detect(text)]


def report(res: dict) -> str:
    lines = ["| Kind | Fully hidden | Recall |", "|---|---|---|"]
    for k, (a, b) in res["recall"].items():
        lines.append(f"| {k} | {a}/{b} | {a / b:.0%} |")
    a, b = res["overall"]
    lines.append(f"| **all** | {a}/{b} | {a / b:.0%} |")
    pa, pb = res["precision"]
    lines.append(f"\nPrecision: {pa}/{pb} = {pa / max(pb, 1):.0%}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(score(rules, pages())))
