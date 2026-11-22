import pytest
from app.modules.m1_sampling.source import load
from app.types import DataFault


# TRAP-02
def test_bom(checked):
    assert load(b"\xef\xbb\xbf" + checked)["targets"][0]["beam"] == "0007"


# TRAP-06 TRAP-15
def test_fullwidth_and_centimetres(report):
    assert report["原始采信"][2]["位移毫米"] == "27.000"


# TRAP-07
def test_na_is_not_displacement(report):
    assert any(r["梁号"] == "0009" and r["原因码"] == "BAD_READING" for r in report["隔离"])


# TRAP-08
def test_identifier_zeros(report):
    assert report["原始采信"][0]["梁号"] == "0007"


# TRAP-14
def test_disagreeing_ids_both_isolated(report):
    assert len([r for r in report["隔离"] if r["原因码"] == "ID_CONFLICT"]) == 2


# TRAP-16
def test_truncated_file_is_rejected(checked):
    with pytest.raises(DataFault) as exc:
        load(checked[:-4])
    assert exc.value.code == "FILE"


# TRAP-17
def test_legacy_field(report):
    assert report["原始采信"][3]["位移毫米"] == "7.000"


def test_duplicate_is_counted_once(report):
    assert [r["源行"] for r in report["重复"]] == [7]
