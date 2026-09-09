---
name: testing-strategy
description: How to test the crawler — risk map, the eight test layers, synthetic and real fixtures, clock and render determinism, and the four known defects to fix with a red test first. Read before writing any test in this app.
projects: [all]
status: pending
created_at: 2026-09-02
---

# Testing strategy

The project has no tests. The refactor into layers created the seams that were missing — injected HTTP transport, database by path, clock as a parameter — and [0004](../done/0004-textual-tui.md) adds the one missing at the edge: the services reach the App through the constructor, so the whole interface can be exercised with fakes. This document decides what to test, with what, and in what order.

The vocabulary is in [CONTEXT.md](../../CONTEXT.md), the design decisions in [0001](../done/0001-ava-atividades-crawler.md), the layers in [0003](../done/0003-crawler-api-cli-layers.md) and the interface in [0004](../done/0004-textual-tui.md). **Nothing here is written before 0004 is executed**: it changes every `fetch`, `sync` and repository signature to `async`, and tests written before it would be born to be rewritten.

## The risk map

The list of tests does not come from coverage, it comes from here. Ordered by damage × probability:

1. **Alias drift in the DTO.** The AVA renames a field and the data becomes `None` with no error at all: the DTOs use `extra="ignore"` and almost every interesting field is optional. The symptom is a missing grade on screen, months later. It is the only risk no synthetic test catches.
2. **A transient 404 destroys the cache.** `AtividadeRequest.fetch` returns `[]` on 404, `replace` deletes what was there, `mark_synced` marks it as fresh. A network failure becomes "matéria with no atividades, synced just now".
3. **Wrong oferta rule.** `aproveitamento ?? atual` decides whether data or a 404 comes back. Getting this wrong empties matérias silently.
4. **Timestamp lost on a resync.** If the dictionary in `MateriaRepository.save` breaks, every "Sincronizar matérias" resets the age of all 26 and forces a refetch.
5. **The sync guard gives way and two coroutines touch the same `AsyncSession`.** New with 0004. The non-blocking screen opens three paths to two simultaneous syncs, and the `AsyncSession` does not accept concurrent operations: the symptom is an exception in the user's face, and on the session's first access also a duplicated login POST. It is the only risk whose test lives in the interface layer.
6. **Wrong média and graded weight.** It is the only arithmetic in the project, and it goes straight to the user's face.
7. **Atividades out of order.** `posicao` is the only ordering there is; the AVA guarantees none.

## Tooling

`pytest` plus `pytest-asyncio`, and nothing else. `asyncio` stopped being optional when 0004 made the whole app async: `fetch`, `sync`, the repositories and Textual's `run_test()` are all coroutines. With `asyncio_mode = "auto"` this shows up in no test beyond the `async def`.

**No `pytest-httpx` or `respx`**: `AvaSession` takes the client through the constructor, so the `httpx.MockTransport` that ships with httpx is enough. Verified against a real `AsyncClient`, and the transport handler can stay **synchronous** — the fixtures do not change shape because of async.

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = ["rede: exige credenciais e acesso ao AVA (desabilitado por padrão)"]
addopts = "-m 'not rede'"

[tool.pyright]
include = ["src", "tests"]

[tool.pdm.scripts]
test = {cmd = "pytest", help = "Roda a suíte, sem os testes de rede"}
```

Tests go into pyright's `include`: a fake that drifted from the real interface is a test that lies — and with everything async, the missing `await` is precisely the error that passes silently at runtime.

## Where the tests live

Mirroring the packages in `src/`, so the test file is obvious from the code file:

```
tests/
  conftest.py             sessao em tmp_path, ava falso, fabricas de Materia/Atividade
  crawler/                test_session
    materias/             test_dto  test_request
    atividades/           test_dto  test_request
  api/
    materias/             test_entity  test_repository  test_service
    atividades/           test_entity  test_media  test_repository  test_service
  cli/                    test_format  test_atividades  test_app
  e2e/                    test_fluxo
  contract/               test_dtos_reais  test_smoke (marker rede)
  fixtures/               login.json  materias.json  atividades-*.json
  golden/                 materia-renderizada.txt
