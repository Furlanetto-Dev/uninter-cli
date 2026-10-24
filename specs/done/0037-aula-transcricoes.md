---
name: aula-transcricoes
description: The transcrição of each aula — WebVTT per video, found through the rota's public index.json or straight from an mp4, fetched on demand block by block by TranscricaoService.of_aula and stored as plain text in its own table for the MCP and the chat. Read before touching how transcrições are fetched, parsed or stored, the service the MCP calls for them, or the FakeAva's text answers.
projects: [crawler, api]
status: done
created_at: 2026-10-24
---

# Aula transcrições

## TL;DR
- `TranscricaoService.of_aula(aula) -> list[Transcricao]` returns what is stored and fetches only the blocks still missing; it is the call the MCP of 0038 makes.
- A material whose URL carries `c=` is read through its public `index.json`, one WebVTT per block; one whose URL is an mp4 is read straight from it.
- Requests go through a plain client, outside `AvaSession`: nothing here needs the AVA login.
- Each block becomes one `Transcricao` row of plain text, in a table the aulas sync never touches.
- The FakeAva learns to answer text, and serves an `index.json` and the VTTs for the mocked rota and video.

The MCP of 0038 `mcp-server` and the chat need the content of the aulas, not only their links ([0034](../done/0034-aulas-tab.md)); the AVA holds that content as the transcrição of each video ([CONTEXT.md](../../CONTEXT.md)).

