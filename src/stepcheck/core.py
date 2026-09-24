"""Verified math core: parsing, equivalence, and diagnosis of common student mistakes.

Every verdict here is computed by a computer algebra system (SymPy). A line is accepted only
with a symbolic proof; numeric substitution is used to reject faster, never to accept.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
# Every single letter is a variable (a learner's "e" or "i" is an unknown, not Euler's number).
_ALLOWED = {name: sp.Symbol(name) for name in "abcdefghijklmnopqrstuvwxyz"}
_ALLOWED.update({"sqrt": sp.sqrt, "pi": sp.pi})
_NAMES = {"sqrt", "pi"}


# Only what parse_expr's own transformations need: no SymPy functions reachable from input.
_GLOBALS = {"Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational, "Symbol": sp.Symbol,
            "Add": sp.Add, "Mul": sp.Mul, "Pow": sp.Pow}


class ParseError(ValueError):
    """Raised when a student's input cannot be read as math."""


class UndefinedError(ParseError):
    """The input is readable but undefined, e.g. a division by zero."""


def _notation(text: str) -> str:
    """How students actually type: unicode signs, √ and ², French decimal comma."""
    t = text.strip()
    t = t.replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/").replace("·", "*")
    t = t.replace("²", "^2").replace("³", "^3")
    t = re.sub(r"√\s*(\d+|[a-z])", r"sqrt(\1)", t)
    t = t.replace("√", "sqrt")
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)  # 1,5 -> 1.5 (a list is written "3, -3" or "3 ; -3")
    return t


def _clean(text: str) -> str:
    t = _notation(text)
    if re.search(r"[^0-9a-zA-Z+\-*/^().=\s]", t):
        raise ParseError(f"unexpected character in {text!r}")
    # homework-sized input only: bounded length, numbers and exponents (no CAS blow-ups)
    if len(t) > 160 or re.search(r"\d{10,}", t) or re.search(r"(\^|\*\*)\s*\(?\s*-?\d{3,}", t):
        raise ParseError(f"{text!r} is larger than homework-sized math")
    t = t.lower()

    def letters(m):  # "xy" -> "x*y"; only sqrt and pi are words
        w = m.group(0)
        if w in _NAMES:
            return w
        if len(w) > 2:  # a word, not a product of unknowns: "true", "factorial"
            raise ParseError(f"{w!r} is not math I can check")
        return "*".join(w)

    t = re.sub(r"[a-z]+", letters, t)
    t = re.sub(r"(\d)\s*(?=[a-z(])", r"\1*", t)  # "0x" must not become a hex literal
    return t


def parse(text: str) -> sp.Expr:
    """Parse one expression. Rational arithmetic is kept exact (1/3 stays 1/3)."""
    t = _clean(text)
    if not t or "=" in t:
        raise ParseError(f"expected an expression, got {text!r}")
    raw = _raw(t, text)
    _check_size(raw, text)
    try:
        expr = parse_expr(t, local_dict=dict(_ALLOWED), global_dict=_GLOBALS,
                          transformations=_TRANSFORMS, evaluate=True)
    except Exception as exc:  # SymPy raises many exception types on bad input
        raise ParseError(f"could not read {text!r}") from exc
    if not isinstance(expr, sp.Expr):
        raise ParseError(f"could not read {text!r} as a number or expression")
    if expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        raise UndefinedError(f"{text!r} is undefined (division by zero)")
    return sp.nsimplify(expr, rational=True) if expr.has(sp.Float) else expr


def _raw(t: str, text: str) -> sp.Expr:
    """Unevaluated parse: cheap, and keeps what evaluation would erase (x^2/x stays a fraction)."""
    try:
        return parse_expr(t, local_dict=dict(_ALLOWED), global_dict=_GLOBALS,
                          transformations=_TRANSFORMS, evaluate=False)
    except Exception as exc:
        raise ParseError(f"could not read {text!r}") from exc


def _check_size(raw, text: str) -> None:
    """Refuse exponent towers and large exponents before SymPy evaluates anything."""
    for p in raw.atoms(sp.Pow) if isinstance(raw, sp.Basic) else ():
        e = p.exp
        if e.has(sp.Pow) and not (e.is_Rational or (isinstance(e, sp.Pow) and e.base.is_Integer and e.exp == -1)):
            raise ParseError(f"{text!r} is larger than homework-sized math")
        if e.is_number and abs(sp.nsimplify(e)) > 20:
            raise ParseError(f"{text!r} is larger than homework-sized math")


