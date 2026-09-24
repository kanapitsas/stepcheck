"""Soundness evaluation, independent of the mistake detectors.

For generated homework items we take (a) correct next lines produced by the hint engine and
(b) wrong lines produced by random *textual* perturbations of those correct lines (flip a
sign, change a digit, drop a term). The perturbation code shares nothing with the diagnosis
code, so the diagnosis cannot grade its own homework.

Measured: correct lines rejected (must be 0), wrong lines accepted (must be 0), and the share
of wrong lines for which Stepwise names a specific misconception.
Run: uv run python eval/soundness.py 400 11   (the README figures)
"""
import random
import re
from collections import Counter

from stepcheck.practice import generate
from stepcheck.core import ParseError, check_step, equivalent_equations, parse_equation
from stepcheck.hints import next_move

SKILLS = ["two_step_equations", "moving_terms", "distribute_then_solve", "negative_parentheses"]


def perturb(line: str, rng: random.Random) -> str:
    kind = rng.choice(["sign", "digit", "drop"])
    if kind == "sign":
        spots = [m.start() for m in re.finditer(r"[+-]", line)]
        if spots:
            i = rng.choice(spots)
            return line[:i] + ("-" if line[i] == "+" else "+") + line[i + 1:]
    if kind == "digit":
        spots = [m.start() for m in re.finditer(r"\d", line)]
        if spots:
            i = rng.choice(spots)
            return line[:i] + str((int(line[i]) + rng.randint(1, 8)) % 10) + line[i + 1:]
    lhs, rhs = line.split("=")
    terms = re.split(r"(?=[+-])", lhs.replace(" ", ""))
    if len(terms) > 1:
        terms.pop(rng.randrange(len(terms)))
        return "".join(terms) + " = " + rhs.strip()
    return line.replace("=", "= 1 +")


def main(n_items: int = 60, seed: int = 7):
    rng = random.Random(seed)
    stats = Counter()
    for k in range(n_items):
        item = generate(SKILLS[k % len(SKILLS)], seed=seed * 1000 + k)
        line = item.problem
        for _ in range(4):
            _, nxt = next_move(line)
            if nxt == line:
                break
            v = check_step(line, nxt)
            stats["correct_lines"] += 1
            stats["correct_rejected"] += not v.ok
            bad = perturb(nxt, rng)
            try:
                truly_wrong = not equivalent_equations(parse_equation(line), parse_equation(bad))
            except ParseError:
                truly_wrong = False
            if truly_wrong:
                w = check_step(line, bad)
                stats["wrong_lines"] += 1
                stats["wrong_accepted"] += w.ok
                stats["wrong_diagnosed"] += w.diagnosis is not None
                if w.diagnosis:
                    stats["code:" + w.diagnosis.code] += 1
            line = nxt
    s = stats
    print(f"correct lines checked : {s['correct_lines']}  rejected: {s['correct_rejected']}")
    print(f"wrong lines checked   : {s['wrong_lines']}  accepted: {s['wrong_accepted']}")
    print(f"wrong lines with a named misconception: {s['wrong_diagnosed']} "
          f"({100 * s['wrong_diagnosed'] / max(1, s['wrong_lines']):.0f} %)")
    for key, v in sorted(s.items()):
        if key.startswith("code:"):
            print(f"   {key[5:]:24} {v}")
    return s


if __name__ == "__main__":
    import sys

    main(*(int(a) for a in sys.argv[1:3]))  # README figures: 400 11
