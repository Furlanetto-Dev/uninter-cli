---
name: crawler-api-cli-layers
description: Reorganisation of src/ into three layers — crawler (AVA requests and DTOs), api (entities, repositories, services) and cli — with the source/destination map of each file, the type renames and the accepted direction of the dependencies. Read before creating a new module or deciding where a file lives.
projects: [all]
status: done
created_at: 2026-09-02
---

# Layers: crawler, api and cli

Today `src/` is organised by domain: `materias/` and `atividades/` hold side by side the entity that becomes a table, the payload that comes from the AVA and the service that stitches the two together. It works, but it erases precisely the boundary that matters most here — the one separating what Uninter returns from what we model. A JSON alias and a SQLite column should not be folder neighbours.

The reorganisation swaps the axis: layer first, then domain. No behaviour changes; it is moving, renaming and repointing imports. The vocabulary is in [CONTEXT.md](../../CONTEXT.md), the design decisions in [0001](0001-ava-atividades-crawler.md) and the planned tests in [0002](../rejected/0002-testing-strategy.md).

## The target structure

```
src/
  main.py                     composition root, inalterado no conteúdo
  settings.py                 RU, senha, id_curso e APP_ROOT
  crawler/                    tudo que fala com o AVA
    session.py                ava_client, AvaSession, LoginRejected
    dto.py                    AvaDTO (base), LoginDTO, UsuarioDTO
    materias/
      dto.py                  MateriaDTO, MateriasDTO
      request.py              MateriaRequest
    atividades/
      dto.py                  ProvaDTO, AtividadeDTO, AtividadesDTO
      request.py              AtividadeRequest
  api/                        o que é nosso: o que persiste e o que decide
    db.py                     db_session, DATABASE_PATH, MAPPED_TABLES
    materias/
      entity.py  repository.py  service.py
    atividades/
      entity.py  media.py  repository.py  service.py
  cli/                        inalterado
    app.py  format.py  prompts.py  render.py
```

The `infra/` package disappears. It was never a layer: it was the landing spot for two files that fit neither in `materias/` nor in `atividades/`, and each belongs to a different side of the new boundary.

## From where to where

| Today | After |
| --- | --- |
| `infra/ava.py` | `crawler/session.py` + `crawler/dto.py` |
| `materias/gateway.py` | `crawler/materias/dto.py` + `crawler/materias/request.py` |
| `atividades/gateway.py` | `crawler/atividades/dto.py` + `crawler/atividades/request.py` |
| `infra/db.py` | `api/db.py` |
| `materias/{entity,repository,service}.py` | `api/materias/` |
| `atividades/{entity,media,repository,service}.py` | `api/atividades/` |
| `cli/*`, `main.py`, `settings.py` | in place |

Renames that go with the change: `AvaPayload` → `AvaDTO`, `LoginPayload` → `LoginDTO`, `UsuarioPayload` → `UsuarioDTO`, `_MateriaPayload` → `MateriaDTO`, `_MateriasPayload` → `MateriasDTO`, `_ProvaPayload` → `ProvaDTO`, `_AtividadePayload` → `AtividadeDTO`, `_AtividadesPayload` → `AtividadesDTO`, `MateriaGateway` → `MateriaRequest`, `AtividadeGateway` → `AtividadeRequest`.

## Decisions

### DTO is the name, and it stops being private

`Payload` described where the data came from; `DTO` describes the role — the object that crosses the boundary and dies right after, converted into an entity. The `_` prefix was there to mark it as private inside `gateway.py`; in a module called `dto.py` these types are the content, not a hidden detail, and the layer 2 tests of [0002](../rejected/0002-testing-strategy.md) need to name them.

### Request, not gateway

`crawler/materias/request.py` holds `MateriaRequest`, with the same `fetch()` as always. "Gateway" was the generic name for an exit door; now the whole layer already says it is an exit, and what is left for the file to name is what it actually is — a request to the AVA, with the URL built and the response validated. Noun in Portuguese, method in English, as in the rest of the repository.

### The conversion stays in the DTO

`MateriaDTO.to_materia()` and `AtividadeDTO.to_atividade()` stay where they are. The DTO is what knows the AVA's crooked format; moving the mapping into the request would only spread the knowledge of the aliases across two files.

### Dependencies point to `api`, with one accepted exception

- `cli` → `api` for everything that is data, and `crawler.session` for a single thing: `LoginRejected`, which it catches to render the reason for the refusal.
- `crawler` → `api`, entities only, because of `to_materia`/`to_atividade`.
- `api/*/service.py` → `crawler`, to annotate the request and the `AvaSession` it receives through the constructor.
- `main.py` → all of them, which is its job.

The third arrow is the dirty one: a domain service importing the adapter. Accepted because the only way to eliminate it is to declare Protocols for two objects with one method each. There is no import cycle today — entities do not import services — but one becomes possible, so **an entity never imports a service or a request**.

The first arrow has the `LoginRejected` exception because exceptions cross layers by nature: the crawler is what knows the AVA refused the login, and the screen is what knows what to do about it. Translating it into an `api` error would be one more class that only passed the message along.

### The database is not touched

The table name comes from the class name, and neither `Materia` nor `Atividade` changes name or fields. `uninter.db` stays valid after the change; if a `select` breaks, it is a wrong import, not the schema.

### 0002 is updated in the same commit

The "Where the tests live" section mirrors `src/` and starts lying the minute after this change. The `tests/` tree follows the layers: `tests/crawler/`, `tests/api/`, `tests/cli/`. The tests do not exist yet, so it is a spec edit, not a code edit.

## Rejected

- **Protocols in `api` to invert the service dependency.** Purist and defensible, but it costs two one-member classes for a project with two requests, and moves the real type away from where the error would show up. If a third gateway appears, revisit.
- **`crawler/materias.py` and `crawler/atividades.py`, with DTO and request in the same file.** Two folders fewer, but it repeats the defect the reorganisation is here to fix: the AVA's format and the HTTP call glued together. And the folder per domain is the idiom the repository already uses.
- **A single `crawler/dto.py` with all the payloads.** The atividade one has three nested classes and will grow when someone wants more fields; mixing it with matéria turns the file into a dumping ground.
- **Keeping `infra/` for `db.py` and `session.py`.** Puts back together, under a vague label, exactly the two files that belong to opposite layers.
- **Moving `settings.py` into one of the layers.** It is read by `api/db.py` (via `APP_ROOT`) and by `main.py`; at the root of `src/` it belongs to nobody, which is correct.
- **Using the change to fix the four known defects.** They are listed in [0002](../rejected/0002-testing-strategy.md) and wait for a red test first. A reorganisation in which no behaviour changes is a reorganisation reviewed by reading the imports.

## Execution order

1. **`crawler/`** — `session.py` and `dto.py` out of `infra/ava.py`, then the two `dto`/`request` pairs out of the `gateway.py` files.
2. **`api/`** — `db.py`, and the entities, repositories, services and `media.py` moved with no edit beyond the import.
3. **`cli/` and `main.py`** — only repoint imports; `render.py` and `prompts.py` start importing from `api.*`.
4. **Cleanup and check** — delete `infra/`, `materias/`, `atividades/` and the orphaned `__pycache__`, run `pdm run start` and open one matéria with cache and another without.
5. **0002** — update the `tests/` tree to the three layers.
