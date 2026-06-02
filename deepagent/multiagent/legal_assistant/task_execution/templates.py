from __future__ import annotations


def select_template(query: str) -> str:
    text = (query or "").lower()
    if "khiếu nại" in text:
        return "don-khieu-nai"
    if "cam kết" in text:
        return "van-ban-cam-ket"
    return "van-ban-chung"
