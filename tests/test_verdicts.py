from decimal import Decimal

from app.modules.m5_verdicts.service import classify


def test_passing_total_from_two_ends(check):
    row = check["判验"][0]
    assert (row["合计毫米"], row["判验"]) == ("40.000", "通过")


def test_two_checks_independent(report):
    assert report["判验"][1]["证据"] == ["L-SIDE_TOLERANCE", "TOTAL_TOLERANCE"]


def test_weak_end_cannot_hide_in_passing_total():
    ends = {
        ("B", "S", e): {"有效毫米": Decimal(v), "源行": [index]}
        for index, (e, v) in enumerate([("L", 14), ("R", 26)], 1)
    }
    target = {("B", "S"): {"theory": {"L": Decimal(20), "R": Decimal(20)}}}
    assert classify(target, ends)[0]["证据"] == ["L-SIDE_TOLERANCE", "R-SIDE_TOLERANCE"]


def test_incomplete_has_no_total(report):
    assert report["判验"][2]["合计毫米"] is None


def test_incomplete_remains_pending(report):
    assert report["判验"][2]["判验"] == "待复测"


def test_keeps_source_readings(check):
    assert check["判验"][0]["源行"] == [1, 2, 3, 4, 5, 6]
