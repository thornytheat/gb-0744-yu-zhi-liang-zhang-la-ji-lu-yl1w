from decimal import Decimal

from app.modules.m4_elongation.formula import evaluate


def test_zero_point_extrapolated(check):
    row = check["补偿记录"][0]
    assert (row["峰值毫米"], row["零点毫米"], row["回缩毫米"], row["有效毫米"]) == (
        "27.000",
        "5.000",
        "2.000",
        "20.000",
    )
    assert Decimal(row["有效毫米"]) != Decimal(row["峰值毫米"])


def test_other_end_uses_own_anchor(check):
    row = check["补偿记录"][1]
    assert (row["零点毫米"], row["回缩毫米"], row["有效毫米"]) == ("3.000", "1.000", "20.000")


def test_ordered_real_loads_not_nominal():
    rows = [{"kn": Decimal(f), "stroke": Decimal(s)} for f, s in [(210, 9), (390, 13), (1000, 27)]]
    result = evaluate(rows, Decimal(2))
    assert result["零点毫米"].quantize(Decimal("0.001")) == Decimal("4.333")


def test_plateau_rejected(report):
    assert any(r["钢束"] == "S01" and r.get("原因码") == "REVERSED" for r in report["补偿记录"])


def test_no_synthesized_missing_stage(report):
    assert any(
        r["钢束"] == "S03" and r["端位"] == "R" and r.get("原因码") == "MISSING_LEVEL"
        for r in report["补偿记录"]
    )


def test_anchor_can_invalidate_measurement():
    rows = [{"kn": Decimal(f), "stroke": Decimal(s)} for f, s in [(200, 9), (400, 13), (1000, 27)]]
    assert evaluate(rows, Decimal(30)) == {"原因码": "NO_EXTENSION"}
