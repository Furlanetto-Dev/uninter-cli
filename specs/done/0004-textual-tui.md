---
name: textual-tui
description: Replaces questionary + rich with Textual on a master-detail screen and converts crawler and api to async end to end (AsyncClient, AsyncSession, aiosqlite); brings the guard against concurrent syncs, the widget inventory and what the change does to 0002. Read before touching cli/, any request/repository/service signature, or the tests.
projects: [all]
status: done
created_at: 2026-09-02
---

# A TUI in Textual

Today the list of matérias disappears on every lookup: `browse_materias` asks, `open_materia` renders, and to see the next matéria the user goes back to the selector and picks again. It is the navigation cost `questionary` imposes — one prompt at a time, nothing permanent on screen.

Replacing `questionary` + `rich` with Textual is not a library swap: it is inversion of control. The `while True: pergunta → renderiza` of `cli/app.py` disappears and becomes widget plus handler. And since Textual runs on an event loop, every blocking I/O has to get out of the way — which drags `crawler` and `api` into async. Once this spec is executed, there is a single screen, the list never leaves it, and no synchronous call is left on the path to the network or the database.

The vocabulary is in [CONTEXT.md](../../CONTEXT.md), the design decisions in [0001](0001-ava-atividades-crawler.md), the layers in [0003](0003-crawler-api-cli-layers.md) and the tests in [0002](../rejected/0002-testing-strategy.md).

## Observed behaviour

Measured in the app's venv (Python 3.12.12, SQLAlchemy 2.0.52, SQLModel 0.0.42, httpx 0.28.1):

- `create_engine("sqlite:///uninter.db")` returns a `QueuePool` and passes `check_same_thread=False` to pysqlite. A `Session` used from two threads **raises no error** — it fails silently. That is what ruled out solving the blocking with a thread.
- `sqlmodel.ext.asyncio.session.AsyncSession` exists and has `.exec()`, so the repositories keep the shape they have today: `list(( await sessao.exec(stmt)).all())`.
- `greenlet` 3.5.5 is already installed, which is what SQLAlchemy's async mode requires. `aiosqlite` and `textual` are not.
- `httpx.MockTransport` with a **synchronous** handler works against an `AsyncClient` — verified with a real request. The layer 2 fixtures of 0002 survive unedited; only the test functions become `async def`.

On concurrency in the `AsyncSession`, measured with `asyncio.gather` over the real session:

- **Two concurrent `service.sync()` calls break**: 25 rounds of three simultaneous syncs produced 74 failures, with `IllegalStateChangeError: Method 'commit()' can't be called here`, `ResourceClosedError`, `PendingRollbackError` and `IntegrityError` from autoflush. That is what makes the guard mandatory, not optional.
- **One sync concurrent with reads does not break**: 25 rounds of one `sync()` against 40 simultaneous `list_all()` calls, zero failures. That is why moving the cursor during a sync is safe and stays allowed.
- `AvaSession._session_headers()` logs in lazily (`if self._stamp is None`), so two workers on the first network access issue two login POSTs. Read in the code, and avoided by the guard.

Measured on Textual 8.2.8, which settled the three items that were unverified when this spec was written — no fallback was needed:

- `Option` accepts `VisualType`, which includes `RenderableType`, so one `rich.Table` per option works. And `disabled=True` options are **skipped by navigation**: with a group title set to `disabled`, the initial highlight lands on the first matéria and the arrows never stop on the title.
- `Widget.loading` exists as a `Reactive` and accepts direct assignment.
- `check_action` decides between hiding and showing, not between enabled and dimmed: `False` **hides** the key from the `Footer` and blocks the action; `None` **shows** the key and blocks silently; `True` allows it. No return value produces "visible but dimmed" — `FooterKey.disabled` never becomes true. The guard uses `False`, which is what gives the shrinking footer from the design.

## Decisions

### There is a single screen, and the list of matérias never leaves it

List on the left, the matéria's panel on the right, `Footer` at the bottom. Switching matéria becomes an arrow key, not backing out of two menus — it is the only design that pays for the migration. The alternatives (replicating today's flow in stacked `Screen`s, or a single screen with a selection modal) would keep exactly the cost that motivated the change.

### Moving the cursor never touches the network

`OptionHighlighted` reads only from SQLite and fills the panel; `OptionSelected` (`⏎`) and `r` are the only network triggers. In a list where the arrow moves the cursor, loading on highlight would mean up to 27 requests to the AVA just from scrolling the list — and 0001 already decided that "refreshing is an explicit act". A never-synced matéria shows an empty state with the call to action, which makes the rule visible instead of implicit.

