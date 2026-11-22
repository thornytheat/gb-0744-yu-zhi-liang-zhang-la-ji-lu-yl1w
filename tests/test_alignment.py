import json

from app.modules.m1_sampling.source import load
from app.modules.m7_runs.service import calculate


def test_force_exceeding_boundary(report):
    assert len([row for row in report["隔离"] if row["原因码"] == "FORCE_TOLERANCE"]) == 2


def test_exact_force_tolerance_is_inclusive(checked):
    content = load(checked)
    content["readings"][0]["force"] = "21"
    data = calculate(json.dumps(content).encode())
    assert data["力级记录"][0]["载荷千牛"] == "210.000"


def test_no_matching_design(report):
    assert [r["梁号"] for r in report["隔离"] if r["原因码"] == "NO_TARGET"] == ["0010"]


def test_multiple_valid_readings_at_level(report):
    assert len([r for r in report["隔离"] if r["原因码"] == "LEVEL_CONFLICT"]) == 2


def test_both_ends_independently_aligned(check):
    assert sorted((r["端位"], r["力级%"]) for r in check["力级记录"]) == [
        (s, l) for s in ("L", "R") for l in (20, 40, 100)
    ]


def test_foreign_day_ignored(checked):
    content = load(checked)
    content["readings"][0]["day"] = "2026-11-19"
    assert calculate(json.dumps(content).encode())["隔离"][0]["原因码"] == "NO_TARGET"
