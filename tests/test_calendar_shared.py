from datetime import date

from calendar_shared import day_square


def _classes(critical=False, extra_classes=()):
    rendered = day_square(date(2026, 4, 1), True, False, [], "/day-url", extra_classes=extra_classes, critical=critical)
    return rendered.attrs["class"]


def test_day_square_has_no_critical_day_class_by_default():
    assert "critical-day" not in _classes().split()


def test_day_square_has_critical_day_class_when_flagged():
    assert "critical-day" in _classes(critical=True).split()


def test_day_square_keeps_extra_classes_alongside_critical_day():
    classes = _classes(critical=True, extra_classes=("some-other-class",)).split()
    assert "some-other-class" in classes and "critical-day" in classes