## Observed behaviour
- A transcrição is a WebVTT whose URL is the mp4's with `.mp4` replaced by `_pt_BR.vtt`, the rule in the newrota bundle. Proof: Lince, `uninter-endpoints/aulas/get-video-transcricao.txt`.
- The VTT is public: no cookie, no `x-time`, `200 text/vtt`, UTF-8 with no charset declared. Proof: same capture.
- A rota's `Material.url` carries `c=/gradNova/<ano>/<curso>/<disciplina>/a<N>`, HTML-escaped (`&amp;`); `https://conteudosdigitais.uninter.com/materiais/aulas<c>/index.json` is public; `aula.midia` is an object keyed `"1"`..`"6"`, not a list, each `{titulo, url}` holding one mp4 per block (Conversa Inicial, Tema 1..5), beside a top-level `video_completo`. Proof: `get-rota-index.txt` and `get-rota-index.response.json`, POO a1 and Banco de Dados a1, 7/7 VTTs answered 200.
- The newrota hash and `GetROA` are not needed for any of it. Proof: the two captures above, sent without them.
- A videoaula's `Material.url` is already the mp4; the rule gives its VTT. Proof: Lince, one videoaula.
- The aula prática is the "Laboratorio Virtual" item: `classificacaoTipo` `rota`, link an mp4 with `?hash`, no `c`. The AVA plays the raw mp4 in an iframe with no `<track>`, and `_pt_BR.vtt` and `_en_US.vtt` answer 404 with or without the query: it has no transcrição. Proof: Lince, `GetROA` and `VisualizacaoObjeto.js`, A07..A12.
- The Univirtus VOD is the "Video Restrito" item: `classificacaoTipo` `video`, link a CloudFront-signed mp4 (`?Policy=..&amp;Signature=..&amp;Key-Pair-Id=..`, tied to the student's IP, valid for hours). The path with the query dropped and the rule applied answers 200, public, `spk` shape; the AVA's `videoplayer.js` does the same replace. Proof: `get-univirtus-vod-transcricao.txt`, `get-aula-detalhes-anexos.univirtus-vod.response.json`, POO Aula 1.
- Inference: that signed link is what `MaterialDTO.link` stores as `Material.url`, by reading `dto.py`.
- The VTT comes in two shapes, both `WEBVTT` plus a blank line with CRLF ends. `spk`: `HH:MM:SS.mmm`, a ` line:-1` setting, each cue line opened by `<v.Male.spk1 Speaker1>` with no `</v>` and closed by a space. `plain`: `H:MM:SS.mmm`, no setting, no voice. Proof: `get-video-transcricao.spk.vtt` and `.plain.vtt`.
- Cues break mid-sentence, and `>> ` marks a change of speaker: at the start of the cue in `plain`, right after the voice tag in `spk` (`<v.Male.spk1 Speaker1>>> Olá`). Proof: the same two files.
- `index.json` carries the professor's CPF in `aula.professores`.
- `conteudosdigitais` guards `index.json` by Referer: without one from its own domain it answers `200 text/html`, a "Conteúdo bloqueado" page, for every rota; with `https://conteudosdigitais.uninter.com/libraries/newrota/` it answers the JSON. The VTT host needs no Referer. Proof: Lince, POO a1 and Banco de Dados a1, and the lead's run that hit the block.
- Inference: `video_completo` is the blocks back to back; nobody compared the texts.

## Decisions

### The service is the contract with the MCP
```python
class TranscricaoService:
    async def of_aula(self, aula: Aula) -> list[Transcricao]: ...
```
Agreed with Tomada (0038): an entity in, a list out, ordered by atividade and block, an empty list meaning no transcrição. `httpx.HTTPError` propagates and becomes a tool error there; the materiais committed before it stay.

### The service is built per call, over the caller's session
`TranscricaoService(session=, request=, repository=TranscricaoRepository(session), aulas=AulaRepository(session))` is assembled by whoever calls, on the `AsyncSession` of that call; `main.py` holds no service, since its session belongs to the queue. Only the `TranscricaoRequest` over `public_http` lives as long as the process, and it is what `main.py` hands the MCP.

### A material is read by its URL, not by its tipo
After `html.unescape`, a URL with `c=` goes through `index.json`; a URL whose path ends in `.mp4` is one video, its VTT built from the path with the query dropped, which serves the videoaula and the signed VOD alike; anything else, arquivos included, has no transcrição, and so has a rota whose `index.json` does not parse. The `index.json` request carries the newrota's Referer. The Laboratorio Virtual, a rota with an mp4 URL, is then a 404, not a parse error.

### Fetched means every block, not the material
`Transcricao` is `material_id`, `ordem`, `titulo`, `texto`, `blocos`, `buscada_em`, keyed `(material_id, ordem)`, where `blocos` is how many videos the source announced (1 for an mp4). A material with fewer rows than `blocos`, or none, is fetched again and only its missing `ordem` are written, so a block that answered 404 is asked again next call. There is no foreign key into `Material`, so `AulaRepository.replace` on a re-sync leaves the transcrições alone: the ids are the AVA's.

### A rota is read by its blocks, with `video_completo` as fallback
Each block's title is what lets the chat cite "Tema 3": blocks follow their `midia` keys read as numbers, titled `"<atividade> · <bloco>"`; an mp4 is titled with its atividade name. `video_completo` is skipped so the text is not stored twice, and read as the single block only when `midia` is empty.

### The text is stored plain
The parser decodes with `utf-8-sig`, replacing an invalid byte, splits on blank lines, anchors each cue on its `-->` line and drops what precedes it, so cue ids and `NOTE`/`STYLE` blocks vanish. It strips `<v …>` before looking for `>> `, joins the lines with spaces and collapses whitespace, starting a paragraph at each `>> `. The chat reads prose; timings would only cost tokens.

### Fetching needs no AVA session
Both hosts answer without a cookie, so the MCP can read a transcrição while the app holds the single AVA session, and that session is never at risk.

### The plain client is the AVA client without the AVA, over its own FakeAva
`public_client(transport, log)` sits beside `ava_client` in `crawler/session.py`: same timeout and request-log hooks, no `base_url` and none of the AVA's headers. `main.py` opens it for the whole `run()` over a second `FakeAva` wrapping its own `AsyncHTTPTransport`, because a client closes its transport on exit; both FakeAvas take their answers from the same `MockedAva` instance. The MCP's stdio entry builds the same pair.

### The FakeAva answers text
`crawler/mock.py` only answers JSON or a PNG; it gains a third answer, a body with its content type, which `api/mock/aulas.py` uses for an `index.json` of the mocked rota's `c` and a `text/vtt` per mp4, one in each shape. Dev mode and the MCP then exercise the whole path offline.

### Two fetches of the same aula end in an upsert, not an error
Rows are written with SQLite's `INSERT … ON CONFLICT (material_id, ordem) DO UPDATE`, so a chat and a TUI asking at once both fetch and the last write wins with the same text. It holds across sessions and processes, where a lock would not.

### The CPF stays out of the database and out of the request history
Nothing here becomes a captura, and the DTO reads `aula.midia` and `video_completo`, never `aula.professores`. The request log keeps the `index.json` request, URL and status but replaces its body with the `<…, N bytes>` note it already uses for binaries: the history exists to be copied into captures and bug reports, and a CPF there is one paste away from leaving the machine.

## Tests
An exception to `novo-teste`'s "only `cli/` is tested", since 0037 has no screen: `tests/crawler/` and `tests/api/` mirror `src/`, asserting only what comes out (text, rows, requests that reached the transport), with unique basenames.
- `test_vtt_text.py`: the parser over the two whole sample VTTs, no timing, tag or setting left, a paragraph at each `>> ` in both shapes, single spaces; a cue id and a `NOTE` block; a BOM.
- `test_rota_index.py`: the DTO over `get-rota-index.response.json`, blocks in numeric key order with a `"10"` key added, no professor in what it returns; an empty `midia` yields `video_completo`.
- `test_transcricao_service.py`, over a temporary database and `httpx.MockTransport`: a second `of_aula` sends nothing; a rota with one block 404 stores the rest and the next call asks only that block; two concurrent calls return without error and leave one row per block; an mp4 with `?hash` and a signed VOD link with `&amp;` both ask for the VTT without the query; an `index.json` 404 gives `[]`.
- `test_mocked_transcricoes.py`: `of_aula` on the mocked aula through the FakeAva over a transport that fails every request returns both transcrições, so nothing escapes to the internet, the leak [0028](../done/0028-fake-ava.md) recorded.

## Rejected
- **Downloading the mp4 and transcribing it (speech-to-text).** The user refused it, and the AVA already publishes the text as a VTT.
- **Fetching every transcrição at the aulas sync.** About a dozen requests per aula for text read only when the chat asks.
- **A lock per aula.** It only serialises callers in one process, and the per-call service has no shared place to keep it.
- **Reusing `ava_client`'s `http`.** It would send the AVA's referer and `x-requested-with` to the CDN, and a relative URL would land on the AVA.
- **Logging the `index.json` body and recording the risk.** The debug history is built for copying out, and the CPF is a third party's.
- **Storing the raw VTT.** Nobody reads the timings, and both shapes would leak into every reader.
- **Remembering the Laboratorio Virtual's 404.** The AVA has no transcrição for it today, but the retry is one public request per call, and a transcrição added later shows up with no change here.

## What execution corrected
- **`of_aula` takes only the aula.** The matéria was never read: atividades are found by the aula's id. Tomada was told.
- **`ArquivoRequest` moved onto `public_http`.** The repositório download is public too, and it gives the client a user in this floor; 0038 adds the `TranscricaoRequest`.
- **`index.json` is answered through the FakeAva's JSON payload;** only the VTT needed the new document answer.
- **The request log withholds by host.** `conteudosdigitais.uninter.com` serves the app nothing but `index.json`.
- **A block's `ordem` is its `midia` key,** not its position, so a block missing once keeps its number on the retry.
- **The mocked seed also clears the mocked transcrições,** with the other rows of negative ids.
- **`public_client` sends only the browser's user-agent.**
- **Each material is upserted and committed as its blocks arrive,** not once at the end, so a failure on one material keeps the ones fetched before it in the same call (Ferrolho).
- **An invalid byte in a VTT becomes `�`** instead of a `UnicodeDecodeError` (Ferrolho).
- **The `index.json` request sends the newrota's Referer.** The public client sent only a user-agent, so every real rota got the block page; Banco de Dados a1 now yields its 6 blocks plus the videoaula.
- **A blocked or unparseable `index.json` counts as no transcrição** for that material, retried next call like a 404, instead of a `ValidationError` that took down the whole aula. It stays silent to the MCP; the request history still shows the `200` and its `text/html` type.
