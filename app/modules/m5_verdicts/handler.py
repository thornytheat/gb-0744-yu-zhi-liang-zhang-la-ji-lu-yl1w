from app.web import batch
from flask import Blueprint, jsonify

router = Blueprint("verdicts", __name__)


@router.get("/api/verdicts/<key>")
def verdicts(key):
    value = batch(key)
    return jsonify({field: value[field] for field in ("判验",)})
