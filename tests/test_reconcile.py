from app.modules.m6_reconcile.service import ledger


def test_books_conserve(report):
    rows = report["读数勾稽"]
    assert rows["原读数"] == rows["对齐"] + rows["隔离"] + rows["重复"] == 38


def test_clean_balanced(check):
    assert check["读数勾稽"] == {"原读数": 6, "对齐": 6, "隔离": 0, "重复": 0, "行差": 0}


def test_per_beam_statuses(report):
    assert report["梁号勾稽"][0] == {
        "梁号": "0007",
        "设计钢束": 3,
        "通过": 1,
        "待复测": 1,
        "超限": 1,
        "行差": 0,
    }


def test_no_phantom_beam(report):
    assert {row["梁号"] for row in report["梁号勾稽"]} == {"0007", "0008", "0009"}


def test_missing_readings_detected():
    assert ledger(2, [], [], [], [])[0]["行差"] == 2


def test_beam_totals_match_design(report):
    assert sum(r["设计钢束"] for r in report["梁号勾稽"]) == len(report["判验"]) == 6
