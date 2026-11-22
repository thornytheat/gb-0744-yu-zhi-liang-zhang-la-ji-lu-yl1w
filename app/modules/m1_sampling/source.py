import json

from app.config import MATCH_LIMIT
from app.types import DataFault


def load(data):
    if len(data) > MATCH_LIMIT:
        raise DataFault("SIZE", "文件超过 256 KiB")
    try:
        result = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique)
    except (ValueError, RecursionError) as exc:
        raise DataFault("FILE", "检查 JSON 文件与 UTF-8 编码") from exc
    if not isinstance(result, dict) or set(result) != {"readings", "calibrations", "targets"}:
        raise DataFault("FIELDS", "需要读数、标定和钢束三份记录")
    if any(not isinstance(rows, list) or len(rows) > 1200 for rows in result.values()):
        raise DataFault("LIMIT", "每组记录最多 1200 行")
    return result


def unique(values):
    record = {}
    for key, value in values:
        if key in record:
            raise ValueError("字段重复")
        record[key] = value
    return record
