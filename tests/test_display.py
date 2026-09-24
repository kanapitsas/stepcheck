import pytest

from stepcheck import to_latex


@pytest.mark.parametrize("text,tex", [
    ("3(x - 2) = 12", r"3 \left(x - 2\right) = 12"),
    ("x^2 = -2", r"x^{2} = -2"),
    ("x = sqrt(-2)", r"x = \sqrt{-2}"),
    ("1/2 + 1/3", r"\frac{1}{2} + \frac{1}{3}"),
    ("x^2/x = 0", r"\frac{x^{2}}{x} = 0"),
    ("10 - (x + 3) = 4", r"10 - \left(x + 3\right) = 4"),
    ("5/6 ≈ 0.83", r"\frac{5}{6} \approx 0.83"),
    ("x = ±3", r"x = \pm 3"),
])
def test_written_form_is_kept(text, tex):
    assert to_latex(text) == tex


def test_lists_and_unreadable():
    assert to_latex("x = 2 ou x = 3") == r"x = 2\ \text{ou}\ x = 3"
    assert to_latex("x = ??").startswith(r"\text{")
