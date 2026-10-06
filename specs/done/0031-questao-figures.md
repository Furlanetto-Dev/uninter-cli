---
name: questao-figures
description: Figures inside a questão — kitty pixels where the terminal has the graphics protocol, today's link everywhere else, bytes fetched once through the AVA session and kept in the database. Read before touching html_to_textual, the prova or gabarito body, or the alternativa list.
projects: [all]
status: done
created_at: 2026-09-24
---

# Figures inside a questão

## TL;DR
- `html_to_blocks` gains a `Figure` block: an `<img>` stops being a word in the prose and becomes a block of its own.
- The bytes are fetched once through `AvaSession` and kept in a `figure` table keyed by the `src` URL.
- `main.py` probes the terminal before Textual starts and hands the app one of two presenters: pixels, or the link that exists today.
- Prova and gabarito paint a `Figure` in the body as a widget; the prova's alternativa list paints it as a Rich renderable inside the option.
- Alternativa texts stop going through `html_to_text` and read the same converter chain as the body.

The sketch is [asciifying images](../asciifying-images.sketch.md). Today an `<img>` reaches the screen as the word "imagem" linking to the browser ([0026](0026-html-to-textual.md)), so a questão that leans on a figure is answered outside the terminal or not at all — and the terminal is the whole point of [CONTEXT.md](../../CONTEXT.md). The pages are [0018](0018-pages-and-their-components.md), the gabarito is [0030](0030-gabarito-of-a-prova.md).

## Observed behaviour
- Of 602 stored questões, 42 carry an `<img>` in the enunciado or comando, 48 in a comentário, and 44 alternativas across 11 questões are nothing but a figure. Counted over `uninter.db`.
- Every asset is text rendered as an image — formulas, z-tables, code, lecture slides. Not one photograph among the 126 collected in the sibling `uniter-image-to-ascii-poc` repo.
- Thirteen character-cell renderers were measured there against this content: braille is the best of them and still turns "escreva" into "escruva" on dense type. Only true pixels read cleanly.
- `textual-image` probes the terminal once and cannot do it after Textual owns stdin; importing `textual_image.widget` triggers the probe (`textual_image._terminal.probe_terminal`).
- The AVA serves figures from `repositorio/SistemaRepositorioPublico/?id=…`, the URL already stored in the enunciado. Whether it needs the session cookie was not tested — inference: going through `AvaSession` costs nothing and puts the request in the history either way.
- Whether a kitty placeholder survives an `OptionList` highlight is unverified — inference: a segment's own colour wins over the base style, and the placeholder carries the image id in the foreground colour.

## Decisions

### An `<img>` becomes a `Figure` block
`Block` becomes `Prose | Table | Figure`, with `Figure(source, label)`. An image inside a paragraph closes the prose and opens a block of its own, exactly as a `<table>` does — a figure is never half a line of text.

### Pixels or the link, nothing in between
The terminal either speaks the kitty graphics protocol or it gets the clickable link it gets today. A braille or half-block drawing of a page of 12px type is noise, and noise that looks like content is worse than a link that admits it is one.

### One converter, two presenters
The blocks are built once; who paints them is injected, so the same `Figure` is a widget in the body and a renderable in the option list.

```python
class Figures(Protocol):
    def widget(self, figure: Figure, image: bytes | None) -> Widget: ...
    def option(self, figure: Figure, image: bytes | None, columns: int) -> RenderableType: ...
```

`LinkFigures` ignores the bytes and answers the link both times. `PixelFigures` answers `TGPImage`/the TGP renderable when the bytes are there and the link while they are not. `main.py` builds one of them before `app.run_async()` and passes it down; `PixelFigures` imports `textual_image` on construction, so nothing probes a terminal the app was never going to draw on.

### The bytes are a week-long cache in the database
`api/figures` keeps `Figure(url, data, fetched_at)` in its own table, `crawler/figures` fetches it through a new `AvaSession.get_bytes`, and a row older than seven days reads as absent and is deleted — on sight, and in one sweep when the app starts. Opening a prova prefetches every questão's figures in the background, four requests at a time, the questão on screen first; a reset wipes what is left with the rest of the database.

### A figure is drawn at its natural size, bounded by the pane
Natural pixel size where it fits, scaled down to the pane width or 24 rows, whichever binds first, aspect kept. A 1181×1364 lecture slide is unreadable at any width a terminal offers; it is still better seen small than not at all, and the link under it opens the original.