def _denominators(raw) -> list:
    return [p.base for p in raw.atoms(sp.Pow) if p.exp.is_number and p.exp < 0] if isinstance(raw, sp.Basic) else []



def parse_equation(text: str) -> sp.Eq:
    parts = _clean(text).split("=")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise ParseError(f"expected one '=' in {text!r}")
    return sp.Eq(parse(parts[0]), parse(parts[1]), evaluate=False)


def exclusions(text: str) -> list:
    """Denominators of the equation AS WRITTEN (x^2/x keeps its x), which must not vanish.
    Passed explicitly: SymPy caches equal expressions, so nothing may be attached to them."""
    if "=" not in text:
        return []
    out = []
    for side in _clean(text).split("="):
        raw = _raw(side, text)
        out += [d for d in _denominators(raw) if d.free_symbols]
        # sqrt(u) is defined only where u >= 0 (in the real numbers)
        out += [("radicand", p.base) for p in raw.atoms(sp.Pow)
                if p.exp.is_Rational and p.exp.q % 2 == 0 and p.base.free_symbols]
    return out


def is_equation(text: str) -> bool:
    return "=" in text


def variables(obj) -> list[sp.Symbol]:
    return sorted(obj.free_symbols, key=lambda s: s.name)


def same_value(a: sp.Expr, b: sp.Expr) -> bool:
    """Exact equivalence. Numeric substitution is used only to DISPROVE quickly; acceptance
    always requires a symbolic proof that the difference is zero."""
    diff = a - b
    syms = sorted(diff.free_symbols, key=lambda s: s.name)
    rng = random.Random(0)
    for _ in range(6):
        subs = {s: sp.Rational(rng.randint(-40, 40), rng.randint(1, 7)) for s in syms}
        try:
            v = sp.nsimplify(diff.subs(subs))
        except (ZeroDivisionError, TypeError):
            continue
        if v.is_number and v.is_finite and v != 0:
            return False
    for simplify in (sp.expand, sp.cancel, sp.simplify):
        if simplify(sp.together(diff)) == 0:
            return True
    return False  # not proven equal: never accept


def solution_set(eq: sp.Eq, var: sp.Symbol | None = None, excluded: list | None = None,
                 domain=sp.S.Reals):
    var = var or (variables(eq)[0] if variables(eq) else None)
    if var is None or var not in eq.free_symbols:
        # "0x = 0" or "3 = 3": true for every value, or for none
        sols = domain if sp.simplify(eq.lhs - eq.rhs) == 0 else sp.S.EmptySet
    else:
        sols = sp.solveset(sp.Eq(eq.lhs, eq.rhs), var, domain=domain)
    if var is not None:
        for d in excluded or []:  # the written form is undefined where a denominator is 0
            if isinstance(d, tuple):  # ("radicand", u): real-domain condition u >= 0
                if domain == sp.S.Reals and var in d[1].free_symbols:
                    sols = sp.Intersection(sols, sp.solveset(d[1] >= 0, var, domain=sp.S.Reals))
                continue
            sols = sp.Complement(sols, sp.solveset(sp.Eq(d, 0), var, domain=domain))
    return sols


def equivalent_equations(e1: sp.Eq, e2: sp.Eq, excl1: list | None = None, excl2: list | None = None) -> bool:
    vs = sorted(set(variables(e1)) | set(variables(e2)), key=lambda s: s.name)
    if len(vs) <= 1:
        v = vs[0] if vs else None
        # Compared over the complex numbers: two equations with no REAL solution are not
        # interchangeable (x^2 = -2 and x = sqrt(-2) are both empty over the reals).
        return (solution_set(e1, v, excl1, sp.S.Complexes) == solution_set(e2, v, excl2, sp.S.Complexes)
                and solution_set(e1, v, excl1) == solution_set(e2, v, excl2))
    # several unknowns: same solution set as polynomial relation (up to a nonzero factor)
    p1 = sp.together(e1.lhs - e1.rhs)
    p2 = sp.together(e2.lhs - e2.rhs)
    ratio = sp.simplify(p1 / p2) if p2 != 0 else None
    return ratio is not None and ratio.is_number and ratio != 0


def pretty(obj) -> str:
    """Plain text that can be read aloud or shown on screen."""
    if isinstance(obj, sp.Equality):
        return f"{pretty(obj.lhs)} = {pretty(obj.rhs)}"
    s = sp.sstr(obj).replace("**", "^")
    return re.sub(r"(?<![\w.])(\d+)\*(?=[a-z(])", r"\1", s)


