from collections import Counter

STATES = ("通过", "待复测", "超限")


def ledger(read_count, aligned, isolated, duplicates, verdicts):
    measurements = {
        "原读数": read_count,
        "对齐": len(aligned),
        "隔离": len(isolated),
        "重复": len(duplicates),
    }
    measurements["行差"] = read_count - len(aligned) - len(isolated) - len(duplicates)
    beams = {}
    for row in verdicts:
        beams.setdefault(row["梁号"], Counter())[row["判验"]] += 1
    lines = [
        {
            "梁号": key,
            "设计钢束": sum(count.values()),
            **{state: count[state] for state in STATES},
            "行差": sum(count.values()) - sum(count[s] for s in STATES),
        }
        for key, count in sorted(beams.items())
    ]
    return measurements, lines
