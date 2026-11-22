import os

from app.config import BASE, MATCH_LIMIT, SAMPLES, STAGES, VERSION
from app.modules import register
from app.modules.m7_runs.service import run_once
from app.modules.m7_runs.store import History
from app.types import DataFault
from app.web import batch, history, raw_sample
from flask import Flask, abort, jsonify, render_template, request, url_for

PAGE_SECTIONS = {
    "sampling": ["原始采信", "隔离", "重复"],
    "calibration": ["标定依据"],
    "alignment": ["力级记录"],
    "elongation": ["补偿记录"],
    "verdicts": ["判验"],
    "reconcile": ["梁号勾稽", "读数勾稽"],
    "runs": ["清单"],
}


def create_app(settings=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("STRETCH_DB", BASE / "instance" / "stretch.sqlite3"),
        SAMPLE_DIR=BASE / "sample_data",
        MAX_CONTENT_LENGTH=MATCH_LIMIT + 32000,
    )
    if settings:
        app.config.update(settings)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    app.extensions["beam-history"] = History(app.config["DATABASE"])
    register(app)

    @app.errorhandler(DataFault)
    def invalid(error):
        return jsonify(code=error.code, detail=str(error)), 413 if error.code == "SIZE" else 422

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(code="SIZE", detail="文件超过 256 KiB"), 413

    @app.get("/health")
    def health():
        return {"status": "ok", "rules": VERSION}

    @app.get("/")
    @app.get("/desk/<stage>")
    def desk(stage="verdicts"):
        if stage not in STAGES:
            abort(404)
        key = request.args.get("run")
        data = batch(key) if key else run_once(history(), raw_sample("yard"))[0]
        selected = request.args.get("strand")
        records = data["判验"]
        chosen = next(
            (row for row in records if f"{row['梁号']}/{row['钢束']}" == selected),
            records[0] if records else None,
        )
        sides = {
            r["端位"]: r
            for r in data["补偿记录"]
            if chosen and (r["梁号"], r["钢束"]) == (chosen["梁号"], chosen["钢束"])
        }
        return render_template(
            f"{stage}.html",
            stages=STAGES,
            active=stage,
            labels=SAMPLES,
            current=request.args.get("sample", "yard"),
            reused=request.args.get("reused") == "1",
            sections=PAGE_SECTIONS[stage],
            run=data,
            meta=data["清单"],
            strand=chosen,
            sides=sides,
            recent=history().recent() if stage == "runs" else [],
        )

    @app.get("/api/runs")
    def recent():
        return jsonify(history().recent())

    @app.post("/api/runs")
    def inspect():
        form = request.get_json(silent=True) if request.is_json else request.form
        if not hasattr(form, "get"):
            raise DataFault("REQUEST", "提交样例名或上传记录")
        sample, stage = form.get("sample", "yard"), form.get("stage", "verdicts")
        if not isinstance(stage, str) or stage not in STAGES:
            raise DataFault("STAGE", "业务页不存在")
        file = request.files.get("file")
        source = file.read(MATCH_LIMIT + 1) if file and file.filename else raw_sample(sample)
        result, reused = run_once(history(), source)
        key = result["清单"]["编号"]
        return jsonify(
            id=key,
            reused=reused,
            balance=result["读数勾稽"],
            verdicts=result["判验"],
            next=url_for("desk", stage=stage, run=key, sample=sample, reused="1" if reused else None),
        ), 200 if reused else 201

    @app.get("/api/export/<key>")
    def export(key):
        result = jsonify(batch(key))
        result.headers.set("Content-Disposition", "attachment", filename=f"stretch-{key}.json")
        return result

    return app
