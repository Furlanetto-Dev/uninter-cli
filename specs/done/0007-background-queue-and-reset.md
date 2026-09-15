---
name: background-queue-and-reset
description: The queue that fetches every matéria's atividades on its own and the command that deletes the database — the two changes that alter when the network runs and what the cache means. Carries the measured cost of the sweep, the user's preemption of the queue and why deleting the file forces the App to restart. Read before touching the 0004 guard, main.py or anything that syncs on its own.
projects: [frontend, api]
status: done
created_at: 2026-09-02
---

# Background queue and reset

Two changes that look independent and are the same decision seen from two sides: **when the network runs without anyone asking**, and **what makes the cache count again**. Today opening a never-visited matéria costs half a second of waiting, and there is no way to start over from scratch other than deleting `uninter.db` by hand, outside the app.

After this spec the database fills itself after the first sync, and one key wipes it whole. The two things meet at the same point: wiping the database with the queue on triggers precisely the full sweep.

What the project is lives in [CONTEXT.md](../../CONTEXT.md), the design decisions in [0001](0001-ava-atividades-crawler.md), the interface and the sync guard in [0004](0004-textual-tui.md), and the trabalhos in [0005](0005-trabalhos.md).

## Observed behaviour

**Deleting `uninter.db` with the session open leaves the app half dead.** Measured: after the `unlink`, reads **keep working** and return data from the orphaned inode, as if nothing had happened; writes fail with `OperationalError: attempt to write a readonly database`; and the file is not recreated. The database only shows up empty when a new session opens. It is the worst possible state — the screen shows data that no longer exists on disk and the next sync dies with a SQLite error. Any reset needs to recycle the engine, not just delete the file.

**Two concurrent syncs on the same `AsyncSession` break, concurrent reads do not.** Measured in [0004](0004-textual-tui.md): 25 rounds of three simultaneous `sync()` gave 74 failures (`IllegalStateChangeError`, `ResourceClosedError`, `PendingRollbackError`); one `sync()` against 40 simultaneous `list_all()` gave zero. The queue has to be serial, and navigating during it is safe.

**The full sweep costs about 13 seconds.** That is 26 matérias at half a second each, of which 6 return a legitimate 404 — a matéria with no atividade, indistinguishable from a failure, as [0001](0001-ava-atividades-crawler.md) recorded.

## Decisions

### The queue sweeps every matéria without a cache

Once the matérias sync finishes, a queue enqueues **every** matéria without a sync stamp, ongoing ones first. By the end of the first run the app is complete offline.

The cost of the sweep is the same as ever — 26 matérias at half a second each. What changes is who waits for it: in the background, the 13 seconds are in nobody's way, and the app stops depending on having visited the matéria before to work offline.

What does not change is the principle: SQLite remains the read source, and the network never enters the path of a key.

### Moving the cursor still never touches the network

[0004](0004-textual-tui.md) decided that the highlight reads only from the database, and that does not change. The queue is not triggered by the cursor, does not know where it is and does not reorder because of it. Whoever moves the cursor during the queue sees whatever cache exists — including the "never synced" state, if that matéria's turn has not come yet.

### No key is blocked; the queue is what serialises

The `sincronizando` from [0004](0004-textual-tui.md) disabled `r`, `s` and `⏎` via `check_action`. Keeping it that way during the queue would lock the keyboard for 13 seconds, and making it blink per item would light and dim the footer 26 times.

Both problems vanish when **every** sync — the list's, a matéria's, the queue's — goes through a single serial consumer. There is nothing left to block: what guarantees there are no two simultaneous commits is having one consumer, not the key being dimmed. `check_action` goes, and `sincronizando` becomes just the "there is an item in flight" signal that lights the loading indicator.

The guard is no longer visible in the footer, and what shows in its place is better: the header shows how many items remain.

### The user's work cancels the background item in flight

