---
name: resending-materias-listing
description: The matérias listing is re-sent every time the student comes back to the matérias page from another page — the login gate included, so every open — and on r, and it repaints the list without moving the student. Read before touching when the listing runs, what r does, ScreenSuspend/ScreenResume on the matérias page, or the toasts of a listing sync.
projects: [frontend]
status: done
created_at: 2026-10-22
---

# Re-sending the matérias listing

## TL;DR
- The matérias listing is re-sent every time the student comes back to the matérias page from another page, and on `r` next to the highlighted matéria's tab. The login gate is a page, so this also covers every open.
- Closing a dialog — a confirmation, the command palette — is not coming back; it sends nothing.
- Over a list that already has matérias, the listing repaints it in place: highlight, focus and detail pane stay where the student left them.
- Known matérias are not fetched again, and the toast names only the matérias that are new.
- A listing that fails mid-session, for lack of network or with an HTTP error such as a 401, reports it instead of closing the app.

[0007](0007-background-queue-and-reset.md) sent the listing only into an empty database or when the palette asked, so a matéria added to the AVA mid-semester never showed up on its own. Discovering it now rides on the navigation the student already does.

## Observed behaviour
- `fetch_pending` sends the listing only when the database has no real matéria; otherwise it enqueues the never-synced ones from the database, and the listing waits for `Reload matérias`. Proof: `src/cli/app.py`.
- `MateriaRepository.save` copies the stored sync stamps onto the listed matérias, so the `enqueue_pending` after a listing only picks matérias never synced. Proof: `src/api/materias/repository.py`.
- `reload_materias` focuses the list; run after every listing, it would pull the student out of the atividade they were reading. Proof: `src/cli/pages/materias/page.py`.
- Textual posts `ScreenResume` to the page under any popped screen, modals and the command palette included. Proof: `App.pop_screen` in textual 8.2.8.
- `AvaSession.get` re-raises `httpx.TransportError` as is and turns a 401 into `httpx.HTTPStatusError`, and `_run_materias_sync` catches neither, so the worker dies with the app. Proof: `src/crawler/session.py`, and `specs/bugs/401-crash-bugfix.bug.md`.

## Decisions

### Coming back means leaving a page, not closing a dialog
When the page is covered it notes whether the cover is a `ModalScreen`, and on `ScreenResume` it sends the listing only if it was not. A prova, a gabarito, a trabalho, the requisições or the login gate is the student coming back; a confirmation answered or the palette closed is the student who never left.

### The login gate is the open
The gate covers the page at every start ([0024](0024-login-page.md)), so coming back from it is the "every time the cli opens", with no second trigger. `fetch_pending` and the after-login worker go: the listing that the return sends enqueues the never-synced matérias from the database once it has saved, the mocked one included.

### `r` sends the listing next to the matéria
`r` still puts the highlighted matéria's tab at the front of the queue, and also asks for the listing. The consumer runs the listing first, as it always has.

### A listing repaints the list in place
Over a populated list only `MateriaList.show` runs, which keeps the highlight ([0008](0008-building-the-materias-list.md)): no cover, no focus, since the listing changes no atividade, trabalho or aula. The first listing, into an empty list, keeps the cover and the full `reload_materias`.

### Only news is announced
The toast names the matérias the database did not have — one by name, several by count — and stays quiet otherwise. `27 matérias sincronizadas` on every return and every `r` would be noise; errors still speak.

### A failed listing never closes the app
`_run_materias_sync` reads `httpx.TransportError` as the AVA being unreachable and reports an `httpx.HTTPStatusError` with its status. Logging in again on a 401 stays with the 401 bug.

## Rejected
- **A 20-minute timer.** Asked first and replaced by the return home: it ran while nobody was looking, and every tick against a dead session was a toast or a crash.
- **Sending on every `ScreenResume`.** Answering a confirmation or closing the palette would reach the AVA.
- **Sending from each `push_screen` that leaves the page.** Five places today, and the next page would forget; the page knows when it is back.
- **Re-fetching every matéria on `r` or on the way back.** Only discovery was asked; a known matéria is still refreshed alone with `r` or `⏎`.
- **Logging in again on a 401.** Unasked, it would take the session back from the browser each time the student comes home.

## What execution corrected
- **The after-login worker raced the listing for the session.** Both started when the gate closed, and its `list_all` landed inside the listing's `commit`: `This session is in 'prepared' state`. Rather than order two workers, the worker went away, and every read of the listing now happens inside the consumer, after the save.
- **`r` during a listing in flight sends no second one.** `sync_materias` already ignores a request while a listing is pending, and the answer on its way is only milliseconds older than a second one would be.
- `tests/cli/pages/materias/test_materias_listing.py` runs the real `UninterApp` against an `httpx.MockTransport` and counts the listing requests: one at the open, one more coming back from a trabalho, none after closing the palette, one more on `r` next to the matéria's atividades, a new matéria shown while the focus stays on the trabalhos table, and a 401 or a dropped network that leave the app open. The requisições page only opens in debug mode, which is why the round trip goes through a trabalho.