# --------------------------------------------------------------------------------------
# Mistake diagnosis
# --------------------------------------------------------------------------------------

@dataclass
class Diagnosis:
    code: str
    message: str  # addressed to the learner, never contains the answer
    hint: str


MISTAKES = {
    "moved_term_kept_sign": Diagnosis(
        "moved_term_kept_sign",
        "It looks like a term moved to the other side but kept its sign.",
        "When a term crosses the equals sign, do the same operation to both sides: "
        "subtracting it on one side means subtracting it on the other.",
    ),
    "divided_one_term": Diagnosis(
        "divided_one_term",
        "Only part of one side was divided.",
        "Dividing a side means dividing every term on that side, and the other side too.",
    ),
    "divided_one_side": Diagnosis(
        "divided_one_side",
        "One side was divided but the other side was not.",
        "Whatever you do to one side of an equation, do exactly the same to the other side.",
    ),
    "multiplied_one_side": Diagnosis(
        "multiplied_one_side",
        "One side was multiplied but the other side was not.",
        "To clear a denominator, multiply BOTH sides by it.",
    ),
    "partial_distribution": Diagnosis(
        "partial_distribution",
        "The number in front of the parentheses was not multiplied by every term inside.",
        "Distribute to each term: a(b + c) = ab + ac.",
    ),
    "negative_distribution": Diagnosis(
        "negative_distribution",
        "A minus sign in front of parentheses was not applied to every term inside.",
        "A minus in front of parentheses flips the sign of every term inside.",
    ),
    "fraction_add_across": Diagnosis(
        "fraction_add_across",
        "Numerators were added together and denominators were added together.",
        "To add fractions, first rewrite them with the same denominator.",
    ),
    "square_of_sum": Diagnosis(
        "square_of_sum",
        "(a + b)^2 was written as a^2 + b^2; the middle term is missing.",
        "(a + b)^2 = a^2 + 2ab + b^2. Try multiplying (a + b)(a + b) term by term.",
    ),
    "sqrt_of_negative": Diagnosis(
        "sqrt_of_negative",
        "The square root of a negative number is not a real number.",
        "A square is never negative, so x^2 = (a negative number) has no real solution.",
    ),
    "negative_square": Diagnosis(
        "negative_square",
        "The square of a negative number was given a negative sign.",
        "A negative times a negative is positive: (-a)^2 = (-a)(-a).",
    ),
    "minus_not_squared": Diagnosis(
        "minus_not_squared",
        "Without parentheses, the minus sign is not squared.",
        "-a^2 means -(a^2); only (-a)^2 squares the minus sign.",
    ),
    "division_by_zero": Diagnosis(
        "division_by_zero",
        "Division by zero is not defined.",
        "No number can be divided by zero, not even zero itself.",
    ),
    "rounded_not_equal": Diagnosis(
        "rounded_not_equal",
        "That decimal is a rounded value, not exactly equal.",
        "Keep the exact value (a fraction or a square root), or write ≈ for a rounded value.",
    ),
    "false_statement": Diagnosis(
        "false_statement",
        "This equality between numbers is false.",
        "Re-do this calculation step by step.",
    ),
    "sign_slip": Diagnosis(
        "sign_slip",
        "Everything is right except one sign.",
        "Re-check the signs one term at a time.",
    ),
    "arithmetic_slip": Diagnosis(
        "arithmetic_slip",
        "The method is right, but a number is off.",
        "Your method is correct. Re-do the arithmetic on the last line carefully.",
    ),
}


def _terms(e: sp.Expr) -> list[sp.Expr]:
    return list(sp.Add.make_args(e))


