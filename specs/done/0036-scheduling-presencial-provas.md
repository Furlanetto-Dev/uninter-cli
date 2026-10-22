---
name: scheduling-presencial-provas
description: "`a` on a presencial prova opens a calendar enabled only on days the AVA has free horários, with the cursor day's horários beside it; enter books one through AgendamentoUsuario, `x` cancels after a confirmation, and the atividades sync mirrors the agendamentos so the tree reads `Agendada 29/10 15:00`. Read before touching the agendamento requests, the Agendamento table, the datepicker, the ids taken from the login, or what enter does on a presencial row."
projects: [crawler, api, frontend]
status: done
created_at: 2026-10-22
---

# Scheduling presencial provas

## TL;DR
- `a`, or enter, on a presencial prova awaiting start opens `ChooseHorario`: the [datepicker](../datepicker.sketch.md) POC enabled only on days with a free horário, and that day's horários beside it. Enter on a horário books it.
- Booking sends the browser's `POST pap/AgendamentoUsuario`. `x` on a booked prova asks `ConfirmCancel` and sends `PUT …/Cancelar`.
- The atividades sync also fetches the agendamentos of a matéria with a presencial prova open to booking, into a new `Agendamento` table, and the tree's Situação reads `Agendada 29/10 15:00`.
- The login keeps `idUsuario` and `idGrupoEstrutura`, so five of the seven captured requests are sent and the other two are not needed.

Booking a presencial prova means the AVA's agendamento screen: three dropdowns and a grid of hours, prova by prova. With this spec it is one key on the row already on screen, and the date stays next to the prova afterwards. Context in [CONTEXT.md](../../CONTEXT.md); the presencial mark is [0013.1](../done/0013.1-avaliacao-presencial.md).

