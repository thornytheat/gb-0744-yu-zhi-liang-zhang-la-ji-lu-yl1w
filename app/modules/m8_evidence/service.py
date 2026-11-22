"""张拉证据的签发生命周期。

状态含义：
- 待签：尚无任何凭据；
- 有效：存在一份有效凭据；
- 撤回：曾签发过，但当前唯一一份凭据已撤回。

签发前复核勾稽。读数或梁号勾稽存在差额时，复算结果照常可查，
但拒绝签发（BALANCE）。签发时冻结当时的读数与结论（快照），
因此撤回后按原凭据号仍能查回签收时的依据。补签一律换新号，
旧凭据原样保留为「撤回」，绝不复用原号。
"""

import json

from app.modules.m8_evidence.store import PENDING, REVOKED, VALID
from app.types import DataFault

ACTOR_LIMIT = 60


def clean_actor(actor):
    if not isinstance(actor, str) or not actor.strip():
        return "班组"
    if len(actor.strip()) > ACTOR_LIMIT:
        raise DataFault("ACTOR", "签发人或撤回人名称过长")
    return actor.strip()


def gaps(result):
    """返回勾稽差额；为空表示账实相符，可以签发。"""
    found = []
    conservation = result.get("读数勾稽") or {}
    if conservation.get("行差", 0) != 0:
        found.append({"范围": "读数勾稽", "项目": "行差", "差额": conservation.get("行差")})
    for row in result.get("梁号勾稽") or []:
        if row.get("行差", 0) != 0:
            found.append({"范围": f"梁号勾稽 {row.get('梁号')}", "项目": "行差", "差额": row.get("行差")})
    return found


def snapshot(result):
    """签发时冻结的完整依据：读数、换算、判验与勾稽。"""
    return json.loads(json.dumps(result, ensure_ascii=False))


def describe(store, run_code):
    history = [{k: v for k, v in row.items() if k != "快照"} for row in store.history(run_code)]
    current = store.current(run_code)
    status = VALID if current else (REVOKED if history else PENDING)
    if current:
        current = {k: v for k, v in current.items() if k != "快照"}
    return {
        "班次": run_code,
        "状态": status,
        "凭据": current,
        "历史": history,
    }


def issue(store, result, actor):
    found = gaps(result)
    if found:
        raise DataFault("BALANCE", "勾稽存在差额，证据不能签发")
    run_code = result["清单"]["编号"]
    receipt, created = store.issue(run_code, snapshot(result), clean_actor(actor))
    return receipt, created


def revoke(store, run_code, actor, reason):
    try:
        return store.revoke(run_code, clean_actor(actor), (reason or "错签撤回").strip()[:200])
    except LookupError as exc:
        raise DataFault("NOT_ISSUED", "该班次从未签发凭据") from exc


def download_notice(result, store):
    """下载正文顶部展示的证据状态，收件方一眼可辨。"""
    status = describe(store, result["清单"]["编号"])
    current = status["凭据"]
    notice = {
        "状态": status["状态"],
        "凭据号": current["凭据号"] if current else None,
        "签发时间": current["签发时间"] if current else None,
        "签发人": current["签发人"] if current else None,
    }
    if status["状态"] == PENDING:
        found = gaps(result)
        notice["说明"] = "未签发，仅供复算查阅" if not found else "勾稽存在差额，不能签发"
    elif status["状态"] == REVOKED:
        last = status["历史"][0] if status["历史"] else None
        notice["说明"] = "凭据已撤回，不能作为签收依据"
        notice["撤回时间"] = last["撤回时间"] if last else None
        notice["撤回原因"] = last["撤回原因"] if last else None
    else:
        notice["说明"] = "凭据有效"
    return notice
