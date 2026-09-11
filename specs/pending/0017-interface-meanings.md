---
name: interface-meanings
description: The 59 colour literals spread over 12 modules become six named meanings in `cli/style.py` — muted, done, notice, problem, tag, working — plus the two marks and the one deadline rule that is written twice. Read before choosing a colour, adding a glyph, or styling a prazo.
projects: [frontend]
status: pending
created_at: 2026-09-11
---

# The interface names meanings, not colours

## TL;DR
- `cli/style.py` holds six names — `MUTED`, `DONE`, `NOTICE`, `PROBLEM`, `TAG`, `WORKING` — each a Rich style with one line saying what it marks. Modules write `DONE`, never `"green"`.
- The two marks go with them: `●` and `○`, whose meaning today depends on which module you open.
- `format.py` gains the prazo rule that `atividades/tree.py` and `trabalhos/table.py` each implement: dim once done, `PROBLEM` once late and still undone.
- `atividades/media.py` keeps its literals — there the colour is the datum, not a state.
- Shapes are [0016](0016-cli-components.md)'s subject; a component there takes its colours from here.

The colours agree with each other by luck rather than by construction: green means done in three modules that never met, and yellow means four different things. [0015](../done/0015-atividade-completion.md)'s prova screen picked its own before settling on the app's, and `provas/list.py` has already given up and defined `ANSWERED_STYLE` locally — the need for a name is felt, one module at a time. Context in [CONTEXT.md](../../CONTEXT.md).

## Observed behaviour
Counted over `src/cli` today: 59 opening colour literals in 12 of the 21 modules.
- `dim` 37, `yellow` 7, `red` 6, `green` 6, `magenta` 2, `cyan` 1.
- Green marks a realizada in `atividades/tree.py`, an aprovado in `trabalhos/table.py` and an answered questão in `provas/list.py` — three modules, one meaning, no shared name.
- Yellow marks an empty collection in three modules, an open trabalho in a fourth, the prova's warning in a fifth, and the exam band in `media.py`. Five of those are one meaning; the sixth is a number.
- Red marks a prazo that passed with the work undone, a reprovado, and a 4xx body in the debug panel.
- `●` is the pending mark in `materias/list.py` and the answered mark in `provas/list.py`; `○` is the unanswered one. The glyph is shared, the meaning is carried by a colour chosen locally.
- `atividades/tree.py::_deadline` and `trabalhos/table.py::_deadline` implement the same rule with different return types.

## Decisions

### Code names the meaning, never the colour
Six names for what the app already says: `MUTED` for everything secondary, `DONE` for work that is finished, `NOTICE` for something waiting or missing, `PROBLEM` for a deadline missed or a request refused, `TAG` for a word that labels an item, `WORKING` for a fetch in progress. Each is one line in `cli/style.py` with what it marks — the reason a later screen can pick the right one without reading three modules.

### A meaning gets a name even with one caller
`WORKING` is the sync spinner and nothing else today. Naming it is what stops the next spinner from choosing its own cyan, which is exactly how green ended up defined in three places.

### The marks are part of the vocabulary
`●` and `○` move to `cli/style.py` beside the colours, because what they mean is the pair glyph-plus-style and splitting them across modules is what let one glyph mean two things.

### The prazo rule lives in `format.py`
Dim when the work is done, `PROBLEM` when the date passed and it is not: one function taking a date, a now and a boolean. It belongs with the other formatting and needs no domain type, so both callers can reach it.

### `media.py` keeps its literals
Its green, yellow and red are the AVA's published cut-offs, not states of the interface. Writing `DONE` where the AVA says "aprovado" would hide the one place a colour carries a number.

## Rejected
- **A Textual theme, or CSS variables alone.** More than half the colours are in Rich markup inside rows and labels, where the stylesheet does not reach.
- **One name per colour.** `dim` is used for the secondary text, the disabled heading and the finished-but-late prazo; a `DIM` constant would rename the problem.
- **Renaming `media.py`'s scale to these six.** Covered above, and it is the one place where the colour is data.
