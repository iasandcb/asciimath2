import argparse
import sys

from .errors import UnsupportedLatexError
from .render import convert


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="asciimath2",
        description="Convert a LaTeX math expression to AsciiMath2 (see SPEC.md).",
    )
    parser.add_argument(
        "latex", nargs="?", help="LaTeX expression. Reads stdin if omitted."
    )
    args = parser.parse_args(argv)

    latex = args.latex if args.latex is not None else sys.stdin.read()
    try:
        print(convert(latex))
    except UnsupportedLatexError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
