---
name: global-colours
description: Every colour in the TUI comes from a theme variable, markup included, under a semantic mapping (aprovado, exame, reprovado, aviso, erro) instead of ANSI names. Read before writing a colour in markup, in a DEFAULT_CSS or in a test that asserts one.
projects: [frontend]
status: done
created_at: 2026-09-14
---

# Global colours

## TL;DR
- Markup stops using ANSI names and takes its colour from a theme variable, as the stylesheets already do.
- Coloured text uses the `$text-*` family, the only one that inverts with the background.
- The mapping is semantic and decided once here; `media_colour` returns a variable name.
- A test reads the expected colour off the running app instead of freezing a hex.

The stylesheets are disciplined — `$accent`, `$surface`, `$warning`, `$text-muted`, `$border` — while markup hardcodes an ANSI name in 12 places across 8 files. Two colour systems run side by side and only one of them follows the theme. The pages are [0018](../done/0018-pages-and-their-components.md), the média's bands are [0006](../done/0006-deadline-and-media-colour.md), and what the project is lives in [CONTEXT.md](../../CONTEXT.md).

## Observed behaviour

Measured on 2026-09-14 against Textual 8.2.8, painting each token and reading the colour off the rendered segment:

- **ANSI names are frozen.** `[green]` paints `#008000`, `[yellow]` `#ffff00` and `[red]` `#ff0000` — the same values under `textual-dark`, `textual-light`, `nord` and `gruvbox`.
- **Theme variables follow the theme.** `$text-success` is `#8ad4a1` under `textual-dark`, `#337e4a` under `textual-light` and `#c2d4b3` under `nord`.
- **Only the `$text-*` family inverts with the background.** `$success` stays a light `#4ebf71` over `textual-light`'s `#E0E0E0` ground, while `$text-success` darkens to `#337e4a`.
- **Markup accepts `[$variable]`**, the same token the CSS uses. There is no helper to write and nothing to resolve by hand.
- **The app never sets a theme**, so it runs on Textual's default and the stock command palette can change it mid-session.
- The empty state of every page is `[yellow]`, which is pure `#ffff00`.

## Decisions

### Colour comes from a theme variable, never from an ANSI name

An ANSI name is a pigment with no meaning and no theme: it ignores the background it lands on. Every `[green]`, `[yellow]`, `[red]`, `[cyan]` and `[magenta]` in markup becomes the variable that carries what it meant.

### Coloured text uses the `$text-*` family

`$success`, `$warning` and `$error` are block colours, meant to sit behind text. Ours is always text over the app's own background, and only `$text-*` is guaranteed legible there under both a light and a dark theme.

### The mapping is semantic, and named by meaning rather than by pigment

```
[green]    aprovado, chosen answer        →  [$text-success]
[yellow]   exame, empty state, warning    →  [$text-warning]
[red]      reprovado, login failure       →  [$text-error]
[cyan]     sync spinner                   →  [$text-accent]
[magenta]  mock tag                       →  [$text-secondary]
```

A matéria in exame and an empty list share `$text-warning` because both are "look at this, nothing is broken". The spinner joins `Loading`, which already paints itself `$accent` for the same idea.

### `media_colour` returns a variable name

It already returns `"green" | "yellow" | "red"`; it comes to return `"$text-success" | "$text-warning" | "$text-error"`. The bands decided in [0006](../done/0006-deadline-and-media-colour.md) do not move — only the pigment they name.

### A test asserts the colour the theme resolves, not a literal

`GREEN = "#008000"` in a test freezes a value the theme owns, so changing theme would turn the suite red without anything breaking. The test resolves the variable against the running app and compares with that, which asserts the meaning — that the média used *success* — instead of the pigment.

## Rejected

- **A `cli/colours.py` with our own hex constants.** Centralises the twelve call sites, but re-freezes the pigment and duplicates a palette the theme already publishes.
- **The block family (`$success`, `$warning`, `$error`) for text.** One token shorter, and wrong on a light theme: it is built to have text on top of it, not to be the text.
- **Pinning a single theme so the ANSI names stay predictable.** Spends the user's theme choice to protect a workaround.
- **A Textual theme of our own.** Nothing on screen needs a colour the stock themes lack, and it would be a palette to maintain for no gain.

## What execution corrected

- **Twelve sites across seven files, not eight.** `media.py` holds three of them, which the count above read as three files.
- **A variable closes with `[/]`, not `[/$text-success]`.** Fifteen edits landed: the twelve markup sites plus `media_colour`'s three returns.
- **`[bold $text-success]` composes**, so `MediaBar` needed no change beyond the returned token.
- **The variables resolve uppercase and paint lowercase** — `#8AD4A1` against `#8ad4a1`. A test that compares the two has to casefold, which is why `theme_colour` in `test_media.py` lowers.
- **The colour follows a live theme change** with no repaint of our own, verified across `textual-dark`, `textual-light`, `nord` and `gruvbox`. The spec assumed this; it is now a test.
- `$text-accent` is longer than `cyan` and pushed the spinner past the formatter's line limit, so its frame became a local.
- **A theme variable only reaches Textual's own pipeline.** A `Static` resolves `$text-warning` in markup and in a `rich.text.Text` style. A rich renderable does not: inside a `Tree`, a `DataTable` or a `rich.table.Table` in an `OptionList` option, the variable is **silently dropped** and the text paints in the default colour — and in rich *markup* it raises `MarkupError` at render, which crashed the prova screen.
- **So the rule has an exception, and it is the renderable, not the file.** Ten sites keep their ANSI names because they render through rich: four in `tree.py`, four in `table.py`, `ANSWERED_STYLE` in `questoes.py` and the sync spinner in `list.py`. Everything that lands in a `Static` — every empty state, the `MediaBar`, the prova summary, the debug panel's error line — carries the variable.
- `"dim"` stays as it is everywhere. It is a style, not a colour, and the theme has no variable for it.
- Both facts came out of writing a `ProvaPage` test, not from reading the code: the crash needs the screen to actually render.
