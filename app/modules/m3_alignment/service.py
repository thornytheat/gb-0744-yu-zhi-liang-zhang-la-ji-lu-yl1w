from decimal import Decimal

from app.stages import group
from app.types import evidence

MAX_FORCE_ERROR = Decimal("0.05")


def align(rows, targets):
    candidates, isolated = [], []
    for row in rows:
        target = targets.get((row["beam"], row["strand"]))
        if target is None or row["day"] != target["day"]:
            isolated.append(evidence(row, "NO_TARGET"))
            continue
        nominal = target["design"] * row["level"] / 100
        if abs(row["kn"] - nominal) > nominal * MAX_FORCE_ERROR:
            isolated.append(evidence(row, "FORCE_TOLERANCE"))
        else:
            candidates.append(row)
    accepted = {}
    for key, values in group(candidates, ["beam", "strand", "end", "level"]).items():
        if len(values) == 1:
            accepted[key] = values[0]
        else:
            isolated.extend(evidence(row, "LEVEL_CONFLICT") for row in values)
    return accepted, isolated
