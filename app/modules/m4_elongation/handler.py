from app.web import batch
from flask import Blueprint, jsonify

router = Blueprint("elongation", __name__)


@router.get("/api/elongation/<key>")
def elongation(key):
    value = batch(key)
    return jsonify({field: value[field] for field in ("补偿记录",)})
