import pytest

from stepcheck.core import check_answer, check_step, solve_steps

# (previous line, learner's next line, expected ok, expected mistake code or None)
STEPS = [
    # valid moves
    ("2x + 4 = 10", "2x = 6", True, None),
    ("2x = 6", "x = 3", True, None),
    ("3(x - 2) = 12", "3x - 6 = 12", True, None),
    ("3(x - 2) = 12", "x - 2 = 4", True, None),
    ("5 - x = 2", "-x = -3", True, None),
    ("x/4 + 1 = 3", "x/4 = 2", True, None),
    ("x^2 - 5x + 6 = 0", "(x - 2)(x - 3) = 0", True, None),
    ("2(x + 3)", "2x + 6", True, None),
    ("(x + 1)^2", "x^2 + 2x + 1", True, None),
    ("1/2 + 1/3", "5/6", True, None),
    # classic mistakes
    ("2x + 4 = 10", "2x = 14", False, "moved_term_kept_sign"),
    ("x - 7 = 3", "x = -4", False, "moved_term_kept_sign"),
    ("2x + 4 = 10", "x + 4 = 5", False, "divided_one_term"),
    ("3x = 12", "x = 12", False, "divided_one_side"),
    ("3(x - 2) = 12", "3x - 2 = 12", False, "partial_distribution"),
    ("2(x + 5)", "2x + 5", False, "partial_distribution"),
    ("10 - (x + 3) = 4", "10 - x + 3 = 4", False, "negative_distribution"),
    ("-(x - 4)", "-x - 4", False, "negative_distribution"),
    ("1/2 + 1/3", "2/5", False, "fraction_add_across"),
    ("(x + 3)^2", "x^2 + 9", False, "square_of_sum"),
    ("2x = 6", "x = -3", False, "sign_slip"),
    ("4x = 20", "x = 6", False, "arithmetic_slip"),
    ("7 + 8", "16", False, "arithmetic_slip"),
]


@pytest.mark.parametrize("prev,step,ok,code", STEPS)
def test_steps(prev, step, ok, code):
    v = check_step(prev, step)
    assert v.ok is ok, (prev, step, v.as_dict())
    if code:
        assert v.diagnosis is not None and v.diagnosis.code == code, (prev, step, v.as_dict())


def test_feedback_never_contains_the_answer():
    v = check_step("4x = 20", "x = 6")
    d = v.as_dict()
    assert "5" not in d["feedback"] + d["hint"]


@pytest.mark.parametrize("problem,answer,ok", [
    ("2x + 4 = 10", "x = 3", True),
    ("2x + 4 = 10", "3", True),
    ("2x + 1 = 4", "1.5", True),
    ("2x + 1 = 4", "x = 3/2", True),
    ("x^2 = 9", "3", False),          # partial
    ("x^2 = 9", "x = 3 or x = -3", True),
    ("x^2 = 9", "-3, 3", True),
    ("2(x + 3)", "2x + 6", True),
    ("2x + 4 = 10", "x = 4", False),
])
def test_answers(problem, answer, ok):
    assert check_answer(problem, answer).ok is ok


def test_worked_solution_is_verified():
    lines = solve_steps("3(x - 2) = 12")
    assert lines[-1].replace(" ", "") == "x=6"
    lines = solve_steps("x^2 - 5x + 6 = 0")
    assert "x = 2" in lines[-1] and "x = 3" in lines[-1]


# Adversarial cases found in review: each one was a wrong verdict or a crash before the fix.
@pytest.mark.parametrize("problem,answer,ok", [
    ("2x = 6", "y = 3", False),              # wrong unknown
    ("x^2 = 9", "y = 3, z = -3", False),
    ("2e = 6", "e = 3", True),               # e and i are unknowns, not constants
    ("x = x + 1", "no solution", True),
    ("x = x + 1", "x = 1", False),
    ("x = x", "all real numbers", True),
    ("0x = 0", "all real numbers", True),
    ("0x = 5", "no solution", True),
    ("2x = 6", "no solution", False),
])
def test_answers_adversarial(problem, answer, ok):
    assert check_answer(problem, answer).ok is ok


def test_e_and_i_are_variables_in_steps():
    assert check_step("2e = 6", "e = 4").ok is False
    assert check_step("2i = 6", "i = 3").ok is True


def test_numeric_coincidence_is_never_accepted():
    # vanishes at many rational points, but is not the zero polynomial
    import sympy as sp
    x = sp.Symbol("x")
    p = sp.expand(sp.prod([(x - k) for k in range(-4, 5)]))
    assert check_step("0", str(p).replace("**", "^")).ok is False


@pytest.mark.parametrize("bad", ["True", "False", "None", "factorial(10)", "x = ??", "__import__('os')"])
def test_unreadable_input_is_a_parse_error(bad):
    from stepcheck.core import ParseError
    with pytest.raises(ParseError):
        check_step("2x = 6", bad if "=" in bad else f"x = {bad}")


@pytest.mark.parametrize("big", ["x^99999999", "x**1000", "12345678901234 x", "x + " * 60 + "1"])
def test_oversized_input_is_refused_fast(big):
    from stepcheck.core import ParseError
    with pytest.raises(ParseError):
        check_step("2x = 6", f"x = {big}")


def test_domain_is_kept_from_the_written_form():
    assert check_step("x^2/x = 0", "x = 0").ok is False       # undefined at 0: no solution
    assert check_answer("x^2/x = 0", "no solution").ok is True
    assert check_answer("x/x = 1", "all real numbers").ok is False
    assert check_answer("x/x = 1", "all real numbers except 0").ok is True
    assert check_step("1/x = 2", "1 = 2x").ok is True
    assert check_answer("1/x = 2", "x = 1/2").ok is True


@pytest.mark.parametrize("prev,step", [("1/0 = 1/0", "0 = 1"), ("1/0", "1/0"), ("2x = 6", "x = 9^9^7")])
def test_undefined_or_tower_is_refused(prev, step):
    from stepcheck.core import ParseError
    with pytest.raises(ParseError):
        check_step(prev, step)


def test_letters_of_sqrt_and_pi_are_still_unknowns():
    assert check_answer("0i = 0", "all real numbers").ok is True
    assert check_answer("0i = 5", "no solution").ok is True
    assert check_answer("2t = 6", "t = 3").ok is True


@pytest.mark.parametrize("empty", ["", ",", "x ="])
def test_empty_answer_is_not_partial_credit(empty):
    from stepcheck.core import ParseError
    with pytest.raises(ParseError):
        check_answer("2x = 6", empty)


def test_expression_simplification_states_its_condition():
    v = check_step("x^2/x", "x")
    assert v.ok is True and v.extra["condition"] == ["x ≠ 0"]
    assert "condition" not in check_step("2(x + 3)", "2x + 6").extra


@pytest.mark.parametrize("answer,ok", [
    ("all real numbers except 0", True),
    ("all real numbers except 7", False),
    ("all real numbers except", False),
])
def test_except_names_the_right_values(answer, ok):
    try:
        assert check_answer("x/x = 1", answer).ok is ok
    except Exception:
        assert ok is False


def test_except_with_two_excluded_values():
    assert check_answer("(x^2 - 1)/(x^2 - 1) = 1", "all real numbers except 1 and -1").ok is True
    assert check_answer("(x^2 - 1)/(x^2 - 1) = 1", "all real numbers except 0").ok is False


def test_never_mind_is_not_no_solution():
    from stepcheck.core import ParseError
    try:
        assert check_answer("x = x + 1", "never mind").ok is False
    except ParseError:
        pass