```

`cli/test_atividades` covers `build_table`, which still returns a `rich.Table`; `cli/test_app` is the Pilot with fake services. `test_render` disappeared along with the module.

## The layers, and what each one proves

### 1. Pure functions — no fixture, no mock

`cli/format.py` imports nothing and `api/atividades/media.py` imports only the entity. They are the cheapest tests in the project and cover risk 6.

- `format_number`: `None → "—"`, `0.0 → "0"`, `8.0 → "8"`, `7.5 → "7,5"`, `33.33 → "33,3"`, negative
- `short_periodo`: `None → ""`, and that cutting at the first `" - "` drops the UTA
- `humanize_age`: `None`, now, 59s, 1h, 23h, 1d, 45d — the clock comes as a parameter
- `Media.from_atividades`: empty list → `(0, 0)`; partially graded → sums only the completed ones; `nota = 0.0` counts as completed and is not mistaken for absence; `parcial` switches on and off at 100
- `Materia.oferta`: with aproveitamento uses it; without, uses the current one
- `Atividade.realizada`: `contribuicao = 0.0` is completed, `None` is not

`truncate` left `format.py` with 0004 — the row width became `overflow="ellipsis"` on the renderable —, so its cases left this list.

### 2. Requests — `MockTransport` + fixtures

Covers risks 1 and 3. All `async def`, with an `AsyncClient` built over the `MockTransport` and a synchronous handler.

- Login: one POST for N GETs on the same `AvaSession`; `x-time` repeats `usuario.time` on every GET; the session cookie goes back to the server
- `LoginRejected` when `usuario` is `null`, with the AVA's message
- 404 → `[]` in both requests; 500 raises
- `MateriaRequest`: drops the sala without `modulo` (the coordinator's channel); builds the URL with the `id_curso` received
- `AtividadeRequest`: the querystring carries `materia.oferta`, not `oferta_atual`; `posicao` follows the order of the response
- **The trap aliases, one test each**: `peso` comes from `pesoMedia` and not from the `peso` that is worth 100; `contribuicao` comes from `notaMedia`; `periodo` comes from `modulo`; `prova` comes from `atividade`
- A missing required field raises `ValidationError` instead of becoming `None`

### 3. Repositories — real SQLite in `tmp_path`

`db_session(path)` takes a path, so no mocks here. Covers risks 4 and 7.

- Round-trip of `Materia` and `Atividade`, with `datetime`, `float | None` and `nota = 0.0` surviving
- `MateriaRepository.list_all`: current ones first, then by name
- `MateriaRepository.save` **preserves the timestamp** of what was already stored — the test that protects risk 4
- `AtividadeRepository.list_all` orders by `posicao`
- `AtividadeRepository.replace` replaces instead of duplicating; an atividade that left the AVA disappears
- No repository commits: after calling `save`, a second `AsyncSession` on the same file still does not see the data

Two `AsyncSession`s over the same file is why the database is a file in `tmp_path` and not `:memory:`, now as before.

### 4. Services — fake requests, real repositories

The fakes are coroutines, and pyright in `strict` over `tests/` is what guarantees they keep matching the real request.

- `MateriaSyncService.sync` fetches, stores and commits; `aluno` reflects the AVA session
- `AtividadeSyncService.sync` stores the atividades **and** stamps the matéria **in the same commit** — a parallel session sees both writes or neither
- The timestamp is asserted by range (`antes <= carimbo <= depois`), not by value: avoids `freezegun` for two `datetime.now()`
- A request that raises leaves the database intact

### 5. The interface — `run_test()` and Pilot, fake services

Replaces the scripted-prompts layer that existed before 0004: `questionary.select`, the global `render.console` and the `EOFError` without a TTY all ceased to exist. `App.run_test()` runs headless, with no pty, and takes fake services through the constructor — which is what 0004's composition root decision bought. The fakes record the calls, and it is on that list that most assertions fall.

It is the only layer that covers risk 5, and the only one that proves 0004's behaviour decisions:

- **Moving the cursor does not touch the network**: `pilot.press("down", "down")` and the fake service's call list stays empty
- `⏎` on a never-synced matéria calls `sync` exactly once; on a cached matéria, not at all
- **The guard**: with the fake service suspended on an `asyncio.Event`, `r` and `s` during the in-flight sync produce no second call, and `check_action` refuses all three actions
- The badge appears only on matérias with `atividades_sincronizadas_em is None`
- `LoginRejected` raised by the fake notifies and **the app keeps running** — 0004's most visible behaviour change
- An empty database shows the empty state, not a list of zero items

`run_test(size=(100, 30))` in all of them: the terminal size goes into the layout, and without pinning it the assertion depends on who ran it.

### 6. E2E — real services, fake AVA, temporary database

One or two tests, covering the `main.py` wiring that no unit test touches. Same `run_test()` as layer 5, but with the real services assembled over a `MockTransport` and a `db_session` in `tmp_path`.

- Opening a matéria without cache triggers the sync, persists, stamps and renders
- Opening a cached matéria makes **no** request at all — the transport handler counts the calls and the count is zero

### 7. Contract — real fixtures

The only test that catches risk 1. Validates the DTOs against real responses and fails when the AVA changes shape. Nothing async here: they are Pydantic models against JSON in a file.

- Every real fixture parses without error
- **No optional field comes back `None`** in a fixture that has a value — this is what detects the renamed alias
- The fixture's keys cover every alias the DTOs declare

### 8. Smoke — `@pytest.mark.rede`, opt-in

Off by default. Asserts **structural invariants, never values**: login returns `time`, matérias > 0, every matéria with a period has an oferta, a known matéria returns atividades. It exists to know the AVA changed before the user sees a missing grade.

## Fixtures: two levels

**Synthetic**, written by hand and committed. They test the code. It is what layers 2 to 6 use.

**Real**, captured once and anonymised. They test the contract. Capture: one login and two GETs with the curls in `uninter-endpoints/`, saving the bodies. Anonymisation: swap the user's `nome`, RU and ids for fixed values, and **check field by field** that nothing personal is left — the atividade JSON has about 160 fields between the object and the nested ones.

We need four: login, matérias (with and without `oferta_aproveitamento`, and the sala without `modulo`), atividades with a grade posted, atividades with no grade at all.

## Determinism

- **Clock**: `humanize_age` already takes one. `mark_synced` and the App's sync handler remain, resolved by range. No `freezegun`.
- **Render**: `build_table` returns a `rich.Table`, and the `Console` is no longer an app global — whoever wants text builds one in the test, with `Console(width=100, force_terminal=False)`. It is better than the previous seam: the width becomes a parameter of the test, not state someone has to remember to replace.
- **Screen**: no asserting the whole screen. Layer 5's assertions are about widget state and the fakes' call list, with the size pinned in `run_test(size=...)`.
- **Golden**: one file in `tests/golden/` with the rendered matéria, generated in layer 5's first test and **checked by hand before committing**. A reference was generated during the 0003 refactor and did not survive — it is neither in the repository nor in the history —, so it is to be redone, not reused.

## The known defects come in as a red test first

Preserved on purpose in the refactor and in 0004, to be fixed with a test first:

1. **404 wipes the cache and marks it as fresh.** The most serious. Candidate fix: `replace` not deleting when the list arrives empty, or the request telling "empty" from "failed".
2. **`Materia.oferta` uses `or`**, so `oferta_aproveitamento == 0` would fall through to the current one. Theoretical — the real ids run from 511 thousand to 1.2 million and absence comes as `None`.
3. **A matéria removed from the AVA never leaves the database**: `save` only does `merge`.
4. **`MateriaRepository.save` mutates the caller's objects.**

## What we will not test

- The `main.py` wiring in isolation — the e2e already exercises it
- `MAPPED_TABLES`, which exists only to register the tables in the metadata
- Internal behaviour of `rich`, `textual` or `aiosqlite`
- The layout: no screen snapshots, no asserting position or borders
- The exact text of toasts and binding labels, which change without consequence
- Coverage as a numeric target

## Rejected

- **`pytest-httpx` or `respx`.** They solved the global monkeypatch that injecting the client made unnecessary. Confirmed that httpx's `MockTransport` also works for the `AsyncClient`, so not even async brings that cost back.
- **`anyio` instead of `pytest-asyncio`.** It would work, and would bring `anyio_backend` for free. But Textual runs on asyncio and its own suite uses `pytest-asyncio`; parametrising the backend for an app that has only one is ceremony.
- **`freezegun` or `time-machine`.** Only two `datetime.now()` remain, and asserting a range covers what matters: that the timestamp was written.
- **`syrupy` or `pytest-textual-snapshot`.** A golden in a text file reads in the diff; a snapshot brings a dependency, a `--snapshot-update` flow and the temptation to accept the change without looking. `pytest-textual-snapshot` would on top of that record an SVG of the whole screen, which is exactly what "we will not test layout" refuses.
- **In-memory SQLite.** Faster, but the "repository does not commit" test needs two connections seeing the same file.
- **`unittest`.** Loses `parametrize`, which is precisely what the formatting tests want.
- **CI now.** The repository has no remote. It stays a `pdm run test` until there is somewhere to push to.
- **Running the App in a real pty.** It was mandatory while `questionary` required a TTY, and the previous strategy worked around it by replacing the prompt. With Textual's `run_test()` the app runs headless out of the box, so the pty stopped being a problem to solve — and keeping it would only add timing flake.
- **Writing any test before 0004.** Every `fetch`, `sync` and repository signature becomes async, and the whole of layer 5 depends on widgets that do not exist yet. They would be tests written to be rewritten.

## Execution order

After 0004, never before.

1. **Scaffolding and pure functions** — pytest and `pytest-asyncio` in `pyproject`, `conftest.py`, layer 1. No fixtures at all, delivers value the same day.
2. **Boundaries** — requests with synthetic fixtures (layer 2) and repositories in `tmp_path` (layer 3). It is where most of the risk per line written lives.
3. **Composition** — services (layer 4).
4. **Interface** — layer 5 with the fakes and the `build_table` golden, then layer 6's e2e. The guard test comes first: it is the new risk and the easiest to regress without anyone noticing.
5. **Contract** — capture and anonymisation of the real fixtures, layer 7, and layer 8's smoke.
6. **The four defects**, one by one, red test first.