`⏎` or `r` on a matéria put it at the front of the queue **and abort whatever background request is in flight**. Without that, "jumping the queue" still left the user waiting for the current fetch to finish — background work getting in the way of requested work, which is exactly what cannot happen. The interrupted matéria goes back to right after the user's and is redone next.

**The write is not cancellable.** Cancelling inside the `commit` leaves the session in a state not even `rollback()` recovers — it raises `IllegalStateChangeError`, the same risk [0004](0004-textual-tui.md) cited when rejecting `exclusive=True`. That is why `AtividadeSyncService.sync` wraps the database phase in an `asyncio.shield`: the cancellation always catches the fetch, and the write, if it has started, finishes.

Two consequences that only show up in the implementation: a matéria **already enqueued** needs to be promoted to the front when the user asks for it, instead of ignored for already being in the queue; and asking for the same matéria several times in a row cannot enqueue several copies. With that, `r` hit seven times is worth one request, and `⏎` on three matérias is worth three, one at a time.

### The queue waits one second between one matéria and the next

`PAUSA_ENTRE_MATERIAS = 1.0`, applied between consecutive items. The full sweep goes from 13 to some 40 seconds, and that is the point: in the background nobody is waiting for it, so there is no reason to dump 26 back-to-back requests on the university's server. What was a burst becomes a trickle.

**The pause is interrupted by a user request.** Without that, `⏎` on a matéria with no cache would sit waiting on work nobody asked for. The wait is a `wait_for` on an event that priority enqueueing fires, so the user's request cuts the pause the instant it arrives.

### What is syncing shows in the matéria's own badge

The one-character column that shows `●` for "never synced" now shows a spinner on the matéria being fetched. It is the only place on the screen where the information fits without competing with anything, and it says **which** matéria the queue is processing — something an indicator in the panel does not.

With that the detail panel **is no longer covered** during an atividades sync: whoever is reading a matéria keeps reading while the background works. The cover is left only for the matérias list sync, where the whole list is going to be replaced anyway, and there the `Carregando` — a wave of blocks — returned by `get_loading_widget` comes in.

And the row is redrawn on its own, via `replace_option_prompt`, without rebuilding the list: rebuilding moved the highlight and redrew the panel under whoever was navigating.

### The reset deletes the file and restarts the App

The command discards `uninter.db` whole and brings everything up again. It is the only reset that clears orphaned schema, which stops being a detail now that [0005](0005-trabalhos.md) adds three tables to the database.

Clearing only the sync stamps would be more conservative and reversible, but would leave the old rows in the database and is not what "invalidar todo o cache" means. And nothing is truly lost: the AVA is the source, and with the queue on the database rebuilds itself in 27 requests right after coming up.

### `main.py` deletes and rebuilds, not the App

The App only signals. `main.py` gains a loop: it runs the App, and if it asked for a reset, deletes the file **outside** the `async with` — with the engine already discarded and the session closed — and assembles everything once more.

```python
async def main() -> None:
    while True:
        async with ava_client() as http, db_session() as sessao:
            ...
            app = UninterApp(...)
            await app.run_async()
            if not app.resetar:
                return
        DATABASE_PATH.unlink(missing_ok=True)
```

That is what solves the orphaned inode measured above without touching a repository, a service or the App's constructor — the constructor injection of [0004](0004-textual-tui.md) still stands, and [0005](0005-trabalhos.md) does not need to change a line of its task list. The price is the screen flickering and the cursor going back to the top, which for "apagar o banco" is what one expects anyway.

### The reset lives in the command palette, not on a key

`ctrl+p` and the "Apagar o banco" command, registered by its own `Provider`. Deleting the database is rare and destructive: spending one of the footer's few keys on it puts the app's most dangerous operation one wrong finger away, next to `r` and `s`, which are the two most frequent.

The palette also gives what a letter does not — a full name, a description of what is about to happen and search —, and the footer goes back to listing only what is used all the time.

### The reset asks for confirmation

