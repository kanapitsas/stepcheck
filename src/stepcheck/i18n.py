"""Learner-facing text in English (the reference) and French.

The verifier and the hint engine produce English text only; this module translates their
messages, so the math code stays single-language and a translation can never change a verdict.
Unknown text is returned unchanged (and caught by the tests, which translate every template).
"""

from __future__ import annotations

import re

LANGS = ("en", "fr")

_FR = {
    # mistake diagnoses: feedback, then hint
    "It looks like a term moved to the other side but kept its sign.":
        "On dirait qu'un terme a changé de membre sans changer de signe.",
    "When a term crosses the equals sign, do the same operation to both sides: "
    "subtracting it on one side means subtracting it on the other.":
        "Quand un terme passe de l'autre côté du signe égal, on fait la même opération des deux "
        "côtés : le soustraire d'un côté, c'est le soustraire aussi de l'autre.",
    "One side was multiplied but the other side was not.": "Un membre a été multiplié, mais pas l'autre.",
    "To clear a denominator, multiply BOTH sides by it.":
        "Pour enlever un dénominateur, multiplie les DEUX membres par ce nombre.",
    "Only part of one side was divided.": "Seule une partie d'un membre a été divisée.",
    "Dividing a side means dividing every term on that side, and the other side too.":
        "Diviser un membre, c'est diviser chacun de ses termes, et l'autre membre aussi.",
    "One side was divided but the other side was not.": "Un membre a été divisé, mais pas l'autre.",
    "Whatever you do to one side of an equation, do exactly the same to the other side.":
        "Ce que tu fais à un membre de l'équation, fais exactement la même chose à l'autre.",
    "The number in front of the parentheses was not multiplied by every term inside.":
        "Le nombre devant les parenthèses n'a pas multiplié chaque terme à l'intérieur.",
    "Distribute to each term: a(b + c) = ab + ac.": "Distribue sur chaque terme : a(b + c) = ab + ac.",
    "A minus sign in front of parentheses was not applied to every term inside.":
        "Le signe moins devant les parenthèses n'a pas été appliqué à chaque terme à l'intérieur.",
    "A minus in front of parentheses flips the sign of every term inside.":
        "Un moins devant des parenthèses change le signe de chaque terme à l'intérieur.",
    "Numerators were added together and denominators were added together.":
        "Les numérateurs ont été additionnés entre eux, et les dénominateurs aussi.",
    "To add fractions, first rewrite them with the same denominator.":
        "Pour additionner des fractions, mets-les d'abord au même dénominateur.",
    "(a + b)^2 was written as a^2 + b^2; the middle term is missing.":
        "(a + b)² a été écrit a² + b² : il manque le terme du milieu.",
    "(a + b)^2 = a^2 + 2ab + b^2. Try multiplying (a + b)(a + b) term by term.":
        "(a + b)² = a² + 2ab + b². Essaie de développer (a + b)(a + b) terme à terme.",
    "The square root of a negative number is not a real number.":
        "La racine carrée d'un nombre négatif n'est pas un nombre réel.",
    "A square is never negative, so x^2 = (a negative number) has no real solution.":
        "Un carré n'est jamais négatif : x² = (un nombre négatif) n'a pas de solution réelle.",
    "The square of a negative number was given a negative sign.":
        "Le carré d'un nombre négatif a reçu un signe moins.",
    "A negative times a negative is positive: (-a)^2 = (-a)(-a).":
        "Un négatif fois un négatif donne un positif : (-a)² = (-a)(-a).",
    "Without parentheses, the minus sign is not squared.":
        "Sans parenthèses, le signe moins n'est pas élevé au carré.",
    "-a^2 means -(a^2); only (-a)^2 squares the minus sign.":
        "-a² veut dire -(a²) ; seul (-a)² élève le moins au carré.",
    "Division by zero is not defined.": "La division par zéro n'est pas définie.",
    "No number can be divided by zero, not even zero itself.":
        "Aucun nombre ne peut être divisé par zéro, pas même zéro lui-même.",
    "That decimal is a rounded value, not exactly equal.":
        "Ce nombre décimal est une valeur arrondie, pas une égalité exacte.",
    "Keep the exact value (a fraction or a square root), or write ≈ for a rounded value.":
        "Garde la valeur exacte (fraction ou racine), ou écris ≈ pour une valeur arrondie.",
    "Correct as a rounded value.": "Juste, en valeur arrondie.",
    "This equality between numbers is false.": "Cette égalité entre nombres est fausse.",
    "Re-do this calculation step by step.": "Refais ce calcul étape par étape.",
    "Everything is right except one sign.": "Tout est juste sauf un signe.",
    "Re-check the signs one term at a time.": "Revérifie les signes, un terme à la fois.",
    "The method is right, but a number is off.": "La méthode est juste, mais un nombre est faux.",
    "Your method is correct. Re-do the arithmetic on the last line carefully.":
        "Ta méthode est correcte. Refais calmement le calcul de la dernière ligne.",
    # notes
    "The previous line and this line are not the same kind (one is an equation, the other is not).":
        "La ligne précédente et celle-ci ne sont pas du même type (l'une est une équation, l'autre non).",
    "Correct, but there is another solution.": "Juste, mais il y a une autre solution.",
    "Check again: can this equation ever be true?": "Vérifie encore : cette équation peut-elle être vraie ?",
    "Check again: is this true for more than one value?": "Vérifie encore : est-ce vrai pour plus d'une valeur ?",
    "Careful: this is true for many values, but not where a denominator is zero.":
        "Attention : c'est vrai pour beaucoup de valeurs, mais pas là où un dénominateur s'annule.",
    "This equation does have specific solutions.": "Cette équation a bien des solutions précises.",
    "The answer should be a number.": "La réponse doit être un nombre.",
    "This equation needs a more careful check.": "Cette équation demande une vérification plus poussée.",
    # tutor
    "Remove the parentheses first: multiply the number in front by every term inside.":
        "Commence par enlever les parenthèses : multiplie le nombre devant par chaque terme à l'intérieur.",
    "Remove the parentheses first: the minus in front changes the sign of every term inside.":
        "Commence par enlever les parenthèses : le moins devant change le signe de chaque terme à l'intérieur.",
    "Write the square as a product: (a + b)^2 = (a + b)(a + b), then multiply each term by each term.":
        "Écris le carré comme un produit : (a + b)² = (a + b)(a + b), puis multiplie chaque terme par chaque terme.",
    "Distribute: multiply the number in front by each term inside the parentheses.":
        "Développe : multiplie le nombre devant par chaque terme dans les parenthèses.",
    "Multiply each term of the first parentheses by each term of the second.":
        "Multiplie chaque terme de la première parenthèse par chaque terme de la seconde.",
    "Hints don't cover equations with the unknown in a denominator yet. "
    "Remember the unknown can't make a denominator zero.":
        "Les indices ne couvrent pas encore les équations avec l'inconnue au dénominateur. "
        "Rappelle-toi que l'inconnue ne peut pas annuler un dénominateur.",
    "Hints cover equations in one unknown.": "Les indices couvrent les équations à une inconnue.",
    "Hints cover linear equations like 3x + 5 = 20.": "Les indices couvrent les équations du premier degré comme 3x + 5 = 20.",
    "I can't find a safe next step for this line.": "Je ne trouve pas d'étape suivante sûre pour cette ligne.",
    # server
    "Got it. What is your first step?": "C'est noté. Quelle est ta première étape ?",
    "Tell me the problem first.": "Dis-moi d'abord l'exercice.",
    "I could not read that as math. Could you say it again, slowly?":
        "Je n'ai pas compris ces maths. Tu peux répéter, doucement ?",
    "I don't know that exercise number.": "Je ne connais pas ce numéro d'exercice.",
    "That exercise belongs to someone else.": "Cet exercice appartient à quelqu'un d'autre.",
    "Which problem is this the answer to?": "C'est la réponse à quel exercice ?",
    "I can't check that one reliably. Let's ask a grown-up to look at it.":
        "Je ne peux pas vérifier celui-là de façon fiable. Demandons à un adulte de regarder.",
    # exercise prompts and skills
    "Solve for x.": "Résous en x.",
    "Solve for x. Show the line after you distribute.": "Résous en x. Montre la ligne après avoir développé.",
    "Add and simplify.": "Additionne et simplifie.",
    "Expand.": "Développe.",
    "Solve by factoring. There are two answers.": "Résous en factorisant. Il y a deux solutions.",
    "Solve two-step equations like 3x + 5 = 20": "Résoudre des équations en deux étapes comme 3x + 5 = 20",
    "Move terms across the equals sign, e.g. 12 - x = 5": "Faire passer un terme de l'autre côté du signe égal, ex. 12 - x = 5",
    "Distribute, then solve, e.g. 4(x - 3) = 20": "Développer puis résoudre, ex. 4(x - 3) = 20",
    "Handle a minus in front of parentheses, e.g. 9 - (x + 2) = 3": "Gérer un moins devant des parenthèses, ex. 9 - (x + 2) = 3",
    "Add fractions with different denominators": "Additionner des fractions de dénominateurs différents",
    "Expand (x + a)^2": "Développer (x + a)²",
    "Solve x^2 + bx + c = 0 by factoring": "Résoudre x² + bx + c = 0 en factorisant",
}

