---
name: pages-and-their-components
description: Every screen becomes `cli/pages/<page>/page.py`, a widget only one page uses moves into that page's own `components/`, and the matérias screen stops being `UninterApp.compose`. Read before adding a screen, deciding where a widget goes, or looking for a file that used to be under `materias/` or `debug/`.
projects: [frontend]
status: done
created_at: 2026-09-11
---

# Pages, and the components each one owns

## TL;DR
- `cli/pages/<page>/page.py` for each of the four screens: `materias`, `prova`, `inicio`, `reset`. Nothing is called `screen.py`.
- A widget one page uses lives in that page's `components/`; a widget two pages use lives in `cli/components/`. The directory answers "who else uses this".
- The matérias screen becomes a real `Screen`. `app.py` keeps the services, the sync queue and the workers; the page owns the layout, the focus and the tabs.
- `q`, `r`, `j` and `d` move to the matérias page, which retires the prova's three shadow bindings.
- An import that crosses a page is absolute (`from cli.components.footer import Footer`); inside a page it stays relative.

The four screens are filed in four unrelated places: one inside `UninterApp.compose`, one in `provas/screen.py`, and two confirmations under `atividades/` and `commands/`. Nothing says which widgets belong to which screen, so [0016](../done/0016-cli-components.md)'s `components/` is the only directory whose name is a claim about reuse — and the rest have to be read to find out. Context in [CONTEXT.md](../../CONTEXT.md); the layers in [0003](../done/0003-crawler-api-cli-layers.md).

## Observed behaviour
- `app.py` is 570 lines: eight services and repositories, the queue, four workers, and the whole main screen — its layout, its focus rules and its tab handling.
- `ProvaScreen` carries `Binding(key, "nothing", "", show=False)` for `q`, `r` and `j`, because those are app bindings and an app binding fires from every screen.
- `materias/`, `atividades/`, `trabalhos/` and `debug/` hold nine widgets, and the main screen is the only thing that composes any of them.
- A confirmation modal lives in `commands/reset.py`, next to the command palette, because that is what pushed it.

## Decisions

### A page is a screen, and its file is `page.py`
One name for the thing, in one place per page: `pages/prova/page.py`, not `provas/screen.py`. The directory carries the name, so the file does not repeat it, and a page's own widgets sit beside it rather than in a sibling of the app.

### `components/` means shared, `<page>/components/` means not
Two directories with the same name and opposite claims. A widget starts in the page that needs it and moves up to `cli/components/` on its second caller — the rule [0016](../done/0016-cli-components.md) already sets, now with somewhere to move *from*.

### The matérias screen becomes a `Screen`; the app keeps the queue
The split follows what survives a screen push: the services, the queue and the workers outlive the prova being open, so they stay on `UninterApp`; the layout, the highlighted matéria and the focus do not, so they go to the page. `get_default_screen` builds it, which is also what gives the app one typed reference to talk to.

### The keys a page uses are the page's keys
`r`, `j`, `d` and the tab numbers only mean something on the matérias page, and `q` is the way out of it. Declaring them there instead of on the app deletes the shadow bindings the prova needed and keeps the footer identical, since a screen's bindings already come before the app's.

### Crossing a page is an absolute import
`from cli.components.footer import Footer` rather than `from ....components.footer import Footer`. Four levels of dots is the point at which a relative path stops saying where a module is; inside a page, one or two dots still do.

## Rejected
- **Splitting `app.tcss` per page.** Worth doing, but it changes what wins in the cascade, and this spec moves files without changing a pixel. Later, on its own.
- **`pages/home/`.** The page shows matérias; naming it for its position in a stack says less than naming it for what is on it.
- **Keeping `ProvaScreen` as a class name.** It is `ProvaPage` now: the vocabulary is pages, and half of it saying screen is how `screen.py` came back.
- **One `pages/confirmacoes/` for both modals.** They confirm unrelated things and are pushed by different pages; grouping them by their shape is what put one of them under `commands/`.

## What execution corrected
- **The app and the page talk through four methods, not a shared type.** `SyncItem` would have had to live somewhere both could import, and `app.py` already imports the page — a cycle. The app exposes `fetch`, `is_fetching`, `fetch_pending` and `sync_materias`; the page reaches them through a `uninter` property, and the queue's item type never leaves `app.py`.
- **The initial load moved into the page's `on_mount`.** On the app it ran before the page's widgets existed, and the first sync writes straight into the matéria list. The page asks for it once it is mounted instead.
- `q` became `("q", "app.quit", …)`: an unqualified action on a screen looks for `action_quit` on that screen, and only the app has one.
- Removing the prova's shadow bindings changed nothing on screen, which is the proof they were only ever guarding against app-level keys.
- **Every `app.focus_*` in a widget became `screen.focus_*`.** Those actions moved to the page with the layout, and an action string naming the wrong namespace fails quietly: the key does nothing and nothing is logged. Found by pressing `right` on the matéria list in the binding check, not by reading.
- The specs still pending had their module paths rewritten. The three already in `done/` describe the layout of the day they were executed and were left alone.