### The alternativas read the same chain as the body
`alternativa.texto` stops going through `html_to_text`, which escapes the markup and drops the tag. In the gabarito the alternativas become blocks in the body, so a figure alternativa is a widget under its letter; in the prova they stay an `OptionList`, so the option prompt becomes a Rich renderable — the mark and letter, then the figure. If the highlight style turns out to eat the placeholder, that alternativa keeps the link and the body keeps the pixels.

### The fake AVA answers bytes
`FakeAva` only knows how to answer JSON ([0028](0028-fake-ava.md)). It gains a bytes branch and the mocked questão's figure is a PNG committed under `api/mock`, so dev mode draws a real image with no AVA behind it.

### What a test can prove
That pixels reached the screen is not provable headless, and no test will try. The tests drive a page with a recording `Figures` and a `FigureSource` that answers bytes, and assert which shape each block asked for and with which bytes; a second pass with `LinkFigures` asserts the link still reads "imagem" and still opens the URL.

## What execution corrected

- **A `Figures` facade carries the painter.** A page would otherwise hold both the painter and the `FigureSource`; it now takes one collaborator — `load(blocks)` before painting, `widget(figure)` and `option(figure, columns)` after — which is also the single double a test injects.
- **`Painter.option` answers `None` when there is nothing to draw**, and the alternativa stays a Textual markup line. A Rich renderable inside an `OptionList` loses the theme variables and the clickable link, so it is used only when there really are pixels.
- **Only the prova answers through an `OptionList`.** The gabarito already lists its alternativas as blocks in the body, so there a figure alternativa is a widget like any other; consecutive text alternativas are merged back into one block so the spacing does not move.
- **`figure_box` sizes the drawing, not textual-image's `auto`**, which always fills the container and would blow a 253×28 formula up to the width of the pane.
- **The request history stops storing bodies it cannot read.** An image used to reach the debug panel as kilobytes of replacement characters; it now reads `<image/png, 8396 bytes>`.
- **The sidebar rows read the blocks too**, instead of putting raw `<img …>` in the prova's answer line and nothing at all in the gabarito's. The mock figures under `api/mock` are drawn locally, so no AVA course material is committed.
- **The download happens after the paint, never before it.** Awaiting the AVA before showing a questão made walking a prova crawl; the page now paints what is stored and a worker fetches the rest, repainting only if something arrived and the student is still on that questão. A terminal that only links downloads nothing at all.
- **A drawing is transmitted once.** The body figure is a cached renderable inside a `Static`, not a fresh `TGPImage` per repaint, so navigating back and forth does not push the same image through the terminal again.
- **Under tmux the probe is useless.** tmux answers the graphics-protocol query itself and never hands the reply to the pane, so the app asks tmux instead: `allow-passthrough` on and a kitty client is what decides.
- **The page stylesheet reached inside the figure.** `#gabarito-blocks Static` matched the image and its caption, spending four blank rows on every figure; the rule is now a direct-child selector. A prose block also stopped starting on a blank line — a figure cuts a paragraph in two and the second half kept the paragraph's opening blank.
- **The drawing is the link.** A caption line under every figure was a row of clutter next to a visible image, so the figure widget itself opens the original on a double click; the text link stays only where nothing is drawn.
- **Downloading is a page-wide prefetch, not a per-questão errand.** Entering a prova walks every questão in the background from the one on screen outwards, fetching four figures at a time; a stale `fetched_at` is what expires them. `AvaSession.log_in` grew a lock so the first concurrent batch cannot log in four times.
- **Verified in kitty**, after those four corrections: the figures draw inside tmux, and the boxes leave at most 0.4 of a row unused against the real assets.

## Rejected
- **Braille or quadrants as the fallback.** Measured in the POC as the best that works everywhere, and still misreads the type this content is made of.
- **`term-image`.** Pins `pillow<11`, dragging the whole project back a major version for a widget `textual-image` already provides.
- **A cache directory for the bytes.** A second place to keep state, a second thing for reset to remember.
- **OCR as a reading mode.** The most legible option in the POC and the least faithful: a stacked fraction comes back as three lines. It belongs to its own spec, if ever.
- **Fetching every figure at sync time.** Hundreds of requests for the handful of questões anyone opens.
