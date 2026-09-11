---
name: atividade-start-confirmation
description: ⏎ on an atividade opens ConfirmStart, a modal copying the AVA's "Orientações para realização da avaliação" page from three new Atividade columns (periodo, orientacao, tempo_total) and answered by two buttons with SIM focused; SIM closes with a toast because no start call is captured; only Aguardando início opens it and a presencial one gets a toast; the tree gains a Tentativa column. Read before making an atividade startable, adding a field to Atividade, or binding ⏎ on the tree.
projects: [crawler, api, frontend]
status: done
created_at: 2026-09-09
---

# Confirming the start of an atividade

## TL;DR
- `Atividade` gains `periodo`, `orientacao` and `tempo_total`, from `avaliacao`; the start-up reset of [0013](../done/0013-materia-groups.md) adds the columns.
- `⏎` on a leaf of the atividades tree opens `ConfirmStart`, a modal with the AVA's page text built from the stored fields, answered by two plain buttons, NÃO then SIM, with SIM focused on opening; `esc` is still NÃO.
- SIM is inert: no start call is captured, so it closes with a toast saying so. Only `Aguardando início` opens the modal; a presencial one gets a toast instead.
- The tree gains a `Tentativa` column, `1/3`.

First step of completable atividades: the page the AVA shows before a prova, without the call behind its green button. Context in [CONTEXT.md](../../CONTEXT.md); the tree in [0012](../done/0012-grouped-atividades.md), the presencial flag in [0013.1](../done/0013.1-avaliacao-presencial.md), the no-capture rule in [0001](../done/0001-ava-atividades-crawler.md).

## Observed behaviour
- The page's text lives in `avaliacao`: `nomeAvaliacaoTipo`, `nome`, `periodo`, `orientacao` (HTML with `<br>` and `<span>`), `tempoTotal` in minutes, `avaliacaoPresencial`. Counted over the 151 items in the stored capturas: `tempoTotal` is 0 on all 42 APOLs and 10 práticas, 30 to 120 on provas.
- `uninter-endpoints/atividades/confirmar-inicio-atividade.html.txt` is the page's template GET; its own note says it adds nothing to the list. No call for SIM is captured.
- Textual 8.2.8 `Tree` binds `enter` to `select_cursor`, which toggles an expandable node and posts `NodeSelected`; the tree stops that message today. Checked in `BINDINGS` and the source.
- `Atividade` already carries `tipo`, `presencial`, `tentativa` and `tentativa_total`.

## Decisions

### Three more columns on `Atividade`, read from `avaliacao`
`periodo: str | None`, `orientacao: str | None` kept as the AVA's HTML like the etiqueta of [0005](../done/0005-trabalhos.md), `tempo_total: int | None` in minutes. `ProvaDTO` gets the aliases and `to_atividade` carries them. An existing database resets itself at start-up, as 0013 decided.

### `⏎` on a leaf posts `Start`; groups keep toggling
`AtividadeTree.on_tree_node_selected` posts `Start(atividade)` when the node has data and stays silent for a group, whose `select_cursor` already toggled it. The App decides what to do.

### The modal copies the AVA page
`ConfirmStart(ModalScreen[bool])` in `cli/atividades/start.py`, styled like `ConfirmReset`: title "Orientações para realização da avaliação.", then "{tipo} - {nome} ({periodo}):", " - {matéria}", "Dicas da coordenação:" with `orientacao` through `html_to_text` — `<br>` to newline, tags dropped, entities unescaped — or "—", "Tempo máximo: N minutos" or "ilimitado (enquanto a avaliação estiver vigente)" when 0 or absent, "Tentativa N de M" and "Deseja iniciar a prova agora?", answered by a row of two buttons, "Não" then "Sim", each a label inside a round border and no wider than its word. Neither carries a variant colour and neither inverts: the selected one is the one whose border is `$foreground`, against `$foreground 15%` on the other. `AUTO_FOCUS` puts the selection on SIM, `←`/`→` and tab move it, `⏎` presses the selected one and `esc` dismisses False from anywhere.

### SIM closes with a toast, until the call is captured
Nothing is searched for: the rule since 0001. The App answers True with "Iniciar ainda não está disponível: a chamada do AVA não foi capturada." The next spec replaces the toast with the request once the curl exists.

### Only `Aguardando início` opens it; presencial gets a toast
`Atividade.aguardando_inicio` reads the AVA's status string. Any other status makes `⏎` do nothing — the row already says why. A presencial atividade awaiting start shows "Avaliação presencial: ainda não dá para iniciar pelo app." and no modal, since its rules are not captured.

### A `Tentativa` column after Situação
`{tentativa}/{tentativa_total}`, right-aligned in 9 columns under the header "Tentativa". The name column yields the width, down to its minimum, as [0012](../done/0012-grouped-atividades.md) already lets it.

## Rejected
- **A line of key hints in place of the buttons.** What the first implementation had; it made the two answers equal text and left no visible default, and the reset confirmation's hints work only because there is one destructive answer.
- **Textual's default buttons, green SIM on the left.** Three rows tall and 16 columns wide each, they took over a modal that is mostly text; the colour also read as a recommendation on the answer that starts a prova.
- **Textual's own focus style, `b reverse`, as the selection mark.** A filled block of foreground on the chosen word, next to a modal that is text on `$surface`; the border carries the same information without touching the text.
- **Reading the page's fields from the `Captura` JSON when the modal opens.** No schema change, but the entity would not know what the screen shows; 0013 made a column cheap.
- **A full page in place of the detail panel, like the AVA.** A modal keeps the matéria and the tree in sight and matches the reset confirmation.
- **A toast for `Finalizada` and the rest.** The status column already says it.
- **The attempt inside Situação.** Widens the status column by its longest text and buries the number in prose.
- **Calling the start endpoint by guessing its shape.** Not captured, not called.

## What execution corrected
- No decision above needed changing; `pyright` strict, `ruff` and a headless `run_test` pass matched the spec on the first implementation.
- `to_atividade` was checked against a real captured APOL body, not only synthetic fixtures: `periodo`, `orientacao` and `tempo_total` decode as expected, and `aguardando_inicio` reads true for it.
- Verified headless, one App per scenario: the modal's text against all six pieces (title, tipo/nome/período, matéria, orientação turned to plain text, "ilimitado", "Tentativa N de M"); `esc` dismissing with no toast; `⏎` then `⏎` closing with the not-captured toast; a presencial atividade producing its own toast and no modal; a `Finalizada` atividade producing neither; `⏎` on a group node toggling it instead of posting `Start`.
- The answers became buttons after the first implementation, on seeing the modal: the key-hint line left no visible default. Their shape came from the same screen — word-wide, uncoloured and NÃO first, since the full-size coloured pair dominated the text it answers, and marked by the border because inverting the text was louder than the modal. Verified headless that SIM opens selected and `⏎` dismisses True, `esc` dismisses False, `→` or tab moves to NÃO and `⏎` there dismisses False, `←` comes back, and the border colour is the only difference between the two — the labels render identically.
