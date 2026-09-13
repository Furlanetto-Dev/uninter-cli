---
name: repainting-less
description: The interface flickers because a clock lays the whole screen out once a second, the footer recomposes on every arrow key, and every list rebuild paints its intermediate states. Read before adding a timer, calling `refresh_bindings`, or rebuilding a list.
projects: [frontend]
status: done
created_at: 2026-09-13
---

# Repainting less

## TL;DR
- `Static.update()` lays out by default. `DetailHeader` is two lines and never changes size, so it updates with `layout=False` and the prova's clock stops re-arranging the screen every second.
- `refresh_bindings()` makes the footer *recompose* — every key widget destroyed and rebuilt. The matéria list only calls it when the answer it guards actually changes.
- A modal focuses its safe answer through `AUTO_FOCUS`, not in `on_mount`, so the focus lands once instead of moving from `Não` to `Sim` in view.
- The debug panel is `display: none` in CSS and shows itself only once filled: owning `display` in Python alone meant it was painted, empty, before `on_mount` ran.
- Measured, not guessed: a counter on `Widget.refresh` over the same scripted keystrokes, before and after.
- The render is byte-identical at 45 and 30 rows.

The flicker is worst on the prova, and that is the page with a clock. Nothing here changes what is on screen — only how often it is redrawn.

## Observed behaviour
Counting `Widget.refresh(layout=…)` calls while driving the app headless.
- Three seconds idle on the prova: 3 layout passes, one per second, all `DetailHeader`. A layout pass re-arranges the whole screen; the header's text changes but its size never does.
- One arrow key on the matéria list: 32 layout passes and 20 repaints, of which `Footer` ×4 and `FooterKey` ×14 — the footer rebuilding its keys because [0016.1](../done/0016.1-footer-from-bindings.md)'s guard calls `refresh_bindings()` on every highlight, even when the answer is the same.
- Answering one alternativa: 7 layout passes, including `QuestaoList` ×2 for a rebuild of all eleven rows to change one mark.
- The matérias page is quiet at rest: 0 passes over three seconds.
- Opening `ConfirmStart` focuses twice: `set_focus(confirm-no)` then `set_focus(confirm-yes)`. Textual's `AUTO_FOCUS` defaults to `"*"` and takes the first focusable widget before `on_mount` moves it to the safe answer.
- The debug panel runs `reload()` before `follow_mode` ever sets `display`, because a widget with no `display` rule is visible from the moment it is composed. With debug off it appears and vanishes; with debug on it appears empty and then fills.
- `AtividadeTree` costs 13 of the 23 remaining passes on a matéria change: `clear()` plus one `add` per group and per leaf, each invalidating the layout.

## Decisions

### A widget that cannot change size updates with `layout=False`
`DetailHeader` is pinned to two lines, `text-wrap: nowrap` and `text-overflow: ellipsis`, and then `layout=False` is safe rather than a gamble. A header that silently reflowed was never wanted; one that truncates a very long nome is the honest trade.

### `refresh_bindings` is for a changed answer, not for every event
The footer recomposes when bindings change, so calling it on every highlight rebuilds a dozen widgets to draw the same keys. `MateriaList` remembers what it last answered and calls it only when that flips.

### A synchronous rebuild needs no batching
Measured: zero frames are painted *during* a full clear-and-refill of the matéria list, because the handler never yields and Textual paints on idle. `batch_update` around code that cannot be interrupted prevents nothing, so the five wrappers written for it were taken out again.

### A first frame is a frame
Two of the three things that flicker are not repaint counts at all — they are one frame showing the wrong thing. A focus that moves after mount and a widget that is visible before its `on_mount` runs both paint a state nobody asked for, so the answer is to be right from the start: `AUTO_FOCUS` for the focus, CSS for the visibility.

### Flicker is a number before it is a fix
Counting `refresh` calls over scripted keystrokes turns "it flickers" into 32 → 23 and 3 → 0. Every change here was kept or dropped on that measurement, with the rendered output compared at two terminal heights to prove nothing moved.

## Rejected
- **Batching any rebuild, including the tree's.** Written, measured, removed: see the decision above. The tree's 13 refreshes per matéria are real but reach the terminal as one frame.
- **A shorter clock interval, or none.** The clock is the feature; the cost was the layout pass, not the tick.
- **Rebuilding only the changed row of the questões list.** Correct, and more delicate than batching: it needs the summary row and the highlight kept in step. Worth doing once the batch has been lived with.

## What execution corrected
- `DetailHeader.show` had been reformatted onto one line, so the first attempt at `layout=False` silently did nothing and the idle count stayed at 3. Worth a look at the measurement, not at the diff.
- **The panel's flash was mine**, from [0019](../done/0019-debug-panel-as-a-component.md): moving `display` from the stylesheet into the panel's own watcher left it visible until `on_mount`. The CSS rule is back, and Python only ever turns it *on*.
- Fixing the first frame also took opening the prova from 86 layout passes to 59, because the panel is no longer laid out empty and then again full.
- **The batching came out.** It was added on the assumption that a clear-and-refill paints its steps; counting `App._display` says otherwise — 0 frames during the rebuild, 3 after it settles. A `refresh` count is not a frame count, and only the frame count is flicker.
- Frames painted, before and after, over the same keystrokes: three seconds idle on the prova 6 → 3, a matéria change 4 → 3, opening the prova 13 → 13 with the panel no longer laid out empty first.
