from datetime import date

from app.stages import code, decimal
from app.types import DataFault


def parse_targets(records):
    targets = {}
    for row in records:
        try:
            key = code(row, "beam"), code(row, "strand")
            target = {
                "day": date.fromisoformat(row["day"]),
                "design": decimal(row["design_kn"]),
                "theory": {side: decimal(row[f"{side}_mm"]) for side in ("L", "R")},
                "loss": {side: decimal(row[f"{side}_anchor"]) for side in ("L", "R")},
            }
            if (
                key in targets
                or target["design"] <= 0
                or min(target["theory"].values()) <= 0
                or min(target["loss"].values()) < 0
            ):
                raise ValueError("钢束重复或设计值非法")
        except (TypeError, ValueError, KeyError) as exc:
            raise DataFault("TARGET", "钢束设计字段无效或重复") from exc
        targets[key] = target
    return targets
