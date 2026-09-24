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


# Found by hand in the simulator on 24/09: both were accepted before.
def test_sqrt_of_negative_is_not_a_valid_step():
    assert check_step("x^2 + 2 = 0", "x^2 = -2").ok is True
    v = check_step("x^2 = -2", "x = sqrt(-2)")
    assert v.ok is False and v.diagnosis.code == "sqrt_of_negative"


def test_false_side_calculation_is_never_a_valid_step():
    v = check_step("x = sqrt(2)", "(-2)^2 = -4")
    assert v.ok is False and v.diagnosis.code == "negative_square"
    assert check_step("x^2 = -2", "(-2)^2 = -4").ok is False


@pytest.mark.parametrize("claim,ok,code", [
    ("(-2)^2 = -4", False, "negative_square"),
    ("(-2)^2 = 4", True, None),
    ("-2^2 = 4", False, "minus_not_squared"),
    ("-2^2 = -4", True, None),
    ("7 + 8 = 16", False, "false_statement"),
    ("sqrt(-4) = 2", False, "sqrt_of_negative"),
])
def test_claims(claim, ok, code):
    from stepcheck.core import check_claim
    v = check_claim(claim)
    assert v.ok is ok and (code is None or v.diagnosis.code == code)


def test_equations_without_real_solution_are_still_distinguished():
    assert check_step("x^2 = -2", "x^2 = -3").ok is False
    assert check_step("x^2 = -4", "x^2 + 4 = 0").ok is True
    assert check_step("x = x + 1", "0 = 1").ok is True


# Found by the simulated-student red team on 24/09.
@pytest.mark.parametrize("answer,ok", [
    ("pas de solution réelle", True), ("aucune solution", True), ("pas de solution", True),
    ("no real solution", True), ("x = 2", False),
])
def test_no_solution_in_french(answer, ok):
    assert check_answer("x^2 + 2 = 0", answer).ok is ok


@pytest.mark.parametrize("answer,ok", [
    ("x = ±3", True), ("x = 3 ou x = -3", True), ("3 ; -3", True), ("x = 3 et x = -3", True), ("±√9", True),
    ("x = ±√(-9)", False),
])
def test_student_notations_for_two_solutions(answer, ok):
    assert check_answer("x^2 = 9", answer).ok is ok


@pytest.mark.parametrize("step,ok,code", [
    ("x = 2 ou x = 3", True, None),
    ("x = 2", False, None),              # partial: one solution missing
    ("x = ±√(-2)", False, "sqrt_of_negative"),
])
def test_solution_lines_in_steps(step, ok, code):
    prev = "x^2 = -2" if "-2" in step else "x^2 - 5x + 6 = 0"
    v = check_step(prev, step)
    assert v.ok is ok and (code is None or v.diagnosis.code == code)


def test_french_decimal_comma_and_unicode():
    assert check_answer("2x + 1 = 4", "x = 1,5").ok is True
    assert check_step("x² = 9", "x = ±3").ok is True
    assert check_answer("x/x = 1", "tous les réels sauf 0").ok is True


def test_one_root_of_two_is_partial_not_wrong():
    v = check_step("x^2 - 5x + 6 = 0", "x = 2")
    assert v.ok is False and v.extra.get("partial") is True


# Found by the second red-team run on 24/09.
def test_two_terms_moved_without_sign_change():
    v = check_step("5x - 3 = 2x + 9", "5x + 2x = 9 - 3")
    assert v.ok is False and v.diagnosis.code == "moved_term_kept_sign"


@pytest.mark.parametrize("claim,ok,code", [
    ("5/6 = 0.83", False, "rounded_not_equal"),
    ("5/6 ≈ 0.83", True, None),
    ("5/6 = 0,83", False, "rounded_not_equal"),
    ("5/6 = 0.84", False, "false_statement"),
    ("0/0 = 1", False, "division_by_zero"),
    ("1/2 = 0.5", True, None),
])
def test_claims_rounding_and_zero(claim, ok, code):
    from stepcheck.core import check_claim
    v = check_claim(claim)
    assert v.ok is ok and (code is None or v.diagnosis.code == code)


def test_chained_equalities_and_partial():
    v = check_step("x^2 - 5x + 6 = 0", "x = (5 + sqrt(1))/2 = 6/2 = 3")
    assert v.ok is False and v.extra.get("partial") is True
    bad = check_step("x^2 - 5x + 6 = 0", "x = (5 + sqrt(1))/2 = 5/2")
    assert bad.ok is False and bad.diagnosis.code == "false_statement"


@pytest.mark.parametrize("answer", ["pour tout x différent de zéro", "tous les x sauf 0", "all x except 0",
                                    "tout réel x ≠ 0"])
def test_every_x_except_zero(answer):
    assert check_answer("x/x = 1", answer).ok is True


def test_multiplied_one_side():
    v = check_step("2x/3 = 4", "2x = 4")
    assert v.ok is False and v.diagnosis.code == "multiplied_one_side"
    assert check_step("2x/3 = 4", "2x = 12").ok is True


# Fourth review round (24/09): radicals, lists, commas, "not equal to", ≈ in chains.
def test_square_root_domain_is_kept():
    assert check_answer("sqrt(x - 1) = sqrt(x - 1)", "all real numbers").ok is False
    assert check_step("sqrt(x - 1) = sqrt(x - 1)", "x = x").ok is False
    assert check_step("sqrt(x) = 2", "x = 4").ok is True


@pytest.mark.parametrize("step", ["x = 3, -3", "3 ; -3", "x = +-3", "x = ±3"])
def test_solution_lists_in_steps(step):
    assert check_step("x^2 = 9", step).ok is True


@pytest.mark.parametrize("answer,ok", [("2,3", True), ("2, 3", True), ("2,5", False)])
def test_ambiguous_comma(answer, ok):
    assert check_answer("x^2 - 5x + 6 = 0", answer).ok is ok


def test_decimal_comma_still_a_decimal():
    assert check_answer("2x = 5", "2,5").ok is True


def test_not_equal_to():
    assert check_answer("x/x = 1", "all x not equal to zero").ok is True


def test_approximate_link_in_a_chain():
    assert check_step("2x = 6", "x = 6/2 ≈ 3").ok is True
    assert check_step("2x = 7", "x = 7/2 ≈ 3.5").ok is True
    assert check_step("2x = 7", "x = 7/2 ≈ 4").ok is False


def test_negative_square_with_a_root():
    from stepcheck.core import check_claim
    assert check_claim("(-sqrt(2))^2 = -2").diagnosis.code == "negative_square"