### The whole app goes async, with no thread at all

`ava_client()` returns `httpx.AsyncClient`, `AvaSession.get` and the two `fetch` become `async def`, and so do the two `service.sync`. No `asyncio.to_thread`, no `@work(thread=True)`: the `check_same_thread=False` measured above means a `Session` crossing threads gives no warning, and the alternative of keeping the domain synchronous would cost exactly that trap. The accepted cost is rewriting the `crawler` layer that 0003 has just tidied, with no parallel request to justify the gain — it is uniformity, not performance.

### SQLite follows along, with AsyncSession and aiosqlite

`api/db.py` moves to `create_async_engine("sqlite+aiosqlite:///...")` and `AsyncSession`; the two repositories and the two services gain `await`. `SQLModel.metadata.create_all` no longer takes the engine directly and becomes `async with engine.begin() as conn: await conn.run_sync(SQLModel.metadata.create_all)`.

None of this is a speed gain — the database is 24KB and `aiosqlite` is a thread wrapper underneath. It is consistency: with `crawler` async, leaving `sessao.exec()` synchronous on the event loop would be the only blocking call left, and nobody would remember why. The entities and the schema do not change.

### The session turns off `expire_on_commit`

`AsyncSession(engine, expire_on_commit=False)`. SQLAlchemy's default expires every instance after a commit, and the next attribute access triggers a lazy refresh — which under async is not slow, it is `MissingGreenlet`. Found on the first run of stage 2: `atividades_db.list_all(materia)` right after `service.sync()` blew up reading `materia.id`.

Turning it off is what the app wants anyway: the entities are snapshots handed to the screen, and nothing here depends on the commit bringing fresh values from disk. It is the only line of the migration that earned a comment, because it is a library quirk nobody deduces from reading this repository.

### `main.py` remains the composition root

`main.py` opens the resources with `async with` and hands ready services to the App constructor, which starts through `run_async()` inside an `asyncio.run(main())`. The App does not import `httpx`, `sqlmodel` or `settings` — the "cli → api, never crawler" arrow from 0003 survives intact.

The concrete gain is in testing: `App.run_test()` receives fake services through the constructor, and the 0002 e2e no longer needs monkeypatch. The alternative — the App opening everything in an `AsyncExitStack` in `on_mount` — would shrink `main.py` to three lines at the price of punching through the layer boundary.

### The package stays `cli/`, split by domain

```
cli/
  app.py         UninterApp: layout, bindings, workers, guarda
  materias.py    MateriaList, MateriaHeader
  atividades.py  AtividadeTable, MediaBar
  format.py      format_number, short_periodo, humanize_age
  app.tcss
```

`prompts.py` dies with `questionary`; `render.py` stops being a module of functions and becomes a widget. The name `cli` gets less accurate after this change — there is no command line left at all — but renaming to `tui/` would repoint imports everywhere and touch 0003 and 0002 for a vocabulary gain. The split by domain mirrors `api/materias/` and `api/atividades/`, which is the axis the repository already uses.

### One `OptionList` and one `Static` — a single focusable

`MateriaList` extends `OptionList`, which is the direct analogue of `questionary.select`: it has a separator for the EM CURSO and FINALIZADAS groups and emits the two messages the cursor decision needs. `AtividadeTable` is a `Static` that receives the `rich.Table` from `build_table`, so that code survives almost whole and the render golden stays a text file checkable in the diff.

`DataTable` would be the idiomatic path, but it enters the focus order and fights the list for `↑↓` — in a master-detail, the arrow has to always mean the same thing. With a single focusable widget that is structural, not convention.

### Each list row is a renderable, not a string

Each option is a two-column `Table.grid()`: name with `overflow="ellipsis"` on the left, period on the right. The panel reflows when the window is resized, and the width stops being a number in the code.

The consequence is that `truncate` and `NAME_WIDTH` become orphans — `truncate` had a single caller, `ask_materia`. They leave `format.py` in the same commit, and their cases leave layer 1 of 0002. The other three pure functions stay where they are, unedited.

### `LoginRejected` stops being fatal

Today it is caught at the top of `run()`, prints and ends the process. It becomes an error `notify()` with the app alive: the SQLite cache stays readable, and killing the session over a wrong password in `.env` throws away everything already synced. Loading is `loading` on the waiting panel; a sync outcome — the `aluno` and the total that today come out of `render_sync_summary` — is a success toast.

The exception is the first run with an empty database: there is no cache to browse then, and the screen shows an empty state explaining it, instead of a list of zero items.

### A "syncing" signal disables the keys

