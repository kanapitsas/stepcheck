"""LaTeX for display: shows what the student WROTE (never a simplified form).

    >>> to_latex("3(x - 2) = 12")
    '3 \\\\left(x - 2\\\\right) = 12'
"""

from __future__ import annotations

import re

import sympy as sp

from .core import ParseError, _expr_from_text_raw, _notation

_SEP = re.compile(r"\s*(,|;|\bor\b|\bou\b|\band\b|\bet\b)\s*", re.IGNORECASE)


def _expr(text: str) -> str:
    t = text.strip()
    pm = ""
    for sign in ("±", "+/-", "+-"):
        if t.startswith(sign):
            pm, t = r"\pm ", t[len(sign):].strip()
    tex = sp.latex(_expr_from_text_raw(t), order="none")
    tex = re.sub(r"(?<![\d.])1 \\cdot ", "", tex)  # 1/2 is parsed as 1*(1/2)
    return pm + tex


def _text(text: str) -> str:
    return r"\text{" + re.sub(r"([{}\\#$%&_^~])", r"\\\1", text) + "}"


def to_latex(text: str) -> str:
    """Math line -> LaTeX, keeping its written structure. Unreadable input becomes \\text{...}."""
    try:
        t = _notation(text)
        pieces = _SEP.split(t)
        if len(pieces) > 1:  # a list of solutions: x = 2 ou x = 3
            out = []
            for i, p in enumerate(pieces):
                out.append(r"\ \text{" + p + r"}\ " if i % 2 else to_latex(p))
            return "".join(out)
        tokens = re.split(r"(=|≈)", t)
        return " ".join(_expr(tok) if i % 2 == 0 else ("=" if tok == "=" else r"\approx")
                        for i, tok in enumerate(tokens))
    except (ParseError, Exception):
        return _text(text)
