---
name: debug-panel-as-a-component
description: The debug panel stops knowing what a matéria is — it reads two structural protocols, the AVA lookup moves to `api/capturas` over the DTO aliases, and the mode becomes app state the panel subscribes to. Read before showing debug data on a page, or before touching the panel's arguments.
projects: [api, frontend]
status: done
created_at: 2026-09-12
---

# The debug panel stops belonging to a page

## TL;DR
- `cli/components/debug/` holds the panel, which imports nothing from `api` and reads two `Protocol`s: `Fetched` (what the AVA answered) and `Stored` (what the database kept).
- Finding the raw record behind a stored one moves to `api/capturas`, over the aliases the crawler DTOs already declare.
- `debug_mode` becomes a reactive on `UninterApp`; the panel subscribes to it itself, so a page gets debug by composing the panel and nothing else.
- A page offers its data by satisfying `DebugSource` — one `debug_view()` instead of six call sites passing six arguments.
- The page decides where the panel sits; the panel is a flex child, `1fr` open and `display: none` closed.

The panel is a component in name only: it imports four entities, re-declares three AVA response keys, and takes six domain arguments. Nothing about showing *what came back* against *what we kept* is specific to matérias — but only the matérias page can show it. Part of [0016](../done/0016-cli-components.md)'s vocabulary and [0018](../done/0018-pages-and-their-components.md)'s layout; the panel itself is [0010](../done/0010-debug-mode.md).

## Observed behaviour
- `DebugPanel.show` takes six arguments, four of them domain types, and the module imports `Materia`, `Atividade`, `Trabalho` and `Captura`.
- `salaVirtuais`, `avaliacaoUsuarios` and `trabalhoEtapas` are string literals in the panel **and** aliases in `crawler/materias/dto.py`, `crawler/atividades/dto.py` and `crawler/trabalhos/dto.py`. Renaming one in the crawler leaves the panel silently showing a dash.
- The panel also knows how each is found: trabalho by `id`, atividade by `posicao` index, matéria by `id`.
- `api/*/service.py` already imports `crawler`, so the lookup can sit in `api` without inverting a layer.
- Only the three sync services write a `Captura`; `ProvaSource` writes none, so no second page has anything to show yet.
- The command palette says "Enable debug mode" and calls `app.page.toggle_debug` — global language, one hard-coded page.

## Decisions

### Two protocols, satisfied structurally
`Fetched` carries the located item and where it came from — status, url, moment, the body of a 4xx, and what to say when there is no item. `Stored` carries a label, the field rows and the JSON to copy. They are `Protocol`s, so a page passes whatever it already has and nothing inherits from anything. `Stored` does not ask for a `BaseModel` either: requiring pydantic is still requiring a base class.

### The TUI stops parsing the AVA
`api/capturas` gains the lookup, reading the key off the DTO's alias instead of repeating it. The interface asks for the raw record behind a stored one and renders what it gets; how the AVA shapes a response is the crawler's business, which is why the crawler exists ([0003](../done/0003-crawler-api-cli-layers.md)).

### The mode is context, not a page's state
`UninterApp.debug_mode` is the one flag, and the panel subscribes with `self.watch(self.app, …)` and shows or hides itself. Composing a panel is the whole of opting in — no mixin, no binding to declare, nothing handed down the tree. `j` lives on the app, disabled by `check_action` where the screen has no panel, and the panel sets `-debug` on its own screen so a page's own squeeze rules keep working.

### Data is pulled through `DebugSource`, navigation leaves by message
The page implements one `debug_view()`; the panel asks when it opens and when nudged. Leaving is the other direction and stays a message the page handles, because where `esc` goes is the page's business and not the panel's.

## Rejected
- **A `DebugHost` mixin for pages.** Context is the smaller answer: with the panel subscribing itself there is nothing left for a mixin to carry.
- **Moving the panel to `cli/components/` only when a second page wants one.** The rule in [0016](../done/0016-cli-components.md) is about shapes copied by guesswork; this one is being decoupled because it reaches into three layers, and that is worth doing with one caller.
- **Recording a `Captura` for the prova so it gets a panel too.** A separate change with its own reason; this spec does not invent a second caller to justify itself.
- **Keeping the six arguments and only moving the file.** The imports are what make it page-specific, not the directory.

## What execution corrected
- **The second meta line went.** With one `Fetched` there is one fetch to describe, so the line that showed the *collection's* captura and its row count — a different response from the one in the AVA column — is gone. What it told you is still on screen: the `●` in the matéria list and the header's "sincronizada há 1d". The only view of the six that changed.
- **`steps.py` and `copyable.py` moved back to `cli/components/`.** A shared component may not reach into a page's components, so [0016.6](0016.6-pane-navigation.md) and [0016.7](0016.7-copyable.md) lose the placement they were given yesterday — the same test that sent them down sends them back up.
- **The columns navigate by message, not by action.** Textual resolves an action namespace against `app`, `screen` or `focused` only, so `screen.focus_stored` could never be the panel's own business. `DebugColumn.Move` bubbles to the panel, which focuses the next column or posts `DebugPanel.Left` for the page — which is also what let the prova page reuse the panel without implementing three focus actions.
- `step_left`/`step_right`/`step_up` now take a callable as well as an action string, because the panel's edges are inside itself.
- The prova needed `ProvaSource.raw()` to hand over the payload it parsed; the questão lookup then came free, since `QuestoesDTO` declares `avaliacaoUsuarioHistoricos` the same way the other three declare theirs.
- `stored_record` reads pydantic models and dataclasses alike — the matéria is a `SQLModel`, the questão a frozen dataclass, and neither had to grow a base class to be shown.
