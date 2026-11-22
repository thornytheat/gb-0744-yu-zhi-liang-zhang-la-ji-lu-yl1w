from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
VERSION = "beam-1.0"
STAGES = {
    "sampling": "读数采信",
    "calibration": "千斤顶标定",
    "alignment": "力级对齐",
    "elongation": "伸长补偿",
    "verdicts": "分级判验",
    "reconcile": "梁号勾稽",
    "runs": "工艺复算",
}
MATCH_LIMIT = 256 * 1024
SAMPLES = {"yard": "夜班原始记录", "checked": "对照钢束"}
