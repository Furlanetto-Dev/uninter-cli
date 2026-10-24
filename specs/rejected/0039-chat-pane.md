---
name: chat-pane
description: An AI chat under the Atividades tab and under the prova, answered by the user's own `claude -p` reading the app's MCP server — the exact invocation, the tutor prompt file, one conversation per matéria, `i`/`esc`/`enter`/`ctrl+s`, the process lifecycle, and doubles that never call the model. Read before touching the chat pane, the claude process, the space under the atividade tree or the questão, or focus handling on those pages.
projects: [frontend]
status: rejected
created_at: 2026-10-24
---

# A chat pane under the atividades and under the prova

## TL;DR
- A `ChatPane` sits under the média in tab `1 Atividades` and under the questão in the prova, outside what those pages repaint.
- Each question runs the user's own `claude -p` from a neutral folder, the message on stdin, the app's MCP server (0038 `mcp-server`) as its only tools, and a versioned tutor prompt that teaches rather than just answers; the reply is painted as it streams.
- One conversation per matéria, in the app's memory, shared with that matéria's prova and dropped when the account changes.
- `i` focuses the chat, `enter` sends, `esc` gives focus back, `ctrl+s` stops the reply; nothing but the student moves focus out of the chat.
- No `claude` on the PATH, or no MCP, leaves a hint; the tests drive a fake executable and a scripted assistant.

The student wants to ask about a matéria — its aulas' transcrições (0037 `aula-transcricoes`), notas, agendamentos — without leaving the terminal, with the questão on screen. **The student decided** the chat is their own `claude`, run as if typed in a terminal and handed the sala's data: their subscription pays, no API key enters the app, and the matéria's data and the current questão of a prova in progress go to the model. [CONTEXT.md](../../CONTEXT.md) says nothing leaves the machine; execution rewrites it to name this exception in those terms.

## Observed behaviour
From `claude --help`, version 2.1.310, 2026-10-24, unless marked:
- The chat needs claude 2.1.310 or newer: `--permission-prompts`, `--system-prompt-snapshot` and `--setting-sources` were checked on that version, and an older claude is not known to have them.
- `--tools ""` disables all built-in tools, and the MCP's survive it: the `init` line lists exactly the nine `mcp__uninter__*` tools (recording, 2026-10-24).
- `--allowedTools` takes "comma or space-separated tool names"; no glob is documented. `mcp__uninter` allows the whole server: `list_materias` and `list_aulas` ran with no prompt, and each result is marked `permission_decision: accept, source: config` (recording, 2026-10-24).
- `--setting-sources` takes a comma list of `user`, `project`, `local`. With `""`, `init` still lists Claude Code's built-in skills, slash commands, agents and plugins, and an auto-memory path. Asked, the model said its context mentions the user's `~/.claude/CLAUDE.md` (recording, 2026-10-24).
- `--bare` would skip CLAUDE.md, auto-memory and hooks, but authenticates only with `ANTHROPIC_API_KEY`, never OAuth — unusable with a subscription.
- `--system-prompt-snapshot` defaults to `on`: the first request's system prompt is recorded and reused on every `--resume`, even when a later launch passes different text. `off` renders it fresh.
- Skills are disabled by `--disable-slash-commands` and `--safe-mode`; nothing documents whether `--setting-sources ""` keeps the cwd's `.claude/skills`.
- `--safe-mode` keeps the subscription and removes `~/.claude/CLAUDE.md` and auto-memory, but it also drops the `--mcp-config` server: `init` shows no MCP servers and no tools, and the model answered without the app's data. So the chat does not use it (recording, 2026-10-24).
- `--input-format text` is the default and `-p` reads the prompt from a pipe. `--permission-prompts none` denies whatever would prompt. There is no `--max-turns`.
- Textual 8.2.8: `Input` binds `ctrl+x` (cut), `ctrl+c`, `ctrl+k`, `ctrl+left`/`ctrl+right` and `enter`, but neither `escape` nor `ctrl+s`; no app binding is priority, so `Input` stopping printable keys keeps the prova's `a`–`h`, `0`–`9` and the app's `j` from firing while typing.
- The prova binds `escape` to leave and `ctrl+enter` to the next questão, which refocuses the page (`ProvaPage.action_step_questao`).
- A stream-json line carries a whole `tool_result`; a full VTT measured 145 KB (Ferrolho), past asyncio's 64 KiB line limit.
- Contract with Tomada (0038): `app.mcp_url` (`http://127.0.0.1:8765/mcp`, `None` when the server did not start), server `uninter`. Booking and cancelling open a `Confirm` over any screen, focused on NÃO and naming prova, matéria and horário; a refusal returns a tool error `Recusado no app: <causa>; nada foi feito.` Cancelling the call closes the modal as refused; a claude killed without cancelling leaves it until the 2-minute timeout. `AppHost(app).confirm(modal)` opens one without the server.

