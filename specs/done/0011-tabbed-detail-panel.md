---
name: tabbed-detail-panel
description: The matéria detail panel becomes a TabbedContent under MateriaHeader — one pane per collection, "1 Atividades" now, "2 Trabalhos" and "3 Aulas" with their own specs — switched by the digit keys, with a tab strip that never takes focus, esc stepping back one level, and a per-pane contract for r, ⏎ and the empty states. Read before touching the right side of the screen, adding a collection to the matéria, binding a digit, or changing where esc goes.
projects: [frontend]
status: done
created_at: 2026-09-08
---

# Tabbed detail panel

## TL;DR
- Below `MateriaHeader`, a `TabbedContent#collections` with one `TabPane` per collection: "1 Atividades" now, "2 Trabalhos" with [0011.1](../pending/0011.1-trabalhos-tab.md), "3 Aulas" with a spec of its own. Today only `#atividades` exists, holding `AtividadeHint`, `AtividadeTable` and `MediaBar`.
- `1`, `2`, `3` activate the tab with that number from anywhere; the label carries the digit, the footer does not. A digit without a pane does nothing.
- The tab strip cannot take focus, so `←`/`→` stay the panel-focus keys of 0010.1 and 0010.2.
- `esc` steps back along the focus chain: debug panel → the active pane's table → the list. `focus_atividades` becomes `focus_pane`.
- Switching tabs moves focus into the new pane only when it was inside the panel; on the list it stays.

[0005.1](../pending/0005.1-trabalhos-in-the-interface.md) asked where trabalhos go on screen. The answer is a second tab in the same panel, and the tab layout lands now so nothing moves when the other collections arrive. Context in [CONTEXT.md](../../CONTEXT.md); the master-detail screen in [0004](0004-textual-tui.md), the debug panel in [0010](0010-debug-mode.md), the focus chain in [0010.1](0010.1-selectable-atividades.md) and [0010.2](0010.2-debug-panel-focus-and-copy.md).

## Observed behaviour
- Textual 8.2.8 `ContentTabs`, the strip inside `TabbedContent`, is focusable and binds `←`/`→` to previous/next tab; `TabbedContent` itself binds nothing. Checked in `BINDINGS` and `can_focus`.
- No widget in `cli/` binds a digit, and neither do `OptionList`, `DataTable` or `Tabs`. Checked in every `BINDINGS`.
- A `TabbedContent` with one pane still renders the strip, two rows high; `TabbedContent` and `TabPane` are `height: auto` with no padding, so `#detail` needs no CSS change. Checked with `run_test` and `DEFAULT_CSS`.
- When the pane holding the focused widget hides, focus drops to nothing; and `focus()` on a widget inside a hidden pane succeeds silently. Checked with `run_test`.
- Hiding a pane leaves its children's `display` untouched, so `table.display` keeps working as the "has rows" flag. Same probe.
- `MediaBar.show()` sets `display` inline, so only hiding a parent hides it from CSS ([0010](0010-debug-mode.md)).

## Decisions

### The panel is `MateriaHeader`, then the tabs, then `DebugPanel`
The header describes the matéria and the tabs describe its collections, so the header stays above them. `DebugPanel` stays below and outside: it already renders any resource's capture ([0010](0010-debug-mode.md)), and it must not vanish when the tab changes.

### Panes are declared in `compose`, one per collection
The set is static and named now: `#atividades`, `#trabalhos`, `#aulas`, in that order, each arriving with its spec as a `TabPane` in `compose`. Only the first exists today. `add_pane` is for dynamic sets. The container is `#collections`.

### Digits switch tabs from anywhere, and the label teaches the key
App bindings `1`, `2`, `3` with `show=False`, calling `show_tab(n)`, which activates the n-th pane and does nothing when there is none. Titles are "1 Atividades", "2 Trabalhos", "3 Aulas", so the footer stays with `r`, `q`, `j`, `d`. Clicking a tab keeps working.

### The strip never takes focus
`can_focus = False` on the strip after mount kills its `←`/`→`, so `→` keeps focusing the table and `←` the list, as 0010.1 and 0010.2 built them. Still one focusable at a time, as [0004](0004-textual-tui.md) wanted.

### `esc` goes back one step, and "the table" means the active pane's
`focus_atividades` becomes `focus_pane`: it focuses the active pane's table, or the list when that pane has nothing to focus. The debug panel's `esc`, the list's `→` and closing debug mode all call it. `AtividadeTable` gains `esc` → `focus_materias`, so the chain unwinds one `esc` at a time: debug → table → list. `←` at the edge keeps doing the same ([0010.2](0010.2-debug-panel-focus-and-copy.md)).

### Switching tabs moves focus only when it was inside the panel
On `TabActivated`, if nothing has focus — what a hidden focused widget leaves behind — `focus_pane` runs. Focus on the list stays there. So a digit pressed from the table lands on the new pane's table, or on the list when that pane has nothing to focus.

### The active pane owns `r`, `⏎`, the hint and the empty message
Today the only pane is atividades and nothing changes. The contract 0011.1 implements: `action_refresh` and `⏎` refetch the active pane's collection, each pane reads its own stamp for "never synced" into its own hint, and `show_materia` updates every pane on cursor move so switching is instant.

### `#grades` dissolves into the pane; `-short` hides `#collections`
The pane is the wrapper `#grades` existed for. With the debug panel open on a short terminal, hiding the whole `TabbedContent` also removes a strip whose content is hidden anyway.

## Rejected
- **No strip while there is one pane.** Two rows jump when trabalhos arrive, and the strip is the panel's title today.
- **Placeholder panes for trabalhos and aulas.** An empty tab is a promise on screen; each arrives with its spec. Tab switching is tested with a pane added at runtime.
- **`tab` cycling tabs.** It is Textual's focus key, and 0010.2 built the chain on arrows and `esc`.
- **Focusable strip with `←`/`→`.** Collides with 0010.1 and needs a focus step before every switch.
- **Focus always following the tab.** Pressing `2` from the list would drag focus into the panel; the list is where navigation happens.
- **Digits in the footer.** Three entries for what the labels already say.
- **`r` refetching every collection of the matéria.** Trabalhos cost three requests per matéria ([0005](0005-trabalhos.md)); the person pressing `r` is looking at one tab.
- **Sections stacked in one pane.** Half the matérias have no trabalho ([0005.1](../pending/0005.1-trabalhos-in-the-interface.md)); an empty section costs rows the table needs on short terminals.
- **A `Screen` per collection.** Freezes the matéria, as 0010 already found.

## What execution corrected
- `focus_atividades` lived in five places of the debug panel — both `esc` bindings and the edge steps of `←` and `↑` — not just the two `esc` bindings; all five became `focus_pane`.
- `focus_pane` falls back to the list whenever the active pane is not atividades, so a pane added at runtime never leaves focus on a hidden table.
- The strip is reached with `query_one(Tabs)`, since `ContentTabs` is a `Tabs`, instead of importing Textual's private module.
- Verified headless against a seeded temporary SQLite with stubbed services: one-pane strip, `2` and `3` as no-ops, `→`/`esc` through the debug panel and back, a digit from the table landing on the list when the target pane has nothing to focus, a digit from the list leaving focus alone, a tab click, a matéria without atividades keeping `→` on the list, and `#collections` hidden at 24 rows with debug open.
- `run_test` cannot be reused on one App instance; the harness builds a fresh App per terminal size — worth knowing for the layer-5 tests of [0002](../pending/0002-testing-strategy.md).
