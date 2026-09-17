---
name: novo-sketch
description: "Writes a sketch spec: a few lines saying what we need and why, before anyone has decided how. Use when the user asks for a sketch, a sketch spec or a .sketch.md file."
---

A sketch is the need, written down before anyone has decided how to meet it.

> We need a config page to help the user configure the CLI and enable us to deliver settings faster.

That is a whole sketch. It is not a small spec: a spec decides, a sketch does not.

# Where it goes

`specs/<slug>.sketch.md`.

No number: numbers belong to specs, and a sketch may never become one. The `specs/` root, not `pending/` — the [novo-plano](../novo-plano/SKILL.md) validator only walks the folders under `specs/`, so a file at its root is never seen.

# The rules

- **Under 20 lines.** Most are three.
- **No frontmatter, no section headers.** A `#` title and prose.
- **Assume nothing.** No key, no file path, no class name, no directory, no widget, no library, no decision. If the line says "we should", "it would be", or names something that does not exist yet, delete it.
- **Do not go read the codebase for it.** A sketch is what someone already knows. A fact about how things are today goes in only when it is the reason the sketch exists, and one line is the budget.
- **An open question is a sentence, not a section.** "Who calls it first is still open."

# The shape

```markdown
# Config page

We need a config page to help the user configure the CLI and enable us to deliver settings faster.

Today the settings are split between the command palette, config.json and .env, and no screen shows what is on.
```

# After

A sketch becomes a spec through [novo-plano](../novo-plano/SKILL.md): that is where the number, the header, the decisions and the `pending/` folder come in. Deleting the sketch then is fine — the spec replaces it.

Tell the user the path of the file. Do not commit unless they ask.
