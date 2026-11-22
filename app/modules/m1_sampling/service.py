from datetime import date

from app.stages import code, decimal, group
from app.types import evidence

LEVELS = {20, 40, 100}
END_NAMES = {"左": "L", "右": "R", "L": "L", "R": "R"}


def accept(rows):
    parsed, isolated, duplicates = [], [], []
    for index, raw in enumerate(rows, 1):
        row = {"line": index}
        try:
            row.update(
                id=code(raw, "id"),
                beam=code(raw, "beam"),
                strand=code(raw, "strand"),
                end=END_NAMES[code(raw, "end")],
            )
            row.update(
                day=date.fromisoformat(raw["day"]),
                jack=code(raw, "jack"),
                level=raw["level"],
                unit=code(raw, "unit"),
            )
            aliases = set(raw.keys()) & {"stroke", "extension"}
            if (
                len(aliases) != 1
                or type(row["level"]) is not int
                or row["level"] not in LEVELS
                or row["unit"] not in {"kN", "MPa"}
            ):
                raise ValueError("列或力级无效")
            row["force"] = decimal(raw["force"])
            row["stroke"] = decimal(raw[aliases.pop()])
            displacement_unit = raw.get("displacement_unit", "mm")
            if displacement_unit not in ("mm", "cm") or row["force"] <= 0:
                raise ValueError("计量单位或载荷错误")
            if displacement_unit == "cm":
                row["stroke"] *= 10
        except (TypeError, ValueError, KeyError):
            isolated.append(evidence(row, "BAD_READING"))
            continue
        parsed.append(row)
    unique = []
    for rows_for_id in group(parsed, ["id"]).values():
        first, *remaining = rows_for_id
        first_value = {k: v for k, v in first.items() if k != "line"}
        if any({k: v for k, v in row.items() if k != "line"} != first_value for row in remaining):
            isolated.extend(evidence(row, "ID_CONFLICT") for row in rows_for_id)
        else:
            unique.append(first)
            duplicates.extend(evidence(row, "DUPLICATE") for row in remaining)
    return unique, sorted(isolated, key=lambda row: row["源行"]), duplicates
