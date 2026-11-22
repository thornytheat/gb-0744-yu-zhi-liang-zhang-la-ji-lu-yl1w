from app.modules.m8_evidence.service import describe, issue, revoke
from app.web import batch, evidence
from flask import Blueprint, jsonify, request

router = Blueprint("evidence", __name__)


def _actor(form):
    if not hasattr(form, "get"):
        return ""
    return form.get("actor") or request.headers.get("X-Operator") or ""


@router.get("/api/evidence/<key>")
def status(key):
    result = batch(key)
    return jsonify(describe(evidence(), result["清单"]["编号"]))


@router.get("/api/evidence/receipt/<serial>")
def receipt(serial):
    store = evidence()
    found = store.find(serial)
    if not found:
        return jsonify(code="NOT_FOUND", detail="凭据号不存在"), 404
    return jsonify(found)


@router.post("/api/evidence/<key>/issue")
def sign(key):
    result = batch(key)
    form = request.get_json(silent=True) if request.is_json else request.form
    record, created = issue(evidence(), result, _actor(form))
    return jsonify(record=record, created=created, status=describe(evidence(), record["班次"])), (
        201 if created else 200
    )


@router.post("/api/evidence/<key>/revoke")
def cancel(key):
    result = batch(key)
    form = request.get_json(silent=True) if request.is_json else request.form
    reason = form.get("reason") if hasattr(form, "get") else None
    record, changed = revoke(evidence(), result["清单"]["编号"], _actor(form), reason)
    return jsonify(record=record, changed=changed, status=describe(evidence(), record["班次"]))
