---
name: english-code-portuguese-domain
description: Rules for the English rewrite — what stays Portuguese (entities, DTOs and their fields, screen text, the AVA's vocabulary), what goes English (everything else, specs and CONTEXT.md included), how to name a variable that holds an entity, how to undo the collisions translation exposes — and the move of apps/uninter-crawler/ to the repo root, with spec and novo-plano paths adjusted. Read before naming anything new, executing the rewrite, writing or translating a spec, proposing a field translation, or creating a second app.
projects: [all]
status: done
created_at: 2026-09-08
---

# English code, Portuguese domain, one app at the root

Today the code mixes both languages with no rule saying where one ends and the other begins. The convention in force covers three points — a class is a domain noun with an English technical suffix, a method is an English verb, a field is Portuguese — and leaves out everything around them: locals, private attributes, constants, module-level functions, file names, CSS selectors and comments. The result is `self._sessao` next to `self._repository`, `enfileirar` next to `list_all`, a class called `Carregando` inside a module called `loading.py`, and nobody can say whether any of it is right or wrong because there is no ruler.

A worktree rehearsal (branch `tryout/english-rewrite`) applied the rule "domain in Portuguese, everything else in English" to the whole app. It touched 28 files and left six untouched — the entities and the DTOs, which are pure model. Besides reading better, the translation exposed two things the mix was hiding: public and private methods sharing a name across languages, and nouns serving as method names. This spec fixes the rehearsal's rules so the rewrite is done in one pass and everything that comes after is born inside them.

The specs are part of the rewrite. Every spec written before this one is Portuguese, this one's first draft included, and they are where the code's names get decided — a Portuguese spec proposing English names has to translate itself in every sentence. The specs written since ([0010.1](0010.1-selectable-atividades.md), [0010.2](0010.2-debug-panel-focus-and-copy.md), [0011](0011-tabbed-detail-panel.md), [0011.1](0011.1-trabalhos-tab.md)) already follow this rule. From here on, the specs, `CONTEXT.md` and the `novo-plano` skill are English prose around the same Portuguese domain nouns, and the ones still in Portuguese are translated.

The same pass settles something else left half-done: the repository is shaped like a monorepo — `apps/uninter-crawler/` — with a single app in it. The `apps/` folder exists for a second app that never came, and it charges every day: each spec reaches `CONTEXT.md` through four `../`, the spec skill starts by discovering which app, and the `.venv`, the `.env` and the database live two levels below where the terminal opens. The app moves to the root.

The layers these rules refer to are in [0003](0003-crawler-api-cli-layers.md); the domain vocabulary is in [CONTEXT.md](../../CONTEXT.md). The pending specs [0002](../pending/0002-testing-strategy.md) and [0005.1](../pending/0005.1-trabalhos-in-the-interface.md) propose Portuguese names; they execute under these rules, whichever lands first. [0008](0008-building-the-materias-list.md) and [0010](0010-debug-mode.md) have already landed with Portuguese names, and the rewrite covers what they added.

## Decisions

### The domain stays Portuguese; everything else goes English

The domain is what models the student's academic life and what the AVA returns:

- the entities in `api/*/entity.py`, class, fields and properties (`Materia.vigente`, `Atividade.realizada`, `Trabalho.entregue`);
- the values derived from them, such as `Media`, with their fields (`valor`, `peso_lancado`, `parcial`);
- the DTOs in `crawler/`, fields and aliases — the AVA payload already speaks Portuguese, and the DTO mirrors it;
- the packages and modules named after an entity (`api/materias`, `api/capturas`, `crawler/trabalhos`, `cli/atividades/`).

Everything not on that list is English: locals, private attributes, parameters, functions and methods, constants, classes that are not model (widgets, screens, providers, services, requests), modules not named after an entity, CSS ids and selectors, comments. It holds across the three layers.

The line sits there and nowhere else because it is the one separating what has an external owner from what is only ours. `contribuicao`, `aproveitamento` and `vigente` mean what the AVA says they mean; translating them would be inventing. A queue, a timer and a `deque` carry no such tie.

### A class is a domain noun with an English suffix; a method is an English verb, no exceptions

This is the convention that already existed, now without gaps. Every Portuguese verb goes (`rodar`, `enfileirar`, `consumir`, `pausar`, `gravar`, `avancar`, `girar`, `focar`), and so does the noun serving as a method: `TrabalhoRepository.entregas(trabalho)` and `etiquetas(entrega)` become `list_entregas` and `list_etiquetas`, following `list_all`. A class that is not model is English throughout: `Carregando` becomes `Loading`, `ComandosDoApp` becomes `AppCommands`, `ConfirmarReset` becomes `ConfirmReset`.

### A variable holding an entity takes the entity's name

`for materia in materias`, `trabalho`, `entrega`, `etiqueta`, and `etapa` for an instance of `TrabalhoEtapaDTO`. It is the variable-to-type link the reader navigates by, and translating only the variable (`subject`) would break that link without translating the type.

The flip side is that what is **not** an entity may not dress up as one. The list widget is `materia_list`, not `lista`; the average bar is `media_bar`, so it is not mistaken for `media`, the `Media` value. Collections and services of an entity follow the rule in the plural: `materias_db`, `atividades_service`.

### A value that is a field takes the field's name; a derived value takes an English name

A parameter that only carries a field to a constructor is named after the field: `to_atividade(materia_id, posicao)`, `to_etiqueta(correcao_id)`. So is a variable that resolves one field out of others: `oferta_aproveitamento = materia.oferta_aproveitamento or materia.oferta_atual`. A sum, a filtered list or a sync stamp is ours and goes English: `contributions`, `weights`, `sync_stamps`, `atividades_synced_at`.

### Screen text stays Portuguese; the constant holding it goes English

Binding labels, table headers, notifications, the reset prompt, `"RU ou senha inválidos"`: all of it is what the student reads, and the interface language is a product decision, not a code one. Only the constant's name changes: `SEM_MATERIAS` becomes `NO_MATERIAS`, `CRITERIOS` becomes `CRITERIA`, `PERGUNTA` becomes `PROMPT`.

The AVA's vocabulary is untouchable in every layer: endpoint paths, form fields (`senha` in the login POST), DTO aliases.

### Configuration goes English, and RU stays RU

`Settings` becomes `ru`, `password` and `course_id`; the `.env` becomes `UNINTER_RU`, `UNINTER_PASSWORD` and `UNINTER_COURSE_ID`, and `.env.example` changes in the same commit. `RU` stays because it is the identifier Uninter gives the student — a domain noun, not a translation of "enrolment number".

The cost is editing the `.env` of whoever already runs the app. Two lines, and the pydantic-settings error names the missing field.

### Comments are English, and only record what the AVA imposes

The comments that exist today record externalities — the `x-time` cookie, `expire_on_commit` under async, the `shield` around the write, the AVA's passing cut-offs — and they stay, translated. No new comment enters because of this spec.

### A collision the translation exposes is resolved by role, not by suffix

Translating makes names that coexisted in different languages land on the same one. The rehearsal found three cases, and each becomes a rule:

- **Request and execution.** `sync_materias` (what the user asks for) and `sincronizar_materias` (what the queue runs) collide. The public request keeps the short verb; the private execution takes `_run_`: `sync_materias` and `_run_materias_sync`, `refresh_materia` and `_run_atividades_sync`.
- **Redraw and refetch.** `MateriaList.atualizar` only repaints one row, but `refresh` in the app means fetching from the AVA again. Repainting is `redraw`; refetching is `refresh`.
- **State and action.** `MateriaList.sincronizando(id)` was a method named like a state. What changes the state is `set_syncing`; the state itself is `syncing`.

The list's `em_foco` follows from there: it becomes `highlighted_materia`, because it derives from the `OptionList`'s `highlighted` and returns a `Materia` — neither `focused`, which collides with Textual vocabulary, nor `em_foco`.

### Module, class and CSS selector agree

When the TUI was split into packages, the modules got English names and the classes inside kept Portuguese ones: `Carregando` lives in `animations/loading.py`, `ComandosDoApp` in `commands/palette.py`, `ConfirmarReset` in `commands/reset.py`. The class follows the module: `Loading`, `AppCommands`, `ConfirmReset`. Packages named after an entity stay — `cli/materias/`, `cli/atividades/`, `api/capturas/` — and so do the modules inside them, which are already English (`list.py`, `header.py`, `table.py`, `media.py`). In `app.tcss`, `#detalhe` becomes `#detail` and `#confirmacao` becomes `#confirmation`, next to `#grades` and `#debug-meta`, which were born English; the `ConfirmarReset` selector follows its class.

### Specs, `CONTEXT.md` and the `novo-plano` skill are English prose around Portuguese domain nouns

The same line as the code: prose, titles, decision headings, file slugs and the `description` field go English; `matéria`, `atividade`, `trabalho`, `entrega`, `etiqueta`, `oferta`, `aproveitamento`, `RU` and `AVA` stay as they are, as do quoted screen text and quoted AVA payload. A spec that discusses `Materia.vigente` writes `Materia.vigente`; one that explains what "vigente" means to the AVA explains it in English.

Every spec still in Portuguese, done or pending, is translated, not summarised: every decision and every rejected alternative survives, because the Rejected section is what stops an idea from being re-proposed. Their numbers stay, since the number is the identity (`0005.1` says whose child it is); their slugs follow their translated titles, so the skill's rule that `name` equals the slug keeps holding. `CONTEXT.md` goes with them. The skill's instructions and template are rewritten in English, and its line telling the writer to use Portuguese becomes its opposite.

The cost is a one-time translation of every spec, of `CONTEXT.md` and of the skill, plus a rename of every spec file, with every cross-link touched. It is paid once. Leaving the specs Portuguese would put the code's names in one language and the documents that decide them in another.

### `apps/uninter-crawler/` moves to the root, and `apps/` ceases to exist

What is tracked goes with `git mv`: `src/`, `specs/`, `uninter-endpoints/`, `pyproject.toml`, `pdm.lock`, `.gitignore` and `.env.example`. `CONTEXT.md`, `.claude/` and `ignore.md` are already at the root and do not move. What is ignored is not git's and is rebuilt in the new place: `.env` and `uninter.db` are copied by hand; `.venv` and `.pdm-python` are recreated with `pdm install`, because `.pdm-python` stores the absolute path of the old interpreter.

Nothing in the code changes. `APP_ROOT` in `settings.py` is "two levels above `src/settings.py`", which becomes the repo root — `.env` and `uninter.db` keep being looked up next to `pyproject.toml`. `[tool.pyright]`, the `pdm start` script and `.gitignore` are already relative to their own file.

### Specs and the skill lose the `apps/<app>/` prefix

`CONTEXT.md` ends up two levels from `specs/pending/`: every `../../../../CONTEXT.md` link becomes `../../CONTEXT.md`, in the same commit as the folder move, so no commit leaves a broken link. Links between specs (`../done/`, same folder) do not change. Neither does the `projects` field: `crawler`, `api` and `frontend` were always layers inside `src/`, not apps.

The `novo-plano` skill stops discovering an app: the file goes to `specs/pending/`, numbering counts `specs/done` and `specs/pending`, the validator scans `specs/*/*.md`, the promotion example uses `specs/`, and the template links `../../CONTEXT.md`. The "four levels" note becomes "two".

### Folder first, then the documents, then the names

Three commits, in that order. Moving first, the move's diff is only paths. Translating second, the skill produces English specs before any further spec is written, and the code rewrite lands in a repo whose documents already speak its names. Rewriting last, that diff is only language. Each of the three reviews alone. Mixed together, git has to pair source and destination with path and content changing at once, and the files that change most — in the rehearsal, `carregando.py` → `loading.py` already fell below the similarity git requires — show up as deleted and created, with no side-by-side. The rehearsal was done still under `apps/`, so it serves as a reference for the rewrite, not as a patch.

### The rewrite is a mechanical refactor, done in one pass

No behaviour changes, in any of the three steps. Verification is `pyright` in strict mode passing and `pdm start` at the root opening the app with the list, the detail pane, the background queue and the reset working as before — the same criteria as [0007](0007-background-queue-and-reset.md) — plus the skill's validator reporting every spec consistent. The code rewrite itself is a single commit: the intermediate state, `session` in one repository and `sessao` in the next, is worse than either extreme, and the rehearsal showed the whole change fits in 28 files.

## What execution corrected

- **`_tarefa` could not become `_task`.** Textual's `MessagePump` keeps its own message-processing task in `self._task`; the rename clobbered it silently, and the background queue accepted work it never ran. The attribute is `_sync_task`. A private name on an `App` or `Widget` subclass is checked against the Textual base classes before it is used.
- **A scripted rename must skip string literals.** The word-boundary pass that renamed `restantes` also hit the subtitle text "N restantes" on screen. Screen text is reviewed in the diff separately from identifiers.
- **The rewrite landed on a code base the spec had not seen.** 0010 to 0010.2 added `api/capturas/`, the debug panel and the `animations`, `commands` and `navigation` packages. They fell under the rules with no new decision: `Captura` is a model and keeps its fields; everything around it went English.
- **Specs written between this spec and its execution were already English.** 0010.1, 0010.2, 0011 and 0011.1 needed no translation; the ten older ones did, and got English slugs: `ava-atividades-crawler`, `testing-strategy`, `crawler-api-cli-layers`, `textual-tui`, `trabalhos`, `trabalhos-in-the-interface`, `deadline-and-media-colour`, `background-queue-and-reset`, `building-the-materias-list`, `debug-mode`.
- **Verification ran headless.** `pyright` strict and `ruff` pass; the app was driven with Textual's `run_test` against a copy of the database with the AVA login stubbed to refuse, covering the list, the atividades table, `r`, the debug panel and its focus chain, `d` and the reset modal. `pdm start` in a real terminal was not run as part of the execution.

## Rejected

- **Translating the entity fields (`nome` → `name`, `nota` → `grade`).** Changes the SQLite schema, detaches the code from the vocabulary in [CONTEXT.md](../../CONTEXT.md) and the specs, and produces hybrids like `Materia.name`. Terms like `contribuicao` and `aproveitamento` have no translation that keeps the meaning the AVA gives them.
- **Translating everything, entities included (`Subject`, `Activity`, `Assignment`).** Loses the tie to the payload — `salaVirtuais`, `avaliacaoUsuarios`, `trabalhoEtapas` — and forces a glossary between code, specs and screen.
- **Translating screen text.** The app is for a Brazilian student. Interface language is a product decision; this spec is about what the developer reads, not what the student reads.
- **Keeping the current convention and stopping there.** It was the starting point. It covered class, method and field and left the rest to each commit's taste; that slack is what let `sync_materias` and `sincronizar_materias` coexist with nobody feeling the friction.
- **English names for entity variables (`for subject in materias`).** Breaks the variable-to-type reading without translating the type.
- **Undoing collisions with a generic suffix or prefix (`do_sync_materias`, `sync_materias_impl`).** They say nothing about role. `_run_` says it is the private executor of a public request.
- **Keeping `UNINTER_SENHA` and `UNINTER_ID_CURSO`.** Configuration is code; the only reason would be saving two edited lines in a `.env`.
- **Doing the rewrite gradually, by layer or by file.** Every intermediate state is a third convention. The change is mechanical and fits in one PR.
- **Using the rewrite to delete the comments.** A different decision with a different ruler; mixing the two hides in the diff what each one changed.
- **Leaving the existing specs in Portuguese and writing only new ones in English.** The old ones decide most of the names the code carries; a reader would need both languages to trace any one of them. And the mix in prose is exactly the mix this spec removes from code.
- **Translating the specs but keeping their Portuguese slugs for link stability.** The number identifies a spec, not the slug, and the skill requires `name` to equal the slug — a Portuguese slug under an English title breaks the skill's own rule. The validator catches every link the rename touches.
- **Keeping `apps/` for a second app that might come.** There is one app and no plan for another. When it comes, creating the folder is one `git mv`; until then, it only costs.
- **Moving and rewriting in the same commit.** Path and content changing together make git give up pairing the files that change most, and the rewrite review becomes a list of deletions and creations.
- **Leaving `settings.py`, `pyproject.toml` or the skill accepting both layouts.** There is nothing to be compatible with: it is the same repo, and the old folder vanishes in the same commit.