## Decisions

### The chat runs the user's claude with the sala's data and nothing of the repo
```
claude -p --input-format text --output-format stream-json --verbose --include-partial-messages
  --mcp-config '{"mcpServers":{"uninter":{"type":"http","url":"<app.mcp_url>"}}}' --strict-mcp-config
  --tools "" --allowedTools mcp__uninter --permission-prompts none --setting-sources ""
  --system-prompt-snapshot off --system-prompt "<context>"  [--resume <session_id>]
```
The message goes on stdin, which is then closed, so a message starting with `-` is never a flag. The cwd is `APP_ROOT/.chat`, gitignored and fixed because `--resume` finds sessions by folder: the repo's CLAUDE.md does not load and the chat's sessions stay out of the repo's `claude --resume`. `~/.claude/CLAUDE.md` and auto-memory still load, an accepted cost: `--safe-mode` would drop them but takes the MCP with them, and `--bare` would skip them but refuses the subscription. `--model` is left out on purpose: the user's default. Every `uninter` tool is allowed, booking and cancelling included, because the student chose them and the app's modal confirms each one.

### The chat is a tutor, written in a versioned prompt file
`cli/lib/claude/tutor.md` is the tutor's text; the app reads it, appends the context and passes the whole as `--system-prompt`. It is a file and not a skill because `--system-prompt` replaces Claude Code's coding-agent prompt instead of sitting on top of it, applies on every request instead of when the model chooses to load it, and needs no skill discovery, which is undocumented under `--setting-sources ""`. The wording is code and changes with the code; the spec fixes only the principles: Portuguese; teach, not just answer — explain the why; cite the aula and the transcrição's material and passage the answer came from; ask a short question to check understanding; adapt to what the student showed they know in the conversation and in their notas; say plainly when the aulas do not cover something, and mark any knowledge from outside them as such.

### Context goes after the tutor's text, rebuilt on every question
The open matéria (nome, id, período) and, in the prova, the atividade, the current questão as plain text and the chosen alternativa. `--system-prompt-snapshot off` is what lets moving to another questão change the context of the same conversation. In the prova, **the student decided**: by default the tutor teaches the concept the current questão tests and leads the reasoning with the aula at hand; when the student explicitly asks for the alternativa, it gives the letter and explains why.

### One conversation per matéria, in the app's memory
The app keeps `Conversation`s by matéria id — the turns as painted and claude's `session_id` — and runs each reply in a worker of group `chat-<materia_id>`, so a reply survives opening or leaving the prova and a question in another matéria does not cancel it. Nothing goes to the database. Switching account or resetting drops every conversation and stops their replies.

### The process never outlives its reply
stdout is read in chunks and split on newlines, with no line limit; stderr is drained alongside, keeping its last lines. The worker's `finally` calls `AppHost.refuse_pending(Recusa.CHAT_PAROU)`, closing any open `Confirm` without depending on claude cancelling its call, then terminates the process, waits 2 seconds and kills it; it runs on `ctrl+s`, app exit and reset. The refusal is global, an accepted risk: stopping one matéria's reply also refuses an action that another client, such as an external Claude Code, is waiting on at that same moment. Scoping the refusal to its origin through a request header is a follow-up.

### The pane is a shared component that knows no `api`
`cli/components/chat/` from the start, since both pages call it; the page hands it the context string and the conversation, never an entity. The process and the stream parsing live in `cli/lib/claude/`, behind an `Assistant` protocol whose `ask(message, context, session_id)` yields `Chunk(text)`, `ToolCall(name)`, `ToolRefused(name)` (a result starting `Recusado no app:`), `Finished(session_id)` or `Failed(reason)`. `ClaudeAssistant` takes the executable's path, which `main.py` resolves with `shutil.which`.

### The chat is a sibling of what the pages repaint
In the prova it follows `#prova-body` inside the `DetailPane`: at least 6 rows, growing into what a short questão leaves; a long questão scrolls above those 6 rows. In tab 1 it follows the `MediaBar`, and the `AtividadeTree` stops 6 rows short, scrolling when a matéria has many atividades. On a `-short` terminal it keeps 3 rows (input and two lines); with the `DebugPanel` open it is hidden and `i` disabled. A tool call shows as a dim `consultando list_aulas…`, or `book_prova recusado no app` when refused.

```
│ Atividade 1 ... nota │      │ enunciado / comando  (scrolls)│
│ média 72 (60% ...)   │      │ a) ... b) ... c) ...          │
├─ chat ───────────────┤      ├─ chat ────────────────────────┤
│ você: ...  claude: ..│      │ ...                           │
│ > _                  │      │ > _                           │
```

