import json
from concurrent.futures import ThreadPoolExecutor

from app.config import BASE
from app.modules.m7_runs.service import calculate, run_once
from app.modules.m7_runs.store import History
from app.modules.m8_evidence.service import describe, gaps
from app.modules.m8_evidence.store import EvidenceStore, PENDING, REVOKED, VALID


def _checked_run(client):
    return client.post("/api/runs", json={"sample": "checked"}).json


def _issue(client, run_id, actor="质检员甲"):
    return client.post(f"/api/evidence/{run_id}/issue", json={"actor": actor})


def test_unissued_is_pending(client):
    run = _checked_run(client)
    status = client.get(f"/api/evidence/{run['id']}").json
    assert status["状态"] == PENDING
    assert status["凭据"] is None
    assert client.get("/api/runs").json[0]["证据状态"] == PENDING


def test_issue_freezes_valid_receipt(client):
    run = _checked_run(client)
    response = _issue(client, run["id"])
    assert response.status_code == 201
    record = response.json["record"]
    assert record["状态"] == VALID and record["凭据号"]
    assert response.json["status"]["状态"] == VALID
    assert client.get("/api/runs").json[0]["证据状态"] == VALID
    # 快照冻结了签发时的判验结论
    receipt = client.get(f"/api/evidence/receipt/{record['凭据号']}").json
    assert receipt["快照"]["判验"][0]["合计毫米"] == "40.000"


def test_retry_does_not_add_receipt(client):
    run = _checked_run(client)
    first = _issue(client, run["id"])
    second = _issue(client, run["id"])
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json["record"]["凭据号"] == second.json["record"]["凭据号"]
    assert len(client.get(f"/api/evidence/{run['id']}").json["历史"]) == 1


def test_balance_blocks_issuing_but_result_still_readable(client):
    run = _checked_run(client)
    # 把一份带勾稽差额的结果直接入库（模拟账实不符的历史结果）
    doctored = calculate((BASE / "sample_data" / "checked.json").read_bytes())
    doctored["读数勾稽"] = {**doctored["读数勾稽"], "行差": 1}
    history = client.application.extensions["beam-history"]
    with history.connect() as db:
        db.execute(
            "UPDATE calculations SET result=? WHERE code=?",
            (json.dumps(doctored, ensure_ascii=False), run["id"]),
        )

    assert gaps(doctored)
    blocked = _issue(client, run["id"])
    assert blocked.status_code == 422 and blocked.json["code"] == "BALANCE"
    # 复算记录照常可查，只是不能签发
    assert client.get(f"/api/runs/{run['id']}").status_code == 200
    assert client.get(f"/api/export/{run['id']}").json["证据凭证"]["状态"] == PENDING
    assert client.get(f"/api/evidence/{run['id']}").json["历史"] == []


def test_gap_rejects_issuing_directly(tmp_path):
    broken = calculate((BASE / "sample_data" / "checked.json").read_bytes())
    broken["读数勾稽"]["行差"] = 1
    store = EvidenceStore(tmp_path / "ev.sqlite")
    from app.modules.m8_evidence.service import issue
    from app.types import DataFault

    try:
        issue(store, broken, "质检员")
    except DataFault as exc:
        assert exc.code == "BALANCE"
    else:
        raise AssertionError("差额时应拒绝签发")
    assert describe(store, broken["清单"]["编号"])["状态"] == PENDING


def test_revoke_keeps_original_receipt_and_reissues_new_number(client):
    run = _checked_run(client)
    original = _issue(client, run["id"]).json["record"]["凭据号"]
    revoked = client.post(f"/api/evidence/{run['id']}/revoke", json={"actor": "质检员乙", "reason": "错签"})
    assert revoked.status_code == 200
    assert revoked.json["record"]["凭据号"] == original
    assert revoked.json["record"]["状态"] == REVOKED
    assert revoked.json["status"]["状态"] == REVOKED
    # 撤回后仍可按原号查到当时的读数与结论
    receipt = client.get(f"/api/evidence/receipt/{original}").json
    assert receipt["状态"] == REVOKED
    assert receipt["快照"]["判验"][0]["合计毫米"] == "40.000"
    # 补签换新号，旧号不被覆盖
    reissued = _issue(client, run["id"], "质检员丙")
    assert reissued.status_code == 201
    assert reissued.json["record"]["凭据号"] != original
    assert reissued.json["record"]["替代凭据"] == original
    assert client.get(f"/api/evidence/receipt/{original}").json["快照"]["判验"][0]["合计毫米"] == "40.000"
    assert client.get(f"/api/evidence/receipt/{reissued.json['record']['凭据号']}").json["状态"] == VALID


