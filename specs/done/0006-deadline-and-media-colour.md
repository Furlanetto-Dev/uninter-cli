---
name: deadline-and-media-colour
description: Two columns of information that were already in the database and did not appear — the deadline of each atividade and the média's status by the AVA's own bands, with the yardstick written on screen. Covers the grade's 0–100 scale, the 67–69 band the AVA does not cover and why the partial média gets no colour. Read before touching cli/atividades.py or anything that colours a grade.
projects: [frontend]
status: done
created_at: 2026-09-02
---

# Deadline and colour on the média

The matéria's table shows name, status, grade, weight and contribution. It lacks the two things the student actually wants to know on opening a matéria: **until when** each atividade counts, and whether the média **passes**. The first has been in the database from the start and was never drawn; the second needs a yardstick, and the AVA publishes its own.

This spec only touches what the screen draws: no new request, no new database column, no signature changed. What the project is lives in [CONTEXT.md](../../CONTEXT.md), the interface in [0004](0004-textual-tui.md) and the tests in [0002](../pending/0002-testing-strategy.md).

## Observed behaviour

Measured on 2026-09-02 against the account's real `uninter.db`, with 26 matérias and 37 atividades:

- **`inicio` and `fim` come filled in 37 of 37.** They have been persisted since [0001](0001-ava-atividades-crawler.md) and were never displayed. The type stays optional, but in practice the data is always there.
- **The grade is 0–100, not 0–10.** The account's values run from 60 to 100, and `contribuicao = nota × peso / 100` — grade 100 with weight 15 gives a contribution of 15,0; grade 70 with weight 40 gives 28,0. Since `Media.valor` is the sum of the contributions, **the média is already on the same 0–100 scale as the AVA's criteria**, with no conversion at all.
- **Status and deadline disagree.** 8 atividades with status `Aguardando início` have `fim` in the past, and 7 `Finalizada` have `fim` in the future. The deadline column cannot be styled from `status`: "overdue" only comes from comparing `fim` with the clock.
- **The AVA publishes its own approval criteria** on the sala virtual screen, under "Critérios de aprovação (período Regular)": `de 70 até 100` APR.MÉDIA, `de 30 até 66` EM EXAME, `de 0 até 29` REP.MÉDIA. The screen has three tabs — Regular, Exame and Recuperação — each with its own table.
- **The published table skips 67, 68 and 69.** It goes from "até 66" straight to "de 70", and none of the three statuses covers that band.
- **Only 2 of the 5 matérias with atividades have 100% of the weight posted.** The other three sit at 30%, 0% and 0% — the partial state is the norm, not the exception.

Not measured: the criteria came from the screen, not from a captured endpoint. The Exame and Recuperação bands were not seen.

## Decisions

### The deadline is a column, and comes from `fim`

A `Prazo` column at the end of the table, with `fim` formatted as `dd/mm/aa`. The year is mandatory: the account's atividades run from 2025 to 2026 and a bare `dd/mm` would be ambiguous between semesters.

Overdue and not done shows in red; overdue and done, dimmed, because the deadline no longer decides anything. The cut comes from comparing with the clock, not from `status` — by the observed data, the two disagree in 15 of the 37 atividades.

### The média's colour uses the AVA's own yardstick

`≥ 70` green, `30–69` yellow, `< 30` red.

The 70 is not our choice: it is what the AVA publishes on the sala virtual screen, with a name of its own — APR.MÉDIA. The colour copies the institution's classification instead of proposing one.

What the colour does **not** do is project: no computing how much is missing to pass, no simulating scenarios with the atividades that have no grade yet. It classifies what is already posted, and only that.

### The 67–69 band closes downwards

The AVA's table does not cover 67, 68 and 69. We close the exam interval upwards — `30–69` — instead of leaving three values without colour. It is the conservative reading: a 68 is not approval by média anywhere in the table, and painting it green would claim more than the AVA claims.

It stands recorded as a deliberate divergence from the source, not as a reading of it.

### A partial média gets no colour