### Only the student moves focus out of the chat
`i` (`chat`) is declared on both pages, enabled on the matérias page only in tab 1 with a matéria highlighted. Inside the chat, `enter` (`enviar`) is disabled while a reply streams, `ctrl+s` (`parar`) shows only then, and `esc` (`voltar`), bound on the chat's own input, returns focus to the widget that had it, so it never leaves the prova. Page code that refocuses — `step_questao`, `jump`, `reload_materias`, tab activation — leaves the chat alone while it has focus; `ctrl+enter` in the chat does nothing.

### The Confirm interrupts the chat on the safe side
A `Confirm` that opens while the student types takes focus on NÃO: letters typed ahead are lost and a stray `enter` refuses. When it closes, focus returns to the chat's input.

### Unavailable is a hint, not an error
No executable → `Chat indisponível: o comando claude não está no PATH.`; `app.mcp_url` is `None` → `Chat indisponível: o servidor MCP do app não subiu.` The input is not shown and `i` is disabled. A non-zero exit (not logged in, no quota) ends that reply as an error line with the last line of stderr; the conversation and its `session_id` survive.

### Tests never call the model
Via `novo-teste`:
- the stream parser, a pure function, over a `stream.jsonl` recorded once after the code is approved, with the app's MCP in dev mode and read tools only (`list_materias`, `list_aulas`; never horários, booking or cancelling), its `init` sanitised (cwd, session_id, model, servers) before commit. The recording settles the inferences above;
- `ClaudeAssistant` against a fake executable in `tests/`: the argv, a `--system-prompt` holding the tutor file and the context (never its wording), a message starting with `-` on stdin, a line over 1 MB, a sleeping fake whose pid is gone after `ctrl+s` and after `app.exit()`, a non-zero exit with stderr;
- the pages with a `ScriptedAssistant` in `tests/doubles.py`: streaming paint, `i`/`esc` (and `esc` not leaving the prova), letters not picking while typing, `ctrl+enter` and a sync repaint not stealing focus, a `Confirm` opened through `AppHost` while typing (NÃO refuses, focus back on the input), two matérias answering at once, both hints, the debug panel hiding the chat.

## Rejected
- **Only read tools in `--allowedTools`.** The student chose booking and cancelling, and the app's modal guards them.
- **The Anthropic API with a key.** The student decided the chat is their own `claude`.
- **`--bare`.** It is the clean environment, but it never reads the subscription's OAuth.
- **A skill in `APP_ROOT/.chat` for the tutor.** It loads only when the model invokes it, on top of the coding prompt, and its discovery under `--setting-sources ""` is undocumented.
- **`--append-system-prompt`.** It keeps Claude Code's coding-agent prompt underneath the tutor.
- **The message as a positional argument.** A message like `-1 na questão 3?` becomes a flag.
- **`readline()` with asyncio's default limit.** A transcrição's line passes 64 KiB.
- **`mcp__uninter__*` in `--allowedTools`.** No glob is documented.
- **A recording without the MCP.** It would hold no tool call or result to parse.
- **Persisting conversations in the database.** Nothing asks to reread yesterday's chat.
- **One conversation per screen.** Entering the prova would lose what was just asked about the matéria.
- **A separate chat page.** The point is asking with the questão on screen.
- **`c`, `esc` or `ctrl+x` for chat and stop.** `c` answers alternativa C, `esc` means voltar, `ctrl+x` is the input's cut.

## What execution corrected
- **CSS cannot hold the chat's 6 rows.** `max-height: 1fr` on the questão ignores its sibling's `min-height`, so a long questão pushed the chat off screen. `ChatPane.fit_under(widget)` sets that widget's `max-height` to what the parent has left after its other children and the chat's minimum, on every resize. `#prova-body` is `height: auto` (and `1fr` again with the debug panel open). In tab 1, `#collections`, its `ContentSwitcher` and `#atividades` take `1fr`. Measured headless at 120×40: a two-line questão leaves the chat 27 rows; a sixty-line one scrolls above a 6-row chat.
- **Textual cancels workers on exit without awaiting them**, so claude outlived the app. `UninterApp.on_unmount` awaits `Tutor.close()`, which cancels only the replies not already cancelled: a second cancel interrupted the kill. The process stop is shielded too.
- **Only an unfinished reply refuses pending confirmations.** A reply that ends with its result refuses nothing, so one matéria finishing never closes a `Confirm` that another matéria's reply opened.
- **The SDK prefixes tool errors** (`Error executing tool book_prova: Recusado no app: …`), so the refusal is found anywhere in the result's text, not only at its start.
- **The debug panel hides the chat** because the pane watches the app's `debug_mode`, as `DebugPanel` does, not through a CSS class.
- **The merge with 0038 is a task.** Here `UninterApp` gained a plain `self.mcp_url: str | None = None` and an empty `refuse_chat_confirmations`. In 0038, `mcp_url` is a property fed by the constructor (`mcp_url=`, `mcp_failure=`), and `main.run` builds the `AppHost` after the app. At the merge:
  - drop the attribute and use 0038's property;
  - hand the app (or the `Tutor`) its `AppHost`;
  - make `refuse_chat_confirmations` call `host.refuse_pending(Recusa.CHAT_PAROU)`, importing `Recusa` from `api/mcp_server/host.py`. That call also refuses the confirmations still in the queue.
