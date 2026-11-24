from datetime import date

import jdatetime


MONTH_NAMES = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)


def persian_month_title(start_date: str, end_date: str) -> str:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    start_persian = jdatetime.date.fromgregorian(date=start)
    end_persian = jdatetime.date.fromgregorian(date=end)

    if start.day == 1:
        month = MONTH_NAMES[start_persian.month - 1]
        if end.day <= 15:
            return f"گزارش فنی نیمه اول ماه {month}"

    if start.day == 16:
        month = MONTH_NAMES[start_persian.month - 1]
        if end.month == start.month:
            return f"گزارش فنی نیمه دوم ماه {month}"

    if start_persian.year == end_persian.year and start_persian.month == end_persian.month:
        month = MONTH_NAMES[start_persian.month - 1]
        return f"گزارش فنی بازه انتخابی {start_persian.day} تا {end_persian.day} {month}"

    if start_persian.year == end_persian.year:
        start_month = MONTH_NAMES[start_persian.month - 1]
        end_month = MONTH_NAMES[end_persian.month - 1]
        return f"گزارش فنی از {start_persian.day} {start_month} تا {end_persian.day} {end_month}"

    return "گزارش فنی بازه انتخابی"


def persian_to_gregorian(value: str) -> str:
    year, month, day = (int(part) for part in value.split("-"))
    return jdatetime.date(year, month, day).togregorian().isoformat()


def gregorian_to_persian(value: str) -> dict:
    gregorian = date.fromisoformat(value)
    persian = jdatetime.date.fromgregorian(date=gregorian)
    return {"year": persian.year, "month": persian.month, "day": persian.day}


def title_filename(title: str) -> str:
    cleaned = title.strip()
    for character in '<>:"/\\|?*':
        cleaned = cleaned.replace(character, "")
    return f"{cleaned}.docx"