A yes-or-no modal after picking the command. Nothing is lost forever — the AVA rebuilds —, but the whole list vanishes from the screen and the app restarts, and that deserves one more step even coming from the palette.

## Rejected

- **Enqueuing only the ongoing matérias.** Two or three requests instead of 26, and the finished ones would stay on demand. Discarded by explicit decision: the goal is the app complete offline, not just the current semester.
- **Triggering on the idle cursor, with a debounce.** Would make the work follow the user's attention and never fetch what they did not look at. It is the same debounce [0004](0004-textual-tui.md) already refused: it reopens scrolling-the-list turning into a request, and it is not background, it is on demand with a delay.
- **A parallel queue, with several requests in flight.** Would cut the 13 seconds to some 3. Impossible without one session per worker: it is measured that three concurrent `sync()` on the same `AsyncSession` produce 74 failures in 25 rounds.
- **Keeping `sincronizando` on for the whole queue.** One line fewer and no concurrency risk. Discarded because it locks `r`, `s` and `⏎` for 13 seconds and turns the background into the foreground under another name.
- **A reset clearing only the sync stamps.** One `UPDATE`, no `DELETE`, and the old data survives a network drop right after. Loses to the file because it does not clear schema, which is what [0005](0005-trabalhos.md) makes relevant.
- **A reset deleting the atividade rows and keeping the matérias.** Would avoid the restart and the list would stay on the screen. But it is literally defect 1 of [0002](../rejected/0002-testing-strategy.md) — "404 apaga o cache" — promoted to a feature, and it would still leave the schema untouched.
- **A `Banco` injected into the repositories, with `recycle()`.** Recycles the session without restarting and preserves the cursor. Costs changing today's two repositories and the three [0005](0005-trabalhos.md) is still going to write, plus an indirection on every read.
- **The App receiving new services from a factory.** Also avoids the restart and does not touch the repositories. Discarded because it loosens the constructor injection, which is the seam the `run_test()` of layer 5 of [0002](../rejected/0002-testing-strategy.md) depends on.

## What execution corrected

- **The consumer flag, set inside the worker, created several consumers.** `@work` only schedules, so two enqueues in a row fired two parallel queues — and parallel is exactly what cannot be. It is the same lesson [0004](0004-textual-tui.md) had already recorded for its guard: the synchronous method sets the flag, not the worker.
- **Deduplication killed preemption.** Skipping what is already in the queue is what makes hammered `r` worth one request, but applied without exception it made the user's request be ignored when the matéria was already enqueued at the end. A user request now promotes; the rest keeps being skipped.
- **The per-key guard was replaced by the serial consumer**, not narrowed as this spec foresaw. It is rewritten in the decision above.
- **The loading widget does not show up in `query`.** Textual mounts it as a *cover*, outside the normal tree, so whoever tests it looks at `_cover_widget` — applies to layer 5 of [0002](../rejected/0002-testing-strategy.md).
- **`$accent` is not `rich` markup.** The list rows are `rich` renderables, not Textual's: a CSS variable in there becomes a `MarkupError` at the closing tag. A badge colour is a `rich` colour name.
- **Cancelling the fetch required shielding the write.** The first attempt cancelled and did a `rollback()`, and collided with the cancellation itself (`IllegalStateChangeError`). It became `asyncio.shield`, described in the decision above.

## Execution order

1. **The serial consumer.** A single worker that drains the queue, with `sincronizando` reduced to a loading signal and `check_action` removed.
2. **The queue.** Serial, fed after the matérias sync, with user preemption and progress on the screen.
3. **The pause and the animation.** `PAUSA_ENTRE_MATERIAS` between items, interruptible by a user request, and the `Carregando` in `get_loading_widget`.
4. **The reset.** A command in the palette, a signal in the App, a confirmation modal, and the loop in `main.py`.
5. **0002**: layer 5 gains the queue cases (preemption, seriality, free cursor during the sweep) and the risk map gains the reset entry — deleting the file with the session alive is the defect this spec exists not to commit.
