import unittest

from timesheet_fmt import ParseError, normalize_entry, normalize_line, split_entry_prefix

# Each row is (raw input, expected normalized output). Kept as one flat table
# so a new awkward case can be added without touching any test logic.
NORMALIZE_CASES = [
    ("9-5", "09:00-17:00"),
    ("9-5pm", "09:00-17:00"),
    ("9:00am-5:00pm", "09:00-17:00"),
    ("9am-12pm", "09:00-12:00"),
    ("12am-1am", "00:00-01:00"),
    ("12-1", "12:00-13:00"),
    ("0900-1730", "09:00-17:30"),
    ("930-1730", "09:30-17:30"),
    ("9.30-17.45", "09:30-17:45"),
    ("9,30-17,45", "09:30-17:45"),
    ("9 to 5:30", "09:00-17:30"),
    ("9 until 5", "09:00-17:00"),
    ("  9:00   -   17:00  ", "09:00-17:00"),
    ("9:00—17:00", "09:00-17:00"),
    ("9:00–17:00", "09:00-17:00"),
    ("9~17", "09:00-17:00"),
    ("8-4:30pm", "08:00-16:30"),
    ("22:00-06:00", "22:00-06:00"),
    ("2200-0600", "22:00-06:00"),
    ("22-6", "22:00-06:00"),
    ("10pm-6am", "22:00-06:00"),
    ("23:30-07:15", "23:30-07:15"),
]

# Inputs that should be rejected rather than silently misread.
INVALID_CASES = [
    "25:00-5:00",
    "9",
    "abc-5",
    "9:00",
    "13pm-5pm",
    "9:60-17:00",
]

# Entries with a leading day-of-week or date label.
ENTRY_CASES = [
    ("Mon 9-5", "Monday 09:00-17:00"),
    ("mon 9-5", "Monday 09:00-17:00"),
    ("Monday, 9-5pm", "Monday 09:00-17:00"),
    ("Tues 9am-5pm", "Tuesday 09:00-17:00"),
    ("Weds 9-5", "Wednesday 09:00-17:00"),
    ("Thurs 9-5", "Thursday 09:00-17:00"),
    ("Sat 22:00-06:00", "Saturday 22:00-06:00"),
    ("3/14 9-5", "3/14 09:00-17:00"),
    ("3/14/2026 9-5", "3/14/2026 09:00-17:00"),
    ("2026-03-14 9-5", "2026-03-14 09:00-17:00"),
    # no recognizable prefix - falls back to a bare range
    ("9-5", "09:00-17:00"),
]

# Entries whose leading word looks like a prefix but isn't one, so the
# whole string should be handed to the range parser and fail there.
INVALID_ENTRY_CASES = [
    "13/14 9-5",  # month out of range
    "2026-13-14 9-5",  # month out of range
    "Someday 9-5",  # not a real weekday
]


class NormalizeLineTests(unittest.TestCase):
    def test_normalize_cases(self):
        for raw, expected in NORMALIZE_CASES:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_line(raw), expected)

    def test_invalid_cases_raise(self):
        for raw in INVALID_CASES:
            with self.subTest(raw=raw):
                with self.assertRaises(ParseError):
                    normalize_line(raw)


class NormalizeEntryTests(unittest.TestCase):
    def test_entry_cases(self):
        for raw, expected in ENTRY_CASES:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_entry(raw), expected)

    def test_invalid_entry_cases_raise(self):
        for raw in INVALID_ENTRY_CASES:
            with self.subTest(raw=raw):
                with self.assertRaises(ParseError):
                    normalize_entry(raw)

    def test_split_entry_prefix_no_match_returns_stripped_input(self):
        self.assertEqual(split_entry_prefix("  9-5  "), (None, "9-5"))


if __name__ == "__main__":
    unittest.main()
