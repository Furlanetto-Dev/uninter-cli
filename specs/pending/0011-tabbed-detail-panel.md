---
name: tabbed-detail-panel
description: The matéria detail panel becomes a TabbedContent under MateriaHeader — one pane per collection, "1 Atividades" today and "2 Trabalhos" with 0011.1 — switched by the digit keys, with a tab strip that never takes focus and a per-pane contract for r, ⏎ and the empty states. Read before touching the right side of the screen, adding a collection to the matéria, or binding a digit.
projects: [frontend]
status: pending
created_at: 2026-09-08
---

# Tabbed detail panel

## TL;DR
- Below `MateriaHeader`, a `TabbedContent#collections` with one `TabPane` per collection of the matéria; today only `#atividades`, titled "1 Atividades", holding `AtividadeTable` and `MediaBar`.
- `1`, `2`, `3` activate the tab with that number from anywhere; the label carries the digit, the footer does not.
- The tab strip cannot take focus, so `←`/`→` stay the panel-focus keys of 0010.1.
- Each pane owns one collection: `r`, `⏎`, the "never synced" hint and the empty message act on the active pane. Today that is atividades, unchanged.
- `#grades` dissolves into the pane; the `-short` debug rule hides `#collections` instead.

[0005.1](0005.1-trabalhos-na-interface.md) asked where trabalhos go on screen. The answer is a second tab in the same panel, and the tab layout lands now so nothing moves when [0011.1](0011.1-trabalhos-tab.md) arrives. Context in [CONTEXT.md](../../CONTEXT.md); the master-detail screen in [0004](../done/0004-tui-em-textual.md), the debug panel in [0010](../done/0010-modo-debug.md), focus keys in [0010.1](../done/0010.1-selectable-atividades.md).

## Observed behaviour
- Textual 8.2.8 `ContentTabs`, the strip inside `TabbedContent`, is focusable and binds `←`/`→` to previous/next tab; `TabbedContent` itself binds nothing. Checked in `BINDINGS` and `can_focus`.
- Neither `OptionList`, `DataTable` nor `Tabs` binds a digit. Checked in `BINDINGS`.
- A `TabbedContent` with one pane still renders the strip, two rows high. With `can_focus = False` on the strip, `tab` skips it, `→` no longer switches, and a click on a tab still does. Checked with `run_test`.
- `MediaBar.show()` sets `display` inline, so only hiding a parent hides it from CSS ([0010](../done/0010-modo-debug.md)).

## Decisions

### The panel is `MateriaHeader`, then the tabs, then `DebugPanel`
The header describes the matéria and the tabs describe its collections, so the header stays above them. `DebugPanel` stays below and outside: it already renders any resource's capture ([0010](../done/0010-modo-debug.md)), and it must not vanish when the tab changes.

### Panes are declared in `compose`, one per collection
The set of collections is static: atividades now, trabalhos with 0011.1 as a second `TabPane` in `compose`. `add_pane` is for dynamic sets. Pane ids are the domain nouns, `#atividades` and `#trabalhos`; the container is `#collections`.

### Digits switch tabs from anywhere, and the label teaches the key
App bindings `1`, `2`, `3` with `show=False`, calling `show_tab(n)`, which activates the n-th pane and does nothing when there is none. Titles are "1 Atividades", "2 Trabalhos", so the footer stays with `r`, `q`, `j`, `d` ([0010.1](../done/0010.1-selectable-atividades.md)). Clicking a tab keeps working.

### The strip never takes focus
`can_focus = False` on the `ContentTabs` after mount kills its `←`/`→`, so `→` keeps focusing the table and `←` the list, and `tab`/`esc` stay the debug keys. Still one focusable at a time, as [0004](../done/0004-tui-em-textual.md) wanted.

### The active pane owns `r`, `⏎`, the hint and the empty message
Today the only pane is atividades and nothing changes. The contract 0011.1 implements: `action_refresh` and `⏎` refetch the active pane's collection, each pane reads its own stamp for "never synced", and `show_materia` updates every pane on cursor move so switching is instant.

### `#grades` dissolves into the pane; `-short` hides `#collections`
The pane is the wrapper `#grades` existed for. With the debug panel open on a short terminal, hiding the whole `TabbedContent` also removes a strip whose content is hidden anyway.

## Rejected
- **No strip while there is one pane.** Two rows jump when trabalhos arrive, and the strip is the panel's title today.
- **`tab` cycling tabs.** It is Textual's focus key and the debug panel's entry ([0010](../done/0010-modo-debug.md)).
- **Focusable strip with `←`/`→`.** Collides with 0010.1 and needs a focus step before every switch.
- **Digits in the footer.** Three entries for what the labels already say.
- **`r` refetching every collection of the matéria.** Trabalhos cost three requests per matéria ([0005](../done/0005-trabalhos.md)); the person pressing `r` is looking at one tab.
- **Sections stacked in one pane.** Half the matérias have no trabalho ([0005.1](0005.1-trabalhos-na-interface.md)); an empty section costs rows the table needs on short terminals.
- **A `Screen` per collection.** Freezes the matéria, as 0010 already found.
