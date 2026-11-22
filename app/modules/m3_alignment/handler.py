from app.web import batch
from flask import Blueprint, jsonify

router = Blueprint("alignment", __name__)


@router.get("/api/alignment/<key>")
def alignment(key):
    value = batch(key)
    return jsonify({field: value[field] for field in ("力级记录",)})
