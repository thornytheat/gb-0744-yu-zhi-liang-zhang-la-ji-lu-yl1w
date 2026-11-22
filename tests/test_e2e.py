from app.config import STAGES


def test_each_operation_has_page_and_api(client):
    run = client.post("/api/runs", json={"sample": "checked"}).json
    assert run["verdicts"][0]["合计毫米"] == "40.000"
    for stage in STAGES:
        assert client.get(f"/api/{stage}/{run['id']}").status_code == 200
        assert client.get(f"/desk/{stage}?run={run['id']}").status_code == 200


def test_correction_and_dirty_have_different_totals(client):
    clean = client.post("/api/runs", json={"sample": "checked"}).json
    dirty = client.post("/api/runs", json={"sample": "yard"}).json
    assert clean["balance"]["隔离"] == 0 < dirty["balance"]["隔离"]
    assert dirty["balance"]["行差"] == 0
