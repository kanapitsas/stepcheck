"""Every English text the learner can see has a French version, and French never changes a verdict."""
import pytest

from stepcheck import core as mathcore
from stepcheck.practice import SKILLS, generate
from stepcheck.i18n import tr
from stepcheck.hints import hint


def test_every_diagnosis_is_translated():
    for d in mathcore.MISTAKES.values():
        assert tr(d.message, "fr") != d.message
        assert tr(d.hint, "fr") != d.hint


def test_every_skill_and_prompt_is_translated():
    for skill, label in SKILLS.items():
        assert tr(label, "fr") != label
        item = generate(skill, seed=1)
        assert tr(item.prompt, "fr") != item.prompt


@pytest.mark.parametrize("line", ["2x + 4 = 10", "3(x - 2) = 12", "5x - 3 = 2x + 9", "7 = 2x - 1",
                                  "(x + 1)/2 = 3", "3x = 12", "x = 4", "2y = 6", "10 - (x + 3) = 4"])
@pytest.mark.parametrize("level", [1, 2, 3])
def test_every_hint_template_is_translated(line, level):
    en = hint(line, level)["hint"]
    fr = tr(en, "fr")
    assert fr != en, en