The colour only comes in when `peso_lancado` reaches 100. Análise e Modelagem has a média of 22,5 with 30% of the weight posted: by the bands that is REP.MÉDIA, but the matéria has barely started and the student is at 75% of what has been graded so far. The AVA's criteria classify the **closing** of the matéria; applying them to an incomplete sum is using them out of context, and would turn "red" into the normal state of whoever has not sat an exam yet.

The accepted cost is that today only 2 of the 5 matérias would show colour. The `(30% do peso lançado)` already on screen remains what explains the absence.

### The criteria are written below the média

A permanent line under the `MediaBar`, with each band in its own colour:

```
média 76,0  (100% do peso lançado)
≥ 70 aprovado · 30–69 exame · < 30 reprovado
```

It sits next to the number it explains, requires discovering no key, and takes a line that is empty today. Since the yardstick is the same for every matéria, repeating it per matéria is no bother — and without it the colour would be a code without a legend.

### Only the Regular period

The Exame and Recuperação tabs have criteria of their own that were not captured, and no API field says which period the student is in for a matéria. The legend line promises no more than it knows.

### The bands are module constants, not discovery

The three limits live in named constants in `cli/atividades.py`. Nobody goes hunting for the endpoint that serves that table: it is the project's rule, and whatever is missing becomes configuration or a question. If the bands change, the constant changes — and the only way to find out they changed is the same screen they came from.

## Rejected

- **Colouring the partial média with the same bands.** It is "pintar de acordo" to the letter and the colour is never missing. But today it would paint Análise e Modelagem red because of 70% of weight not yet posted, and red would become the default state of mid-semester.
- **Colouring the partial in a dimmed tone.** Would keep a single rule, with the uncertainty in the tone instead of the absence. Discarded because `dim` already means "not done" in the Situação column, and because not every terminal theme separates dim from normal well.
- **Colouring by aproveitamento (`valor / peso_lancado`).** Would solve the partial without losing the colour — 22,5 at 30% would become 75%. But it invents a metric the AVA does not publish and that matches no status in its table; the colour would stop meaning APR/EXAME/REP.
- **Also colouring each atividade's Nota column.** The grade is already 0–100 and would fit the same bands, and would spot at once what pulled the média down. Discarded because the Situação column already uses green and dim with another meaning, and two colour systems side by side compete instead of informing.
- **A legend behind a help key.** Would keep the reading screen clean and would have room to grow when Exame and Recuperação are captured. But it hides exactly what gives the colour its meaning, and pays one more shortcut in the Footer for it.
- **Writing the status (`APR.MÉDIA`) next to the number, without the bands.** Uses the AVA's own vocabulary and answers the student's question directly. Lost to the legend because the colour would still have no visible yardstick — and because the status of a partial média would be a claim the decision above refuses to make.
- **A relative deadline ("vence em 3d").** More readable for what is near, and `humanize_age` already does the analogue for the past. But most of the account's atividades are months away, where "em 87d" tells less than the date, and the relative form forces the screen to reformat as the clock moves.
- **Also showing `inicio`.** It is filled in 37 of 37 and would fit as a "window". Out of scope: the request is the expiry date, and a second date column in a five-column table costs width the atividade's name uses better.

## What execution corrected

- **`Situação` started wrapping onto two lines.** The sixth column squeezed the table, and `Aguardando início` — the status of 27 of the 37 atividades — became a double line. The column gained `no_wrap`; the atividade's name remains the only one that folds.
- **Below ~120 columns the table degrades**, with the name folding and the `Contribuição` header truncating. Accepted: `rich` sorts it out on its own and reading remains possible.

## Execution order

1. **The Prazo column.** `format.py` gains the date formatting and the overdue predicate; `build_table` gains the column. Nothing else changes.
2. **The bands and the colour.** Constants and the function that maps a média to a band; `MediaBar.show` starts colouring, and only when `media.parcial` is false.
3. **The legend line**, below the média.
4. **0002**: layer 1 gains the cases for the two new pure functions, and the `build_table` golden is regenerated with the extra column.
