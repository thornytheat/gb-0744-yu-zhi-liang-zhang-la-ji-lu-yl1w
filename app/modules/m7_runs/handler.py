from app.web import batch
from flask import Blueprint, jsonify

router = Blueprint("runs", __name__)


@router.get("/api/runs/<key>")
def runs(key):
    value = batch(key)
    return jsonify({field: value[field] for field in ("清单",)})
