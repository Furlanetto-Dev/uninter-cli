---
name: novo-plano
description: "Creates a new spec in specs/pending with the house header, numbering and structure. Use when the user asks for a plan, a spec, an ADR or a decision document for an app in this repo."
---

You are going to write a new spec. In this repo, "plan", "spec" and "decision document" are the same thing: a markdown file in `specs/`.

# Where the file goes

`specs/pending/NNNN-<slug>.md`

- **Always `pending`.** `done` is for a spec whose work is already finished; a new spec is never born there.
- `NNNN` is the next free number, counting `done` **and** `pending` together, with 4 digits:
  `ls specs/done specs/pending | grep -oE '^[0-9]{4}' | sort -n | tail -1`
- **A continuation of an existing spec uses `NNNN.M`**, like `0005.1`. It is for what was left out of spec NNNN and depends on it: the number says whose child it is. A new subject gets a whole number.
- `<slug>` is the title in kebab-case, unaccented and without the article: `testing-strategy`, not `the-testing-strategy`.

# The header

YAML frontmatter in the skill format, with five required fields, in this order:

```yaml
---
name: <slug, same as the file name, without the NNNN>
description: <see below>
projects: [<see below>]
status: pending
created_at: <today, ISO, via `date +%F`>
---
```

- `name` matches the file slug. No number, no accents.
- `projects` is an array of the parts the spec touches. Valid values: `crawler`, `api`, `frontend` and `all`. Use the order the data flows in — `crawler`, then `api`, then `frontend`. `all` is exclusive: either the spec touches everything, or you list the parts; never both.
- `status` has three values. `pending`: not executed yet. `awaiting-review`: executed, verified, not committed; the file stays in `pending/`. `done`: implementation committed, file in `done/`. Never `aceito`/`proposto`. The directory only knows executed-and-committed from everything else, so the status carries the middle state.
- `created_at` comes from `date +%F`. Never guess the date.
- **No `Status:` and no date in the body.** The header is the only source.

## How to choose the projects

List what the spec **changes**, not its subject. A spec about the interface that migrates the whole app to async touches all three, even if the title only talks about the screen.

- `crawler` — AVA requests and DTOs, HTTP session
- `api` — entities, repositories, services, database
- `frontend` — the TUI in `cli/`
- `all` — touches all three; alone in the array

## The description is a trigger, not a summary

Write when to **open** the spec, not just what it contains. One sentence with the content, another starting with "Read before...". That is what makes the description useful to whoever (or whatever) is deciding whether it needs to read the file.

Good: `Crawler design decisions — x-time cookie, aproveitamento-or-current rule, 404 indistinguishable from empty. Read before touching request, dto or oferta resolution.`

Bad: `A document about the crawler.`

# The body structure

Start from the [template](./template.md). Not every section is required, but the order is:

1. `# Title` in prose, accents included — it is not the slug.
2. `## TL;DR`, as a list: one line per change, up to five. Whoever reads only this knows what the spec does.
3. One or two sentences saying **why the spec exists**: the problem, and what changes once it is executed. Link [CONTEXT.md](../../CONTEXT.md) and the related specs here.
4. **Observed behaviour**, when an external system is involved. One line per fact, with what proves it. Mark what is inference.
5. **Decisions**, each in a `###` whose title is the decision stated, not the subject. `### The database stores only the fields the screen uses`, not `### About the fields`.
6. **Rejected**, as a list. One line per item: the alternative and why not.

## Relative links

From `specs/pending/` the repo root is two levels up:

- project description: `[CONTEXT.md](../../CONTEXT.md)`
- sibling spec in done: `[0001](../done/0001-<slug>.md)`

Check that they resolve before finishing.

# The size yardstick

**More than 70 lines of text is a sign of padding.** It is a yardstick, not a law: the validator counts only what is outside fenced blocks and warns. If the spec you are writing shows up in the warning, reread it looking for a repeated idea; if there is none, the size is justified.

- There is no minimum text per paragraph, section or decision. If the idea fits in one line, it is one line.
- A `mermaid` diagram that replaces paragraphs is welcome — flow, layers, states, layout. It shows more with less text, and does not count toward the yardstick.
- A decision is the what and the why, in one or two sentences. Cost only goes in if it is not obvious.
- A rejected item is the alternative and the reason, in one line.
- An observed fact is the fact and the proof, in one line. Only what changes a decision goes in.
- No introduction that repeats the title, no rhetoric, no code the implementation will rewrite. Code only when the name or the signature is the decision.
- It is not a telegram: whole sentences, in plain English. Concision is cutting repeated ideas, not articles and verbs.

