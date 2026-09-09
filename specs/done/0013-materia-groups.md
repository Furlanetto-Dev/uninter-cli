---
name: materia-groups
description: The matéria list goes from two groups by `vigente` to four decided by precedence over `statusConcluido`, `ofertaFlexivel` and `vigente` — CONCLUÍDAS, EM ANDAMENTO (prazo estendido), EM ANDAMENTO (obrigatórias da fase), PENDENTES OU FUTURAS — shown with current work first; Materia stores the two new fields, and an outdated database schema resets itself at start-up. Read before touching the matéria groups, adding a column to an entity, or changing what happens to uninter.db when the models change.
projects: [crawler, api, frontend]
status: done
created_at: 2026-09-09
---

# Four groups of matérias

## TL;DR
- `Materia` gains `concluida` and `oferta_flexivel`, from the AVA's `statusConcluido` and `ofertaFlexivel`.
- Groups are decided in order: concluída → `CONCLUÍDAS`; else flexível → `EM ANDAMENTO (prazo estendido)`; else vigente → `EM ANDAMENTO (obrigatórias da fase)`; else `PENDENTES OU FUTURAS`.
- The list shows current work first: obrigatórias da fase, prazo estendido, pendentes ou futuras, concluídas last. Plain title rows, as today.
- A database whose tables lack a column the models declare is deleted and rebuilt at start-up, the way Invalidate cache does.

Today the list has `EM CURSO` and `FINALIZADAS`, split on `vigente` alone. That puts two matérias already concluded under EM CURSO next to the two being taken, and hides Pré-Cálculo, running on an extended deadline, among twenty finished ones. Context in [CONTEXT.md](../../CONTEXT.md); the two groups in [0004](0004-textual-tui.md) and how they are built in [0008](0008-building-the-materias-list.md); the reset in [0007](0007-background-queue-and-reset.md); names in [0009](0009-english-code-portuguese-domain.md).

## Observed behaviour
- The captured matérias response (a `Captura` from 0010, 27 salas) carries `statusConcluido`, `ofertaFlexivel` and `vigente` on every item. Neither of the first two is stored today.
- The four combinations all occur: 14 concluídas (12 of them not vigente, 2 vigente), 1 flexível and not concluída, 2 vigentes not concluídas nor flexíveis, 9 neither. The sala without `modulo`, the coordinator channel, is already dropped by the DTO.
- `MateriaRepository.list_all` orders by `vigente desc, nome`; the list then re-splits by `vigente`. The order inside a group is the name.
- `create_all` creates missing tables and never alters existing ones, so a new column on `Materia` is invisible to an existing `uninter.db` and the first `select` fails. Known SQLAlchemy behaviour, recorded in 0010.

## Decisions

### `Materia` stores the two flags the AVA already sends
`concluida: bool = False` from `statusConcluido` and `oferta_flexivel: bool = False` from `ofertaFlexivel`, on the entity and the DTO, with `to_materia` carrying them. Portuguese fields, as the rest of the entity. The debug panel shows them with no extra work.

### The group is a precedence list, decided in the api
`Situacao` replaces `Vigencia` in `api/materias/aggregate.py`: `CONCLUIDA`, `PRAZO_ESTENDIDO`, `OBRIGATORIA_DA_FASE`, `PENDENTE`. `situacao_of(materia)` applies the four rules in the order given — the first that matches wins, so a concluída vigente is concluída — and `aggregate_materias` returns the non-empty groups. The list only draws.

### Current work first, concluídas last
Display order is `OBRIGATORIA_DA_FASE`, `PRAZO_ESTENDIDO`, `PENDENTE`, `CONCLUIDA`. The cursor opens on the first matéria and 14 of 26 are concluídas; showing them first would push what is being taken below the fold. The rule order stays the precedence, not the layout.

### Titles without the word DISCIPLINAS, as plain rows
`EM ANDAMENTO (obrigatórias da fase)`, `EM ANDAMENTO (prazo estendido)`, `PENDENTES OU FUTURAS`, `CONCLUÍDAS`, in the `TITLES` dict of `cli/materias/list.py`. Every row in that list is a disciplina, so the prefix carries nothing, and the longest title drops from 47 to 36 characters, inside the 42 the list has. They stay dim, disabled `Option` rows the cursor skips, exactly the mechanism of 0004; the list does not become a tree here.

### Inside a group, by name
The repository orders by `nome` only; the group now carries the meaning `vigente` carried in the sort.

### A schema behind the models resets the database
`db_session` compares each mapped table's columns, from `PRAGMA table_info`, with the model's; if a column is missing, it disposes the engine, deletes the file and creates it again, then opens the session. It is the reset of 0007 triggered by the code instead of the palette: the database is a cache of the AVA, and the sweep rebuilds it in about 40 seconds. Only missing columns are detected; renames and type changes are out of scope.

### Nothing else moves
The `●` mark, the sweep, `highlighted_materia`, `select_first`, `d home` and the debug panel keep their behaviour. Two titles become four, and two of today's EM CURSO rows move to CONCLUÍDAS.

## Rejected
- **Displaying the groups in the rule order.** CONCLUÍDAS first means opening the app on a finished matéria and scrolling past 14 rows to reach the current one.
- **Keeping the DISCIPLINAS prefix.** Two titles would clip on a 44-cell list or force it wider for a word the context already gives.
- **Collapsible groups in the list.** The list is an `OptionList` with a spinner redrawn per row; turning it into a `Tree` is its own spec, and with concluídas last there is nothing urgent to fold.
- **`ALTER TABLE ADD COLUMN` at start-up.** No resync, but the flags stay `False` until a Reload matérias, so every matéria shows as PENDENTES OU FUTURAS in between.
- **Requiring a manual Invalidate cache.** The old database fails to open before the palette is reachable.
- **Deriving "concluída" from the notas or the período.** The AVA states it; guessing it from grades would disagree with the AVA on exames and recuperações.

## What execution corrected
- `Situacao` replaced `Vigencia` in `api/materias/aggregate.py` with `situacao_of` as the precedence list and `DISPLAY_ORDER` as the layout; `MateriaRepository.list_all` orders by `nome` alone.
- `db_session` checks `PRAGMA table_info` for every mapped table before `create_all` and recreates the file when a model column is missing; only additions are detected.
- Verified headless: the five combinations group and display in the decided order, the list opens on the first obrigatória, an old-schema database with a row in it is rebuilt empty with the new columns, and the atividades and debug flows still pass. On the real database, the first launch after this change resets it: 2 obrigatórias, 1 prazo estendido, 9 pendentes, 14 concluídas.