def _wrong_equation_moves(eq: sp.Eq) -> list[tuple[str, sp.Eq]]:
    """Plausible *wrong* next lines a learner could write from `eq` (unevaluated)."""
    out: list[tuple[str, sp.Eq]] = []
    sides = (eq.lhs, eq.rhs)
    # several terms moved at once, each keeping its sign: 5x - 3 = 2x + 9 -> 5x + 2x = 9 - 3
    lt, rt = _terms(eq.lhs), _terms(eq.rhs)
    if len(lt) + len(rt) <= 6:
        import itertools
        for a in range(len(lt) + 1):
            for b in range(len(rt) + 1):
                if a + b < 2:
                    continue
                for ml in itertools.combinations(lt, a):
                    for mr in itertools.combinations(rt, b):
                        left = [t for t in lt if t not in ml] + list(mr)
                        right = [t for t in rt if t not in mr] + list(ml)
                        if left and right:
                            out.append(("moved_term_kept_sign", sp.Eq(sp.Add(*left), sp.Add(*right))))
    for k in (0, 1):
        side, other = sides[k], sides[1 - k]

        def put(this, that, k=k):
            return sp.Eq(this, that) if k == 0 else sp.Eq(that, this)

        terms = _terms(side)
        if len(terms) > 1:
            for i, t in enumerate(terms):
                rest = sp.Add(*(terms[:i] + terms[i + 1:]))
                out.append(("moved_term_kept_sign", put(rest, other + t)))
                c, var_part = sp.nsimplify(t).as_coeff_Mul()
                if var_part.free_symbols and c not in (0, 1, -1):
                    divided = sp.Add(*(terms[:i] + [t / c] + terms[i + 1:]))
                    out.append(("divided_one_term", put(divided, other / c)))
                    out.append(("divided_one_side", put(divided, other)))
        else:
            c, var_part = sp.nsimplify(side).as_coeff_Mul()
            if var_part.free_symbols and c not in (0, 1, -1):
                out.append(("divided_one_side", put(var_part, other)))
        # multiplied only one side to clear a denominator: 2x/3 = 4 -> 2x = 4
        den = sp.fraction(sp.together(sp.nsimplify(side)))[1]
        if den.is_Integer and den != 1:
            out.append(("multiplied_one_side", put(sp.expand(side * den), other)))
        for code, f in (("partial_distribution", _partial_distributions),
                        ("negative_distribution", _negative_distributions)):
            for w in f(side):
                out.append((code, put(w, other)))
    return out


def _products_with_sum(e: sp.Expr):
    """Yield (term, coefficient, inner terms) for each term of `e` shaped k*(a + b + ...)."""
    for t in _terms(e):
        factors = sp.Mul.make_args(t)
        sums = [f for f in factors if isinstance(f, sp.Add)]
        if len(sums) == 1:
            coeff = sp.nsimplify(sp.Mul(*[f for f in factors if f is not sums[0]]))
            yield t, coeff, _terms(sums[0])


def _replace_term(e: sp.Expr, t: sp.Expr, new: sp.Expr) -> sp.Expr:
    return sp.Add(*[(new if u is t else u) for u in _terms(e)])


def _partial_distributions(e: sp.Expr) -> list[sp.Expr]:
    """k(a + b) -> k*a + b, for each choice of the term that received k."""
    out = []
    for t, k, inner in _products_with_sum(e):
        if k in (1, -1) or not k.is_number:
            continue
        for i in range(len(inner)):
            out.append(_replace_term(e, t, k * inner[i] + sp.Add(*(inner[:i] + inner[i + 1:]))))
    return out


def _negative_distributions(e: sp.Expr) -> list[sp.Expr]:
    """-k(a + b) -> -k*a + k*b : the minus reached only one term."""
    out = []
    for t, k, inner in _products_with_sum(e):
        if not (k.is_number and k < 0):
            continue
        for i in range(len(inner)):
            out.append(_replace_term(e, t, k * inner[i] + abs(k) * sp.Add(*(inner[:i] + inner[i + 1:]))))
    return out


def _wrong_expression_moves(e: sp.Expr) -> list[tuple[str, sp.Expr]]:
    out: list[tuple[str, sp.Expr]] = []
    out += [("partial_distribution", w) for w in _partial_distributions(e)]
    out += [("negative_distribution", w) for w in _negative_distributions(e)]
    for p in e.atoms(sp.Pow):  # (a + b)^2 -> a^2 + b^2
        if isinstance(p.base, sp.Add) and p.exp == 2:
            out.append(("square_of_sum", e.xreplace({p: sp.Add(*[u**2 for u in _terms(p.base)])})))
    values = [(t, sp.nsimplify(t.doit())) for t in _terms(e)]
    fr = [(t, v) for t, v in values if v.is_Rational and not v.is_Integer]
    if len(fr) >= 2:  # a/b + c/d -> (a + c)/(b + d)
        (t1, a), (t2, b) = fr[0], fr[1]
        rest = [t for t, _ in values if t is not t1 and t is not t2]
        out.append(("fraction_add_across", sp.Add(sp.Rational(a.p + b.p, a.q + b.q), *rest)))
    return out


