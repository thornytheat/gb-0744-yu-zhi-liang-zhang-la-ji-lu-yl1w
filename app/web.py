from app.config import SAMPLES
from app.types import DataFault
from flask import abort, current_app


def history():
    return current_app.extensions["beam-history"]


def batch(key):
    dataset = history().find(key)
    if not dataset:
        abort(404)
    return dataset


def raw_sample(slug):
    if not isinstance(slug, str) or slug not in SAMPLES:
        raise DataFault("SAMPLE", "请选择已有记录")
    return (current_app.config["SAMPLE_DIR"] / f"{slug}.json").read_bytes()
