# timesheet-fmt

Every timesheet I've had to reconcile has entries copied from three different
places: a spreadsheet using "0900-1730", a Slack message saying "9-5pm", and
someone's handwritten "9 to 5:30". They all mean the same thing but nothing
downstream can compare them until they're in one shape. This is a small
library and CLI that takes any of those and turns it into `HH:MM-HH:MM`.

## Usage

As a library:

```python
from timesheet_fmt import normalize_line

normalize_line("9-5pm")        # "09:00-17:00"
normalize_line("0900-1730")    # "09:00-17:30"
normalize_line("9 to 5:30")    # "09:00-17:30"
normalize_line("12am-1am")     # "00:00-01:00"
```

`normalize_line` is a thin wrapper over `parse_range` (which returns a pair of
`datetime.time`) and `format_range` (which renders them back to text), so you
can use either half on its own if you need the parsed values rather than a
string.

From the command line:

```
$ python -m timesheet_fmt.cli "9-5pm" "0900-1730"
09:00-17:00
09:00-17:30

$ echo "9 to 5:30" | python -m timesheet_fmt.cli
09:00-17:30
```

Anything that can't be parsed is skipped with a message on stderr rather than
crashing the whole batch.

## Install

No third-party dependencies, standard library only.

```
pip install -e .
python -m unittest discover
```

## What it handles today

- `-`, `–`, `—`, `~`, `to`, `until` as range separators
- `:`, `.`, `,` as hour/minute separators, plus bare military digits (`0930`, `930`)
- am/pm markers in any of `9am`, `9 am`, `9a.m.`
- a missing am/pm on one side of a range, inferred from the other side (`9-5pm` -> `09:00-17:00`)

## What it doesn't handle yet

- overnight shifts where the end time is on the next day (`22:00-06:00`)
- day-of-week or date prefixes on an entry
- computing duration or flagging overlapping entries

See the test table in `tests/test_normalize.py` for the exact cases currently
covered.
