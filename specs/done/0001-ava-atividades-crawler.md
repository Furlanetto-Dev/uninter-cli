---
name: ava-atividades-crawler
description: Design decisions of the crawler — observed AVA behaviour (x-time cookie, aproveitamento-or-current rule, 404 indistinguishable from empty, pesoMedia as the real weight), the scope of Atividade and the rejected alternatives. Read before touching request, DTO or the oferta resolution.
projects: [all]
status: done
created_at: 2026-08-28
---

# AVA atividades crawler

Checking a grade on Uninter's AVA means navigating a slow SPA, matéria by matéria. This project mirrors that information into a local SQLite and exposes it through an interactive CLI. The vocabulary is in [CONTEXT.md](../../CONTEXT.md); the decisions and the reasons behind them live here.

## Observed AVA behaviour

Constraints verified against the real API, not deduced from the documentation (which does not exist). They account for a good part of the decisions below.

- Login returns `usuario.time`, a timestamp that is **the name of the session cookie**. Every following request must send the cookie and repeat that same value in the `x-time` header. The session lasts 4 hours.
- Each matéria carries two ofertas, and only one of them returns atividades: the aproveitamento one when it exists, the current one otherwise. Verified across the account's 27 salas, in both directions, with no counterexample.
- An empty list and an error arrive the same: **HTTP 404 with a plain-text body**, despite the `content-type: application/json`. There is no way to tell "a matéria with no atividade" from a real failure, and 6 of the 27 salas legitimately fall into that case.
- The `idCurso` in the path is ignored whenever `idUsuarioCurso` has a real value, and vice versa — but at least one of the two must be truthy, and neither comes in the login response.
- The response carries `peso` and `pesoMedia`. The first is 100 on every atividade and has no relation to the média; the real weight is `pesoMedia`.

## Decisions

### Atividade is APOL, exam and mock exam, and nothing else

"Listar as atividades de uma matéria" means listing APOLs, exams and mock exams — what the `AvaliacaoUsuario` endpoint returns. Lessons, forums and materials stay out of scope, because they would require endpoints that were not captured. Trabalhos are a separate collection and have their own spec in [0005](0005-trabalhos.md).

### The oferta never appears to the user

Matéria is the unit the student picks; the oferta is an integration detail resolved by the `aproveitamento ?? atual` rule. Exposing both would mean offering an option that always returns 404.

### The database stores only the fields the screen uses

An atividade arrives with about 160 fields between the object and its nested ones, almost all of them internal guts of the AVA. We persist twelve; adding a new field later costs one line and a fresh sync, because the API answers in half a second and is not a dead archive.

### SQLite is the read source, not a by-product

The CLI reads from the database; the network only comes in when the user asks. That keeps navigation instant and makes the 4-hour cookie matter only at sync time.

### Matérias at sync, atividades on demand

Syncing all 27 matérias at once would cost about 14 seconds on every run. Atividades are fetched when the matéria is opened for the first time, and stay cached. The accepted consequence is that only what has already been visited works offline.

### Cache served immediately; refreshing is an explicit act

Opening an already visited matéria shows what is in the database, with the age of the data in plain sight, and an option to refresh. Grades change over time, but a silent re-read from the network would turn the database into the by-product the previous decision rejected.

### The selector hides what is not a matéria

The AVA returns 27 salas, and one of them is the communication channel with the coordinator — no period, no dates, no atividade. By the glossary that is not a Matéria, so it does not enter the list. The ongoing ones come first.

### The screen adds up the média

The contribution of each atividade already comes computed by the AVA, and the sum is the matéria's partial média. We also show how much of the weight has already been posted, because in some matérias the completed atividades do not add up to 100% and a média on its own would lie.

### The CLI has no arguments

No flags, no subcommands: `python main.py` opens a menu and everything happens through it. It follows the repository convention and is what "cli interativa" asks for.

### Credentials only in `.env`

RU, password and `idCurso` come from a `pydantic-settings` reading `.env`; the example curls carry placeholders. The password was committed in plain text and was removed from history with BFG — the repository had no remote, so it never left the machine.

### The `idCurso` is configuration, not discovery

There is no known endpoint that produces `idCurso` or `idUsuarioCurso`, and looking for one would mean reverse-engineering the SPA. It stays an environment variable until someone captures the request in DevTools.

## Rejected

- **Discovering the ids by sweeping the SPA.** Tried and abandoned: the RequireJS modules behind the home screen already receive the `idCurso` ready-made. High cost, noise on the college's server, no benefit.
- **A single set of models serving both API and database.** It is the natural use of SQLModel, but nesting a `table=True` model inside another model makes Pydantic build it through `__init__`, where SQLModel switches validation off: required fields arrive null, with no error. The boundary with the AVA is Pydantic models; the tables are filled by explicit mapping.
- **Append-only grade history.** Storing a dated snapshot per sync would show the grade changing over time, but would require a composite key with the date and a latest-snapshot filter on every read. High cost for a gain nobody asked for.
- **Projecting how much is left to pass.** The cut-off grade does not exist in any field of the API; it would be a guessed 70 inside the code.
