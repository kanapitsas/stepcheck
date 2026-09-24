"""Hint ladder: from a gentle nudge to the next verified line, never straight to the answer."""

from __future__ import annotations

import sympy as sp

from .core import equivalent_equations, exclusions, parse_equation, pretty, variables


def _products_with_sum(e: sp.Expr, x: sp.Symbol) -> str | None:
    """'number' for 3(x - 2), 'minus' for -(x + 3), None if the side has no such parentheses."""
    for t in sp.Add.make_args(e):
        factors = sp.Mul.make_args(t)
        if any(isinstance(f, sp.Add) and f.has(x) for f in factors):
            if any(f.is_Integer and f not in (1, -1) for f in factors):
                return "number"
            if any(f == -1 for f in factors):
                return "minus"
    return None


def next_move(line: str) -> tuple[str, str]:
    """Return (what to do, the resulting line) for a linear equation in one unknown.
    The returned line is verified equivalent, on the same domain, and different from `line`."""
    if exclusions(line):
        raise ValueError("Hints don't cover equations with the unknown in a denominator yet. "
                         "Remember the unknown can't make a denominator zero.")
    eq = parse_equation(line)
    vs = variables(eq)
    if len(vs) != 1:
        raise ValueError("Hints cover equations in one unknown.")
    x = vs[0]
    L, R = eq.lhs, eq.rhs
    diff = sp.expand(L - R)
    if not diff.is_polynomial(x) or sp.Poly(diff, x).degree() != 1:
        raise ValueError("Hints cover linear equations like 3x + 5 = 20.")
    from .core import _expr_from_text_raw  # the written form, before SymPy distributes

    raw_sides = [_expr_from_text_raw(s) for s in line.split("=")]
    n = x.name
    kinds = {_products_with_sum(s, x) for s in raw_sides} - {None}
    if kinds:
        action = ("Remove the parentheses first: multiply the number in front by every term inside."
                  if "number" in kinds else
                  "Remove the parentheses first: the minus in front changes the sign of every term inside.")
        new = sp.Eq(sp.expand(L), sp.expand(R), evaluate=False)
    else:
        L, R = sp.expand(L), sp.expand(R)
        x_left = [t for t in sp.Add.make_args(L) if t.has(x)]
        x_right = [t for t in sp.Add.make_args(R) if t.has(x)]
        const_left = sp.Add(*[t for t in sp.Add.make_args(L) if not t.has(x)])
        if x_left and x_right:
            t = x_right[0]
            c, m = t.as_coeff_Mul()
            action = f"Gather the {n} terms on one side: {'subtract' if c > 0 else 'add'} {pretty(abs(c) * m)} on both sides."
            new = sp.Eq(sp.expand(L - t), sp.expand(R - t), evaluate=False)
        elif not x_left:
            action = f"Swap the two sides so that {n} is on the left."
            new = sp.Eq(R, L, evaluate=False)
        elif const_left != 0:
            action = f"Undo the {pretty(abs(const_left))}: {'subtract' if const_left > 0 else 'add'} {pretty(abs(const_left))} on both sides."
            new = sp.Eq(sp.expand(L - const_left), sp.expand(R - const_left), evaluate=False)
        else:
            coeff = sp.Poly(L, x).coeffs()[0]
            if coeff == 1:
                return f"{n} is already alone: read off the answer.", pretty(eq)
            if coeff.is_Rational and coeff.p in (1, -1) and coeff.q != 1:
                k = sp.Integer(coeff.q) * coeff.p
                action = f"{n} is divided by {pretty(abs(k))}: multiply both sides by {pretty(k)}."
            else:
                action = f"{n} is multiplied by {pretty(coeff)}: divide both sides by {pretty(coeff)}."
            new = sp.Eq(sp.expand(L / coeff), sp.expand(R / coeff), evaluate=False)
    new_line = pretty(new)
    if new_line.replace(" ", "") == line.replace(" ", "") or not equivalent_equations(eq, new):
        raise ValueError("I can't find a safe next step for this line.")
    return action, new_line


def hint(line: str, level: int) -> dict:
    """level 1: which idea; level 2: the exact operation; level 3: the next line (verified)."""
    action, new_line = next_move(line)
    if level <= 1:
        return {"level": 1, "hint": action.split(":")[0].rstrip(".") + ".", "more_available": True}
    if level == 2:
        return {"level": 2, "hint": action, "more_available": True}
    return {"level": 3, "hint": f"{action} That gives: {new_line}", "next_line": new_line, "more_available": False}
