from app.web import batch
from flask import Blueprint, jsonify

router = Blueprint("sampling", __name__)


@router.get("/api/sampling/<key>")
def sampling(key):
    value = batch(key)
    return jsonify({field: value[field] for field in ("原始采信", "隔离", "重复")})
