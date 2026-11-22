def evaluate(readings, anchor):
    low, next_low, peak = readings
    forces = [row["kn"] for row in readings]
    strokes = [row["stroke"] for row in readings]
    if not forces[0] < forces[1] < forces[2] or not strokes[0] < strokes[1] < strokes[2]:
        return {"原因码": "REVERSED"}
    intercept = low["stroke"] - low["kn"] * (next_low["stroke"] - low["stroke"]) / (
        next_low["kn"] - low["kn"]
    )
    effective = peak["stroke"] - intercept - anchor
    if effective <= 0:
        return {"原因码": "NO_EXTENSION"}
    return {"峰值毫米": peak["stroke"], "零点毫米": intercept, "回缩毫米": anchor, "有效毫米": effective}
