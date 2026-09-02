---
name: estrategia-de-testes
description: Como testar o crawler — mapa de risco, as sete camadas de teste, fixtures sintéticas e reais, determinismo de relógio e console, e os quatro defeitos conhecidos a corrigir com teste vermelho primeiro. Ler antes de escrever qualquer teste neste app.
status: pending
created_at: 2026-09-02
---

# Estratégia de testes do crawler

O projeto não tem nenhum teste. A refatoração para domínios modulares criou as costuras que faltavam — transporte HTTP injetado, banco por caminho, relógio como parâmetro, console substituível — então agora cada fronteira pode ser exercitada sozinha. Este documento decide o que testar, com o quê, e em que ordem. O vocabulário está em [CONTEXT.md](../../../../CONTEXT.md), as decisões de desenho em [0001](../done/0001-crawler-de-avaliacoes-do-ava.md) e as camadas em [0003](../done/0003-camadas-crawler-api-cli.md).

## O mapa de risco

A lista de testes não sai de cobertura, sai daqui. Ordenado por dano × probabilidade:

1. **Drift de alias no DTO.** O AVA renomeia um campo e o dado vira `None` sem erro nenhum: os DTOs usam `extra="ignore"` e quase todo campo interessante é opcional. Sintoma é nota faltando na tela, meses depois. É o único risco que nenhum teste sintético pega.
2. **404 transitório destrói o cache.** `AvaliacaoRequest.fetch` devolve `[]` em 404, `replace` apaga o que havia, `mark_synced` marca como fresco. Falha de rede vira "matéria sem avaliação, sincronizada agora".
3. **Regra da oferta errada.** `aproveitamento ?? atual` decide se vem dado ou 404. Errar aqui esvazia matérias silenciosamente.
4. **Carimbo perdido num resync.** Se o dicionário em `MateriaRepository.save` quebrar, todo "Sincronizar matérias" zera a idade das 26 e força refetch.
5. **Média e peso lançado errados.** É a única aritmética do projeto, e vai direto para a cara do usuário.
6. **Ordem das avaliações trocada.** `posicao` é a única ordenação existente; o AVA não garante nenhuma.

## Ferramental

`pytest` sozinho. **Nada de `pytest-httpx` nem `respx`**: `AvaSession` recebe o `httpx.Client` por construtor, então o `httpx.MockTransport` que já vem no httpx basta — verificado. Antes da refatoração isso exigiria monkeypatch global.

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["rede: exige credenciais e acesso ao AVA (desabilitado por padrão)"]
addopts = "-m 'not rede'"

[tool.pyright]
include = ["src", "tests"]

[tool.pdm.scripts]
test = {cmd = "pytest", help = "Roda a suíte, sem os testes de rede"}
```

Testes entram no `include` do pyright: um fake que divergiu da interface real é um teste que mente.

## Onde os testes moram

Espelhando os pacotes de `src/`, para que o arquivo de teste seja óbvio a partir do arquivo de código:

```
tests/
  conftest.py             sessao em tmp_path, ava falso, fabricas de Materia/Avaliacao
  crawler/                test_session
    materias/             test_dto  test_request
    avaliacoes/           test_dto  test_request
  api/
    materias/             test_entity  test_repository  test_service
    avaliacoes/           test_entity  test_media  test_repository  test_service
  cli/                    test_format  test_render
  e2e/                    test_fluxo
  contract/               test_dtos_reais  test_smoke (marker rede)
  fixtures/               login.json  materias.json  avaliacoes-*.json
  golden/                 materia-renderizada.txt
