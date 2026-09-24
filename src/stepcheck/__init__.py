"""stepcheck — verify a student's algebra, one line at a time, and name the mistake.

    >>> from stepcheck import check_step
    >>> v = check_step("3(x - 2) = 12", "3x - 2 = 12")
    >>> v.ok, v.diagnosis.code
    (False, 'partial_distribution')
"""

from .core import MISTAKES, Diagnosis, ParseError, StepVerdict, check_answer, check_step, solve_steps
from .hints import hint, next_move
from .i18n import LANGS, localize, tr
from .practice import SKILLS, Item, generate

__all__ = [
    "MISTAKES", "Diagnosis", "ParseError", "StepVerdict", "check_answer", "check_step", "solve_steps",
    "hint", "next_move", "LANGS", "localize", "tr", "SKILLS", "Item", "generate",
]
__version__ = "0.1.0"