# The quality yardstick

- **Decide, do not enumerate.** A spec records the choice and the reason. If you are still weighing alternatives, ask the user instead of listing the options in the file — the place for a discarded option is the Rejected section, with the why.
- **State what was verified and mark the rest.** If you did not measure it, write that it is inference.
- **No frills.** No "this document aims to", no repeating the title in the first paragraph.
- Write in English, in the tone of the existing specs, keeping the domain nouns in Portuguese: matéria, atividade, trabalho, entrega, etiqueta, etapa, oferta, aproveitamento, média, RU, AVA. The file slug and the title are English too; the slug is kebab-case, with the domain nouns unaccented (`materias`, not `matérias`). The tone is the existing specs'; the size is not — they predate the size yardstick.

# Before finishing

Run the validation:

```bash
python3 - <<'PY'
import re
from datetime import date
from pathlib import Path

REQUIRED = ("name", "description", "projects", "status", "created_at")
PROJETOS_VALIDOS = {"crawler", "api", "frontend", "all"}
LIMITE_DE_LINHAS = 70


def projetos_invalidos(bruto):
    if not (bruto.startswith("[") and bruto.endswith("]")):
        return ["projects is not an array [a, b]"]
    itens = [i.strip() for i in bruto[1:-1].split(",") if i.strip()]
    if not itens:
        return ["projects empty"]
    fora = [i for i in itens if i not in PROJETOS_VALIDOS]
    if fora:
        return [f"projects invalid: {fora}"]
    if "all" in itens and len(itens) > 1:
        return ["projects: 'all' does not go with others"]
    return []


def linhas_de_texto(text):
    dentro = False
    total = 0
    for linha in text.splitlines():
        if linha.startswith("```"):
            dentro = not dentro
            continue
        if not dentro:
            total += 1
    return total


ok = True
for p in sorted(Path("specs").glob("*/*.md")):
    text = p.read_text()
    linhas = linhas_de_texto(text)
    if p.parent.name == "pending" and linhas > LIMITE_DE_LINHAS:
        print(f"{p}: WARNING {linhas} lines of text, above {LIMITE_DE_LINHAS}")
    if p.parent.name == "pending" and "## TL;DR" not in text:
        print(f"{p}: WARNING no ## TL;DR")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        print(f"{p}: FRONTMATTER MISSING"); ok = False; continue
    fields = dict(l.split(": ", 1) for l in m.group(1).split("\n") if ": " in l)
    for problema in (
        [f"missing {k}" for k in REQUIRED if k not in fields]
        + ([f"name {fields.get('name')!r} != file slug"]
           if fields.get("name") != re.sub(r"^\d+(\.\d+)?-", "", p.stem) else [])
        + ([f"status {fields.get('status')!r} does not fit folder {p.parent.name!r}"]
           if fields.get("status") not in ({"done"} if p.parent.name == "done" else {"pending", "awaiting-review"}) else [])
        + ([f"Status:/date in the body"] if re.search(r"^Status:|^(Aceito|Proposto) em", text, re.M) else [])
        + projetos_invalidos(fields.get("projects", ""))
    ):
        print(f"{p}: {problema}"); ok = False
    try:
        date.fromisoformat(fields.get("created_at", ""))
    except ValueError:
        print(f"{p}: created_at invalid"); ok = False
    for label, target in re.findall(r"\[([^\]]+)\]\((\.[^)]+)\)", text):
        if not (p.parent / target).resolve().exists():
            print(f"{p}: broken link -> {target}"); ok = False
print("all consistent" if ok else "PROBLEMS FOUND")
PY
```

A warning on the spec you wrote is yours: add the TL;DR, and cut repeated ideas — or conclude that the size is justified. A warning on an old spec waits until that spec is touched.

Then tell the user the path of the file created. Do not commit unless they ask.

# After executing

Execution done and verified, but not committed: set `status: awaiting-review` in the header and keep the file in `pending/`. Add the `## What execution corrected` section then. Do not move the file — only a commit does that.

# Promoting to done

When the implementation is committed, moving is not enough — `status` and directory must move together:

```bash
git mv specs/pending/NNNN-<slug>.md specs/done/
sed -i 's/^status: awaiting-review$/status: done/' specs/done/NNNN-<slug>.md
```

And fix the relative links of whatever pointed at the spec in `pending`.
