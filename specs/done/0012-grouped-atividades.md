---
name: grouped-atividades
description: The atividades table becomes a Tree with three collapsible groups decided by name — APOL, PROVAS and Outras, the last holding recuperação, exame, segunda chamada and simulados — with leaves indented under their group, a header line aligned to them, and the expanded state kept for the session. Read before touching how the atividades pane builds its rows, moves its cursor, or what Enter does on it.
projects: [frontend]
status: done
created_at: 2026-09-09
---

# Grouped atividades

## TL;DR
- The atividades pane is a `Tree`: one node per group, `APOL`, `PROVAS`, `Outras`, one indented leaf per atividade.
- `Outras` holds recuperação, exame, segunda chamada and every simulado. It opens by itself when the matéria can no longer reach 70 or a prova went past its deadline undone, and stays closed otherwise; `APOL` and `PROVAS` start open and remember toggles for the session. `Enter` or `space` toggles any group.
- Groups are decided by the atividade's name: Outras keywords first, then the `APOL`, `Prova` and `Simulado` prefixes.
- Labels are padded to shared column widths, so the six columns stay aligned across groups under a header line above the tree.

A matéria shows up to ten atividades in one flat list, and half of them are exames, recuperações and simulados that only matter after something went wrong. Grouping puts the two things you check every week on top and folds the rest. Context in [CONTEXT.md](../../CONTEXT.md); the selectable table this replaces in [0010.1](0010.1-selectable-atividades.md), the pane it lives in since [0011](0011-tabbed-detail-panel.md), the debug panel it feeds in [0010.2](0010.2-debug-panel-focus-and-copy.md).

## Observed behaviour
- The database holds 151 atividades: 42 start with `APOL`, 32 are provas `(Regular)`, 62 carry `Exame`, `Recuperação` or `Segunda Chamada` in the name, 15 start with `Simulado`, none is left over. Counted with a query on `uninter.db`.
- Names are not clean: `Prova Objetiva  (Exame)` has two spaces, `APOL 2 ` a trailing one. Any rule on names has to collapse whitespace and ignore case.
- The AVA's `tipo` never says whether a prova is regular, exame or recuperação; that variant lives only in the name's parentheses.
- Textual 8.2.8 `Tree` binds only `shift+arrows`, `enter` and `space` besides `↑`/`↓`, so `←`/`→` stay free; `enter` toggles a node with children and `space` toggles any node. Labels are `Text`, not arbitrary renderables. Unlike `DataTable`, `Tree` has no default height rule, so it fills its container unless told otherwise. Checked in the source and in a probe.

## Decisions

### Three groups, by name, with Outras winning ties
Normalise the name (collapse whitespace, casefold), then: a name containing `recuperação`, `exame`, `segunda chamada` or `substitutiva`, or starting with `simulado`, goes to `Outras`; else `apol` goes to `APOL`; else `prova` goes to `PROVAS`; anything else also goes to `Outras`. Order inside a group is the AVA's `posicao`. Outras is checked first because `Prova Objetiva (Exame)` starts with `Prova`. Empty groups get no node.

### Simulado lives inside Outras
It is practice with no weight, almost always `Aguardando início`. Folding it with the exames is the point of the dropdown.

### The pane is a `Tree`, one node per group, one leaf per atividade
`AtividadeTree` replaces the `DataTable` of 0010.1. The tree draws the `▼`/`▶` markers and indents leaves under their group by itself, which is what a dropdown looks like and what a table cannot do. Group labels are `APOL (2)`, `PROVAS (2)`, `Outras (4)`, bold, with the count so a collapsed group still says how much it hides. The App API stays: `show`, `select`, `select_or_first`, `selected`, the `Selected` message; `row_count` becomes `has_atividades`.

### Group nodes are cursor stops; `Enter` and `space` toggle them
Landing on a group is how you open it, so the cursor stops there; a group under the cursor means no atividade selected, and the debug panel shows the matéria's own data as in 0010.1. `Enter` on a leaf stays reserved, as 0010.2 decided. `→` from the list lands on the first visible atividade, not on the `APOL` node.

### Columns stay aligned by padding the labels, under a header line
Every leaf label is built with the same column widths: the numeric columns are fixed, the status column takes its longest value, and the name column gets what is left of the pane width, between 20 and 48 characters, with an ellipsis beyond that. The tree refits on resize and tells the header the new widths, so the two never disagree and the pane never scrolls sideways for the name alone. All leaves sit at the same depth, so the columns line up across groups. `AtividadeHeader`, a `Static` above the tree, prints the column titles with the same widths and the leaf indent.

### `APOL` and `PROVAS` remember their state; `Outras` opens when it matters
`APOL` and `PROVAS` start open and keep whatever you toggle for the session, across matérias, `r` and `d home`. `Outras` is decided per matéria when you land on it: open if the matéria cannot reach 70 any more (the launched média plus every point still available is below `PASSING_GRADE`), or if a prova in `PROVAS` is past its deadline and not done — the two cases where the exame or the segunda chamada inside it becomes the next thing to do. Otherwise it stays closed. A toggle on `Outras` lasts until you move to another matéria. An atividade inside a collapsed group cannot be selected, so a selection folded away clears itself.

### Nothing else moves
`MediaBar` still computes over every atividade. `→` into the debug panel, `←` to the list, `ctrl+c`, `j`, the tabs of 0011 and the row cells of 0010.1 keep their meaning.

## Rejected
- **A `DataTable` with title rows and a toggling Outras row.** Built first: rows cannot indent or span, a title band only covered its own cell, and skipping titles with the cursor felt arbitrary. The user rejected it on sight.
- **A fourth group for Simulado, last.** The first phrasing of the request; it is practice with no weight.
- **Grouping by `tipo`/`categoria`.** Cannot tell `(Regular)` from `(Exame)`; the name has to be read anyway.
- **`Collapsible` widgets, one per group, each with a table.** Three tables, three cursors and a hand-off between them; alignment would need fixed widths anyway.
- **Always expanded, titles only.** Hides nothing, which was the point.
- **Outras remembering its state for the session.** The grill's first answer; replaced by the automatic rule, since an open Outras should mean something is wrong in this matéria, not that it was open in the last one.
- **Reading "média below 70" literally while weight is still to be launched.** Every fresh matéria has a média of 0, so Outras would open everywhere; "cannot reach 70 any more" is the decidable version.

## What execution corrected
- `Tree` has no default height, so it took the whole pane and left the debug panel with zero rows; `AtividadeTree` now has `height: auto; max-height: 100%`, the rule `DataTable` ships with.
- `move_cursor` right after a rebuild reads stale line numbers; the tree touches `last_line` first so the lines are built.
- Verified headless: the real database groups into APOL 42, PROVAS 32, Outras 77; the full-app flow covers the node order, the cursor stopping on groups, `Enter` and `space` toggling with the cursor staying put, APOL collapsing and reopening, the state surviving a matéria change and `d home`, and the debug-panel flow of 0010.2 unchanged.
- Executed alongside 0011.1 in the same working tree; the shared file was the atividades module, and both edits survived.
