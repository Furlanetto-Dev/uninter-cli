---
name: nova-pagina
description: "How a page is built in cli/: where its files go, what the app owns, which keys it declares and how to prove it renders. Use when adding a screen to the TUI, moving a widget between pages, or deciding whether something is a component or a page."
---

You are working on a page of the TUI. The layout is [0018](../../../specs/done/0018-pages-and-their-components.md); the components are [0016](../../../specs/done/0016-cli-components.md).

# Where the files go

```
cli/
  app.py                  UninterApp: services, sync queue, workers
  app.tcss                the only stylesheet
  format.py               text formatting, no widgets
  components/             a widget two or more pages use
  pages/<page>/
    page.py               the Screen, named <Nome>Page
    components/           a widget only this page uses
```

- **The file is always `page.py`.** Never `screen.py`, never `<page>_page.py`; the directory already carries the name.
- **The class is `<Nome>Page`** — `MateriasPage`, `ProvaPage` — except a modal that says what it asks: `ConfirmStart`, `ConfirmReset`.
- **The directory name is the domain noun in Portuguese**, unaccented and singular when the page shows one thing: `pages/prova/`, `pages/materias/`.

## Which `components/`

A widget starts in the page that needs it. It moves to `cli/components/` on its **second calling page** — not when it looks reusable. Moving down is as normal as moving up: if a shared component ends up with one caller again, it belongs to that page.

A module under `cli/components/` **may not import `api`**. If a widget needs to know what an atividade is, it belongs to a page.

# Imports

- Crossing a page, or reaching `cli/` itself: absolute — `from cli.components.footer import Footer`, `from cli.format import format_deadline`.
- Inside the page: relative — `from .components.tree import AtividadeTree`.
- `api`, `crawler` and `settings` are absolute, as everywhere else.

# What the page owns, and what the app owns

The split is **what survives a screen push**. The sync queue and the workers keep running while a prova is open, so they are the app's. The layout, the focus and whatever is highlighted die with the screen, so they are the page's.

- The app talks to the page through named methods (`fetch`, `is_fetching`, `sync_materias`), never by sharing the queue's types — `app.py` imports the page, so the page importing `app.py` at runtime is a cycle. For typing only:

```python
if TYPE_CHECKING:
    from cli.app import UninterApp

@property
def uninter(self) -> "UninterApp":
    return cast("UninterApp", self.app)
```

- Anything that needs the page's widgets to exist goes in the page's `on_mount`, not the app's: the app mounts first.

# Keys

- **Declare a key on the page that uses it.** A binding on the app fires on every screen, which is what forced the prova to shadow `q`, `r` and `j` with a no-op.
- An unqualified action on a screen resolves against that screen. Reaching the app needs the namespace: `("q", "app.quit", "sair")`. A widget reaching the page needs `screen.focus_pane` — **a wrong namespace fails silently**, the key simply does nothing.
- **`esc` means `voltar`**, and `Footer` sorts it first wherever it exists.
- Descriptions are screen text: Portuguese, lowercase, one word where one word does.
- A key shows in the footer only if it is the key that fires. To announce a key a Textual widget owns, re-declare it on the subclass with the inherited action and a description — never mirror it on the screen. Guard it with `check_action` so it is named only while pressing it does something, and make sure the guard does not disable a key that already does something else (`enter` on a `Tree` collapses a group).

# Mixins

A mixin shared by several widgets — navigation, copying — **must not derive from `Widget`**. Textual's `_css_bases` walks only the *first* `DOMNode` base, so a widget mixin in front of `Tree` or `DataTable` hides everything that class declares: its `DEFAULT_CSS`, and its component classes (`No 'tree--guides' key in COMPONENT_CLASSES`).

Write the mixin as a plain class and export the bindings it would have contributed as a list the widget assigns:

```python
STEP_BINDINGS = [Binding("left", "step_left", "", show=False), ...]

class Steps:                      # plain, never Widget
    STEP_LEFT: str | None = None
    async def action_step_left(self) -> None: ...

class AtividadeTree(Steps, Tree[Atividade]):
    BINDINGS = STEP_BINDINGS
    STEP_LEFT = "screen.focus_materias"
```

Never bind a key the host widget already uses for itself: `up` and `down` move a `Tree`'s or `DataTable`'s cursor, and a mixin binding takes them away.

# Composing

```python
def compose(self) -> ComposeResult:
    yield Header()
    with Horizontal():
        yield Sidebar()          # cli/components/sidebar.py
        with DetailPane():       # cli/components/pane.py
            ...
    yield Footer()               # cli/components/footer.py
```

Every page yields `Footer`, modals included — without one, the screen underneath paints its footer through the modal and advertises keys that cannot fire.

# CSS

`app.tcss` is the only stylesheet. A component's own look goes in its `DEFAULT_CSS`; `app.tcss` keeps what one screen bends.

A page may carry its own `page.tcss` through `Screen.CSS_PATH`, but **its rules are global and load the first time that page is opened** — wrap the whole file in one `PageName { … }` block or it will restyle other pages mid-session ([0020](../../../specs/done/0020-one-stylesheet-per-page.md)).

**User CSS beats every `DEFAULT_CSS` rule, whatever the specificity** — `default_rules` is the first field of the specificity tuple. So a declaration that beat `OptionList:focus` from `app.tcss` stops beating it once it becomes a component default: repeat it under `&:focus` in the component.

# Proving it works

There is no test home yet ([0002](../../../specs/rejected/0002-testing-strategy.md)). Drive the app headless and compare the render:

```python
async with app.run_test(size=(140, 45)) as pilot:
    await pilot.pause()
    text = "\n".join(
        " ".join(f"{s.text!r}{s.style!s}" for s in strip if s.text.strip())
        for strip in app.screen._compositor.render_strips()
    )
```

- Compare **styles, not just characters**: a CSS change can move nothing but a colour.
- **Let the screen settle** before reading it. The debug panel loads from the database, so one `pilot.pause()` catches it half drawn and the comparison lies — pause in a loop until the view stops changing.
- Stub the sync services so nothing reaches the AVA, and use the repositories against the real database.
- For keys, read `app.screen.active_bindings` directly — it says what the footer will show and why.
- A refactor is done when the render is byte-identical. A difference you did not intend is a bug in the refactor.

Then:

```bash
pdm run ruff check src/ && pdm run ruff format --check src/
uvx pyright          # strict, configured in pyproject; not installed in the venv
```

**Type checking is not optional.** `pyright` is set to `strict` in `pyproject.toml` but is absent from the venv, so it is easy to write a whole feature without ever running it. Two traps it catches here: a shared `BINDINGS` list must be annotated `list[BindingType]`, not left as `list[Binding]`; and `self.app` is typed `App[Unknown]`, so a page takes its app through its constructor and a component reaches the provider as `self.ancestors_with_self[-1]`, which is a typed `DOMNode`.
