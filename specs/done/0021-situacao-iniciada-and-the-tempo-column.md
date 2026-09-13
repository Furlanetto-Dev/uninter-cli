---
name: situacao-iniciada-and-the-tempo-column
description: The atividades tree shows `Iniciada` for an atividade the app has open, instead of the AVA's `Aguardando início`, and the `Tempo` column moves to sit right after `Situação`. Read before touching the tree's columns or the situação a row shows.
projects: [frontend]
status: done
created_at: 2026-09-13
---

# The situação Iniciada and the Tempo column

## TL;DR
- A row whose atividade is open in the app reads `Iniciada`, in yellow, where it used to read `Aguardando início`.
- `Tempo` moves from last to right after `Situação`; `Prazo` becomes the last column.
- One signal feeds both: the elapsed time the tree already receives. No new state, no new parameter.
- `Iniciada` is the app's word, so it lives in the tree, not in the `Atividade` table that mirrors the AVA.

[0015](../done/0015-atividade-completion.md) gave the tree a clock but left the situação alone, so a started atividade shows a ticking `Tempo` next to the words `Aguardando início` — the row contradicts itself, and the clock sits at the far right where a narrow terminal crops it first. Context in [CONTEXT.md](../../CONTEXT.md); the tree's columns come from [0012](../done/0012-grouped-atividades.md).

## Observed behaviour
- `uninter.db` holds two situações today: `Aguardando início` (92 atividades) and `Finalizada` (59). Counted with `sqlite3`.
- `Iniciada` is 8 characters against `Aguardando início`'s 17, and `widths_for` sizes the column by the longest situação, floored at the header's own 8 — so the column neither widens nor narrows.
- `FIXED_WIDTH` is the sum of the fixed columns, so reordering them changes no width. Read in `tree.py`.
- The start instant lives in `MockProvaSource`'s dict and never reaches `uninter.db` ([0015](../done/0015-atividade-completion.md)), so `Iniciada` dies with the process — as the attempt it names does.
- Inference: the real source will read `started_at` from `get-tempo-decorrido`, which answers for a finished attempt too. Not measured; no real call has been made.

## Decisions

### The elapsed time is the only signal, and it decides both cells
`_elapsed` returns a duration only for an atividade that is started *and* still `aguardando_inicio` at the AVA; `leaf_label` renders `Iniciada` and the clock from that one value. The AVA wins when it says the attempt is over: a `Finalizada` row shows its own situação and an empty `Tempo`, whatever the source still remembers. Today nothing changes — the mock sends nothing, so the situação never turns — and it is what keeps the real source from leaving a row running forever.

### `Iniciada` is yellow, and it lives in the tree
Yellow is what the app already uses for open — the trabalhos' `aberta`, the média between 30 and 69 — against green for done and dim for inert. The constant sits in `tree.py` beside the other screen text, not next to `AWAITING_START` in the entity: the entity is a mirror of the AVA, and the AVA never sends this word.

### `Tempo` sits next to `Situação`, and `Prazo` goes last
`Situação` and `Tempo` are the same fact twice — what the attempt is doing, and for how long — so they are read together. It also moves the only cell that changes every second away from the edge that crops first on a narrow terminal, and leaves the static `Prazo` where cropping costs least. The order lives in two literal sequences, `COLUMNS` and `leaf_label`; both move, or the header lies.

## Rejected
- **Writing `Iniciada` into `Atividade.status`.** `uninter.db` is a mirror of the AVA; a situação the AVA never sent has no row to be written to.
- **A column of its own for "running".** A whole column for one boolean, in a row that already crops at the right.
- **Leaving the situação to the AVA and letting the clock speak.** That is what 0015 shipped, and reading `Aguardando início` beside a running clock is the reason for this spec.
- **Showing `Iniciada` for any atividade with a `started_at`.** It reads well against the mock and rots against the real source, which will remember finished attempts.

## What execution corrected
- Narrowing `_elapsed` is not enough to stop the timer: `_follow_clock` counted any started id present in the tree, so a closed attempt would have kept it firing. It now asks the same `_iniciada` predicate, over the leaves.
- The Situação column never resizes. `widths_for` measures the AVA's own statuses and floors at the header, and `Iniciada` is exactly as long as `Situação` — so the column sits in the same place started or not, which is what keeps the row from jumping when the clock appears.
- The situação's colour still keys on `realizada` (`contribuicao is not None`), not on the status: a `Finalizada` atividade with no contribuição shows dim, as it did before. Untouched here; it only shows up in the smoke because the smoke fakes the flip without a nota.
- Verified headless at 160×34 and 110×34 over a copy of `uninter.db`: the header reads `Atividade Situação Tempo Tentativa Nota Peso Contribuição Prazo`; a `Finalizada` row is green with an empty `Tempo`; `⏎` then `SIM` opens the prova, and back on the tree the row reads `Iniciada` in yellow with `00:00` counting to `00:01`; flipping that atividade's status to `Finalizada` restores its own situação, empties `Tempo` and stops the clock. `ruff` and `pyright` strict are clean.
