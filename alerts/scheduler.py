import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

BRAZIL_HOLIDAYS_FIXED = [
    (1, 1),
    (4, 21),
    (5, 1),
    (9, 7),
    (10, 12),
    (11, 2),
    (11, 15),
    (12, 25),
]


def _easter(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_holidays(year: int) -> set[date]:
    holidays = set()
    for month, day in BRAZIL_HOLIDAYS_FIXED:
        holidays.add(date(year, month, day))
    easter_date = _easter(year)
    holidays.add(easter_date - timedelta(days=47))
    holidays.add(easter_date - timedelta(days=2))
    holidays.add(easter_date)
    holidays.add(easter_date + timedelta(days=60))
    return holidays


def is_business_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d not in get_holidays(d.year)


def get_first_business_day(year: int, month: int) -> date:
    d = date(year, month, 1)
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def get_mid_business_day(year: int, month: int) -> date:
    d = date(year, month, 15)
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def should_send_alert_today() -> bool:
    today = date.today()
    first = get_first_business_day(today.year, today.month)
    mid = get_mid_business_day(today.year, today.month)
    is_alert_day = today == first or today == mid
    if is_alert_day:
        logger.info("Alert day: %s (first=%s, mid=%s)", today, first, mid)
    return is_alert_day
