---
name: cli-components
description: `cli/components/` collects the widgets no screen owns, with "imports nothing from api" as the membership test, and eight shapes that exist twice each become one module, one subspec apiece. Read before writing a screen, copying a widget out of another module, or adding a file under cli/.
projects: [frontend]
status: pending
created_at: 2026-09-11
---

# The cli gets a components directory

## TL;DR
- `src/cli/components/` holds the widgets no screen owns. A module there imports nothing from `api`, and that is the whole membership test.
- `navigation/steps.py`, `animations/loading.py` and `hint.py` move in as they are; the two one-file directories go.
- Eight shapes that already exist twice become one module each, a subspec apiece: [0016.1](0016.1-footer-from-bindings.md) to [0016.8](0016.8-empty-state.md).
- A screen picks from `components/` before inventing a widget, and a shape earns a module on its second caller, never its first.
- Nothing changes on screen except where [0016.5](0016.5-confirmation-modal.md) says so: the four screens are rendered headless before and after and compared.

[0015](0015-atividade-completion.md)'s prova screen was drawn three times before it looked like this app, because there was nothing to copy from except whichever module happened to be open — and then it copied the sidebar by pasting six CSS declarations. Context in [CONTEXT.md](../../CONTEXT.md); the layers in [0003](../done/0003-crawler-api-cli-layers.md).

## Observed behaviour
Counted over `src/cli` today: 2276 lines of Python in 21 modules, 191 of CSS.
- The sidebar rule — `width: 44`, `height: 1fr`, `border: none`, `border-right: solid $panel`, `padding: 1 1`, `background: $surface` — is in `app.tcss` twice, character for character, for `MateriaList` and `#prova-questoes`. The pane beside it, `height: 1fr; padding: 1 2`, is there twice too.
- Both option lists build `Table.grid(expand=True, padding=(0, 1))` with an ellipsis column and a right-aligned one, and both open with a dim disabled `Option` as a section title.
- `MateriaHeader` and the prova header are the same two lines: bold name, dim `·`, secondary field, and a dim `·`-joined line under it. Both carry `margin-bottom: 1` under their own selector.
- Four widgets wrap `navigation/steps.py` in their own `action_step_left` and `action_step_right`, and three of them repeat `Binding("escape", …, "back")` with a different destination.
- `DebugColumn` and `FieldsTable` carry the same `check_action` and `action_copy`, differing only in which attribute holds the JSON.
- `ConfirmReset` and `ConfirmStart` are the same modal — `ModalScreen[bool]`, `align: center middle`, a box of `height: auto`, `padding: 1 2`, `border: round`, `background: $surface`, and a cancel that dismisses false — answered two different ways.
- Two of the four screens compose a `Footer`; the other two spell their keys in prose.

## Decisions

### `components/` holds what no screen owns, and the import list proves it
A module under `src/cli/components/` may import Textual, Rich and `cli/format.py`, never `api`. A widget that knows what an atividade is stays in `atividades/`: the test is mechanical, so it settles the argument about where a file goes without a meeting.

### The move comes first, then one extraction per subspec
`navigation/steps.py`, `animations/loading.py` and `hint.py` move unchanged, and the two directories named after a category rather than a thing disappear. Each extraction after that is its own spec and its own diff, so a component that turns out wrong is dropped without unpicking the other seven.

### A shape earns a module on its second caller
One caller is a guess at the next screen; two is evidence. The eight below each have two today. A ninth is added when something needs it twice, not when it looks reusable.

### The migration is behaviour-free, and the exception is named
Matérias, atividades, trabalhos, the debug panel and the prova are rendered headless before and after and compared line by line; a difference is a bug in the migration. [0016.5](0016.5-confirmation-modal.md) is the one subspec that changes what the user sees, on purpose, and says so.

### Colours and marks are [0017](0017-interface-meanings.md)'s subject
This spec moves shapes. A component that needs a colour takes the name from `cli/style.py`, which 0017 creates; neither spec blocks the other.

## Rejected
- **A general widget library.** Anything without a second caller is a guess, and guesses are what the prova screen had to choose from.
- **One commit for the whole refactor.** Eight extractions in one diff cannot be checked against "nothing changed on screen".
- **`format.py` under `components/`.** It is text, not a widget; letting it in makes the directory mean "shared", which is how `utils/` starts.
- **A ninth subspec for the two spinners.** `Loading`'s wave and `MateriaList`'s frames are one caller each and different shapes; they move as they are.
