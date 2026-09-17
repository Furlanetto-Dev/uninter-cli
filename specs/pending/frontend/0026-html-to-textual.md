---
name: html-to-textual
description: The questão renderer leaves pages/prova/components and becomes cli/lib/html_to_textual, parsing with BeautifulSoup instead of a hand-driven event stream and painting through a chain of one link per tag, with its public surface and its output unchanged. Read before importing the HTML renderer, teaching it a tag, or looking for html_to_text in cli/format.py.
projects: [frontend]
status: awaiting-review
created_at: 2026-09-17
---

# HTML to Textual, a library of its own

## TL;DR
- `pages/prova/components/html.py` becomes `cli/lib/html_to_textual`, a package no page owns.
- Parsing moves from a hand-driven `HTMLParser` to a `BeautifulSoup` tree; `beautifulsoup4` joins the runtime dependencies.
- Painting is a chain of responsibility over nodes: one link per tag, each recursing into its own children.
- bs4 is narrowed to our `Element`/`Text` once, at the edge, so no converter imports it and the package type-checks strict.
- `html_to_markup` and `html_to_text` keep their names and their output byte for byte; the inherited tests prove it.

The only reader of AVA markup in this repo is a private file under one page, and three queued
pieces of work lean on it. Move it out, and let a parser own the tree instead of rebuilding
it by hand. See [CONTEXT.md](../../../CONTEXT.md) and
[0018](../../done/0018-pages-and-their-components.md).

## Observed behaviour
- bs4 4.15 ships `py.typed` and the types are real, not `Any`: `find` gives `Tag | None`, `find_all("tr")` gives `ResultSet[Tag]`, `get_text()` gives `str`, `children` gives `Iterator[PageElement]`. A snippet doing the walk and the table query checks clean under pyright strict — verified.
- A tree parser does not normalise the AVA's malformed HTML. Questão 8 of the mocked prova closes a `<p>` and leaves two lines of bare text at top level, and the `html.parser`, `html5lib` and `lxml` backends all keep them exactly where they sit — verified by parsing it with the three.
- Reading the funcionário table of [0023](../../done/0023-dev-mode.md) off a tree takes three lines, against the 57-line accumulator and the 16-line cell guard it replaces — measured on the real payload.
- `html_to_markup` has one caller, `pages/prova/page.py`; `html_to_text` has two, `pages/prova/components/questoes.py` and `pages/inicio/page.py` — from a grep over `src/`.

## Decisions

### BeautifulSoup owns the structure, this package owns the painting
On the stdlib `html.parser` backend: pure Python, nothing to compile, and the backend is one
argument, so `lxml` can replace it later without touching our code.

### The package is split by concern

```
src/cli/lib/html_to_textual/
    __init__.py       html_to_markup, html_to_text
    nodes.py          Element and Text — a bs4 node narrowed once
    lines.py          the markup line buffer: bold, escaping, blank lines, list markers
    render.py         the walk down the tree, and html_to_markup
    text.py           html_to_text, every tag stripped
    converters/
        __init__.py   CHAIN, the converters in precedence order
        converter.py  the Converter protocol and the Walk type
        breaks.py     br
        bold.py       strong, b
        paragraphs.py p
        lists.py      ul, ol, li
        tables.py     table, and reading a <table> element into rows
        cells.py      tr, td, th reached outside a table
```

`cli/lib/` is new and is for code no single page owns. Every converter is a peer under
`converters/`, so the one that reads a `<table>` is not a special case, and each `__init__.py`
is a surface: the outer one exports the two functions, the inner one the ordered chain.

### bs4 is narrowed once, at the edge
`children` yields `PageElement`, which every link would otherwise have to re-narrow.
`nodes.py` turns each bs4 node into `Element(tag, children)` or `Text(str)` once, so the chain
is typed against our own two types, nothing under `converters/` imports bs4, and swapping the
parser stays one module's problem.

### Painting is a chain over nodes, not events
Each converter claims a tag by name and recurses into the children it wants, so the link that
swallowed events inside a cell disappears: a cell's contents are simply its subtree. A node
nothing claims falls off the end, which is how unknown tags keep being ignored.

### The output does not change, and the tests prove it
Both functions keep their names and their exact output, and the tests move with their bodies
untouched. A depth-first walk visits nodes in document order, which is the order the event
stream delivered them, so the same line buffer fed the same way yields the same string.

## Rejected
- **lxml or selectolax.** Faster, and a compiled dependency for parsing ten questões; bs4's backend is swappable if that ever matters.
- **Keeping the hand-driven `HTMLParser`.** It spends three pieces of mutable state rebuilding nesting the parser already knows.
- **Letting bs4 types reach the converters.** Narrowing `PageElement` in every link spreads the dependency across the package, and makes the chain harder to test than two dataclasses would be.
- **Reimplementing `html_to_text` on the tree.** It strips tags, it does not read structure; `get_text()` would change what `<br>` does, for no gain.
- **Changing the output in the same step as the parser.** Nothing would prove the switch, because every expected string would have had to be rewritten to match. What gets painted changes in [0026.1](0026.1-tables-as-tables.md).

## What execution corrected
- **Byte-identity holds everywhere but one case.** All 20 real fields of the mocked prova and every edge case matched, except an unclosed `<b>`: bs4 closes it at the end of the document, so the markup comes out balanced where the old parser left `[bold]` dangling. The tree keeps no record of a close that was never written, so identity is unreachable there — and balanced markup is the better of the two.
- **bs4 collapses into `NavigableString` what `HTMLParser` split across callbacks.** A comment was dropped before, because `handle_comment` was never overridden, while `<script>` and `<style>` contents *were* painted, because they arrived through `handle_data`. Both are `NavigableString` subclasses to bs4, so `nodes.py` excludes `Comment`, `Declaration`, `ProcessingInstruction` and `CData` by name and keeps the rest.
- **A `StrayCell` link had to be added.** The old parser swallowed a `<td>` sitting outside any `<table>`. With the table link consuming its own subtree, a stray cell would otherwise fall off the end of the chain and have its text painted. The oddity is kept on purpose, so the diff stays clean.
- **`column_widths` and the row renderer were dropped.** They padded cells into aligned text, which is what a `Table` block replaced in [0026.1](0026.1-tables-as-tables.md); nothing called them once the page mounted widgets.
- **The list-marker stack stayed in `Lines`.** The plan called for it to become the recursion's depth argument, but an ordered list also needs a running counter per level, and an `int` cannot carry one.
