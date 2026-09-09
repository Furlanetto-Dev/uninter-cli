---
name: debug-mode
description: Debug mode in the TUI — a command in the palette, `d` in the footer, a panel with the AVA's raw response next to what was written to SQLite; requires the `Captura` entity, written on every sync. Read before touching the return value of `AvaSession.get` and of each `fetch`, or the layout of the detail panel.
projects: [crawler, api, frontend]
status: done
created_at: 2026-09-08
---

# Debug mode

## TL;DR
- Every AVA response is now written to the `Captura` entity (resource, matéria, URL, status, body), in the same commit as the entities.
- A palette command turns debug mode on; while on, `d` appears in the footer.
- `d` opens a table in the matéria panel: raw AVA on the left, stored row on the right, one row per object.
- Terminal with 40 rows or more: the panel sits below the média. Fewer: it replaces the atividades table.

Today the response body dies inside the `fetch`, and when a value looks wrong there is no way to tell whether the AVA, the DTO or the screen is to blame. Context in [CONTEXT.md](../../CONTEXT.md); the 404 in [0001](0001-ava-atividades-crawler.md), layers in [0003](0003-crawler-api-cli-layers.md), `check_action` in [0004](0004-textual-tui.md), the palette in [0007](0007-background-queue-and-reset.md), names in [0009](0009-english-code-portuguese-domain.md), fixtures in [0002](../pending/0002-testing-strategy.md).

## Observed behaviour
- `AvaSession.get` returns only the parsed JSON, or `None` on a 404; URL, status and text are lost. Read in the code.
- A 44-row terminal leaves some 26 empty rows under the média; at 17, the table alone fills the panel. Two screenshots.
- Textual 8.2.8: `VERTICAL_BREAKPOINTS` sets a class on the `Screen` per height band on every `Resize`. Checked in the source.
- `check_action` returning `False` hides the key from the `Footer` (measured in 0004); changing the condition requires `refresh_bindings()`.
- A raw atividade item has some 160 fields (0002). Inference, not measured: about 1 MB of database with the 26 matérias.

## Decisions

### The mode is a session `reactive`, turned on from the palette
`debug_mode = reactive(False)` on the App; a command in `AppCommands` labelled "Enable/Disable debug mode" according to the state — palette commands are in English. It starts off and does not persist: debug is a reaction, not configuration. Turning it off closes the panel.

### `d` only exists in the footer with the mode on
`("d", "debug", "debug")` in `BINDINGS`; `check_action` returns `False` with the mode off and `watch_debug_mode` calls `refresh_bindings()`. `d` toggles the panel.

### The panel lives in `#detail` and follows the cursor
`DebugPanel` (`cli/debug/panel.py`) after the `MediaBar`, fed by `show_materia`. It is not a `Screen`: a pushed screen freezes the matéria, and the arrow switching matérias is what 0004 bought. `MateriaHeader` stays visible in both modes.

### Two modes by terminal height, via breakpoint
`VERTICAL_BREAKPOINTS = [(0, "-short"), (TALL_TERMINAL_ROWS, "-tall")]`, with `TALL_TERMINAL_ROWS = 40`; an open panel puts `-debug` on the `Screen`. In `-tall` the panel is `1fr` under the média; in `-short` the CSS hides `#grades`, the `Vertical` that now wraps table and média. The arithmetic: 21 rows taken by the worst matéria plus 15 readable rows of panel gives 36, rounded to 40.
`#grades` exists because `MediaBar.show()` sets `display` inline, which beats CSS; hiding the parent solves it.

### A two-column table, one row per object
`VerticalScroll` with a `rich.Table`: a header with URL, status and time; the matéria (the `salaVirtuais` entry | `Materia.model_dump()`); one row per atividade (`avaliacaoUsuarios[i]` | the `Atividade` with `posicao == i`). Raw with `JSON.from_data`, stored with `Pretty`. The panel knows no aliases, so it serves trabalhos when 0005.1 lands.
No capture: "sem resposta gravada · `r` para buscar". 404: status and text on the left, stored rows on the right — makes defect 1 of 0002 visible without fixing it.

### `d` opens the panel without stealing focus; `tab` enters it, `esc` goes back
The arrows keep switching the matéria, and the panel follows. To scroll the JSON, `tab` or the mouse wheel move focus to the panel, and `("escape", "app.focus_materias", "voltar")` returns it to the list — the action belongs to the App, so the panel does not know the list. The columns scroll together to keep the alignment.

### The response is always written, to the `Captura` entity
`api/capturas/entity.py`: `id`, `recurso`, `materia_id | None`, `url`, `status`, `corpo`, `recebida_em`. It is an entity, hence Portuguese (0009). `CapturaRepository.replace` deletes by `(recurso, materia_id)` and inserts; `find` feeds the panel. It writes with debug on or off: what fills the database is the queue from 0007, and the reset already wipes everything. Bonus: these are the real fixtures 0002 asks for.

### The body crosses the layers along with the entities
`AvaSession.get` returns `AvaResponse(url, status, text, json)`; each `fetch` returns `FetchResult(response, entities)`; `AvaResponse.to_captura(recurso, materia_id)` creates the entity the way `to_atividade` does. The services write capture and entities in the same transaction (`_store`, under the `shield`). This changes the signature of `fetch`, which layer 2 of 0002 tests.

## Rejected
- **In memory only.** Empty after a restart.
- **Capturing only with debug on.** The queue does most of the syncs; the panel would be empty.
- **An observer on `AvaSession`.** It only knows the URL, and raw and stored would land in separate commits.
- **A raw column on `Materia`.** A new column requires a reset; it serves neither the list nor trabalhos.
- **`Screen` or `ModalScreen`.** Freezes the matéria.
- **Measuring the space after layout.** Depends on a settled layout and flickers for a frame.
- **A field-by-field table.** Alias introspection and 160 rows per atividade. A possible evolution.
- **Stacking raw over stored, or per-column scrolling.** Loses the alignment.
- **`d` focusing the panel on open.** It was the first version: it stole the arrows from the list on every open, and whoever opens debug wants to keep navigating.
- **`j`/`k` on the App, `UNINTER_DEBUG`, a horizontal breakpoint.** Spends footer; debug is a reaction; the panel has 90+ columns in the screenshots.

## What execution corrected
- `debug` collides with Textual's `App.debug` (the framework's debug mode): the reactive became `debug_mode`.
- `cli/` was reorganised into directories by context — `materias/`, `atividades/`, `commands/`, `animations/`, `debug/` — before this spec; the panel lives in `cli/debug/panel.py` and the palette label in `cli/debug/command.py`.
- Verified offline, with `run_test` and fake requests: capture written and replaced, 404 with its text, `d` hidden and visible, panel following the cursor and rebuilt after `r`, `#grades` disappearing at 24 rows.
- The 0002 step is left for when the tests exist, as in 0007.
