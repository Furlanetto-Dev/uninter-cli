---
name: trabalhos
description: A matéria's trabalhos and their corrections — the etapa → entrega → etiqueta chain, the three tables, the cascading sync and which "detalhes" of the AVA screen are reachable. Read before touching anything under crawler/trabalhos or api/trabalhos.
projects: [crawler, api]
status: done
created_at: 2026-09-02
---

# Trabalhos

A matéria has atividades and trabalhos. The atividades are already mirrored; the trabalhos are not, and they are where the student's hands-on entrega lives — protocol number, attachments, grade and the grader's comment. This spec covers **crawler and api only**: no interface, and no change to the TUI of [0004](../done/0004-textual-tui.md). What the project is lives in [CONTEXT.md](../../CONTEXT.md), the design decisions in [0001](../done/0001-ava-atividades-crawler.md), the layers in [0003](../done/0003-crawler-api-cli-layers.md) and the tests in [0002](../rejected/0002-testing-strategy.md).

## Observed behaviour

Checked against the real API on 2026-09-02, with a fresh login and the whole account swept. Where it is inference, it says so.

- **The chain is self-sufficient.** Every id the next step needs comes from the previous response: `trabalhoEtapas[].id` and `trabalhoEtapas[].idTrabalhoVinculadoEtapa` build the entrega URL; `trabalhoEntregas[].idTrabalhoCorrecao` builds the etiquetas URL. Nothing needs guessing or configuring.
- **The listing wants both ofertas, in different positions**: `oferta_atual` in the path, `oferta_aproveitamento` in the query. It is the opposite of the atividades endpoint, which only takes the resolved one — which is why `Materia.oferta` is no use here.
- **When there is no aproveitamento oferta, passing the current one in both positions works.** Checked on the two matérias in the account where it is null; both returned trabalhos.
- **404 means "matéria with no trabalho"**, and that is the case for 13 of the 26 matérias. Same ambiguity as [0001](../done/0001-ava-atividades-crawler.md): a real error and absence arrive the same.
- **The range is small.** 19 etapas in the whole account: most matérias have 1, one has 2 and two have 4. Eight have an entrega made. The 26 matérias were swept in 1,6s.
- **`totalRegistros` lies.** It comes back 0 in the etapas listing and in the etiquetas, even with records in the response. It is no use for detecting empty.
- **The etiqueta does not know whose it is.** `trabalhoCorrecaoEtiquetas[].idTrabalhoEntrega` comes back 0. Only whoever made the request knows which correction the result belongs to.
- **`aprovadoEtapa` is tri-state.** It comes back `true`/`false` on the 8 graded trabalhos and `null` on the 11 that were not. Pydantic's `default=` does not cover this: it only applies when the key is missing, not when the value is null. Sweeping all 19, `dataInicio`, `dataFim`, `dataEntrega`, `notaEtapa` and `mensagemErro` also accept null; no entrega or etiqueta field came back null in the 8 samples.
- **The etiqueta text is HTML.** The tutor's feedback comes with `<br />` and entities like `&gt;`, sometimes thousands of characters long. We store it raw; converting is a problem for whoever displays it.
- **The correction is not a resource of its own.** Its summary — grader, grader's RU, date, file count — comes embedded in the entrega. Only the etiquetas have an endpoint.
- **The AVA itself treats the two as separate things.** The sala virtual's side menu lists "Atividades" and "Trabalhos" as sibling sections, each with its own screen.
- **The trabalho's grade does not appear among the atividades.** In Engenharia de Software the trabalho has grade 100, and none of the matéria's 7 atividades corresponds to it; the atividades' weights add up to 70%. The entrega carries `idAvaliacaoUsuario`, but the id matches no atividade returned for the matéria.

## Decisions

### Trabalho hangs off the matéria, next to atividade

The listing URL only asks for the matéria's ofertas, and the trabalho's grade has no counterpart in the atividades list. They are two sibling collections, and syncing trabalhos does not depend on any atividade being in the database.

### `idAvaliacaoUsuario` does not become a foreign key

The field exists on the entrega and is tempting, but the id resolves to no atividade the API returns for that matéria. Persisting it as an FK would create a dangling reference. It stays out until someone shows where it points.

### Three tables, mirroring the three endpoints

`trabalho` for the etapa, `trabalho_entrega` for the entrega with the correction summary flattened into it — because that is how the AVA delivers it —, and `trabalho_etiqueta` for the items of the correction form. The etiqueta is keyed by the `correcao_id` that originated the request, since the response does not carry it.

Following [0001](../done/0001-ava-atividades-crawler.md), we store only what the screen uses: 14 of the etapa's 33 fields, 13 of the entrega's 48, 3 of the etiqueta's.

### The sync walks the whole cascade, per matéria

One method, one timestamp, one transaction. Syncing a matéria costs 2 to 3 requests and under 200ms — the argument that justified on-demand for the atividades (27 matérias at half a second each) does not apply to a range of 1 to 4 trabalhos. In exchange, there is never a half-synced trabalho in the database.

### The timestamp is its own

`materia.trabalhos_sincronizados_em`, separate from the atividades timestamp. The two collections come from different endpoints, with different costs, and one can be fresh while the other is stale.

### Attachments and answer key stay out

The entrega says **how many** files exist (`totalArquivosEntrega`, `totalArquivosCorrecao`), but listing them takes an endpoint that was not captured. The same goes for the answer key. By the project's rule nobody goes hunting for endpoints: both are recorded as pending capture.

