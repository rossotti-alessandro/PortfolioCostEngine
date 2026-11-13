"""SC-11.9: the rules hide every structured identifier on the SYNTHETIC PII set and flag nothing else.

Names, addresses and birth dates are not rule territory (0% by design); they need the local model
(docs/research/PII_MEASUREMENT.md).
"""

from evaluation.pii_set import pages, rules, score

IDENTIFIERS = ("iban", "ahv", "card", "account", "phone", "email")


def test_rules_hide_every_identifier_on_the_synthetic_set() -> None:
    res = score(rules, pages())
    for kind in IDENTIFIERS:
        hidden, total = res["recall"][kind]
        assert hidden == total, (kind, hidden, total)
    assert res["precision"][0] == res["precision"][1], res["false_positive_shapes"]
