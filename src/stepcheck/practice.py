"""Practice items, generated from templates and verified before they are ever shown.

Each skill targets one classic misconception. A generated item is kept only if the
CAS confirms its stated answer, so the assistant cannot read out a broken exercise.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

from .core import check_answer


@dataclass
class Item:
    skill: str
    problem: str
    answer: str
    prompt: str

    def public(self) -> dict:
        """What the learner may hear: never the answer."""
        d = asdict(self)
        d.pop("answer")
        return d


SKILLS = {
    "two_step_equations": "Solve two-step equations like 3x + 5 = 20",
    "moving_terms": "Move terms across the equals sign, e.g. 12 - x = 5",
    "distribute_then_solve": "Distribute, then solve, e.g. 4(x - 3) = 20",
    "negative_parentheses": "Handle a minus in front of parentheses, e.g. 9 - (x + 2) = 3",
    "adding_fractions": "Add fractions with different denominators",
    "square_of_a_sum": "Expand (x + a)^2",
    "factor_quadratics": "Solve x^2 + bx + c = 0 by factoring",
}


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    while True:
        v = rng.randint(lo, hi)
        if v != 0:
            return v


def _make(skill: str, rng: random.Random) -> Item:
    if skill == "two_step_equations":
        a, x, b = rng.randint(2, 9), rng.randint(-6, 12), _nz(rng, -15, 15)
        return Item(skill, f"{a}x {'+' if b > 0 else '-'} {abs(b)} = {a * x + b}", f"x = {x}",
                    "Solve for x.")
    if skill == "moving_terms":
        c, x = rng.randint(8, 20), rng.randint(-5, 15)
        return Item(skill, f"{c} - x = {c - x}", f"x = {x}", "Solve for x.")
    if skill == "distribute_then_solve":
        a, b, x = rng.randint(2, 7), _nz(rng, -6, 6), rng.randint(-4, 10)
        return Item(skill, f"{a}(x {'+' if b > 0 else '-'} {abs(b)}) = {a * (x + b)}", f"x = {x}",
                    "Solve for x. Show the line after you distribute.")
    if skill == "negative_parentheses":
        c, b, x = rng.randint(10, 25), rng.randint(1, 9), rng.randint(-3, 12)
        return Item(skill, f"{c} - (x + {b}) = {c - x - b}", f"x = {x}", "Solve for x.")
    if skill == "adding_fractions":
        d1, d2 = rng.sample([2, 3, 4, 5, 6, 8, 10], 2)
        n1, n2 = rng.randint(1, d1 - 1), rng.randint(1, d2 - 1)
        from fractions import Fraction

        s = Fraction(n1, d1) + Fraction(n2, d2)
        return Item(skill, f"{n1}/{d1} + {n2}/{d2}", f"{s.numerator}/{s.denominator}" if s.denominator != 1 else str(s.numerator),
                    "Add and simplify.")
    if skill == "square_of_a_sum":
        a = _nz(rng, -9, 9)
        return Item(skill, f"(x {'+' if a > 0 else '-'} {abs(a)})^2", f"x^2 {'+' if a > 0 else '-'} {2 * abs(a)}x + {a * a}",
                    "Expand.")
    if skill == "factor_quadratics":
        r1, r2 = rng.sample([v for v in range(-7, 8) if v != 0], 2)
        b, c = -(r1 + r2), r1 * r2
        bs = "" if b == 0 else f" {'+' if b > 0 else '-'} {abs(b) if abs(b) != 1 else ''}x"
        return Item(skill, f"x^2{bs} {'+' if c > 0 else '-'} {abs(c)} = 0", f"x = {r1} or x = {r2}",
                    "Solve by factoring. There are two answers.")
    raise KeyError(skill)


def generate(skill: str, seed: int | None = None) -> Item:
    rng = random.Random(seed)
    for _ in range(50):
        item = _make(skill, rng)
        if check_answer(item.problem, item.answer).ok:  # verified before use
            return item
    raise RuntimeError(f"could not generate a verified item for {skill}")
