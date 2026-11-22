from datetime import date

from app.stages import code, decimal
from app.types import DataFault


def calibrations(rows):
    entries, seen = [], set()
    for row in rows:
        try:
            jack, rev = code(row, "jack"), code(row, "revision")
            start, end = date.fromisoformat(row["from"]), date.fromisoformat(row["until"])
            slope, offset = decimal(row["slope"]), decimal(row["offset"])
            if start >= end or slope <= 0 or (jack, rev) in seen:
                raise ValueError("标定区间、斜率或版本无效")
        except (TypeError, ValueError, KeyError) as exc:
            raise DataFault("CALIBRATION", "标定证书字段无效") from exc
        seen.add((jack, rev))
        entries.append(
            {"jack": jack, "revision": rev, "start": start, "end": end, "slope": slope, "offset": offset}
        )
    return entries


def applicable(entries, jack, day):
    return [c for c in entries if c["jack"] == jack and c["start"] <= day < c["end"]]
