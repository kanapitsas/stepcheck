import pytest

from stepcheck.core import check_step
from stepcheck.hints import hint, next_move


@pytest.mark.parametrize("line", ["2x + 4 = 10", "3(x - 2) = 12", "5x - 3 = 2x + 9", "12 - x = 5",
                                  "7 = 2x - 1", "(x + 1)/2 = 3", "x/4 = 3", "2y = 6", "-(x - 4) = 1", "10 - (x + 3) = 4"])
def test_every_hint_is_a_valid_step_that_makes_progress(line):
    action, nxt = next_move(line)
    assert nxt.replace(" ", "") != line.replace(" ", "")
    assert check_step(line, nxt).ok


def test_hint_uses_the_real_unknown():
    assert "y" in hint("2y = 6", 2)["hint"] and "x" not in hint("2y = 6", 2)["hint"]


def test_fraction_hint_does_not_talk_about_a_number_in_front():
    h = hint("(x + 1)/2 = 3", 2)["hint"]
    assert "in front" not in h


@pytest.mark.parametrize("line", ["x^2/x = 0", "sqrt(x) = 2", "1/x = 2", "x^2 = 4"])
def test_unsupported_lines_are_refused_not_guessed(line):
    with pytest.raises(ValueError):
        next_move(line)


def test_levels_one_and_two_never_contain_the_next_line():
    h1, h2, h3 = (hint("2x + 4 = 10", k) for k in (1, 2, 3))
    assert h3["next_line"] not in h1["hint"] and h3["next_line"] not in h2["hint"]


def test_minus_before_parentheses_gets_its_own_hint():
    action, nxt = next_move("10 - (x + 3) = 4")
    assert "minus" in action and nxt.replace(" ", "") == "7-x=4"