## Observed behaviour
The student captured the seven requests in `uninter-endpoints/agendamentos/` on 2026-10-22, booking SGBD's Prova Objetiva (Regular) for 29/10 at 15:00 and cancelling it. The GETs were sent again that day; the POST and the PUT never were.
- The login's `usuario` carries `idUsuario` (3316075) and `idGrupoEstrutura` (339). `GetGrupoEstrutura` answers the same 339, `PAP SÃO JOSE DO RIO PRETO - SP`, for POO's oferta and SGBD's.
- `idAvaliacao` is the atividade id (2523475, SGBD's presencial Prova Objetiva (Regular)), and `idSalaVirtualOferta` is the matéria's `oferta_atual` (899306), not its aproveitamento (1195122).
- `GetAvaliacaoTipo` lists only that Regular, the one open now. `GetHorariosDisponiveis` for SGBD's Segunda Chamada, whose window opens 09/11, answers the AVA's 404, `não encontrou registros`.
- `GetLaboratorio` answers one lab, `13263 Laboratório de Informática`, for every prova tried. Several labs were never seen.
- `GetHorariosDisponiveis` answers 63 one-hour slots, weekdays from 22/10 to 30/10, each with `idLaboratorioAgendaDia` (one per day), `qtdComputadores` 6, `qtdAgendamentos` and `permiteAgendamento`. The flag is false for past slots, full ones and every 10:00 and 17:00 slot (inference: those end after the shift's `dataMaximaAgendamento`, 10:30 or 17:30).
- The POST repeats `idAvaliacao` as `idAvaliacaoTipo`, takes the slot's `idLaboratorioAgendaDia`, `dataInicio` and `dataFim`, and sends `fusoAplicado=-3`, where the GET sent `null`. Inference: -3 is Brasília.
- `Paginacao?filtro=196,1,{oferta}` lists the oferta's agendamentos, cancelled ones included (`ativo: "Cancelado"`, still `podeCancelar: true`); POO's, with none, answers the 404. No avaliação id comes back: `nomeAvaliacao` equals `Atividade.nome` exactly.
- Not seen: what `196,1` mean, the `ativo` of a live agendamento, and the bodies the POST and the PUT answer.

## Decisions

### One modal holds the calendar and the day's horários
`ChooseHorario` puts the POC's `DatePicker` beside the horários of the cursor day, so walking the days shows their hours. A day is enabled when it has a slot with `permiteAgendamento`, and the cursor opens on the first one. Enter on a day moves to its list, enter on a horário books it, escape steps back. The POC's `PickDate` modal goes: choosing a day before seeing its hours is the step this layout removes.

### The app answers the browser's dropdowns itself
The atividade is the row, the oferta is `oferta_atual`, polo and usuário come from the login, and the lab is every lab `GetLaboratorio` returns, their horários merged and labelled with the lab only when there is more than one. The student picks the day and the hour, nothing else.

### Enter on a horário books it with no confirmation
The list already names the prova, the day, the hour and the free seats, and an agendamento can be cancelled. Cancelling asks first, through `ConfirmCancel` focused on NÃO, because the slot may not come back.

### The sync mirrors the agendamentos; booking only enqueues it
`AtividadeSyncService` fetches `Paginacao` after the atividades when the matéria has a presencial prova awaiting start within its prazo, and replaces its rows in `Agendamento`, matched to the atividade by name. A failure there keeps the stored rows. Booking and cancelling send their request and enqueue that sync, because the queue shares the database session, as [0033](../done/0033-hand-in-a-prova.md) found.

### The tree shows the live agendamento in Situação
An agendamento is live when it is not cancelled and has not ended. A presencial prova awaiting start with one reads `Agendada 29/10 15:00` in the presencial colour. `a` shows only without one, `x` only when the AVA says `podeCancelar`, and enter on a booked prova toasts the day, the hour, the lab and the polo.

### A refusal is the AVA's `exception`
The POST and the PUT fail on an HTTP error or a non-null `exception`, the envelope every captured response carries, and the student reads that `exception` or the `erro` of an error body.

### The fixture books its own prova
`MockedAgendamentos` answers the lab, a week of slots, the POST, `Paginacao` and the cancel for the mocked oferta, so dev mode runs the whole flow. A real id passes through to the AVA, as in [0032](../done/0032-real-prova-source.md).

## Rejected
- **Sending `GetGrupoEstrutura` and `GetAvaliacaoTipo`.** The login has the polo, the row has the atividade, and a prova not open yet gets no horários anyway.
- **Booking the day's first free slot without asking.** The hour is the student's; the list's cursor starts on the first one.
- **A lab picker.** One lab was seen, and merging the labs' slots covers several without a step.
- **Writing the agendamento from the POST's answer.** That body was never seen, and the queue shares the session.
- **A column for the agendamento.** Situação has nothing better to say about a prova awaiting start.
- **Rescheduling in one key.** Cancel and book again does it, with the confirmation in between.
- **The datepicker in `cli/components/`.** It has one caller; it moves there with the second, per the `nova-pagina` skill.

## What execution corrected
- **The tree picks the live agendamento itself.** It takes the matéria's stored rows and applies `live_agendamentos`, so the rule is tested where the student sees it.
- **One envelope, one form sender.** `ReplyDTO` moved to `crawler/dto.py` beside a new `ErroDTO`, since agendamentos read the same envelope as provas; `put` and the new `post` share one sender in `AvaSession`.
- **The POC's `PickDate` and `datepicker_demo.py` are gone.** `DatePicker` lives in `pages/agendamento/components/` and gained `Highlighted`, posted on every cursor move.
- **A booked row costs the name three characters.** `Agendada 22/10 15:00` is wider than `Aguardando início`, so at 112 columns the mocked prova reads `Prova Objetiva (Mo… presencial`. Names were already truncated at that width.
- **The mock calls a live agendamento `Agendado`.** That is a guess; the app only ever tests for `Cancelado`.
- Verified offline, in dev mode with the login answered locally: the mocked Prova Objetiva was booked at 15:00 and cancelled. The requests went `Paginacao`, `GetLaboratorio`, `GetHorariosDisponiveis`, POST, `Paginacao`, `PUT Cancelar`, `Paginacao`, all answered by the fake AVA, and the POST carried the capture's fields in its order and encoding.
- **Both login ids are optional.** The tests of 0024.1 and 0035 fake a login with only `nome` and `time`, and a field only agendamento needs must not fail a login: a missing id fails the agendamento request instead, saying which.
- **Only a matéria with a presencial atividade reads `Agendamento`.** Showing any other matéria costs no extra query.
- **0035's `r` test waits for the sync before closing.** It closed the database under a sync still writing, about one run in ten with this change on top; it now finishes the workers first, as the opening test does.
- Tests: 14 on the datepicker (the POC's, moved), 11 on `ChooseHorario`, 5 on `ConfirmCancel`, 16 on the tree and 6 on the formatters. Rebased onto 0035, `pdm run test` passes, 417 tests; `uvx pyright` and `pdm run ruff` are clean.