def _expr_from_text_raw(text: str) -> sp.Expr:
    """Parse without evaluation so that '1/2 + 1/3' keeps its two fractions."""
    t = _clean(text)
    # Python's unary minus distributes even with evaluate=False: keep "-(...)" as (-1)*(...)
    t = re.sub(r"-\s*\(", "+(-1)*(", t).lstrip("+").replace("(+(-1)", "((-1)")
    try:
        return parse_expr(t, local_dict=dict(_ALLOWED), global_dict=_GLOBALS,
                          transformations=_TRANSFORMS, evaluate=False)
    except Exception as exc:
        raise ParseError(f"could not read {text!r}") from exc


@dataclass
class StepVerdict:
    ok: bool
    progress: bool = False
    solved: bool = False
    diagnosis: Diagnosis | None = None
    note: str = ""
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = {"ok": self.ok, "progress": self.progress, "solved": self.solved, "note": self.note}
        if self.diagnosis:
            d["mistake"] = self.diagnosis.code
            d["feedback"] = self.diagnosis.message
            d["hint"] = self.diagnosis.hint
        d.update(self.extra)
        return d


def _complexity(obj) -> int:
    return sp.count_ops(obj.lhs - obj.rhs if isinstance(obj, sp.Equality) else obj, visual=False)


def _is_isolated(eq: sp.Eq) -> bool:
    return (isinstance(eq.lhs, sp.Symbol) and not eq.rhs.free_symbols) or (
        isinstance(eq.rhs, sp.Symbol) and not eq.lhs.free_symbols
    )


def _check_solution_list(previous: str, step: str) -> StepVerdict:
    """'x = 2 ou x = 3', 'x = ±3', '3 ; -3' after an equation: compare with its real solutions."""
    prev = parse_equation(previous)
    vs = variables(prev)
    vals = [parse(v) for v in _solution_values(step)]
    if any(v.has(sp.I) for v in vals):
        return StepVerdict(False, diagnosis=MISTAKES["sqrt_of_negative"])
    if len(vs) != 1 or any(v.free_symbols for v in vals):
        return StepVerdict(False, note="The answer should be a number.")
    truth = solution_set(prev, vs[0], exclusions(previous))
    given = sp.FiniteSet(*vals)
    if isinstance(truth, sp.FiniteSet) and given == truth:
        return StepVerdict(True, progress=True, solved=True)
    if isinstance(truth, sp.FiniteSet) and given.is_subset(truth):
        return StepVerdict(False, note="Correct, but there is another solution.", extra={"partial": True})
    return StepVerdict(False, diagnosis=MISTAKES["arithmetic_slip"] if isinstance(truth, sp.FiniteSet)
                       and len(given) == len(truth) else None)