def test_revoke_is_idempotent_and_retry_adds_nothing(client):
    run = _checked_run(client)
    _issue(client, run["id"])
    first = client.post(f"/api/evidence/{run['id']}/revoke", json={"actor": "甲"})
    second = client.post(f"/api/evidence/{run['id']}/revoke", json={"actor": "乙"})
    assert (first.status_code, second.status_code) == (200, 200)
    assert first.json["record"]["凭据号"] == second.json["record"]["凭据号"]
    assert len(client.get(f"/api/evidence/{run['id']}").json["历史"]) == 1


def test_revoke_without_issue_not_found(client):
    run = _checked_run(client)
    response = client.post(f"/api/evidence/{run['id']}/revoke", json={"actor": "甲"})
    assert response.status_code == 422 and response.json["code"] == "NOT_ISSUED"


def test_concurrent_issue_keeps_single_valid(tmp_path, checked):
    store = EvidenceStore(tmp_path / "race.sqlite")
    report, _ = run_once(History(tmp_path / "race-runs.sqlite"), checked)
    run_code = report["清单"]["编号"]

    def attempt(_):
        return store.issue(run_code, report, "质检员")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))

    receipts = store.history(run_code)
    assert len([r for r in receipts if r["状态"] == VALID]) == 1
    assert len(receipts) == 1
    assert sum(created for _, created in results) == 1


def test_concurrent_reissue_keeps_single_valid(tmp_path, checked):
    store = EvidenceStore(tmp_path / "reissue.sqlite")
    report, _ = run_once(History(tmp_path / "reissue-runs.sqlite"), checked)
    run_code = report["清单"]["编号"]
    store.issue(run_code, report, "甲")
    store.revoke(run_code, "乙", "错签")

    def attempt(_):
        return store.issue(run_code, report, "补签人")

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attempt, range(6)))

    receipts = store.history(run_code)
    assert len([r for r in receipts if r["状态"] == VALID]) == 1
    # 撤回那条 + 补签一条，重试不多出签发记录
    assert len(receipts) == 2
    assert sum(created for _, created in results) == 1


def test_download_shows_status(client):
    run = _checked_run(client)
    pending = client.get(f"/api/export/{run['id']}").json
    assert pending["证据凭证"]["状态"] == PENDING
    serial = _issue(client, run["id"]).json["record"]["凭据号"]
    valid = client.get(f"/api/export/{run['id']}").json
    assert valid["证据凭证"]["状态"] == VALID
    assert valid["证据凭证"]["凭据号"] == serial
    client.post(f"/api/evidence/{run['id']}/revoke", json={"actor": "甲", "reason": "错签"})
    revoked = client.get(f"/api/export/{run['id']}").json
    assert revoked["证据凭证"]["状态"] == REVOKED
    # 原凭据仍可按号导出当时依据
    receipt = client.get(f"/api/evidence/receipt/{serial}/export")
    assert receipt.status_code == 200
    assert receipt.json["快照"]["判验"][0]["合计毫米"] == "40.000"


def test_pages_show_status(client):
    run = _checked_run(client)
    page = client.get(f"/desk/runs?run={run['id']}").get_data(as_text=True)
    assert "证据待签" in page
    _issue(client, run["id"])
    page = client.get(f"/desk/runs?run={run['id']}").get_data(as_text=True)
    assert "证据有效" in page
    client.post(f"/api/evidence/{run['id']}/revoke", json={"actor": "甲"})
    page = client.get(f"/desk/runs?run={run['id']}").get_data(as_text=True)
    assert "证据撤回" in page
