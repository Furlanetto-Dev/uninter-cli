---
name: request-history
description: ctrl+l opens, in debug mode, a page listing the last fifty requests the CLI made — method, URL, status, timing, the body sent and the response as a tree of dropdowns — recorded by an httpx event hook so the login POST is caught too, with the senha and the session cookie redacted. Read before adding a request to the crawler, touching ava_client, or looking for where requests are logged.
projects: [crawler, frontend]
status: done
created_at: 2026-09-17
---

# The request history

## TL;DR
- `RequestLog` keeps the last fifty requests in memory, with what was sent and what came back.
- Recording is an httpx event hook on `ava_client`, so every call is caught, login included.
- The `senha` is redacted in the hook, where the body passes; the RU stays.
- `ctrl+l` opens a page listing them, newest first, only while debug mode is on.
- The list is live: the modal subscribes to the log on mount and unsubscribes on unmount.

`captura` keeps the last response per resource, which cannot answer what this run actually
did. Prova answering is next and writes to a real graded exam, so seeing the body that went
out stops being a convenience. See [CONTEXT.md](../../CONTEXT.md) and
[0010](0010-debug-mode.md).

## Observed behaviour
- An httpx event hook sees the login POST body, `login=…&senha=…`, which `AvaSession.get()` never touches because `log_in` posts through the client directly — verified against a `MockTransport`.
- `response.elapsed` raises inside a response hook ("may only be accessed after the response has been read or closed"), so timing is measured between the two; and a transport error fires the request hook and no response hook, leaving the entry with nothing to close it — both verified.
- `CapturaRepository.replace` deletes the row for a `(recurso, materia_id)` before inserting, so `captura` is a latest-value store, never a history — read from the repository.
- A full background sweep is about fifty requests: one `materias` call plus `atividades` and `trabalhos` per matéria, counted from the stored capturas.

## Decisions

### Recording is an httpx event hook, not a wrapper around the session
`ava_client` gains `event_hooks`: the request hook opens an entry, the response hook closes
it. Wrapping `AvaSession.get` would miss the login, the request most worth seeing when
authentication broke — and a transport error fires only the first hook, so `AvaSession`
attaches that error itself.

### `RequestLog` owns the entries and the listeners
A `deque(maxlen=50)` and a list of callbacks, built in `main.py` and handed to both
`ava_client` and the app, so the session keeps its one job. Fifty is under one sweep, so a
refresh flushes the history; accepted, and raising the cap is one word.

### The senha is redacted in the hook
The hook is where the body passes, so it is the only place the password can be caught before
reaching a screen. `login=` keeps its value, `senha=` does not — the database holds it in
plaintext, but [0016.7](0016.7-copyable.md) puts it one keystroke from the clipboard.

### `ctrl+l` opens a page, and only in debug mode
A `Screen[None]` of its own, because the history belongs to the run rather than to any page,
and it needs room for a tree and its buttons. The key cannot collide with the `a`–`h`
answering a questão or the `j` focusing the debug panel. Off debug, it does nothing.

### The page is a list beside one detail
`Sidebar` on the left; on the right the meta line, two buttons, the body sent when there is
one, and the response as a `Tree`. An array opens on its first element, because a collapsed
`[5]` says nothing about what is inside. `c` and `y` copy without reaching for the mouse.

### Copying a request gives a curl with the secrets already placeheld
`as_curl` writes the shape the files in `uninter-endpoints/` already have, `$UNINTER_TIME`
and `$UNINTER_TOKEN` included, so a copied request is safe to paste and replayable by whoever
exports those two.

## Rejected
- **Persisting it, either in a table of its own or by making `captura` append-only.** It answers a question about the run in front of you; a table would need a growth policy nothing else needs, and every reader of `find()` would have to start asking for the newest row of a store keyed by matéria rather than by time.
- **Polling the log from the page.** Cheaper than a subscription and needs no teardown, but it repaints on a timer that is wrong in both directions — too slow to watch a sweep, too fast when nothing is happening.

## What execution corrected
- **`curlify2` could not be used.** It does the job straight off an `httpx.Request`, but ships no `py.typed`, so pyright strict fails the import with `reportMissingTypeStubs`. Eight lines is cheaper than an ignore or a loosened setting, and rolling it let the noise headers go and the cookie be placeheld on the way out.
- **A mocked request says `mock`.** Once [0028](0028-fake-ava.md) routed the mocked matéria through the client, a request the fixture answered was indistinguishable from one the AVA did. `FakeAva` marks its responses through httpx's `extensions`, the response hook carries the mark onto the entry, and the row and the detail wear the tag the prova header already uses.
- **A row and a body speak different markups.** `row_grid` renders through a rich `Table`, where `$text-success` is not a style and a bare `[/]` closes nothing, so the first list painted raised `MarkupError`. Rows use plain colour names with explicit closing tags, as [0025](0025-global-colours.md) found for everything rich draws, and the tree builds `Text` directly — the AVA's JSON is full of `[` that markup would eat.
- **Two names had to move.** Textual's `App` already owns `_log` for its logger, so the app holds the history as `_history`; and a widget's own width belongs in its `DEFAULT_CSS`, not `page.tcss`, which collapses it to nothing wherever that stylesheet is not loaded — including every test.
