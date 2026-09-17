---
name: fake-ava
description: The mocked matéria's atividades and trabalhos stop being written into the database and start arriving over HTTP, through a FakeAva transport that answers its URLs from the fixture and delegates every other one to the network. Read before touching api/mock, ava_client, or what turning dev mode on does.
projects: [crawler, api, frontend]
status: awaiting-review
created_at: 2026-09-17
---

# A fake AVA behind the client

## TL;DR
- `ava_client` takes a transport; dev mode passes an `httpx.MockTransport` answering the AVA's URLs.
- The fixture serves the JSON the AVA returns instead of building entities.
- Seeding becomes syncing: `MockedMateria` and `fixture.capturas()` go, and the sync services record real capturas.
- `MockedProvas` becomes a real `ProvaSource` against the fake, so the prova flow is built before it touches a graded exam.
- Mocked requests reach the event hooks of [0027](0027-request-history.md), so dev mode has a request history like any other run.

Dev mode writes rows straight into SQLite, so everything between the AVA and the database —
the session, the requests, the DTOs — never runs against the mocked matéria. The fixture then
fabricates the artefacts those layers would have produced, which is a second copy of the truth
kept by hand. See [CONTEXT.md](../../CONTEXT.md), the layers of
[0003](../done/0003-crawler-api-cli-layers.md) and the dev mode of
[0023](../done/0023-dev-mode.md).

## Observed behaviour
- `MockedMateria.seed()` adds `Materia`, `Atividade` and `Trabalho` objects to the session and commits; no crawler code runs in dev mode — read from `seed.py`.
- Two fakes of the capture pipeline exist already: `fixture.capturas()` builds `Captura` rows with `mock://uninter/{recurso}` URLs, and `MockedProvas.raw()` assembles an `avaliacaoUsuarioHistoricos` payload, both so the debug panel has something to show.
- What the fixture emits would not parse: `_atividade_item` gives five fields where `AtividadeDTO` needs `avaliacao` with id, nome, `nomeAvaliacaoTipo`, `nomeAvaliacaoTipoCategoria` and `pesoMedia`, plus `tentativa`, `tentativaTotal` and both dates.
- `ava_client()` constructs the client in one place and takes no transport today, so the seam is a single parameter.

## Decisions

### Dev mode swaps the transport, not the data
`ava_client(transport)` is the only new seam. Everything downstream — `AvaSession`, the
`*Request` classes, the DTOs, the sync services, the capturas — runs unchanged and unaware.
Dev mode stops being a second path through the app and becomes a different AVA.

### The fixture serves payloads, and the DTOs make the entities
It builds the JSON the AVA returns, keyed by the URLs the crawler asks for. The entities it
hands out today are what `to_materia`, `to_atividade` and `to_prova` already know how to
build, so the second copy goes and the DTOs get exercised by every dev-mode run.

### Seeding becomes syncing
`MockedMateria.seed()` goes: the mocked matéria arrives through `MateriaSyncService` like any
other. `fixture.capturas()` goes with it, because the sync services record capturas from the
mocked responses themselves. Turning dev mode off still deletes the mocked rows, which is the
one thing `MockedMateria` keeps.

### A negative id is what makes a matéria mocked
`mockada` cannot come from a payload the AVA would never send, so it is derived from the id
the fixture serves: `MATERIA_ID` stays `-1`, and the rows it owns stay the rows dev mode
removes. Nothing else changes about how the interface tells them apart.

### `MockedProvas` becomes a real source against the fake
Once the transport answers `AvaliacaoUsuarioHistorico`, the prova flow has somewhere to be
built and exercised that is not a graded exam. The answering work lands against the fake
first, and the mocked prova stops being a separate implementation of the same protocol.

## Rejected
- **Letting the mock append its own entries to the request log.** A few lines instead of a rewrite, but it would fabricate a log of requests that were never made — a third hand-kept copy beside the two the fixture already carries.
- **A fake client class rather than a transport.** `MockTransport` is httpx's own seam and keeps the client, its headers and its hooks real; a fake client would have to reimplement all three.
- **Serving the real captured bodies from the database.** The most faithful payloads available, and they carry a real student's grades, RU and name — the fixture stays invented.
- **Keeping `fixture.capturas()` as well.** Two capturas for the same response, one recorded and one fabricated, differing the moment either changes.

## What execution corrected
- **The transport is a router, not a `MockTransport`.** Two things ruled out replacing the transport: the client is built once in `main.py` while dev mode toggles at runtime from the palette, and a transport that answers everything would stop real matérias reaching the network. `FakeAva` holds the real transport, answers the URLs the fixture recognises and delegates the rest — verified by driving five URLs through it, three of which reached the network and two of which did not.
- **Seeding becomes syncing, for the collections only.** The matéria row is still seeded. Making it arrive through `MateriaSyncService` would need the router to let the real matérias request through, parse the response, append the mocked matéria and re-serialise it — dev mode rewriting what the AVA said, which is worse than the row it replaces. Its atividades and trabalhos do now arrive over HTTP, which is where the DTOs and the capturas were being skipped.
- **`MockedProvas` went through the transport too, in the end.** It kept answering from memory, so starting a prova made no request at all. It now GETs `AvaliacaoUsuarioHistorico/{id}/Avaliacao` and PUTs each answer through `AvaSession`, which grew a form `put` for it, while still holding the chosen alternativas in memory — the fake has nowhere to persist them. It still refuses a real atividade: the guard on writing to a graded exam belongs to the prova spec.
- **Three things kept the mocked matéria from ever syncing, and the first verification missed all of them.** `fixture.materia()` stamped `atividades_sincronizadas_em` and `trabalhos_sincronizados_em` as already synced, which was right while the seed also inserted the rows and means nothing asks for them once it does not; `materias/page.py` returns early from `refresh_materia` and `fetch_missing_trabalhos` when a matéria is mockada; and `enqueue_pending` skipped them too. All four guards are gone, and the stamps start empty.
- **The trabalhos sync walks past the etapas list.** It fetches entregas for every trabalho and etiquetas for every correção, so the fixture answers `TrabalhoEntrega/-` and `TrabalhoCorrecaoEtiqueta/-` with empty collections — the mocked trabalhos never had entregas, and without those routes the sweep escapes to the real AVA.
