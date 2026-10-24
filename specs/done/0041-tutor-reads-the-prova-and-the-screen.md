---
name: tutor-reads-the-prova-and-the-screen
description: The tutor's Claude Code reads every questão of the open prova through `get_open_prova` and, as a last resort, moves the app's screen with `open_materia`, `open_questao`, `go_back` and `read_screen`, guided by the `navegar-no-uninter` skill the app installs in the chat folder. Read before touching those tools, what a page lets the tutor do, `ScreenRefused`, or the skills in `cli/lib/claude/skills/`.
projects: [api, frontend]
status: done
created_at: 2026-10-24
---

# The tutor reads the whole prova and, as a last resort, moves the screen

## TL;DR
- `get_open_prova` returns every questão of the prova open in the app, as plain text: enunciado, comando, alternativas, the marked one, and which questão is on screen.
- Four navigation tools move the student's screen: `open_materia(materia_id, tab)`, `open_questao(numero)`, `go_back()` and `read_screen()`. They are high level, never press a raw key, and each returns `get_current_screen`'s view after acting.
- None of them starts, answers, hands in or books a prova. A modal on top refuses them all.
- The skill `navegar-no-uninter` lives in the repo. The app copies it into `chat_dir/.claude/skills/` on every launch, and `tutor.md` points to it.

The student wants the tutor of [0040](./0040-claude-terminal.md) to read the whole prova and, when no data tool has the answer, to look around the app itself. Data tools stay the first choice. Context in [CONTEXT.md](../../CONTEXT.md).

## Observed behaviour
- With a skill in `.claude/skills/navegar-no-uninter/SKILL.md` of the cwd, `claude -p` 2.1.310 lists `navegar-no-uninter` in the `skills` and `slash_commands` of its `init` line. The interactive launch of 0040 passes no `--setting-sources`, so project skills load there as well; that last part is an inference.
- `ProvaPage` keeps every questão of the prova in memory (`_prova.questoes`), the marked alternativas included.
- Textual 8.2.8 has no public API for a screen's painted text. `export_screenshot` itself reads `screen._compositor`.
- `QuestaoList.select` only posts a message, so the page's `_page` changes a tick later.

## Decisions

### The data tool reads the prova wherever it sits in the stack
`AppHost.open_prova()` walks `screen_stack` from the top, as `current_screen` does, and asks the first page that holds a prova. So a `Confirm` over the prova does not hide it. With no prova open it raises `ScreenRefused("não há prova aberta no app")`, which reaches the model as a tool error. It is `readOnlyHint`.

### Navigation acts only on the page on top, and only through what that page offers
- `open_materia` needs `MateriasPage` on top. It highlights the matéria in the list and switches the tab; the tab is a `Literal` of `atividades`, `trabalhos` and `aulas`. It never opens an atividade, since opening one that is "Aguardando início" starts the attempt in the AVA.
- `open_questao` needs `ProvaPage` on top. It selects the questão and repaints before answering, so the returned view already shows it. It never marks an alternativa.
- `go_back` calls the top page's `action_leave`, which is what `esc` does on prova, gabarito and trabalho. The home screen and the login have none, so they refuse.
- `read_screen` returns the painted lines after the next refresh, read off `_compositor`. That is the one private access, commented as an externality.

A modal on top (`Confirm`, `ChooseHorario`, `ClaudeCommand` and the rest) refuses every navigation, because only the student answers it. There is no generic key tool: `a`–`h` answer the prova. Everything runs in the app's loop through `call_later` and gives up after 10 seconds as "app closed". Under `pdm run mcp`, every one of these tools answers that the app is closed.

### The skill sets the order of preference and the manners
The skill says what to try first: `list_*` and `get_transcricoes`, then `get_current_screen` and `get_open_prova`, and only then navigation. Before moving the screen, the tutor tells the student and notes where they were. Each tool's answer is checked before the next step, a refusal is never worked around, and at the end the tutor goes back where the student was. The skill is copied on every launch, so an edit reaches the next session. `tutor.md` gains one paragraph pointing to it.

### Tests drive the real pages and an in-memory MCP client
- `AppHost` against a pushed `ProvaPage` and the launched app: the whole prova read without moving, another questão shown and read off the screen, the refusals (questão out of range, unknown matéria, nowhere to go back, a `Confirm` on top).
- The tools against `FakeHost`: each one forwards and answers the screen, a refusal becomes a tool error, and an unknown tab never reaches the app. The output-schema test covers the new tools.
- `prepare_chat_dir` installs the skill as it is in the repo.

## Rejected
- **A tool that presses any key.** `a`–`h` mark alternativas and `enter` on the summary hands the prova in.
- **`open_atividade`.** Opening an atividade "Aguardando início" starts the attempt in the AVA.
- **Navigation that closes a modal on its way.** A `Confirm` is the student's answer to a booking, and only the student gives it.
- **Reading other questões by moving through the prova.** `get_open_prova` already has all of them without touching the screen.
- **The skill installed once, by hand, in the user's `~/.claude/skills`.** It would go stale, and it belongs to this app's chat folder only.
