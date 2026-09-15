---
name: novo-teste
description: "How a test is written in this repo: test the outcome and never the implementation, where the file goes, driving a page with Pilot, reading what a widget actually paints, and what never to assert. Use when adding a test for a page, a component or a pure function, or when a test is asserting the wrong thing."
---

You are writing a test for the TUI. The pages are [0018](../../../specs/done/0018-pages-and-their-components.md), how a page is built is the `nova-pagina` skill, and colour comes from [0025](../../../specs/pending/0025-global-colours.md). The eight-layer plan in [0002](../../../specs/rejected/0002-testing-strategy.md) was rejected — do not build from it.

# Test the outcome, never the implementation

**Assert what the student would see or get, not how the code arrived at it.** A test that knows the internals passes when the behaviour is broken and fails when a rewrite changes nothing — it costs maintenance and buys no confidence.

The question to ask of every assertion: *would this still be true if the module were rewritten from scratch against the same requirement?* If not, it is testing the implementation.

Every other rule here is this one applied:

| implementation | outcome |
| --- | --- |
| walking `visual.spans` for the markup the widget built | the colour `render_line` actually paints |
| a hex literal the component happened to emit | the theme variable resolved off the running app |
| calling `action_focus_previous()` | `pilot.press("left")` |
| reading `_syncing` to see if a sync started | the spinner on the row, or the service's call list |
| asserting `dismiss` was called | `app.answer is False` |

Two things that look like exceptions and are not. Pure functions have no separable implementation — their return value *is* the outcome. And a constant read back from the module under test (`assert page.TITLE in text`) asserts nothing: spell the expected text out, or assert the behaviour that text drives.

# Only `cli/` is tested

`api/` and `crawler/` get no tests. A test here drives the interface — a page, a component, or a pure function `cli/` calls — and stops at that boundary. An entity or a repository is exercised through the screen that shows it, or not at all.

So `Media.from_atividades` is not tested directly; `MediaBar` showing `média 72,5` is, and that covers the arithmetic that reaches the student.

# Where the file goes

`tests/cli/` mirrors `src/cli/`, so the test file is obvious from the code file:

```
src/cli/format.py                          tests/cli/test_format.py
src/cli/pages/materias/components/media.py tests/cli/pages/materias/components/test_media.py
src/cli/pages/inicio/page.py               tests/cli/pages/inicio/test_confirm_start.py
```

- **Basenames must be unique across the whole tree.** There are no `__init__.py` files, so a second `test_page.py` collides at collection. The directory already carries the page name, so name the file after what is under test: `test_confirm_start.py`.
- `pdm run test` runs everything. `pythonpath = ["src"]` and `asyncio_mode = "auto"` are in `pyproject.toml`: an `async def test_` needs no decorator and no fixture.
- `pytest` and `pytest-asyncio`, nothing else. `httpx` already ships `MockTransport` for when the crawler gets tested.

# The three kinds

**A pure function** takes no app at all — `cli/format.py` is the whole of it. Use `parametrize`, one row per case, and put the boundary in the table: `(70.0, APPROVED)` and `(69.0, EXAM)` next to each other say more than either alone.

**A component** mounts inside a throwaway host:

```python
class MediaHost(App[None]):
    def compose(self) -> ComposeResult:
        yield MediaBar()
```

**A page** gets pushed onto a host that records what it answers:

```python
class ConfirmHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.answer: bool | None = None

    def record(self, answer: bool | None) -> None:
        self.answer = answer
```

# Driving it

```python
app = ConfirmHost()
async with app.run_test(size=(100, 30)) as pilot:
    app.push_screen(ConfirmStart(atividade(), MATERIA), app.record)
    await pilot.pause()
    await pilot.press("left")
    await pilot.pause()
    assert app.answer is False
```

- **`await pilot.pause()` after every press**, and after `push_screen`. Without it the dismiss callback has not run and the assertion reads the previous state.
- **Pin `size=`.** The terminal size goes into the layout, and without it the test depends on who ran it.
- **A fresh `App` per test.** `run_test()` cannot be reused on one instance — build the app inside the test, never at module level or in a shared fixture.
- Keys are behaviour: prefer `pilot.press("left")` over calling `action_focus_previous()`. The key is what the student has.

# Reading what the screen paints

`render_line(y)` gives the painted `Strip`: `.text` for the characters, and each segment's `.style.color.name` for the colour.

```python
def painted_colour(bar: MediaBar) -> str:
    label, *_ = bar.render_line(0)
    return label.style.color.name
```

- **Never walk `widget.visual.spans`** looking for the text you expect. That reconstructs how the widget assembled its markup, so the test breaks on a rewrite that changes nothing on screen. Take the segment by position.
- **Never assert a colour as a hex literal.** The pigment belongs to the theme ([0025](../../../specs/pending/0025-global-colours.md)). Resolve the variable off the running app and compare with that, so the assertion says *success* rather than *#8ad4a1*:

```python
def theme_colour(app: App[None], variable: str) -> str:
    return app.get_css_variables()[variable].lower()
```

  The variables resolve uppercase and paint lowercase, hence the `.lower()`.
- For keys, read `app.screen.active_bindings` — it is what the footer will show.
- `Static` has no `.renderable` in Textual 8.x. `render_line` is the way in.

# What not to assert

- **Layout.** No positions, no borders, no whole-screen snapshot. `nova-pagina` compares `_compositor.render_strips()` to prove a refactor moved nothing; that is a throwaway harness, not something to commit.
- **Exact toast and binding text** that changes without consequence — except `escape`, which means `voltar` everywhere and is worth pinning.
- **Private attributes.** If the test needs one, the widget is missing a method.
- Anything the type checker already proves.

# Factories

A factory for an entity lives in the test file that needs it, with keyword defaults and one override per case:

```python
def atividade(*, tempo_total: int | None = 60, ...) -> Atividade:
```

It moves to `tests/factories.py` on its **second** calling file, not when it looks reusable — the same rule components follow in `nova-pagina`. `tests/` is on the path, so the import is `from factories import make_atividade`.

# Before finishing

```bash
pdm run test
uvx ruff check src tests && uvx ruff format --check src tests
uvx pyright          # strict, covers tests/ too; not installed in the venv
```

`tests/` is inside pyright's `include` on purpose: a fake that drifted from the real interface is a test that lies, and with everything async a missing `await` is the error that passes silently at runtime.

An assertion that cannot fail is not a test. If you are unsure a new case discriminates, check that it distinguishes the value it names from its neighbour — that is what the boundary rows in a `parametrize` table are for.
