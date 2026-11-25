"""SC-5.23: on slightly skewed scans and photos the amount sits a few points below its label and was put on
a line of its own, so the fee was lost. Coordinates are the ones RapidOCR gave on the realistic benchmark."""

from __future__ import annotations

from pce.extraction.layout import Cell, _group
from pce.extraction.vocab import map_fee_label


def _texts(cells: list[Cell], skew: bool) -> list[str]:
    return [ln.text for ln in _group(cells, 1, "rapidocr", 0.9, tol=4.0, skew=skew)]


def test_amount_dropped_below_its_label_joins_the_row() -> None:
    cells = [
        Cell("Courtage", (40, 129, 90, 143)),
        Cell("4'759.31", (501, 133, 540, 146)),
        Cell("Fremde Spesen", (40, 145, 120, 159)),
        Cell("182.90", (509, 150.5, 540, 163)),
        Cell("Eidg. Umsatzabgabe", (40, 161, 150, 175)),
        Cell("601.80", (508, 165, 540, 178)),
    ]
    assert _texts(cells, skew=True) == [
        "Courtage 4'759.31",
        "Fremde Spesen 182.90",
        "Eidg. Umsatzabgabe 601.80",
    ]


def test_amount_raised_above_its_label_joins_the_row() -> None:
    cells = [Cell("1'719.17", (497, 114, 540, 125)), Cell("Diritti di custodia", (36, 118, 130, 129))]
    assert _texts(cells, skew=True) == ["Diritti di custodia 1'719.17"]


def test_cells_stacked_in_one_column_stay_separate_rows() -> None:
    cells = [Cell("Total", (40, 100, 80, 112)), Cell("Net", (40, 106, 70, 118))]
    assert len(_texts(cells, skew=True)) == 2


def test_digital_grouping_is_unchanged() -> None:
    cells = [Cell("Fremde Spesen", (40, 145, 120, 159)), Cell("182.90", (509, 150.5, 540, 163))]
    assert len(_texts(cells, skew=False)) == 2


def test_ocr_accent_on_i_does_not_hide_a_fee_word() -> None:
    assert map_fee_label("Commissioní di intermediazione") == map_fee_label("Commissioni di intermediazione")
    assert map_fee_label("Commissioni di intermediazione") is not None
