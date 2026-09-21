import json
from datetime import datetime, timedelta
from typing import Any


def safe_float(text: str) -> float | None:
    try:
        return float(text.replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def safe_int(text: str) -> int | None:
    try:
        return int(float(text.replace(",", ".").strip()))
    except (ValueError, AttributeError):
        return None


def parse_hhmm(text: str) -> str | None:
    try:
        value = datetime.strptime(text.strip(), "%H:%M").time()
        return value.strftime("%H:%M")
    except ValueError:
        return None


def sleep_duration_minutes(start: str, end: str) -> int:
    try:
        start_time = datetime.strptime(start, "%H:%M")
        end_time = datetime.strptime(end, "%H:%M")
        if end_time <= start_time:
            end_time = end_time + timedelta(days=1)
        return max(0, int((end_time - start_time).total_seconds() // 60))
    except ValueError:
        return 0


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def fmt_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"
