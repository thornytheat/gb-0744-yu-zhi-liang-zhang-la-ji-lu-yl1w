from app.modules.m2_calibration.registry import applicable
from app.types import evidence


def convert(readings, registers):
    accepted, issues = [], []
    for row in readings:
        if row["unit"] == "kN":
            accepted.append({**row, "kn": row["force"], "revision": "力传感器"})
            continue
        matched = applicable(registers, row["jack"], row["day"])
        if len(matched) != 1:
            issues.append(evidence(row, "CAL_OVERLAP" if matched else "CAL_MISSING"))
            continue
        version = matched[0]
        force = version["slope"] * row["force"] + version["offset"]
        if force <= 0:
            issues.append(evidence(row, "CAL_NEGATIVE"))
        else:
            accepted.append({**row, "kn": force, "revision": version["revision"]})
    return accepted, issues
