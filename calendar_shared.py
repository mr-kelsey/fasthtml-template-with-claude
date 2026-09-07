"""Presentation-generic month-grid rendering shared by the family calendar (pages/calendar.py)
and the farm calendar (pages/farm_calendar.py). No family/member concepts live here -- each
calendar builds its own day badges and extra CSS classes and hands them in.
"""

import calendar as cal
from datetime import date, timedelta

from fasthtml import common as fast

WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def month_grid(year, month):
    return cal.Calendar(firstweekday=6).monthdatescalendar(year, month)


def events_by_date(events, grid_start, grid_end):
    "Buckets events whose [start_date, end_date] spans days into a dict keyed by each spanned date."
    by_date = {}
    for event in events:
        event_start = max(date.fromisoformat(event["start_date"]), grid_start)
        event_end = min(date.fromisoformat(event["end_date"]), grid_end)
        current = event_start
        while current <= event_end:
            by_date.setdefault(current, []).append(event)
            current += timedelta(days=1)
    return by_date


def month_nav(year, month, url_fn):
    "url_fn(year, month) builds the link for that month; the caller owns any extra filter state."
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    today = date.today()
    return fast.Div(
        fast.A("< Prev", href=url_fn(prev_year, prev_month)),
        fast.Span(f"{cal.month_name[month]} {year}", cls="month-label"),
        fast.A("Next >", href=url_fn(next_year, next_month)),
        fast.A("Today", href=url_fn(today.year, today.month)),
        cls="month-nav",
    )


def day_square(day_date, in_current_month, is_today, badges, day_url, extra_classes=()):
    "badges is a list of pre-rendered fast.Div elements; day_url is the hx-get target for that day's dialog."
    classes = ["day-square", *extra_classes]
    if not in_current_month:
        classes.append("outside-month")
    if is_today:
        classes.append("today")
    return fast.Div(
        fast.Div(str(day_date.day), cls="day-number"),
        *badges,
        cls=" ".join(classes),
        hx_get=day_url,
        hx_target="#event-dialog-body",
        hx_swap="innerHTML",
        **{"hx-on::after-request": "document.getElementById('event-dialog').showModal()"},
    )


def calendar_grid(weeks, month, today, day_square_fn):
    "day_square_fn(day_date, in_current_month, is_today) -> a rendered day square."
    cells = [fast.Div(label, cls="calendar-weekday") for label in WEEKDAY_LABELS]
    for week in weeks:
        for day_date in week:
            cells.append(day_square_fn(day_date, day_date.month == month, day_date == today))
    return fast.Div(*cells, cls="calendar-grid")
