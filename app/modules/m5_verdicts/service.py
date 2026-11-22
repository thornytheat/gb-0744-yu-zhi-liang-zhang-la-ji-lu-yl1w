from decimal import Decimal

END_LIMIT = Decimal("0.10")
TOTAL_LIMIT = Decimal("0.06")


def classify(targets, ends):
    rows = []
    for (beam, strand), target in targets.items():
        pair = [ends[(beam, strand, side)] for side in ("L", "R")]
        intended = [target["theory"][e] for e in ("L", "R")]
        measurements = [end.get("有效毫米") for end in pair]
        reasons = [
            f"{side}-{entry['原因码']}" for side, entry in zip(("L", "R"), pair) if "原因码" in entry
        ]
        total = None
        if reasons:
            status = "待复测"
        else:
            total = sum(measurements)
            for expected, actual, side in zip(intended, measurements, ("L", "R")):
                if abs(actual - expected) > expected * END_LIMIT:
                    reasons.append(f"{side}-SIDE_TOLERANCE")
            if abs(total - sum(intended)) > sum(intended) * TOTAL_LIMIT:
                reasons.append("TOTAL_TOLERANCE")
            status = "超限" if reasons else "通过"
        rows.append(
            {
                "梁号": beam,
                "钢束": strand,
                "左理论毫米": intended[0],
                "右理论毫米": intended[1],
                "左有效毫米": measurements[0],
                "右有效毫米": measurements[1],
                "合计毫米": total,
                "判验": status,
                "证据": reasons,
                "源行": pair[0]["源行"] + pair[1]["源行"],
            }
        )
    return rows
