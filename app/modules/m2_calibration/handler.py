from app.web import batch
from flask import Blueprint, jsonify

router = Blueprint("calibration", __name__)


@router.get("/api/calibration/<key>")
def calibration(key):
    value = batch(key)
    return jsonify({field: value[field] for field in ("标定依据",)})
