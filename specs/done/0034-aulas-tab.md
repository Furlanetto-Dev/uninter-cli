---
name: aulas-tab
description: The "3 Aulas" tab — a tree of aula → atividade → material fetched from the Roteiro de Estudo requests, rotas and videos opened in the browser, arquivos downloaded on demand into UNINTER_AULAS_DIR; read-only, material complementar left for a later capture. Read before touching the aulas requests, the Aula/AulaAtividade/Material tables, the third tab or where downloaded files land.
projects: [crawler, api, frontend]
status: done
created_at: 2026-10-12
---

# The aulas tab

## TL;DR
- The "3 Aulas" tab, promised by [0011](0011-tabbed-detail-panel.md), becomes a tree mirroring the AVA's Roteiro de Estudo: aula → atividade → material.
- One sync fetches the aula list, each aula's atividades and each atividade's materiais, and stores them in `Aula`, `AulaAtividade` and `Material`.
- Enter on a rota or a video opens its link in the browser; enter on an arquivo downloads it into `UNINTER_AULAS_DIR` once and opens the local file.
- Read-only: nothing tells the AVA a material was opened, and there is no progress.

The [sketch](../aulas.sketch.md) asked for the aulas of a matéria on screen and their files on disk, so a class can be followed without the AVA ([CONTEXT.md](../../CONTEXT.md)).

## Observed behaviour
- The aula list is `SalaVirtualEstrutura/0/TipoOfertaCriptografado/1`, whose `id` is the matéria's `cId` from the matérias listing, already URL-encoded; the other two params are the ofertas. Proof: `uninter-endpoints/aulas/list-aulas.txt` against the live listing, POO `hZgseu1RVEZ0FSL4Mb1R2w%3D%3D`.
- An aula's atividades come from `salaVirtualAtividade/0/EstruturaOferta/{oferta_atual}/?id={aula}` with no materiais inside; each atividade's materiais come from `atv/AtividadeItemAprendizagem/{idAtividade}/Atividade`. Proof: the two captures, Aula 6 of POO.
- A material's kind is `classificacaoTipo`: `rota` and `video` carry their URL in the etiqueta whose `nomeTipoRecurso` is `link`, `arquivo` carries a `sistemaRepositorio` with `nome` and an encrypted `url`.
- The arquivo's `urlRecurso` points at an internal AWS host; `https://univirtus.uninter.com/ava/repositorio/SistemaRepositorioPublico?id=<sistemaRepositorio.url, percent-encoded>` serves the same file without any session, through a 301 to the CDN. Proof: `poo.pdf` downloaded with no cookie.
- Only Aula 6's atividades were seen (rota, videoaula, leitura); the captured session expired before the other aulas could be read. Other kinds are inference.
- The Roteiro's "Material complementar" block is estrutura `179134`, an id present in no response we hold, the 59 stored capturas included.

## Decisions

### The aulas follow the trabalhos' sync, but never in the background
`AulaSyncService` mirrors `TrabalhoSyncService`: fetch everything, replace the matéria's rows, store the list's captura, stamp `Materia.aulas_sincronizadas_em`. Unlike atividades and trabalhos, aulas stay out of `enqueue_pending` and the list's pending mark: a sync is about 30 requests per matéria, so it runs only when the tab opens on a never-synced matéria and on `r`.

### `Materia` keeps the `cId`
The aula list is addressed by it and nothing else carries it. The oferta pair follows the trabalhos rule: `oferta_atual`, then `oferta_aproveitamento or oferta_atual`.

### The tree mirrors the Roteiro, always expanded
Aulas show as "Aula 6 · Tratamento de Exceções", always expanded: nothing in the tab collapses, so every material is one cursor walk away; atividades as their name and kind; materiais as their action and, for arquivos, the file name, marked when already on disk. An empty aula list and a never-synced matéria get the tab's `Hint`, as the other panes do.

### Arquivos download on demand, under one directory
`UNINTER_AULAS_DIR` (default `~/Uninter`) holds `<matéria>/<aula>/<file>`. An arquivo on disk opens with no request; one missing is fetched through a plain client that follows the redirect, outside `AvaSession`, since the URL needs no session.

### Rotas and videos stay links
They open in the browser through `open_url`; a video is a large `.mp4` stream, not a file to keep.

## Rejected
- **Material complementar now.** Its estrutura id comes from a request not captured yet; it becomes a follow-up once `179134` is found in DevTools.
- **Registering access in the AVA.** No request for it has been captured and the frequência data was not found either.
- **Bulk download at sync.** Slower syncs and files nobody opens; the user chose on demand.
- **Aulas in the background queue.** Around a thousand requests across every matéria for a tab not always open.

## What execution corrected
- **The repositorio id is percent-encoded.** It carries `+` and `/`, which a query string would read as a space and a separator; the encoded form was checked to redirect to the same file.
- **Trabalhos and aulas share the fetch on opening a tab.** `fetch_missing_trabalhos` became `fetch_missing(materia, collection)`, and the loading state covers both panes.
- **An atividade without a name shows its kind.** The Roteiro sends `nomeAtividade: null` for some, as the Cronograma Semanal of the complementares does.
- **`UNINTER_AULAS_DIR` expands `~`**, since pydantic keeps a `Path` literal.
- **The mocked matéria has two aulas** with a rota, a video and an arquivo the fake AVA serves, so dev mode exercises the whole tab.