_OP = {"subtract": "soustrais", "add": "ajoute", "multiply": "multiplie", "divide": "divise"}

# (English pattern, French template) for parametrised text
_PATTERNS = [
    (r"Gather the (?P<n>\w) terms on one side: (?P<op>subtract|add) (?P<t>.+) on both sides\.",
     "Regroupe les termes en {n} d'un même côté : {op} {t} aux deux membres."),
    (r"Swap the two sides so that (?P<n>\w) is on the left\.",
     "Échange les deux membres pour que {n} soit à gauche."),
    (r"Undo the (?P<c>.+?): (?P<op>subtract|add) (?P=c) on both sides\.",
     "Élimine le {c} : {op} {c} aux deux membres."),
    (r"(?P<n>\w) is already alone: read off the answer\.", "{n} est déjà seul : lis la réponse."),
    (r"(?P<n>\w) is divided by (?P<k>.+?): multiply both sides by (?P<k2>.+?)\.",
     "{n} est divisé par {k} : multiplie les deux membres par {k2}."),
    (r"(?P<n>\w) is multiplied by (?P<c>.+?): divide both sides by (?P=c)\.",
     "{n} est multiplié par {c} : divise les deux membres par {c}."),
    # level-1 hints are the first half of an action, up to the colon
    (r"Gather the (?P<n>\w) terms on one side\.", "Regroupe les termes en {n} d'un même côté."),
    (r"Remove the parentheses first\.", "Commence par enlever les parenthèses."),
    (r"Undo the (?P<c>.+?)\.", "Élimine le {c}."),
    (r"(?P<n>\w) is already alone\.", "{n} est déjà seul."),
    (r"(?P<n>\w) is divided by (?P<k>.+?)\.", "{n} est divisé par {k}."),
    (r"(?P<n>\w) is multiplied by (?P<c>.+?)\.", "{n} est multiplié par {c}."),
    (r"Rewrite every fraction over the common denominator (?P<d>\d+)\.",
     "Mets toutes les fractions au dénominateur commun {d}."),
    (r"Write the square as a product\.", "Écris le carré comme un produit."),
    (r"Distribute\.", "Développe."),
    (r"Rewrite every fraction over the common denominator (?P<d>\d+)\.", "Mets toutes les fractions au dénominateur commun {d}."),
    (r"The unknown in this problem is (?P<n>\w)\.", "L'inconnue de cet exercice est {n}."),
    (r"Right, as long as (?P<c>.+)\.", "Juste, à condition que {c}."),
]


def _one(sentence: str) -> str:
    s = sentence.strip()
    if s in _FR:
        return _FR[s]
    for pat, tpl in _PATTERNS:
        m = re.fullmatch(pat, s)
        if m:
            g = {k: (_OP.get(v, v) if k == "op" else v) for k, v in m.groupdict().items()}
            return tpl.format(**g).replace(" and ", " et ")
    return s


def tr(text: str | None, lang: str = "en") -> str | None:
    """Translate learner-facing text. Hints may chain sentences ('... That gives: 2x = 6')."""
    if not text or lang == "en":
        return text
    if " That gives: " in text:
        action, line = text.split(" That gives: ", 1)
        return f"{_one(action)} Ce qui donne : {line}"
    out = _one(text)
    if out == text.strip() and ". " in text:  # several sentences: translate each
        out = " ".join(_one(p) for p in re.split(r"(?<=\.) ", text))
    return out


def localize(d: dict, lang: str = "en") -> dict:
    """Translate the text fields of a tool result in place and return it."""
    if lang == "en":
        return d
    for key in ("note", "feedback", "hint", "say", "prompt", "why"):
        if isinstance(d.get(key), str):
            d[key] = tr(d[key], lang)
    return d


def english_texts() -> list[str]:
    return list(_FR)
