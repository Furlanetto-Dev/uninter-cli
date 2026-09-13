---
name: one-stylesheet-per-page
description: Each page gets `page.tcss` through `Screen.CSS_PATH`, written as one block nested under the page's own class — because a page stylesheet is global and loads lazily, so an unnested selector restyles another page mid-session. Read before adding a rule to app.tcss or styling a page.
projects: [frontend]
status: done
created_at: 2026-09-12
---

# One stylesheet per page

## TL;DR
- `cli/pages/<page>/page.tcss`, named by `Screen.CSS_PATH`, for the rules only that page needs.
- **Every page file is one block nested under the page's class.** Unnested, its rules are global and arrive the first time that page is opened.
- A component's own look stays in its `DEFAULT_CSS`; a page file styles the page, not the widgets it borrows.
- `app.tcss` keeps only what is true of every screen.
- Nesting raises specificity, so each rule is moved and the render compared — the split must not change a pixel.

`app.tcss` is 29 rules for four pages and six shared components, and nothing in the file says which is which: `#prova-body` sits between the confirmation buttons and the debug columns. [0018](../done/0018-pages-and-their-components.md) deferred this, saying it "changes what wins in the cascade" — it does, and this spec says how.

## Observed behaviour
Measured against Textual 8.2.8.
- `Screen.CSS_PATH` works: `App._load_screen_css` reads it the first time that screen is used and adds it to the app's single stylesheet. It is never unloaded.
- `Stylesheet.read(path)` takes no `scope`, while `Screen.CSS` is added with `scope=screen._css_type_name`. **A page's CSS file is global; only the inline string is scoped.**
- Proved: `MateriaList { width: 20 }` in the prova page's `CSS_PATH` left the matérias sidebar at 41 columns — until a prova was opened once, after which it was 17. The rule arrives mid-session, on a page that never asked for it.
- Proved: the same rule nested as `ProvaPage { MateriaList { … } }` leaves the matérias sidebar at 41 before and after, and `ProvaPage { QuestaoList { … } }` does move the prova's own list to 17.
- User CSS outranks every `DEFAULT_CSS` rule whatever the specificity ([0016.2](../done/0016.2-sidebar-and-detail-pane.md)), and `app.tcss` and a page file are both user CSS. Between them it is specificity, then source order — and source order now means "whichever page was opened first".
- The 29 rules today: 8 belong to the matérias page, 3 to the prova, 6 to the two confirmations, 12 to the debug panel, and 1 — `Screen { layers: base }` — to every screen.

## Decisions

### A page file is one nested block, always
`ProvaPage { … }` wrapping the whole file. It costs one indent and buys the scoping the file does not get on its own. The rule is absolute because the failure it prevents is invisible: nothing breaks until someone opens the other page, and then a width changes with no edit to blame.

### A component's look is its `DEFAULT_CSS`, not a page file
The debug panel's twelve rules follow the panel, not the pages that show it — [0019](../done/0019-debug-panel-as-a-component.md) put it on two. A page file holds what the *page* arranges: where its panes sit, what its own ids do, how it squeezes on a short terminal.

### `app.tcss` keeps only what every screen shares
Today that is one rule. A file that small is the point: anything else in it is a rule nobody could place.

### Moving a rule is a change until proven otherwise
Nesting adds a type selector, so a moved rule outranks the one it replaced, and a rule that used to lose may start winning. Each page moves on its own, and the six headless views are compared before and after — the same bar as [0016](../done/0016-cli-components.md).

## Rejected
- **`Screen.CSS` inline strings.** Scoped for free, but the request was files, and a stylesheet inside a Python string loses its syntax highlighting and its diff.
- **One file per component beside its module.** Components already carry `DEFAULT_CSS`; a second place for a component's look is the split this spec is undoing.
- **Leaving `app.tcss` whole.** It grows with every page, and the next page's rules will land in the middle of another's.

## What execution corrected
- **`Screen.CSS_PATH` does not reach the default screen.** `App._init_mode` calls `_load_screen_css` only on the `MODES` branch; `get_default_screen()` registers the screen and never reads its `CSS_PATH`. The matérias page had `css_path` set and its file absent from `app.stylesheet.source` — every rule silently gone. The four files are listed on `App.CSS_PATH`, which takes a list and resolves relative to `cli/`.
- **That also removes the hazard this spec was built around.** Listed on the app, every page file loads at startup instead of the first time its page opens, so nothing arrives mid-session. The nesting stays load-bearing for exactly the same reason as before: the files are still global.
- **`Screen.-debug.-short DetailHeader` was never the matérias page's rule.** `Screen` matches every screen, so the prova page had been getting that squeeze since [0019](../done/0019-debug-panel-as-a-component.md) gave it a panel. Nesting it under `MateriasPage` took it away and moved the prova body down a line — caught only because the comparison was run at 30 rows as well as 45.
- `app.tcss` keeps four rules, not one: the three `-debug.-short` ones cannot move into a widget's `DEFAULT_CSS`, because `SCOPED_CSS` is `True` and a widget's own CSS cannot select the classes on its screen.
- Grouped selectors nest fine (`AtividadeTree, TrabalhoTable` inside the page block); splitting them was a wrong guess while the real fault was the file not loading at all.
