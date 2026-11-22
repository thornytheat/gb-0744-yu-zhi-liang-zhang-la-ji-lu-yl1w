import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter

from app.config import VERSION
from app.modules.m1_sampling.service import accept
from app.modules.m1_sampling.source import load
from app.modules.m2_calibration.registry import calibrations
from app.modules.m2_calibration.service import convert
from app.modules.m3_alignment.service import align
from app.modules.m3_alignment.targets import parse_targets
from app.modules.m4_elongation.service import compensate
from app.modules.m5_verdicts.service import classify
from app.modules.m6_reconcile.service import ledger
from app.stages import label


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serialized(value):
    if isinstance(value, Decimal):
        return label(value)
    return value.isoformat()


def calculate(data):
    began = perf_counter()
    payload = load(data)
    records, first_issues, duplicates = accept(payload["readings"])
    registry = calibrations(payload["calibrations"])
    targets = parse_targets(payload["targets"])
    forces, calibration_issues = convert(records, registry)
    aligned, force_issues = align(forces, targets)
    measurements = compensate(aligned, targets)
    verdicts = classify(targets, measurements)
    issues = sorted(first_issues + calibration_issues + force_issues, key=lambda row: row["源行"])
    conservation, beams = ledger(len(payload["readings"]), aligned, issues, duplicates, verdicts)
    output = {
        "清单": {
            "编号": digest(VERSION.encode() + data)[:24],
            "摘要": digest(data),
            "规则": VERSION,
            "计算时间": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "时区": "Asia/Shanghai",
            "耗时毫秒": round((perf_counter() - began) * 1000),
        },
        "原始采信": [
            {
                "源行": r["line"],
                "梁号": r["beam"],
                "钢束": r["strand"],
                "端位": r["end"],
                "位移毫米": r["stroke"],
                "读数": r["force"],
                "单位": r["unit"],
            }
            for r in records
        ],
        "标定依据": [
            {
                "千斤顶": r["jack"],
                "版本": r["revision"],
                "生效日": r["start"],
                "截止日": r["end"],
                "斜率": r["slope"],
                "截距": r["offset"],
            }
            for r in registry
        ],
        "力级记录": [
            {
                "源行": r["line"],
                "梁号": r["beam"],
                "钢束": r["strand"],
                "端位": r["end"],
                "力级%": r["level"],
                "载荷千牛": r["kn"],
                "采信来源": r["revision"],
            }
            for r in aligned.values()
        ],
        "补偿记录": [
            {"梁号": key[0], "钢束": key[1], "端位": key[2], **r} for key, r in measurements.items()
        ],
        "判验": verdicts,
        "读数勾稽": conservation,
        "梁号勾稽": beams,
        "隔离": issues,
        "重复": duplicates,
    }
    return json.loads(json.dumps(output, default=serialized, ensure_ascii=False))


def run_once(history, data):
    key = digest(VERSION.encode() + data)[:24]
    existing = history.find(key)
    return (existing, True) if existing is not None else history.publish(key, calculate(data))