```

## As camadas, e o que cada uma prova

### 1. Funções puras — sem fixture, sem mock

`cli/format.py` não importa nada e `api/avaliacoes/media.py` importa só a entity. São os testes mais baratos do projeto e cobrem o risco 5.

- `format_number`: `None → "—"`, `0.0 → "0"`, `8.0 → "8"`, `7.5 → "7,5"`, `33.33 → "33,3"`, negativo
- `truncate`: cabe, no limite exato, estoura com elipse, string vazia
- `short_periodo`: `None → ""`, e que o corte no primeiro `" - "` descarta a UTA
- `humanize_age`: `None`, agora, 59s, 1h, 23h, 1d, 45d — relógio vem por parâmetro
- `Media.from_avaliacoes`: lista vazia → `(0, 0)`; parcialmente lançada → soma só as realizadas; `nota = 0.0` conta como realizada e não é confundida com ausência; `parcial` liga e desliga em 100
- `Materia.oferta`: com aproveitamento usa ele; sem, usa o atual
- `Avaliacao.realizada`: `contribuicao = 0.0` é realizada, `None` não é

### 2. Requests — `MockTransport` + fixtures

Cobre os riscos 1 e 3.

- Login: um POST para N GETs no mesmo `AvaSession`; `x-time` repete o `usuario.time` em todo GET; o cookie de sessão volta ao servidor
- `LoginRejected` quando `usuario` é `null`, com a mensagem do AVA
- 404 → `[]` nos dois requests; 500 levanta
- `MateriaRequest`: descarta sala sem `modulo` (o canal do coordenador); monta a URL com o `id_curso` recebido
- `AvaliacaoRequest`: a querystring leva `materia.oferta`, não `oferta_atual`; `posicao` segue a ordem da resposta
- **Os aliases-armadilha, um teste cada**: `peso` vem de `pesoMedia` e não do `peso` que vale 100; `contribuicao` vem de `notaMedia`; `periodo` vem de `modulo`; `prova` vem de `avaliacao`
- Campo obrigatório ausente levanta `ValidationError` em vez de virar `None`

### 3. Repositórios — SQLite real em `tmp_path`

`db_session(path)` já aceita caminho, então nada de mock aqui. Cobre os riscos 4 e 6.

- Round-trip de `Materia` e `Avaliacao`, com `datetime`, `float | None` e `nota = 0.0` sobrevivendo
- `MateriaRepository.list_all`: vigentes primeiro, depois por nome
- `MateriaRepository.save` **preserva o carimbo** de quem já estava gravado — o teste que protege o risco 4
- `AvaliacaoRepository.list_all` ordena por `posicao`
- `AvaliacaoRepository.replace` substitui em vez de duplicar; avaliação que saiu do AVA desaparece
- Nenhum repositório commita: depois de chamar `save`, uma segunda `Session` no mesmo arquivo ainda não vê o dado

### 4. Services — requests falsos, repositórios reais

- `MateriaSyncService.sync` busca, grava e commita; `aluno` reflete a sessão do AVA
- `AvaliacaoSyncService.sync` grava as avaliações **e** carimba a matéria **no mesmo commit** — uma `Session` paralela vê as duas escritas ou nenhuma
- O carimbo é asseverado por faixa (`antes <= carimbo <= depois`), não por valor: evita `freezegun` para dois `datetime.now()`
- Request que levanta deixa o banco intacto

### 5. E2E — prompts roteirizados, AVA falso, banco temporário

Um ou dois testes, cobrindo a fiação do `main.py` que nenhum teste unitário toca. Receita já verificada: substituir `questionary.select` por um stub com respostas em fila, `render.console` por um `Console(width=100, force_terminal=False)`, e apontar `db_session` para uma cópia do banco.

- Abrir matéria sem cache dispara o sync, persiste, carimba e renderiza
- Abrir matéria com cache **não** faz requisição nenhuma

### 6. Contrato — fixtures reais

O único teste que pega o risco 1. Valida os DTOs contra respostas de verdade e falha quando o AVA muda de forma.

- Cada fixture real parseia sem erro
- **Nenhum campo opcional vem `None`** numa fixture que tem valor — é isto que detecta o alias renomeado
- As chaves da fixture cobrem todos os aliases que os DTOs declaram

### 7. Smoke — `@pytest.mark.rede`, opt-in

Desligado por padrão. Assevera invariantes **estruturais, nunca valores**: login devolve `time`, matérias > 0, toda matéria com período tem oferta, uma matéria conhecida devolve avaliações. Serve para saber que o AVA mudou antes do usuário ver nota faltando.

## Fixtures: dois níveis

**Sintéticas**, escritas à mão e commitadas. Testam o código. É o que as camadas 2 a 5 usam.

**Reais**, capturadas uma vez e anonimizadas. Testam o contrato. Captura: um login e dois GETs com os curls de `uninter-endpoints/`, salvando os corpos. Anonimização: trocar `nome` do usuário, RU e ids por valores fixos, e **conferir campo a campo** que não sobrou nada pessoal — o JSON de avaliação tem cerca de 160 campos entre o objeto e os aninhados.

Precisamos de quatro: login, matérias (com e sem `oferta_aproveitamento`, e a sala sem `modulo`), avaliações com nota lançada, avaliações sem nota nenhuma.

## Determinismo

- **Relógio**: `humanize_age` já recebe. Sobraram `mark_synced` e `cli/app.py`, resolvidos por faixa. Sem `freezegun`.
- **Console**: `render.console` é global substituível; com largura fixa e `force_terminal=False` a saída é byte-estável — verificado.
- **Golden**: já existe uma saída de referência de 151 linhas (4 matérias renderizadas, seletor e as funções puras tabeladas), gerada e conferida durante a refatoração. Vira `tests/golden/` sem precisar de `syrupy`.

## Os defeitos conhecidos entram como teste vermelho primeiro

Preservados de propósito na refatoração, para serem corrigidos com teste antes:

1. **404 apaga o cache e marca como fresco.** O mais grave. Conserto candidato: `replace` não apagar quando a lista chega vazia, ou o request distinguir "vazio" de "falhou".
2. **`Materia.oferta` usa `or`**, então `oferta_aproveitamento == 0` cairia no atual. Teórico — os ids reais vão de 511 mil a 1,2 milhão e a ausência vem como `None`.
3. **Matéria removida do AVA nunca sai do banco**: `save` só faz `merge`.
4. **`MateriaRepository.save` muta os objetos do chamador.**

## O que não vamos testar

- A fiação do `main.py` isoladamente — o e2e já a exercita
- `MAPPED_TABLES`, que existe só para registrar as tabelas no metadata
- Comportamento interno de `rich` e `questionary`
- Texto exato dos spinners e dos rótulos de menu, que mudam sem consequência
- Cobertura como meta numérica

## Rejeitados

- **`pytest-httpx` ou `respx`.** Resolviam o monkeypatch global que a injeção do `httpx.Client` tornou desnecessário. Uma dependência a menos.
- **`freezegun` ou `time-machine`.** Só dois `datetime.now()` sobraram, e asseverar faixa cobre o que importa: que o carimbo foi escrito.
- **`syrupy`.** Golden em arquivo de texto já resolve, e o arquivo de referência já existe.
- **SQLite em memória.** Mais rápido, mas o teste de "repositório não commita" precisa de duas conexões vendo o mesmo arquivo.
- **`unittest`.** Perde `parametrize`, que é justamente o que os testes de formatação querem.
- **CI agora.** O repositório não tem remote. Fica um `pdm run test` até existir para onde empurrar.
- **Testar através da CLI real.** `questionary` exige TTY e o processo morre com `EOFError` sem terminal. Substituir `questionary.select` cobre o mesmo fluxo sem pty.

## Ordem de execução

1. **Arcabouço e funções puras** — pytest no `pyproject`, `conftest.py`, camada 1. Sem fixture nenhuma, entrega valor no mesmo dia.
2. **Fronteiras** — requests com fixtures sintéticas (camada 2) e repositórios em `tmp_path` (camada 3). É onde mora a maior parte do risco por linha escrita.
3. **Composição** — services (camada 4), e2e e o golden do render (camada 5).
4. **Contrato** — captura e anonimização das fixtures reais, camada 6, e o smoke da camada 7.
5. **Os quatro defeitos**, um a um, teste vermelho primeiro.
