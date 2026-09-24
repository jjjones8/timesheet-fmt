"""Parse the many ways people write a work-hours range into a clean HH:MM-HH:MM string.

Real timesheets come from spreadsheets, chat messages, and old paper forms, so
the same shift shows up as "9-5", "9:00am-5:00pm", "0900-1730", or "9 to 5:30".
This module turns any of those into one canonical shape.
"""

import re
from datetime import time

_MERIDIEM_RE = re.compile(r"\s*([ap])\.?m\.?$")
_HOUR_MINUTE_RE = re.compile(r"^(\d{1,2})[:.,](\d{2})$")
_MILITARY_RE = re.compile(r"^(\d{3,4})$")
_HOUR_ONLY_RE = re.compile(r"^(\d{1,2})$")
_SEPARATOR_RE = re.compile(r"\s*(?:-|–|—|~|\bto\b|\buntil\b)\s*", re.IGNORECASE)

_WEEKDAY_NAMES = {
    "mon": "Monday", "monday": "Monday",
    "tue": "Tuesday", "tues": "Tuesday", "tuesday": "Tuesday",
    "wed": "Wednesday", "weds": "Wednesday", "wednesday": "Wednesday",
    "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday", "thursday": "Thursday",
    "fri": "Friday", "friday": "Friday",
    "sat": "Saturday", "saturday": "Saturday",
    "sun": "Sunday", "sunday": "Sunday",
}
# A leading label followed by required whitespace (an optional comma may sit
# between). This has to require trailing whitespace so it never eats part of
# a bare range like "0900-1730" or "22:00-06:00", which have no space at all.
_PREFIX_RE = re.compile(r"^([A-Za-z]{3,9}|\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{4}-\d{2}-\d{2})\s*,?\s+")


class ParseError(ValueError):
    """Raised when a time or range can't be made sense of."""


def _parse_raw(raw):
    """Split raw text into (hour, minute, meridiem). meridiem is 'a', 'p', or None.

    Hour/minute are returned exactly as written; the caller decides how to
    resolve a bare hour like "9" once it knows whether a neighbouring value
    in a range supplied an am/pm marker.
    """
    text = raw.strip().lower()
    if not text:
        raise ParseError("empty time")

    meridiem = None
    match = _MERIDIEM_RE.search(text)
    if match:
        meridiem = match.group(1)
        text = text[: match.start()].strip()

    if match := _HOUR_MINUTE_RE.match(text):
        hour, minute = int(match.group(1)), int(match.group(2))
    elif match := _MILITARY_RE.match(text):
        digits = match.group(1)
        hour, minute = int(digits[:-2]), int(digits[-2:])
    elif match := _HOUR_ONLY_RE.match(text):
        hour, minute = int(match.group(1)), 0
    else:
        raise ParseError(f"can't read a time out of {raw!r}")

    if not (0 <= minute < 60):
        raise ParseError(f"minute out of range in {raw!r}")
    if meridiem is not None and not (1 <= hour <= 12):
        raise ParseError(f"hour out of range for am/pm in {raw!r}")
    if meridiem is None and not (0 <= hour < 24):
        raise ParseError(f"hour out of range in {raw!r}")

    return hour, minute, meridiem


def _resolve(hour, minute, meridiem):
    if meridiem == "p" and hour != 12:
        hour += 12
    elif meridiem == "a" and hour == 12:
        hour = 0
    return time(hour, minute)


def parse_time(raw):
    """Parse a single time like "9", "9:30am", "0930", or "9.30pm"."""
    hour, minute, meridiem = _parse_raw(raw)
    return _resolve(hour, minute, meridiem)


def parse_range(raw):
    """Parse a "start-end" range, inferring missing am/pm markers.

    Two situations come up constantly on real timesheets:

    * one side has a marker and the other doesn't ("9-5pm") - the bare side
      borrows the marker, then flips it if that would put the start at or
      after the end.
    * neither side has a marker ("9-5") - if reading both literally would
      put the end at or before the start, and both hours are plain
      12-hour values (1-12), assume the end is pm.
    * neither side has a marker and at least one hour is outside 1-12
      ("22:00-06:00", "2200-0600") - the range is already unambiguous in
      24-hour terms, so it's left as-is and treated as an overnight shift
      that crosses midnight rather than forced into the same day.
    """
    parts = _SEPARATOR_RE.split(raw.strip(), maxsplit=1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise ParseError(f"couldn't find a start/end separator in {raw!r}")

    start_raw, end_raw = parts
    start_hour, start_minute, start_meridiem = _parse_raw(start_raw)
    end_hour, end_minute, end_meridiem = _parse_raw(end_raw)

    borrowed = start_meridiem is None and end_meridiem is not None
    if borrowed:
        start_meridiem = end_meridiem

    start = _resolve(start_hour, start_minute, start_meridiem)
    end = _resolve(end_hour, end_minute, end_meridiem)

    if borrowed and start >= end:
        flipped = "a" if start_meridiem == "p" else "p"
        start = _resolve(start_hour, start_minute, flipped)
    elif (
        start_meridiem is None
        and end_meridiem is None
        and start >= end
        and 1 <= start_hour <= 12
        and 1 <= end_hour <= 12
    ):
        end = _resolve(end_hour, end_minute, "p")
    # else: start >= end with no marker to flip and an hour outside 1-12
    # (e.g. "22:00-06:00") - that's already an unambiguous 24-hour range,
    # so leave it alone and let it stand as an overnight shift.

    return start, end


def format_range(start, end):
    """Render two datetime.time values as "HH:MM-HH:MM"."""
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def normalize_line(raw):
    """Parse then re-render a messy range in one step."""
    return format_range(*parse_range(raw))


def _canonical_label(label):
    """Turn a matched prefix into its canonical form, or None if it's bogus.

    The prefix regex is deliberately loose (any 3-9 letter word, any
    slash/dash-separated digits) so this is where real validation happens -
    a weekday must be a real weekday, and a numeric date must have a month
    and day in range.
    """
    lower = label.lower()
    if lower in _WEEKDAY_NAMES:
        return _WEEKDAY_NAMES[lower]

    if "/" in label:
        bits = label.split("/")
        if len(bits) not in (2, 3):
            return None
        month, day = int(bits[0]), int(bits[1])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return label
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", label):
        _, month, day = (int(part) for part in label.split("-"))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return label
        return None

    return None


def split_entry_prefix(raw):
    """Split a leading day-of-week or date label off an entry, if present.

    Returns (label, remainder). "Mon 9-5", "Monday, 9-5", "3/14 9-5", and
    "2026-03-14 9-5" all yield a label and a bare range as the remainder.
    Anything else - including a range with no prefix at all - yields
    (None, raw.strip()) so callers can hand the remainder straight to
    parse_range.
    """
    text = raw.strip()
    match = _PREFIX_RE.match(text)
    if not match:
        return None, text
    label = _canonical_label(match.group(1))
    if label is None:
        return None, text
    return label, text[match.end():].strip()


def parse_entry(raw):
    """Parse an entry that may start with a day-of-week or date label.

    Returns (label, start, end); label is None when the entry is a bare
    range with no prefix.
    """
    label, remainder = split_entry_prefix(raw)
    start, end = parse_range(remainder)
    return label, start, end


def normalize_entry(raw):
    """Parse then re-render a messy entry, keeping any leading day/date label."""
    label, start, end = parse_entry(raw)
    range_str = format_range(start, end)
    return f"{label} {range_str}" if label else range_str