A `sincronizando` reactive on the app, and `check_action` refusing `refresh`, `sync` and `open` while it is on. The `Footer` reflects that on its own, so the guard is visible instead of silent.

**The flag is set together with the key press, not inside the worker.** `@work` only schedules the coroutine, so setting `sincronizando` in its body leaves a window in which two keys dispatched before the worker starts both get past `check_action` — reproduced, two fetches where there should be one. The one that sets the flag is the synchronous method that creates the worker; the worker only clears it, in the `finally`.

This exists because the non-blocking screen opens three real paths to two simultaneous syncs: the ~14s window of the full sync, `r` hit twice within the half second of the fetch, and `⏎` on two matérias in a row. In all three, two coroutines touch the same `AsyncSession` and SQLAlchemy raises; in two of them the `AvaSession` lazy login fires twice. A queueing lock would fix the session but would turn a hammered `r` into N requests to the AVA, and without a signal in the footer the key would look like it had not worked. Neither operation gains anything from running in parallel — they are sequential requests to the same server.

### The never-synced badge is the only new thing

A `●` on the row of matérias with `atividades_sincronizadas_em is None`. It costs three lines now that the option is a renderable, and it is what makes the state discoverable before the user reaches it — without it, you only learn a matéria is empty after `⏎`. Beyond that, the first cut is parity: no filter, no sorting, no per-atividade detail.

### The top menu evaporates

`VIEW_ATIVIDADES` goes because the list is already on screen, `BACK` goes because there is nowhere to go back to, and `SYNC_MATERIAS`, `REFRESH` and `QUIT` become bindings: `s`, `r` and `q`. `⏎` stays **out** of `BINDINGS`: the `OptionList` already consumes it to emit `OptionSelected`, and declaring the same shortcut on the app would only show it in the footer without being what fires. The `⏎` guard lives in the message handler; what announces the key is the empty state of the never-synced matéria, which already says "⏎ para buscar no AVA". `render_goodbye` goes too — Textual restores the terminal on exit, and printing after that is noise.

### 0002 is rewritten, not patched

Five of its sections stop holding: Tooling (`pytest-asyncio` comes in, against the "pytest alone"), the `tests/` tree (`cli/test_render` becomes `test_atividades` plus `test_app`), the whole of layer 5 — the three mechanisms it names, the `questionary.select` stub, `render.console` at a fixed width and the avoided pty, all cease to exist —, Determinism, and the golden. Layers 2, 3, 4 and 7 keep their assertions and only become `async def`; layers 1 and 6 barely change. The risk map gains one entry: the sync guard giving way is a new risk, and the only one whose test lives in the interface layer.

The rewrite also corrects a false claim 0002 has carried since it was written: it says the render golden "already exists", generated during the 0003 refactor. It does not — not in the repository, not in the git history. It becomes a file to generate and check by hand, which changes the reason 0002 refuses `syrupy`.

### The database is not touched

`Materia` and `Atividade` change neither name nor field, and the `sqlite+aiosqlite` dialect reads the same file. `uninter.db` stays valid; if a `select` breaks, it is a missing `await`, not schema.

### The four known defects stay standing

The defects listed in 0002 — a 404 wiping the cache, `Materia.oferta` with `or`, a removed matéria that never leaves the database, `save` mutating the caller's objects — are preserved on purpose, as 0003 did. They wait for a red test first, and a migration in which no behaviour changes is a migration reviewed by reading the handlers.

## Rejected

