"""Command line: check a line of working, a final answer, or ask for a hint.

    stepcheck step "3(x - 2) = 12" "3x - 2 = 12"
    stepcheck answer "x^2 = 9" "x = 3 or x = -3"
    stepcheck hint "2x + 4 = 10" --level 2 --lang fr
"""

from __future__ import annotations

import argparse
import json
import sys

from .core import ParseError, check_answer, check_step
from .hints import hint
from .i18n import localize


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="stepcheck", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("step", help="is NEW a valid next line after PREVIOUS?")
    s.add_argument("previous")
    s.add_argument("new")
    a = sub.add_parser("answer", help="is ANSWER a correct final answer to PROBLEM?")
    a.add_argument("problem")
    a.add_argument("answer")
    h = sub.add_parser("hint", help="a hint for the current LINE of a linear equation")
    h.add_argument("line")
    h.add_argument("--level", type=int, default=1, choices=[1, 2, 3])
    for p in (s, a, h):
        p.add_argument("--lang", default="en", choices=["en", "fr"])
    args = ap.parse_args(argv)
    try:
        if args.cmd == "step":
            out = check_step(args.previous, args.new).as_dict()
        elif args.cmd == "answer":
            out = check_answer(args.problem, args.answer).as_dict()
        else:
            out = hint(args.line, args.level)
    except (ParseError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(localize(out, args.lang), ensure_ascii=False, indent=2))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
