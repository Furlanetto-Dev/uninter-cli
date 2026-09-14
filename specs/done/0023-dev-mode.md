---
name: dev-mode
description: A dev mode that persists in `config.json` and seeds one mocked matéria — atividades, trabalhos and a prova — into its own category, replacing the mock that stands in for every prova today. Read before touching the prova source, adding a matéria category, or storing anything that must outlive the reset.
projects: [all]
status: done
created_at: 2026-09-13
---

# Dev mode

## TL;DR
- `config.json` beside the database holds what the app itself writes; `.env` keeps being credentials nobody's code edits. Dev mode is its first entry, and the command palette toggles it.
- Dev mode seeds one matéria with everything a matéria can have, under a new `MOCKADA` situação and its own heading in the list.
- The mock stops standing in for the AVA: with dev mode off, starting a real prova says the call is not written yet. Only a mocked atividade opens a mocked prova.
- `crawler/atividades/prova_mock.py` and its captured JSON go; the fixture is written as entities, not parsed from a response.
- Seeding is idempotent and reversible: turning dev mode off deletes the mocked rows, and the reset takes them with the database.

`MockProvaSource` was a stopgap from [0015](../done/0015-atividade-completion.md) that never stopped being wired in, so today every prova in the app is a mock reading one captured file. Making it a feature means saying which matéria is fake and letting the rest of the app be honest.

## Observed behaviour
- `main.py` passes `MockProvaSource(CAPTURE)` unconditionally; a real atividade and a fake one open the same file.
- `MateriaRepository.save` merges and never deletes what the AVA did not return, so a seeded matéria survives a sync untouched. Nothing else in the app deletes a matéria.
- `enqueue_pending` queues every matéria whose collections were never synced, and `r` refreshes whatever is highlighted — both would send a fake oferta to the AVA.
- The reset deletes `uninter.db`; a schema change recreates it. Anything stored in the database is gone on both counts.
- `Situacao` decides the headings, and `situacao_of` reads only the flags already on `Materia`.

## Decisions

### `config.json` is what the app writes, `.env` is what you write
Credentials are hand-edited and read through `pydantic-settings`; preferences are written by the app while it runs. Two files because they have two authors, and because the reset must be free to delete the database without taking your settings with it.

### The mocked matéria is flagged, not detected
`Materia.mockada` — a column, not a negative id or a name match. `situacao_of` returns `Situacao.MOCKADA` for it, the seed sets it, and every other decision in the app reads the same flag instead of guessing.

### `MOCKADAS` comes first, and reads like its neighbours
It heads the list so the mocked matéria is the one already selected when the app opens in dev mode — the point of the mode is to reach it without hunting. The other headings are Portuguese and none of them repeats the word matéria — `EM ANDAMENTO`, `PENDENTES OU FUTURAS`, `CONCLUÍDAS` — so the new one is `MOCKADAS`, following [0009](../done/0009-english-code-portuguese-domain.md). The enum member is `Situacao.MOCKADA`, like its neighbours.

### Nothing mocked is ever fetched
The seed stamps both collections as synced, so the queue never picks it up, and `refresh_materia` skips a mocked matéria rather than sending a fake oferta to the AVA. The debug panel gets seeded capturas, so the AVA column shows the fixture instead of "sem resposta gravada".

### The fixture is entities, not a captured response
One matéria that carries every state the interface can draw: an APOL awaiting início and one already done, a prova presencial, an overdue atividade nobody did, trabalhos aprovado, reprovado, em correção, aberto and não entregue, and a prova whose questões can be answered. Written as `Materia`, `Atividade`, `Trabalho` and `Prova` objects, so it says what it covers instead of hiding it inside a JSON body.

### A real prova admits it is not written
With the mock scoped to the mocked matéria, starting a real one is honest about the missing AVA call. That is a visible change and the point of the spec.

## Rejected
- **Serving the mock at read time instead of storing it.** Cleaner isolation, but every repository grows a wrapper and the debug panel loses its captura. Rows cost a seed and a delete, and the merge means a sync cannot fight them.
- **A preferences table in the database.** The reset would switch dev mode off exactly while you were testing the reset.
- **`UNINTER_DEV_MODE` in `.env`.** It follows the settings rule, but it is set by editing a file and restarting, not by an option in the app.
- **A restart to apply the toggle.** The palette entry seeds or deletes the rows and reloads the list, the same as any other command; a mode you have to restart into is a flag, not an option.
- **Writing the real start call here.** It is the feature this spec stops the mock from impersonating; it deserves its own.

## What execution corrected
- **Seeding has to finish before the page reads.** Put in the app's `on_mount` it ran concurrently with the page's, and one `AsyncSession` refuses that outright — "this session is provisioning a new connection". Put in `fetch_pending` it ran *after* the list was built, so the mocked matéria was in the database and not on screen. The page calls `uninter.prepare()` and then loads.
- **The matérias captura is the one that cannot be seeded.** It is keyed by `materia_id=None`, and `CapturaRepository.replace` deletes the row it replaces, so seeding it would throw away the real one. Atividades and trabalhos are per matéria and are seeded; the debug panel therefore says the mocked matéria is not in the AVA's last list, which is true.
- `Config` carries the path it was loaded from in a `PrivateAttr`, so `save()` writes back where `load()` read. Without it every save went to the repo root and a test could not use its own file.
- `follow()` only deletes when something is there: with dev mode off it was running four DELETEs and a commit at every startup.
- `config.json` joins `.env` and `*.db` in `.gitignore` — it is state belonging to the machine, not to the repo.
- `MOCKADAS` was written last in the display order and moved to the front: a fixture you have to scroll to is a fixture you stop using.
- Verified against a copy of the database, never the real one: toggling seeds five atividades, five trabalhos and both capturas; the heading `MOCKADAS` appears; a restart with `dev_mode: true` seeds before the first frame; the mocked prova answers with three questões; a real atividade is refused; and toggling off leaves no mocked row behind.
