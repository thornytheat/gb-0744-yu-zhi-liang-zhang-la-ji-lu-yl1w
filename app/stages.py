import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from unicodedata import normalize


def decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("数字需为十进制字符串或整数")
    normalized = normalize("NFKC", str(value)).strip()
    if not re.fullmatch(r"-?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,6})?", normalized):
        raise ValueError("十进制数结构无效")
    try:
        parsed = Decimal(normalized.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("数字无效") from exc
    if abs(parsed) > 10**8:
        raise ValueError("数字超出 10^8")
    return parsed


def code(row, key):
    value = row[key]
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 60:
        raise ValueError(key)
    return value.strip()


def group(rows, keys):
    output = defaultdict(list)
    for row in rows:
        output[tuple(row[key] for key in keys)].append(row)
    return output


def label(number):
    return format(number.quantize(Decimal("0.001")), "f")
