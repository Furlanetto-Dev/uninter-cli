```text
                              ██       ██
                          ▄█▄▄██       ██▄▄█▄
                          █   ██       ██   █
                         ▄▀   ██       ██   ▀▄
                       █████████       █████████
                         █    ██       ██    █
                         █    ██       ██    █     ▀▄▄
                       █████████████████████████     ██
                         █    ██       ██    █      ▄█▀
                     ▄    █   ██       ██   █     ▄█▀
                    █    ▀▀▄▄▄██       ██▄▄▄▀▀  ▄█▀
                   █          ██▀▀▀▀▀▀▀██     ▄█▀
                  █           ▀▀       ▀▀ ▄▄▀▀
                  ██▄             ▄██▄▄▄▀▀
                   ▀▀███▄▄▄▄▄▄▄▄▀▀▀██▀

██   ██ ███▄  ██ ██ ███▄  ██ ████████ ██████ ██████▄    ██████╗██╗     ██╗
██   ██ ██▀█▄ ██ ██ ██▀█▄ ██    ██    ██     ██   ██   ██╔════╝██║     ██║
██   ██ ██ ▀█▄██ ██ ██ ▀█▄██    ██    █████  ██████▀   ██║     ██║     ██║
██   ██ ██  ▀███ ██ ██  ▀███    ██    ██     ██  ▀█▄   ██║     ██║     ██║
▀██▄██▀ ██   ▀██ ██ ██   ▀██    ██    ██████ ██   ██   ╚██████╗███████╗██║
                                                        ╚═════╝╚══════╝╚═╝
```

# Uninter CLI

Uninter's AVA in your terminal: matérias, atividades, médias, trabalhos, provas and aulas,
mirrored on your own machine so that looking something up is instant.

> Unofficial. Not affiliated with or endorsed by Uninter; the name and the globe are Uninter's.

## Why

The AVA (Univirtus) is a slow SPA: seeing a grade means logging in, waiting for it to load and
navigating matéria by matéria. This app fetches that data when you ask, stores it in a local
SQLite database and shows it in a terminal, where lookup is immediate and does not depend on an
open session.

It is for personal use, by a single student. There is no server and no multi-user support, and
nothing leaves your machine except the requests the app makes to the AVA on your behalf.

## What it does

- **Matérias** in four groups — obrigatórias da fase, prazo estendido, pendentes ou futuras,
  concluídas — with current work first.
- **Atividades** of each matéria, grouped, with their deadlines and the média coloured by the
  AVA's own approval bands.
- **Trabalhos**, with entrega, nota, situação and prazo; `⏎` opens one on its own page.
- **Provas**: start one, answer its questões and hand it in without leaving the terminal.
- **Gabaritos**: `⏎` on a finished prova opens its gabarito, kept per tentativa.
- **Aulas**: the Roteiro de Estudo of a matéria as a tree of aulas, atividades and materiais.
  `⏎` opens a rota or a video in the browser, and downloads an arquivo once into
  `UNINTER_AULAS_DIR`, one folder per matéria and aula, before opening it from disk.
- **Figures** in a questão are drawn in place when the terminal speaks the kitty graphics
  protocol, and become clickable links when it does not.
- **Background sync**: a queue fetches whatever is missing, one matéria at a time, and the
  matéria you ask for jumps the queue. The matérias listing is sent again every time you come
  back to the list, and a new matéria is announced. When the AVA does not answer, what is stored
  stays readable.
- **Debug mode** shows the AVA's raw payload next to what was stored, with a history of every
  request the app made.
- **Dev mode** seeds a mocked matéria served by a fake AVA, so every flow can be exercised without
  touching a real prova.

## Getting started

Requires Python 3.12 and [PDM](https://pdm-project.org).

```bash
pdm install
pdm run start
```

The first three times it opens, the app shows the logo above for a few seconds; any key skips it.

On the first run the login page asks for your RU and senha, then takes the curso from your turma,
asking which one only if you have several. Tick *Lembrar de mim* and the credentials are kept in
the local database, in plain text, until you log out from the command palette. To skip the login
page altogether, copy `.env.example` to `.env` and fill in your RU and senha; every variable is
documented there.

## Using it

The footer always lists the keys that work on the current screen. The essentials:

| Key | Where | What |
| --- | --- | --- |
| `⏎` | matérias | fetch the highlighted matéria from the AVA |
| `r` | matérias | fetch the open tab again, and the matérias listing |
| `1` `2` `3` | matérias | atividades, trabalhos or aulas tab |
| `→` `←` | matérias | move between the list and the detail pane |
| `⏎` | atividades | start a prova, or open the gabarito of a finished one |
| `⏎` | aulas | open a rota or a video, or download and open an arquivo |
| `a` … `h` | prova | pick an alternativa |
| `1` … `0` | prova, gabarito | jump to a questão |
| `ctrl+←` `ctrl+→` | prova | previous or next questão |
| `j` `k` | gabarito | previous or next questão |
| `esc` | everywhere | back |
| `ctrl+p` | everywhere | command palette |

The command palette holds the rest: **Reload matérias**, **Invalidate cache** (deletes the local
database and restarts), **Enable debug mode** (`j` then focuses its panel and `ctrl+l` opens the
request history), **Enable dev mode** and **Logout**.

## Files it keeps

These live at the repository root and are gitignored:

| File | What |
| --- | --- |
| `.env` | optional credentials and settings; see `.env.example` |
| `uninter.db` | the local SQLite mirror of the AVA |
| `config.json` | what the app remembers between runs: `dev_mode`, and `logo_shown`, how many times the logo was shown |

The arquivos you download from the aulas go to `UNINTER_AULAS_DIR`, `~/Uninter` by default.

## Development

```bash
pdm run test                                                   # pytest + pytest-asyncio
uvx ruff check src tests && uvx ruff format --check src tests
uvx pyright                                                    # strict; not installed in the venv
```

```text
src/
  main.py             composition root
  crawler/            talks to the AVA: session, requests, DTOs
  api/                what is ours: entities, repositories and services over SQLite
  cli/                the Textual interface: app, pages, components
tests/cli/            mirrors src/cli/; only the interface is tested
specs/                one decision per file: pending/, done/, rejected/
uninter-endpoints/    captured AVA requests the crawler is built from
.claude/skills/       how a page, a test and a spec are written here
```

Code is written in English while the domain stays in Portuguese — matéria, atividade, trabalho,
prova, gabarito, RU, AVA — and so does every word on screen. [CONTEXT.md](CONTEXT.md) has the
project in one paragraph, and `specs/done/` has every decision behind it.