def check_step(previous: str, step: str) -> StepVerdict:
    """Is `step` a mathematically valid next line after `previous`? If not, which classic
    mistake explains it? Works for equations (solution-set equivalence) and expressions
    (value equivalence)."""
    if is_equation(previous) and _is_solution_list(step):
        return _check_solution_list(previous, step)
    if is_equation(previous) != is_equation(step):
        return StepVerdict(False, note="The previous line and this line are not the same kind "
                                       "(one is an equation, the other is not).")
    if is_equation(previous) and step.count("=") + step.count("≈") > 1 and not _is_solution_list(step):
        step, bad_link = _unchain(step)
        if bad_link is not None:
            return bad_link
    if is_equation(previous):
        prev, new = parse_equation(previous), parse_equation(step)
        if new.lhs.has(sp.I) or new.rhs.has(sp.I):
            return StepVerdict(False, diagnosis=MISTAKES["sqrt_of_negative"])
        if not new.free_symbols and variables(prev):
            claim = check_claim(step)
            contradiction = solution_set(prev, None, exclusions(previous), sp.S.Complexes) == sp.S.EmptySet
            if not claim.ok and not contradiction:  # a false calculation is not a step (0 = 1 after x = x + 1 is)
                return claim
        if equivalent_equations(prev, new, exclusions(previous), exclusions(step)):
            solved = _is_isolated(new)
            progress = solved or _complexity(new) < _complexity(prev)
            return StepVerdict(True, progress=progress, solved=solved)
        if _is_isolated(new) and len(variables(prev)) == 1:  # one root of several: say so, kindly
            truth = solution_set(prev, variables(prev)[0], exclusions(previous))
            value = new.rhs if isinstance(new.lhs, sp.Symbol) else new.lhs
            if isinstance(truth, sp.FiniteSet) and len(truth) > 1 and value in truth:
                return StepVerdict(False, note="Correct, but there is another solution.", extra={"partial": True})
        raw_prev = sp.Eq(_expr_from_text_raw(previous.split("=")[0]), _expr_from_text_raw(previous.split("=")[1]), evaluate=False)
        for code, cand in _wrong_equation_moves(raw_prev):
            try:
                if equivalent_equations(cand, new):
                    return StepVerdict(False, diagnosis=MISTAKES[code])
            except Exception:
                continue
        return StepVerdict(False, diagnosis=_slip_equation(prev, new))
    prev_e, new_e = parse(previous), parse(step)
    if same_value(prev_e, new_e):
        v = StepVerdict(True, progress=_complexity(new_e) <= _complexity(prev_e))
        lost = _denominators(_expr_from_text_raw(previous))
        kept = _denominators(_expr_from_text_raw(step))
        conds = []
        for d in lost:
            for var in sorted(d.free_symbols, key=lambda s: s.name):
                zeros = sp.solveset(sp.Eq(d, 0), var, domain=sp.S.Reals)
                if isinstance(zeros, sp.FiniteSet):
                    for z in zeros:
                        if not any(sp.simplify(k.subs(var, z)) == 0 for k in kept if var in k.free_symbols):
                            conds.append(f"{var} ≠ {pretty(z)}")
        if conds:  # x^2/x = x only where x ≠ 0: equal, with a condition the learner must state
            v.note = "Right, as long as " + " and ".join(sorted(set(conds))) + "."
            v.extra["condition"] = sorted(set(conds))
        return v
    for code, cand in _wrong_expression_moves(_expr_from_text_raw(previous)):
        if same_value(cand, new_e):
            return StepVerdict(False, diagnosis=MISTAKES[code])
    return StepVerdict(False, diagnosis=_slip_expression(prev_e, new_e))


def _slip_equation(prev: sp.Eq, new: sp.Eq) -> Diagnosis | None:
    vs = variables(prev)
    if len(vs) != 1:
        return None
    s_true, s_new = solution_set(prev, vs[0]), solution_set(new, vs[0])
    if isinstance(s_true, sp.FiniteSet) and isinstance(s_new, sp.FiniteSet) and len(s_true) == len(s_new) == 1:
        a, b = next(iter(s_true)), next(iter(s_new))
        if a == -b and a != 0:
            return MISTAKES["sign_slip"]
        return MISTAKES["arithmetic_slip"]
    return None


def _slip_expression(prev: sp.Expr, new: sp.Expr) -> Diagnosis | None:
    p, n = sp.Poly(sp.expand(prev)) if prev.free_symbols else None, sp.Poly(sp.expand(new)) if new.free_symbols else None
    if p is not None and n is not None and p.gens == n.gens and p.monoms() == n.monoms():
        diffs = [a - b for a, b in zip(p.coeffs(), n.coeffs()) if a != b]
        if all(a == -b for a, b in zip(p.coeffs(), n.coeffs()) if a != b):
            return MISTAKES["sign_slip"]
        if len(diffs) == 1:
            return MISTAKES["arithmetic_slip"]
    if not prev.free_symbols and not new.free_symbols:
        return MISTAKES["sign_slip"] if sp.simplify(prev + new) == 0 else MISTAKES["arithmetic_slip"]
    return None


_NONE = r"no (real )?solutions?|no answer|impossible|pas de solutions?( r[ée]elles?)?|aucune solution|ensemble vide|∅"
_ALL = (r"all (real )?numbers|any (real )?number|infinitely many|every number|tous les (r[ée]els|nombres|[a-z]\b)|"
        r"tout (r[ée]el|nombre|[a-z]\b)|toutes les valeurs|n'importe quel(le)? (nombre|valeur)|all [a-z]\b|every [a-z]\b|any [a-z]\b")
_EXCEPT = (r"not equal to|\bexcept\b|\bsauf\b|diff[ée]rents? de|other than|\bnot\b|≠")


