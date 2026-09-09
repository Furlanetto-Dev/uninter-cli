# Working in this repo

- Never commit unless the user asks for it in the current message. Finishing a spec, passing checks, or a "commit" request earlier in the session is not permission. Leave the changes in the working tree and say what is ready to commit.
- Never push unless the user asks for it.
- A spec only moves to `specs/done/` after its implementation is committed. Executed but uncommitted work stays in `pending/`, with its execution notes, until the user asks for the commit.
- When a spec has been executed but its implementation is not committed yet, set its `status` to `awaiting-review` and leave the file in `pending/`. The commit is what moves it to `done/`.