- **`asyncio.to_thread` only on the network, keeping the domain synchronous.** It was the smallest blast radius: two async `service.sync`, `crawler` intact, `Session` never crossing threads. Dropped in favour of uniformity — an app where half the signatures are async and the other half are not forces you to remember which is which on every call.
- **`@work(thread=True)` with one session per operation.** Zero async in the domain, but the composition root would stop handing out instances and start handing out factories, with two live SQLite connections and entities from a dead session reaching the UI.
- **`@work(exclusive=True)` per group, with no explicit guard.** Idiomatic, but distinct groups (full sync and matéria sync) still compete on the same `AsyncSession`, and cancelling a worker in the middle of `replace()` leaves the session dirty and needing a rollback.
- **Eager login at boot to kill the `_stamp` race.** It works, and makes the app always open with a network request — 0001 decided the opposite ("the network only comes in when the user asks"), and a wrong password would then block even viewing the cache.
- **`DataTable` in the atividades panel.** Native scroll and zebra stripes, but `build_table` rewritten, the golden redone, and a second focusable that needs `can_focus = False` so as not to steal `↑↓`. Nothing is done with a selected row.
- **`ListView` with a composite item in the list of matérias.** It would give per-element styling via TCSS, but has no separator — the EM CURSO and FINALIZADAS groups would come as hand-made disabled items — and it is more code than `OptionList`.
- **Renaming `cli/` to `tui/`.** The name became imprecise, and that was exactly the criticism 0003 made of `infra/`. But there the name hid a layer boundary; here it hides only the shape of the interface, and the price is repointing imports across all of `src/` plus two specs. Revisit if a second interface shows up.
- **A blocking modal during the sync.** Truer to the current behaviour and with no doubt about inconsistent state on screen, because there is no state to become inconsistent. Dropped because 14 seconds of a frozen screen is what the migration was meant to eliminate.
- **Automatic debounced sync when the cursor stops.** It would fill the database while browsing and remove the `⏎` step. It is the same silent re-read of the network that 0001 rejected by calling refreshing an explicit act.
- **Type-to-filter on the list.** Useful when the list grows, but it introduces a second focusable — which is precisely what the `OptionList` + `Static` choice avoids — plus a mode (`/` enters, `esc` leaves) and filter state to reconcile with the sync guard. 27 items fit in two screens.
- **Two specs, one for async and one for Textual.** Two independent reviews, each with a green state. But async has no motivation of its own: it exists only because Textual's event loop demands it. A spec justifying "goes async" without being able to cite Textual would write the wrong why, and if Textual were abandoned the async would be left in the repository for no reason.
- **A surgical patch to 0002 instead of a rewrite.** Smaller diff and the reviewer sees what changed. But five sections change, and a document whose header says "read before writing any test" should not need the reader to cross two specs to know which paragraphs still hold.
- **A pre-formatted string on each list row.** It would keep `format.py` intact and layer 1 of 0002 whole, lifting the body of `ask_materia` as is. Lost to reflow on resize; recorded as the fallback in case `OptionList` does not accept a renderable.

## Execution order

Three code stages, each with the app running at the end. In the first two the `questionary` CLI stays in place: `main.py` becomes `asyncio.run(main())` and the synchronous prompts keep working inside the coroutine — they block the loop, but there is no concurrency to protect yet.

**`questionary` leaves in stage 3, not in stage 1.** Removing it earlier breaks `cli/prompts.py` on the spot and knocks over precisely the green state the first two stages exist to preserve.

1. **`crawler/` async.** `+textual` and `+aiosqlite` in `pyproject`; `rich` stays explicit (`build_table` and the list rows import `rich.Table`). `ava_client` returns `AsyncClient`, `AvaSession.get` and the two `fetch` gain `async`/`await`. `cli/app.py` and `main.py` follow with `await`.
2. **`api/` async.** `db.py` with `create_async_engine`, `run_sync` in `create_all` and `expire_on_commit=False`; `AsyncSession` in the two repositories, `await` in the two services. Since both context managers are now async, `main.py` goes back to a single `async with`.
3. **`cli/` in Textual.** `app.py` with the layout, the bindings and the guard; `materias.py` and `atividades.py`; `app.tcss`; `truncate` and `NAME_WIDTH` out of `format.py`; `prompts.py` and `render.py` deleted; `questionary` out of `pyproject`.
4. **0002 rewritten**, in the stage 3 commit.

Verification, instead of opening the CLI at each stage: `pyright` in `strict` over `src/` — with everything async, a missing `await` is the error that slips through silently at runtime — plus a headless script per stage, with `MockTransport` in place of the AVA and the database in a temporary directory. Stage 3 uses `App.run_test()` with Pilot, which is the same tooling layer 5 of [0002](../rejected/0002-testing-strategy.md) will use. None of this becomes a committed test here: the tests are 0002's work, after this spec.

## What execution corrected

Recorded because each item was a wrong claim in this spec, not a Textual surprise:

- **`expire_on_commit`** was not foreseen and is mandatory. It became a decision above.
- **The `questionary` order** was contradictory, corrected above.
- **The guard flag** set inside the worker let two fetches through. It became a paragraph in the guard decision.
- **`MateriaList.show` restored the highlight by index**, and after a resync the index could land on a `disabled` group title — `em_foco` returned `None` and `r` became a silent no-op. It now restores by matéria id, with the first matéria as fallback.
- **The empty state never showed on the first run's `LoginRejected`**, because the worker raised before `reload_materias`. `on_mount` now paints the state before syncing, and the `except` repaints it.
- **`overflow="ellipsis"` alone does not truncate in `rich`**: without `no_wrap=True` a long name wraps onto two lines instead of becoming an ellipsis.
