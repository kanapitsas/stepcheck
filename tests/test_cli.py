import json

from stepcheck.cli import main


def test_cli_step_names_the_mistake(capsys):
    assert main(["step", "3(x - 2) = 12", "3x - 2 = 12"]) == 1
    assert json.loads(capsys.readouterr().out)["mistake"] == "partial_distribution"


def test_cli_hint_in_french(capsys):
    assert main(["hint", "2x + 4 = 10", "--level", "2", "--lang", "fr"]) == 0
    assert "soustrais 4 aux deux membres" in json.loads(capsys.readouterr().out)["hint"]


def test_cli_unreadable(capsys):
    assert main(["answer", "2x = 6", "x = ??"]) == 2