def _solution_values(text: str) -> list[str]:
    """'x = 2 or x = -3', 'x = ±3', '2 ; 3', 'x = 2 ou x = 3' -> ['2', '-3'] etc."""
    t = _notation(text).lower()
    t = re.sub(r"\bz[ée]ro\b", "0", t)
    t = re.sub(r"\b[a-z]\s*=", " ", t)
    parts = [p.strip() for p in re.split(r"\s*(?:,|;|\bor\b|\bou\b|\band\b|\bet\b)\s*", t) if p.strip()]
    out = []
    for p in parts:
        if p.startswith("±") or p.startswith("+-") or p.startswith("+/-"):
            core = re.sub(r"^(±|\+/-|\+-)", "", p).strip()
            out += [core, f"-({core})"]
        else:
            out.append(p)
    return out


def _is_solution_list(text: str) -> bool:
    t = _notation(text).lower()
    return ("±" in t or "+-" in t or "+/-" in t or bool(re.search(r"\bor\b|\bou\b|;|,", t)))


def _unchain(step: str) -> tuple[str, StepVerdict | None]:
    """'x = (5 + sqrt(1))/2 = 6/2 = 3' -> ('x = 3', None) if every link is a true calculation,
    or the verdict of the first false link."""
    tokens = [p.strip() for p in re.split(r"(=|≈)", step)]
    parts, ops = tokens[0::2], tokens[1::2]
    if len(parts) < 3:
        return step, None
    if not re.fullmatch(r"[a-z]", parts[0].lower()) or ops[0] != "=":
        raise ParseError("write one equality per line")
    exact = parts[1]
    for a, op, b in zip(parts[1:], ops[1:], parts[2:]):
        link = check_claim(f"{a} {op} {b}")
        if not link.ok:
            return step, link
        if op == "=":
            exact = b
    return f"{parts[0]} = {exact}", None


def _rounding(eq: sp.Eq, text: str) -> tuple[bool, bool]:
    """(exactly equal, one side is the other rounded to its written decimals)."""
    diff = sp.simplify(eq.lhs - eq.rhs)
    if diff == 0:
        return True, False
    for side, other in ((text.split("=")[1], eq.lhs), (text.split("=")[0], eq.rhs)):
        m = re.fullmatch(r"\s*-?\d+[.,](\d{1,4})\s*", side)
        if m and other.is_number and other.is_real:
            decimals = len(m.group(1))
            written = float(side.replace(",", "."))
            if abs(float(other) - written) <= 0.5 * 10 ** -decimals + 1e-12:
                return False, True
    return False, False


def check_claim(text: str) -> StepVerdict:
    """A calculation with numbers only, e.g. '(-2)^2 = -4': true or false, with the classic
    sign mistakes named. The correct value is not revealed."""
    approx = "≈" in text or "~" in text
    text = text.replace("≈", "=").replace("~", "=")
    try:
        eq = parse_equation(text)
    except UndefinedError:
        return StepVerdict(False, diagnosis=MISTAKES["division_by_zero"])
    if eq.free_symbols:
        raise ParseError("check_claim is for calculations with numbers only")
    exact, rounded = _rounding(eq, text)
    if rounded:  # 5/6 = 0.83: a rounded value, not an equality
        if approx:
            return StepVerdict(True, note="Correct as a rounded value.")
        return StepVerdict(False, diagnosis=MISTAKES["rounded_not_equal"])
    if eq.lhs.has(sp.I) or eq.rhs.has(sp.I):
        return StepVerdict(False, diagnosis=MISTAKES["sqrt_of_negative"])
    if sp.simplify(eq.lhs - eq.rhs) == 0:
        return StepVerdict(True)
    for side_text, other in ((text.split("=")[0], eq.rhs), (text.split("=")[1], eq.lhs)):
        t = _clean(side_text).replace(" ", "")
        value = parse(side_text)
        if re.fullmatch(r"\(-(\d+|sqrt\(\d+\))\)\^\d*[02468]", t) and other == -value:
            return StepVerdict(False, diagnosis=MISTAKES["negative_square"])
        if re.fullmatch(r"-\d+\^\d*[02468]", t) and other == -value:
            return StepVerdict(False, diagnosis=MISTAKES["minus_not_squared"])
    return StepVerdict(False, diagnosis=MISTAKES["false_statement"])


