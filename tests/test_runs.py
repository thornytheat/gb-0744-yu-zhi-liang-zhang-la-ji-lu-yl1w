import hashlib
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from app.modules.m7_runs.service import run_once
from app.modules.m7_runs.store import History


def test_run_reuses_batch(client):
    first = client.post("/api/runs", json={"sample": "checked"})
    second = client.post("/api/runs", json={"sample": "checked"})
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json["id"] == second.json["id"]
    assert len(client.get("/api/runs").json) == 1


def test_sha_matches_upload(client, checked):
    result = client.post("/api/runs", data={"file": (BytesIO(checked), "line.json")}).json
    response = client.get(f"/api/export/{result['id']}")
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.json["清单"]["摘要"] == hashlib.sha256(checked).hexdigest()


def test_unknown_sample_has_no_run(client):
    res = client.post("/api/runs", json={"sample": "unknown"})
    assert res.status_code == 422 and res.json["code"] == "SAMPLE"
    assert client.get("/api/runs").json == []


def test_results_reopen(tmp_path, checked):
    filename = tmp_path / "storage.sqlite"
    report, _ = run_once(History(filename), checked)
    assert History(filename).find(report["清单"]["编号"])["判验"][0]["合计毫米"] == "40.000"


def test_atomicity_with_retries(tmp_path, checked):
    history = History(tmp_path / "result.sqlite")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: run_once(history, checked), range(4)))
    assert len(history.recent()) == 1
    assert sum(not reused for _, reused in results) == 1


def test_unknown_batch_404(client):
    assert client.get("/api/export/none").status_code == 404
