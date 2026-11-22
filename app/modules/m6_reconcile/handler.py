from app.web import batch
from flask import Blueprint, jsonify

router = Blueprint("reconcile", __name__)


@router.get("/api/reconcile/<key>")
def reconcile(key):
    value = batch(key)
    return jsonify({field: value[field] for field in ("梁号勾稽", "读数勾稽")})
