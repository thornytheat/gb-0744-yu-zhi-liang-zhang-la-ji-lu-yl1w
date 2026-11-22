from app.modules.m4_elongation.formula import evaluate


def compensate(aligned, targets):
    result = {}
    for (beam, strand), target in targets.items():
        for end in ("L", "R"):
            key = beam, strand, end
            history = [aligned.get((*key, level)) for level in (20, 40, 100)]
            lines = [row["line"] for row in history if row is not None]
            detail = (
                {"原因码": "MISSING_LEVEL"} if len(lines) < 3 else evaluate(history, target["loss"][end])
            )
            result[key] = {**detail, "源行": lines}
    return result
