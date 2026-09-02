---
name: estrategia-de-testes
description: Como testar o crawler — mapa de risco, as oito camadas de teste, fixtures sintéticas e reais, determinismo de relógio e de render, e os quatro defeitos conhecidos a corrigir com teste vermelho primeiro. Ler antes de escrever qualquer teste neste app.
projects: [all]
status: pending
created_at: 2026-09-02
---

# Estratégia de testes do crawler

O projeto não tem nenhum teste. A refatoração para camadas criou as costuras que faltavam — transporte HTTP injetado, banco por caminho, relógio como parâmetro — e a [0004](../done/0004-tui-em-textual.md) acrescenta a que faltava na ponta: os services chegam à App por construtor, então a interface inteira pode ser exercitada com falsos. Este documento decide o que testar, com o quê, e em que ordem.

O vocabulário está em [CONTEXT.md](../../../../CONTEXT.md), as decisões de desenho em [0001](../done/0001-crawler-de-atividades-do-ava.md), as camadas em [0003](../done/0003-camadas-crawler-api-cli.md) e a interface em [0004](../done/0004-tui-em-textual.md). **Nada aqui é escrito antes da 0004 ser executada**: ela muda toda assinatura de `fetch`, `sync` e repository para `async`, e testes escritos antes nasceriam para reescrever.

## O mapa de risco

A lista de testes não sai de cobertura, sai daqui. Ordenado por dano × probabilidade:

1. **Drift de alias no DTO.** O AVA renomeia um campo e o dado vira `None` sem erro nenhum: os DTOs usam `extra="ignore"` e quase todo campo interessante é opcional. Sintoma é nota faltando na tela, meses depois. É o único risco que nenhum teste sintético pega.
2. **404 transitório destrói o cache.** `AtividadeRequest.fetch` devolve `[]` em 404, `replace` apaga o que havia, `mark_synced` marca como fresco. Falha de rede vira "matéria sem atividade, sincronizada agora".
3. **Regra da oferta errada.** `aproveitamento ?? atual` decide se vem dado ou 404. Errar aqui esvazia matérias silenciosamente.
4. **Carimbo perdido num resync.** Se o dicionário em `MateriaRepository.save` quebrar, todo "Sincronizar matérias" zera a idade das 26 e força refetch.
5. **O guarda de sync cede e duas corrotinas tocam a mesma `AsyncSession`.** Novo com a 0004. A tela não-bloqueante abre três caminhos para dois syncs simultâneos, e a `AsyncSession` não aceita operação concorrente: o sintoma é exceção na cara do usuário, e no primeiro acesso da sessão também um POST de login duplicado. É o único risco cujo teste mora na camada da interface.
6. **Média e peso lançado errados.** É a única aritmética do projeto, e vai direto para a cara do usuário.
7. **Ordem das atividades trocada.** `posicao` é a única ordenação existente; o AVA não garante nenhuma.

## Ferramental

`pytest` mais `pytest-asyncio`, e nada além. O `asyncio` deixou de ser opcional quando a 0004 tornou o app inteiro async: `fetch`, `sync`, os repositories e o `run_test()` do Textual são todos corrotinas. Com `asyncio_mode = "auto"` isso não aparece em teste nenhum além do `async def`.

**Nada de `pytest-httpx` nem `respx`**: `AvaSession` recebe o client por construtor, então o `httpx.MockTransport` que já vem no httpx basta. Verificado contra um `AsyncClient` de verdade, e o handler do transporte pode continuar **síncrono** — as fixtures não mudam de forma por causa do async.

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = ["rede: exige credenciais e acesso ao AVA (desabilitado por padrão)"]
addopts = "-m 'not rede'"

[tool.pyright]
include = ["src", "tests"]

[tool.pdm.scripts]
test = {cmd = "pytest", help = "Roda a suíte, sem os testes de rede"}
```

Testes entram no `include` do pyright: um falso que divergiu da interface real é um teste que mente — e com tudo async, o `await` faltando é justamente o erro que passa em silêncio no runtime.

## Onde os testes moram

Espelhando os pacotes de `src/`, para que o arquivo de teste seja óbvio a partir do arquivo de código:

```
tests/
  conftest.py             sessao em tmp_path, ava falso, fabricas de Materia/Atividade
  crawler/                test_session
    materias/             test_dto  test_request
    atividades/           test_dto  test_request
  api/
    materias/             test_entity  test_repository  test_service
    atividades/           test_entity  test_media  test_repository  test_service
  cli/                    test_format  test_atividades  test_app
  e2e/                    test_fluxo
  contract/               test_dtos_reais  test_smoke (marker rede)
  fixtures/               login.json  materias.json  atividades-*.json
  golden/                 materia-renderizada.txt
