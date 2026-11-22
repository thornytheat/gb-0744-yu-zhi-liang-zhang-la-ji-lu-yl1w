class DataFault(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def evidence(row, code):
    return {
        "梁号": row.get("beam", ""),
        "钢束": row.get("strand", ""),
        "端位": row.get("end", ""),
        "源行": row["line"],
        "原因码": code,
    }
