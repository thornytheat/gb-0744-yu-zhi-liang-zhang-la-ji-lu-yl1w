from datetime import date

from app.modules.m1_sampling.source import load
from app.modules.m2_calibration.registry import applicable, calibrations


# TRAP-25
def test_overlap_has_evidence(report):
    assert [(r["梁号"], r["钢束"], r["端位"]) for r in report["隔离"] if r["原因码"] == "CAL_OVERLAP"] == [
        ("0008", "S02", "L")
    ]


# TRAP-23
def test_valid_at_start(yard):
    versions = calibrations(load(yard)["calibrations"])
    assert [v["revision"] for v in applicable(versions, "J-09", date(2026, 8, 1))] == ["J09-02"]


def test_expired_at_end(yard):
    assert applicable(calibrations(load(yard)["calibrations"]), "J-09", date(2027, 2, 1)) == []


def test_pressure_calibrated(check):
    assert check["力级记录"][0]["载荷千牛"] == "200.000"


def test_force_direct(check):
    assert check["力级记录"][4]["采信来源"] == "力传感器"


def test_certificates_retained(report):
    assert [r["版本"] for r in report["标定依据"]] == ["J09-02", "JR-1", "JR-2"]
