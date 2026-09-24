"""Command-line front end: one messy range per line, in on argv or stdin."""

import argparse
import sys

from .normalize import ParseError, normalize_entry


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="timesheet-fmt",
        description="Normalize messy time ranges into HH:MM-HH:MM",
    )
    parser.add_argument(
        "entries",
        nargs="*",
        help=(
            "time ranges to normalize, e.g. '9-5pm' or 'Mon 9-5pm' "
            "(reads stdin if omitted)"
        ),
    )
    args = parser.parse_args(argv)

    lines = args.entries if args.entries else [line.rstrip("\n") for line in sys.stdin]

    exit_code = 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            print(normalize_entry(raw))
        except ParseError as exc:
            print(f"skip: {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