## The screen's "detalhes", and where each one comes from

| detail | source | reachable |
|---|---|---|
| Etapa details | `trabalhoEtapas[]` — name, `dataInicio`, `dataFim`, `nomePeriodo`, `nomeTrabalhoTipo`, `ordemTrabalho` | yes |
| Entrega details | `trabalhoEntregas[]` — `protocolo`, `dataCriacao`, `nomeTrabalhoStatus`, `tentativa`, `finalizadoTrabalhoStatus` | yes |
| Correction block | `trabalhoEntregas[]` — `nomeUsuarioCorretor`, `RUUsuarioCorretor`, `dataCriacaoCorrecao` | yes |
| Correction details | `trabalhoCorrecaoEtiquetas[]` — `constante`, `texto` | yes |
| Attachments | only the `totalArquivosEntrega` counter | **pending capture** |
| Answer key | — | **pending capture** |
| Edit | write operation, flagged by `podeEditar` | out of scope |

## The tables

```
trabalho                          de trabalhoEtapas[]
  materia_id     FK materia.id
  id             PK  (= trabalhoEtapas[].id)
  vinculado_etapa    idTrabalhoVinculadoEtapa, monta a URL da entrega
  nome, tipo         nome, nomeTrabalhoTipo
  ordem, periodo     ordemTrabalho, nomePeriodo
  inicio, fim        dataInicio, dataFim
  entregue_em        dataEntrega
  nota, aprovado     notaEtapa, aprovadoEtapa
  pode_entregar      podeEntregar
  mensagem           mensagemErro

trabalho_entrega                  de trabalhoEntregas[]
  trabalho_id    FK trabalho.id
  id             PK
  tentativa, protocolo, criado_em
  status, finalizado    nomeTrabalhoStatus, finalizadoTrabalhoStatus
  nota                  notaEtapa
  correcao_id           idTrabalhoCorrecao
  corretor, corrigido_em  nomeUsuarioCorretor, dataCriacaoCorrecao
  anexos_entrega, anexos_correcao

trabalho_etiqueta                 de trabalhoCorrecaoEtiquetas[]
  correcao_id    FK trabalho_entrega.correcao_id
  id             PK
  constante, texto
```

## The tasks

Each one is small and verifiable on its own. The order respects the dependencies.

**Preparation**

1. Replace the live session cookie in the three curls under `uninter-endpoints/trabalhos/` with placeholders, as in the others.

**Crawler layer**

2. `crawler/trabalhos/dto.py`: `TrabalhoEtapaDTO` and `TrabalhoEtapasDTO`, with `to_trabalho(materia_id)`.
3. `crawler/trabalhos/request.py`: `TrabalhoRequest.fetch(materia)`, building the path with `oferta_atual` and the query with `oferta_aproveitamento or oferta_atual`, 404 → empty list.
4. `EntregaDTO` and `EntregasDTO`, with `to_entrega(trabalho_id)`.
5. `EntregaRequest.fetch(trabalho)`, using `trabalho.id` and `trabalho.vinculado_etapa`.
6. `EtiquetaDTO` and `EtiquetasDTO`, with `to_etiqueta(correcao_id)`.
7. `EtiquetaRequest.fetch(correcao_id)`.

**API layer**

8. `api/trabalhos/entity.py`: `Trabalho`.
9. `api/trabalhos/entity.py`: `TrabalhoEntrega`.
10. `api/trabalhos/entity.py`: `TrabalhoEtiqueta`.
11. Column `trabalhos_sincronizados_em` on `Materia`, and its counterpart `mark_trabalhos_synced` on `MateriaRepository`.
12. Register the three tables in `MAPPED_TABLES` (`api/db.py`).
13. `api/trabalhos/repository.py`: `list_all(materia)`, `replace(materia, trabalhos)`, and the entrega and etiqueta reads.
14. `api/trabalhos/service.py`: `TrabalhoSyncService.sync(materia)` walking the cascade and committing once.

Bringing the trabalhos to the screen and capturing the attachment and answer-key endpoints are left to [0005.1](../pending/0005.1-trabalhos-in-the-interface.md).

## Rejected

- **Trabalho as a child of atividade.** The API takes no atividade id anywhere in the URL, the trabalho's grade does not appear in the atividades list, and the AVA itself splits the two into distinct menu sections. The link would have to be invented by name or weight.
- **One flattened table.** It fits today, because every etapa in the account has at most one entrega. But the `tentativa` field and the screen's "1ª entrega" label say there are N, and flattening now means a migration when the second one shows up.
- **Etiquetas as JSON in an entrega column.** Would save a table and a join, at the cost of not being able to filter by `constante` in SQL and of introducing the schema's only document field.
- **On-demand sync per level.** Would follow the atividades pattern to the letter, with three timestamps and three methods. Saves one or two requests per matéria and pays with "half-synced trabalho" becoming a normal state of the database.
- **Sweeping the whole account in one command.** 53 requests and some 4 seconds for the full database, 13 of them guaranteed 404s. Goes against the [0001](../done/0001-ava-atividades-crawler.md) decision that the network only comes in when the user asks for that matéria.
- **Hunting for the attachment and answer-key endpoints.** Would take reverse-engineering the SPA. They stay pending capture in DevTools.