- **A failing claude never closes the app.** A worker's error exits a Textual app by default. So a replaced binary (`FileNotFoundError`), a claude that quits before reading its stdin (`BrokenPipeError`, `ConnectionResetError`) or any other `OSError` used to close the TUI, possibly mid-prova. Now `ClaudeAssistant.ask` turns a start failure into `Failed(não foi possível abrir o claude: …)`. A write to a closed stdin is ignored, and claude's own stderr then says why. The reply worker runs with `exit_on_error=False`, so anything else ends the reply as interrupted.
- **Repaints are batched.** Every delta used to re-render the whole turn's Markdown. The pane now repaints at most once every 50 ms while chunks arrive.
- **`stream.jsonl` is a real recording.** It was recorded after the merge with one `claude -p` using the app's invocation and its stdio MCP in dev mode (`pdm run -p <root> mcp`), asking for the matérias and the aulas of the mocked matéria. A second run only tested `--safe-mode`. Before commit, the `init` line was trimmed to its tool and server fields, the cwd and session_id were replaced, and the rate-limit line was dropped; no real matéria name was in the output. The parser read the real format unchanged: it ignores `thinking`, `signature_delta`, `input_json_delta`, `assistant`, `status` and `rate_limit_event` lines, and the streamed text equals the result's final text.
- **The recording caught a 0038 bug.** `list_materias` fails its own output schema: the client rejects `atividades_sincronizadas_em` and `trabalhos_sincronizados_em` (sometimes `aulas_sincronizadas_em`) as not `date-time`. The tool error reached the model, which explained it. The fixture keeps that error, and it shows a tool error that is not a refusal.
- **The pane reads availability when it shows a matéria**, so `app.mcp_url` must be set before the first screen. 0038 binds the port in `run()`, before `run_async`, so it is. The tests set it at launch: setting it later left `i` disabled until the next repaint.
- **`launched_app` moved to `tests/launched.py`**, since the matérias chat test is its second caller.
- **The first pane did not read as a tutor.** The student tried it and found loose text under the média: `você Bom dia`, a bold `tutor`, the reply across the whole width, an input that was only a placeholder. The pane became a panel of its own:
  - a rounded border titled `Tutor · <matéria>` (`Tutor · questão N` in the prova, `Tutor · <atividade>` on its summary), a row away from the table, accented while focus is inside;
  - the student's messages compact and muted, right-aligned on a `$boost` block at most 70% wide; the tutor's behind an `outer $accent` bar, 90 columns at most, rendered by Textual's `Markdown` widget and fed with `append` as chunks arrive, so headings, lists, quotes and inline code take the theme's colours;
  - one animated line under the reply for what the tutor is doing: `pensando…` before the first chunk, `consultando as aulas…` (each MCP tool has its own phrase, the raw name for an unknown one) and `escrevendo…` while text streams; it is the `Turn.activity` the conversation already kept, now set on every state;
  - an empty chat shows the tutor's greeting and two or three things to ask, written per page in `cli/components/chat/introduction.py`;
  - the input sits in a rounded box with a `›` mark and the placeholder `Pergunte ao tutor…`.
- **The chat needs 10 rows, not 6.** The border and the input's box take five, so 10 leaves five for the conversation. On a `-short` terminal it keeps 6: the input loses its box and the pane its top margin. `min_rows` counts the pane's own margin.
- **The log only sticks to the bottom once there is a conversation.** Textual's `anchor()` also pushes short content to the bottom, which put the greeting at the foot of an empty box; the log anchors when the first turn is painted.

## Why this was rejected
The student tried the pane and asked for one tutor for the whole app that is literally Claude Code's terminal, not a chat the app rebuilds screen by screen. [0040](../done/0040-claude-terminal.md) replaced it before any of it was committed: `i` opens the student's interactive Claude Code beside the app, and the screen reaches the model through the MCP tool `get_current_screen`. What of this spec survived is listed in 0040.