def check_answer(problem: str, answer: str) -> StepVerdict:
    """Final-answer check: accepts any equivalent form (x = 3/2, 1.5, 3/2, x=1.5)."""
    if is_equation(problem):
        eq = parse_equation(problem)
        vs = variables(eq) or [sp.Symbol(w) for w in sorted(set(re.findall(r"[a-z]+", _clean(problem)))) if len(w) == 1][:1]
        truth = solution_set(eq, vs[0], exclusions(problem)) if len(vs) == 1 else None
        low = answer.lower()
        if truth is not None and not isinstance(truth, sp.FiniteSet):
            says_none = bool(re.search(_NONE, low))
            says_all = bool(re.search(_ALL, low))
            if truth == sp.S.EmptySet:
                return StepVerdict(says_none, solved=says_none,
                                   note="" if says_none else "Check again: can this equation ever be true?")
            if truth == sp.S.Reals:
                return StepVerdict(says_all, solved=says_all,
                                   note="" if says_all else "Check again: is this true for more than one value?")
            # e.g. x/x = 1: every number except where the written form is undefined
            ok = False
            if says_all and re.search(_EXCEPT, low):
                tail = re.split(_EXCEPT, low, maxsplit=1)[1]
                given = [parse(a) for a in _solution_values(tail)]
                missing = sp.Complement(sp.S.Reals, truth)
                ok = bool(given) and sp.FiniteSet(*given) == missing
            return StepVerdict(ok, solved=ok, note="" if ok else
                               "Careful: this is true for many values, but not where a denominator is zero.")
        if re.search(_NONE, low) or re.search(_ALL, low):
            return StepVerdict(False, note="This equation does have specific solutions.")
        if len(vs) == 1:
            labels = set(re.findall(r"\b([a-z])\s*=", low))
            if labels - {vs[0].name}:
                return StepVerdict(False, note=f"The unknown in this problem is {vs[0].name}.")
        vals = [parse(a) for a in _solution_values(answer)]
        if re.search(r"\d,\d", answer) and isinstance(truth, sp.FiniteSet) and sp.FiniteSet(*vals) != truth:
            # "2,3" may be the decimal 2.3 or the list 2 ; 3: accept the list reading if it is exact
            listed = [parse(a) for a in _solution_values(re.sub(r"(\d),(\d)", r"\1 ; \2", answer))]
            if sp.FiniteSet(*listed) == truth:
                vals = listed
        if not vals:
            raise ParseError("no answer given")
        if any(v.free_symbols for v in vals):
            return StepVerdict(False, note="The answer should be a number.")
        if any(v.has(sp.I) for v in vals):
            return StepVerdict(False, diagnosis=MISTAKES["sqrt_of_negative"])
        if truth is not None and isinstance(truth, sp.FiniteSet):
            given = sp.FiniteSet(*[sp.nsimplify(v) for v in vals])
            if given == truth:
                return StepVerdict(True, solved=True)
            if given.is_subset(truth):
                return StepVerdict(False, note="Correct, but there is another solution.",
                                   extra={"partial": True})
            return StepVerdict(False, diagnosis=_slip_equation(eq, sp.Eq(vs[0], vals[0])) if len(vals) == 1 else None)
        return StepVerdict(False, note="This equation needs a more careful check.")
    ok = same_value(parse(problem), parse(answer))
    return StepVerdict(ok, solved=ok)


def solve_steps(problem: str) -> list[str]:
    """A verified worked solution for a linear equation in one unknown (parent mode).
    Every line is re-checked to be equivalent to the original equation."""
    eq = parse_equation(problem)
    vs = variables(eq)
    if len(vs) != 1:
        raise ParseError("worked solutions currently cover equations in one unknown")
    x = vs[0]
    lines = [pretty(eq)]
    L, R = sp.expand(eq.lhs), sp.expand(eq.rhs)
    if (L, R) != (eq.lhs, eq.rhs):
        lines.append(pretty(sp.Eq(L, R, evaluate=False)))
    poly = sp.Poly(L - R, x)
    if poly.degree() == 1:
        a, b = poly.all_coeffs()
        lines.append(pretty(sp.Eq(a * x, -b, evaluate=False)))
        lines.append(pretty(sp.Eq(x, sp.Rational(-b, 1) / a, evaluate=False)))
    elif poly.degree() == 2:
        f = sp.factor(L - R)
        lines.append(pretty(sp.Eq(f, 0, evaluate=False)))
        sols = sorted(sp.solveset(L - R, x, domain=sp.S.Reals), key=lambda s: float(s))
        lines.append(" or ".join(f"{x} = {pretty(s)}" for s in sols))
    else:
        raise ParseError("worked solutions cover linear and quadratic equations")
    # every line must be equivalent to the original: the assistant never reads an unverified line
    for ln in lines[:-1] if poly.degree() == 2 else lines:
        assert equivalent_equations(eq, parse_equation(ln)), ln
    return lines
