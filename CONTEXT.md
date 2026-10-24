# Uninter

Mirrors locally what Uninter's AVA (Univirtus) knows about a student's academic life, for lookup outside the browser.

The AVA is a slow SPA: seeing a grade means logging in, waiting for it to load and navigating matéria by matéria. This project fetches that data when the student asks, stores the result on their machine and shows it in a terminal, where lookup is immediate and does not depend on an open session.

It is for personal use, by a single student. Credentials live in a `.env` that is never committed, there is no server and no multi-user support, and nothing leaves the machine of whoever is looking.

The one exception is the tutor. `i` opens the student's own Claude Code in a terminal beside the app, and the app's MCP server hands it the sala's data on request: matérias, notas, aulas and their transcrições, and what is on screen, the current questão of a prova included. That data reaches the model through the student's own Claude subscription.