```

`cli/test_atividades` cobre `build_table`, que continua devolvendo um `rich.Table`; `cli/test_app` é o Pilot com services falsos. `test_render` desapareceu junto com o módulo.

## As camadas, e o que cada uma prova

### 1. Funções puras — sem fixture, sem mock

`cli/format.py` não importa nada e `api/atividades/media.py` importa só a entity. São os testes mais baratos do projeto e cobrem o risco 6.

- `format_number`: `None → "—"`, `0.0 → "0"`, `8.0 → "8"`, `7.5 → "7,5"`, `33.33 → "33,3"`, negativo
- `short_periodo`: `None → ""`, e que o corte no primeiro `" - "` descarta a UTA
- `humanize_age`: `None`, agora, 59s, 1h, 23h, 1d, 45d — relógio vem por parâmetro
- `Media.from_atividades`: lista vazia → `(0, 0)`; parcialmente lançada → soma só as realizadas; `nota = 0.0` conta como realizada e não é confundida com ausência; `parcial` liga e desliga em 100
- `Materia.oferta`: com aproveitamento usa ele; sem, usa o atual
- `Atividade.realizada`: `contribuicao = 0.0` é realizada, `None` não é

`truncate` saiu de `format.py` com a 0004 — a largura da linha virou `overflow="ellipsis"` no renderable —, então os casos dele saíram desta lista.

### 2. Requests — `MockTransport` + fixtures

Cobre os riscos 1 e 3. Tudo `async def`, com um `AsyncClient` construído sobre o `MockTransport` e um handler síncrono.

- Login: um POST para N GETs no mesmo `AvaSession`; `x-time` repete o `usuario.time` em todo GET; o cookie de sessão volta ao servidor
- `LoginRejected` quando `usuario` é `null`, com a mensagem do AVA
- 404 → `[]` nos dois requests; 500 levanta
- `MateriaRequest`: descarta sala sem `modulo` (o canal do coordenador); monta a URL com o `id_curso` recebido
- `AtividadeRequest`: a querystring leva `materia.oferta`, não `oferta_atual`; `posicao` segue a ordem da resposta
- **Os aliases-armadilha, um teste cada**: `peso` vem de `pesoMedia` e não do `peso` que vale 100; `contribuicao` vem de `notaMedia`; `periodo` vem de `modulo`; `prova` vem de `atividade`
- Campo obrigatório ausente levanta `ValidationError` em vez de virar `None`

### 3. Repositórios — SQLite real em `tmp_path`

`db_session(path)` aceita caminho, então nada de mock aqui. Cobre os riscos 4 e 7.

- Round-trip de `Materia` e `Atividade`, com `datetime`, `float | None` e `nota = 0.0` sobrevivendo
- `MateriaRepository.list_all`: vigentes primeiro, depois por nome
- `MateriaRepository.save` **preserva o carimbo** de quem já estava gravado — o teste que protege o risco 4
- `AtividadeRepository.list_all` ordena por `posicao`
- `AtividadeRepository.replace` substitui em vez de duplicar; atividade que saiu do AVA desaparece
- Nenhum repositório commita: depois de chamar `save`, uma segunda `AsyncSession` no mesmo arquivo ainda não vê o dado

Duas `AsyncSession` sobre o mesmo arquivo é o motivo de o banco ser um arquivo em `tmp_path` e não `:memory:`, agora como antes.

### 4. Services — requests falsos, repositórios reais

Os falsos são corrotinas, e o pyright em `strict` sobre `tests/` é o que garante que continuam casando com o request real.

- `MateriaSyncService.sync` busca, grava e commita; `aluno` reflete a sessão do AVA
- `AtividadeSyncService.sync` grava as atividades **e** carimba a matéria **no mesmo commit** — uma sessão paralela vê as duas escritas ou nenhuma
- O carimbo é asseverado por faixa (`antes <= carimbo <= depois`), não por valor: evita `freezegun` para dois `datetime.now()`
- Request que levanta deixa o banco intacto

### 5. A interface — `run_test()` e Pilot, services falsos

Substitui a camada de prompts roteirizados que existia antes da 0004: `questionary.select`, o `render.console` global e o `EOFError` sem TTY todos deixaram de existir. O `App.run_test()` roda headless, sem pty, e recebe services falsos por construtor — que é o que a decisão de composition root da 0004 comprou. Os falsos registram as chamadas, e é sobre essa lista que a maioria das asserções cai.

É a única camada que cobre o risco 5, e a única que prova as decisões de comportamento da 0004:

- **Mover o cursor não toca a rede**: `pilot.press("down", "down")` e a lista de chamadas do service falso continua vazia
- `⏎` numa matéria nunca sincronizada chama `sync` exatamente uma vez; numa matéria com cache, nenhuma
- **O guarda**: com o service falso suspenso num `asyncio.Event`, `r` e `s` durante o sync em voo não produzem segunda chamada, e `check_action` recusa as três ações
- O selo aparece só nas matérias com `atividades_sincronizadas_em is None`
- `LoginRejected` levantado pelo falso notifica e **o app continua rodando** — a mudança de comportamento mais visível da 0004
- Banco vazio mostra o estado vazio, não uma lista de zero itens

`run_test(size=(100, 30))` em todos: o tamanho do terminal entra no layout, e sem fixá-lo a asserção depende de quem rodou.

### 6. E2E — services reais, AVA falso, banco temporário

Um ou dois testes, cobrindo a fiação do `main.py` que nenhum teste unitário toca. Mesmo `run_test()` da camada 5, mas com os services de verdade montados sobre um `MockTransport` e um `db_session` em `tmp_path`.

- Abrir matéria sem cache dispara o sync, persiste, carimba e renderiza
- Abrir matéria com cache **não** faz requisição nenhuma — o handler do transporte conta as chamadas e a contagem é zero

### 7. Contrato — fixtures reais

O único teste que pega o risco 1. Valida os DTOs contra respostas de verdade e falha quando o AVA muda de forma. Não tem nada de async: são models Pydantic contra JSON em arquivo.

- Cada fixture real parseia sem erro
- **Nenhum campo opcional vem `None`** numa fixture que tem valor — é isto que detecta o alias renomeado
- As chaves da fixture cobrem todos os aliases que os DTOs declaram

### 8. Smoke — `@pytest.mark.rede`, opt-in

Desligado por padrão. Assevera invariantes **estruturais, nunca valores**: login devolve `time`, matérias > 0, toda matéria com período tem oferta, uma matéria conhecida devolve atividades. Serve para saber que o AVA mudou antes do usuário ver nota faltando.

## Fixtures: dois níveis

**Sintéticas**, escritas à mão e commitadas. Testam o código. É o que as camadas 2 a 6 usam.

**Reais**, capturadas uma vez e anonimizadas. Testam o contrato. Captura: um login e dois GETs com os curls de `uninter-endpoints/`, salvando os corpos. Anonimização: trocar `nome` do usuário, RU e ids por valores fixos, e **conferir campo a campo** que não sobrou nada pessoal — o JSON de atividade tem cerca de 160 campos entre o objeto e os aninhados.

Precisamos de quatro: login, matérias (com e sem `oferta_aproveitamento`, e a sala sem `modulo`), atividades com nota lançada, atividades sem nota nenhuma.

## Determinismo

- **Relógio**: `humanize_age` já recebe. Sobraram `mark_synced` e o handler de sync da App, resolvidos por faixa. Sem `freezegun`.
- **Render**: `build_table` devolve um `rich.Table`, e o `Console` deixou de ser um global do app — quem quiser texto o constrói no teste, com `Console(width=100, force_terminal=False)`. É melhor do que a costura anterior: a largura passa a ser parâmetro do teste, não estado que alguém precisa lembrar de substituir.
- **Tela**: nada de asseverar a tela inteira. As asserções da camada 5 são sobre estado de widget e sobre a lista de chamadas dos falsos, com o tamanho fixado em `run_test(size=...)`.
- **Golden**: um arquivo em `tests/golden/` com a matéria renderizada, gerado no primeiro teste da camada 5 e **conferido à mão antes de commitar**. Uma referência foi gerada durante a refatoração de 0003 e não sobreviveu — não está no repositório nem no histórico —, então ela é para refazer, não para reaproveitar.

## Os defeitos conhecidos entram como teste vermelho primeiro

Preservados de propósito na refatoração e na 0004, para serem corrigidos com teste antes:

1. **404 apaga o cache e marca como fresco.** O mais grave. Conserto candidato: `replace` não apagar quando a lista chega vazia, ou o request distinguir "vazio" de "falhou".
2. **`Materia.oferta` usa `or`**, então `oferta_aproveitamento == 0` cairia no atual. Teórico — os ids reais vão de 511 mil a 1,2 milhão e a ausência vem como `None`.
3. **Matéria removida do AVA nunca sai do banco**: `save` só faz `merge`.
4. **`MateriaRepository.save` muta os objetos do chamador.**

## O que não vamos testar

- A fiação do `main.py` isoladamente — o e2e já a exercita
- `MAPPED_TABLES`, que existe só para registrar as tabelas no metadata
- Comportamento interno de `rich`, de `textual` ou do `aiosqlite`
- O layout: nada de snapshot da tela, nada de asseverar posição ou moldura
- Texto exato dos toasts e dos rótulos de binding, que mudam sem consequência
- Cobertura como meta numérica

## Rejeitados

- **`pytest-httpx` ou `respx`.** Resolviam o monkeypatch global que a injeção do client tornou desnecessário. Confirmado que o `MockTransport` do httpx serve também para o `AsyncClient`, então nem o async traz esse custo de volta.
- **`anyio` em vez de `pytest-asyncio`.** Funcionaria, e traria o `anyio_backend` de brinde. Mas o Textual roda em asyncio e sua própria suíte usa `pytest-asyncio`; parametrizar backend para um app que só tem um é cerimônia.
- **`freezegun` ou `time-machine`.** Só dois `datetime.now()` sobraram, e asseverar faixa cobre o que importa: que o carimbo foi escrito.
- **`syrupy` ou `pytest-textual-snapshot`.** Um golden em arquivo de texto se lê no diff; snapshot traz dependência, um fluxo de `--snapshot-update` e a tentação de aceitar a mudança sem olhar. O `pytest-textual-snapshot` ainda por cima gravaria SVG da tela inteira, que é exatamente o que "não vamos testar layout" recusa.
- **SQLite em memória.** Mais rápido, mas o teste de "repositório não commita" precisa de duas conexões vendo o mesmo arquivo.
- **`unittest`.** Perde `parametrize`, que é justamente o que os testes de formatação querem.
- **CI agora.** O repositório não tem remote. Fica um `pdm run test` até existir para onde empurrar.
- **Rodar a App num pty de verdade.** Era obrigatório enquanto o `questionary` exigia TTY, e a estratégia anterior contornava substituindo o prompt. Com o `run_test()` do Textual o app roda headless de fábrica, então o pty deixou de ser um problema a resolver — e mantê-lo só adicionaria flake de temporização.
- **Escrever qualquer teste antes da 0004.** Toda assinatura de `fetch`, `sync` e repository vira async, e a camada 5 inteira depende de widgets que ainda não existem. Seriam testes escritos para reescrever.

## Ordem de execução

Depois da 0004, nunca antes.

1. **Arcabouço e funções puras** — pytest e `pytest-asyncio` no `pyproject`, `conftest.py`, camada 1. Sem fixture nenhuma, entrega valor no mesmo dia.
2. **Fronteiras** — requests com fixtures sintéticas (camada 2) e repositórios em `tmp_path` (camada 3). É onde mora a maior parte do risco por linha escrita.
3. **Composição** — services (camada 4).
4. **Interface** — camada 5 com os falsos e o golden de `build_table`, depois o e2e da camada 6. O teste do guarda vem primeiro: é o risco novo e o mais fácil de regredir sem ninguém notar.
5. **Contrato** — captura e anonimização das fixtures reais, camada 7, e o smoke da camada 8.
6. **Os quatro defeitos**, um a um, teste vermelho primeiro.
