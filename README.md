# stepcheck

Verify a student's algebra **one line at a time**, and name the classic mistake behind a
wrong line — without giving the answer away.

Built for tutoring tools and AI assistants that must never tell a learner that a wrong line is
right. Language models are good at talking to students and bad at being reliably right about
algebra; `stepcheck` does the "right or wrong" part with a computer algebra system (SymPy),
so the model only has to talk.

```python
>>> from stepcheck import check_step, check_answer, hint
>>> v = check_step("3(x - 2) = 12", "3x - 2 = 12")
>>> v.ok, v.diagnosis.code
(False, 'partial_distribution')
>>> v.diagnosis.message
'The number in front of the parentheses was not multiplied by every term inside.'
>>> check_step("3(x - 2) = 12", "x - 2 = 4").ok        # any valid route is accepted
True
>>> check_answer("x^2 = 9", "x = 3").as_dict()["note"]
'Correct, but there is another solution.'
>>> hint("2x + 4 = 10", level=2)["hint"]
'Undo the 4: subtract 4 on both sides.'

```

## What it does

- **`check_step(previous, new)`** — is `new` a valid next line? Equations are compared by
  solution set (on the domain of the line *as written*: `x^2/x = 0` has no solution), and
  expressions by a symbolic proof that the difference is zero. When a simplification is only
  valid under a condition (`x^2/x → x`), the verdict says so (`x ≠ 0`).
- **Mistake diagnosis** — a wrong line is matched against classic misconceptions:
  a term moved across `=` without changing sign, a factor applied to only one term of the
  parentheses, a minus that reached only one term, dividing only one side or one term,
  fractions added across (`1/2 + 1/3 = 2/5`), `(a + b)^2 = a^2 + b^2`, a sign slip or an
  arithmetic slip. The feedback never contains the answer.
- **`check_answer(problem, answer)`** — any equivalent form (`x = 3/2`, `1.5`,
  `x = 3 or x = -3`), "no solution", "all real numbers", "all real numbers except 0"; the
  answer must use the problem's unknown.
- **`hint(line, level)`** for linear equations — level 1 the idea, level 2 the exact
  operation, level 3 the next line. Every hinted line is verified before it is returned;
  lines it cannot hint safely raise `ValueError` instead of guessing.
- **`generate(skill)`** — practice items for seven skills, each verified before use.
- **English and French** learner-facing text (`tr(text, "fr")`, `localize(result, "fr")`).

Input is refused rather than guessed when it is not homework-sized math: words other than
`sqrt` and `pi`, division by zero, exponent towers, exponents above 20, very long lines.
Every single letter is an unknown (`e` and `i` included).

## Command line

```bash
stepcheck step "3(x - 2) = 12" "3x - 2 = 12"
stepcheck answer "x^2 = 9" "x = 3 or x = -3"
stepcheck hint "2x + 4 = 10" --level 2 --lang fr
```

Exit code 0 for a valid line, 1 for a wrong one, 2 for unreadable input.

## Evaluation

`uv run pytest` — unit tests including adversarial cases found in review (wrong unknown,
`e`/`i` as unknowns, vanishing denominators, numeric coincidences, exponent towers).

`uv run python eval/soundness.py 400 11` — correct lines from the hint engine versus wrong
lines made by random textual perturbations (flip a sign, change a digit, drop a term), with
code that shares nothing with the diagnosis:

| | lines | verdict errors |
|---|---|---|
| correct lines | 1,000 | 0 rejected |
| wrong lines | 924 | 0 accepted |

A specific misconception is named for 96 % of the wrong lines (mostly, and rightly,
"arithmetic slip" for random digit changes). The accept/reject verdict rests on symbolic
equivalence, so this mainly shows that parsing and edge cases hold; the misconception labels
are heuristics with a fixed catalogue.

## Scope

Algebra from roughly grades 6–10 (collège / seconde): linear equations, distribution,
fractions, squares of a sum, quadratics by factoring. Contributions for more topics are
welcome.

Used by [Stepwise](https://github.com/kanapitsas/stepwise), a math homework coach for Alexa+.

## License

MIT
