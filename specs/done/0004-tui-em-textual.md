---
name: tui-em-textual
description: Troca questionary + rich por Textual numa tela master-detail e converte crawler e api para async de ponta a ponta (AsyncClient, AsyncSession, aiosqlite). Traz o guarda contra sync concorrente, o inventário de widgets e o que a mudança faz com a 0002. Ler antes de mexer em cli/, em qualquer assinatura de request/repository/service, ou nos testes.
projects: [all]
status: done
created_at: 2026-09-02
---

# TUI em Textual

Hoje a lista de matérias desaparece a cada consulta: `browse_materias` pergunta, `open_materia` renderiza, e para ver a próxima matéria o usuário volta ao seletor e escolhe de novo. É o custo de navegação que o `questionary` impõe — um prompt de cada vez, nada permanente na tela.

Trocar `questionary` + `rich` por Textual não é trocar de biblioteca: é inversão de controle. O `while True: pergunta → renderiza` de `cli/app.py` desaparece e vira widget mais handler. E como o Textual roda num event loop, todo I/O bloqueante tem que sair da frente — o que arrasta `crawler` e `api` para async. Quando esta spec for executada, a tela é uma só, a lista nunca sai dela, e nenhuma chamada síncrona sobra no caminho da rede ou do banco.

O vocabulário está em [CONTEXT.md](../../CONTEXT.md), as decisões de desenho em [0001](0001-crawler-de-atividades-do-ava.md), as camadas em [0003](0003-camadas-crawler-api-cli.md) e os testes em [0002](../pending/0002-estrategia-de-testes.md).

## Comportamento observado

Medido no venv do app (Python 3.12.12, SQLAlchemy 2.0.52, SQLModel 0.0.42, httpx 0.28.1):

- `create_engine("sqlite:///uninter.db")` devolve um `QueuePool` e passa `check_same_thread=False` ao pysqlite. Uma `Session` usada de duas threads **não levanta erro** — falha em silêncio. É o que descartou resolver o bloqueio com thread.
- `sqlmodel.ext.asyncio.session.AsyncSession` existe e tem `.exec()`, então os repositories mantêm a forma que têm hoje: `list(( await sessao.exec(stmt)).all())`.
- `greenlet` 3.5.5 já está instalado, que é o que o modo async do SQLAlchemy exige. `aiosqlite` e `textual` não estão.
- `httpx.MockTransport` com handler **síncrono** funciona contra um `AsyncClient` — verificado com uma requisição de verdade. As fixtures da camada 2 da 0002 sobrevivem sem edição; só as funções de teste viram `async def`.

Sobre concorrência na `AsyncSession`, medido com `asyncio.gather` sobre a sessão real:

- **Dois `service.sync()` concorrentes quebram**: 25 rodadas de três syncs simultâneos produziram 74 falhas, com `IllegalStateChangeError: Method 'commit()' can't be called here`, `ResourceClosedError`, `PendingRollbackError` e `IntegrityError` por autoflush. É o que torna o guarda obrigatório, não opcional.
- **Um sync concorrente com leituras não quebra**: 25 rodadas de um `sync()` contra 40 `list_all()` simultâneos, zero falhas. Por isso mover o cursor durante um sync é seguro e continua liberado.
- `AvaSession._session_headers()` faz login preguiçoso (`if self._stamp is None`), então dois workers no primeiro acesso à rede emitem dois POSTs de login. Lido no código, e evitado pelo guarda.

Medido no Textual 8.2.8, o que resolveu os três itens que estavam sem verificação quando esta spec foi escrita — nenhum fallback foi necessário:

- `Option` aceita `VisualType`, que inclui `RenderableType`, então um `rich.Table` por opção funciona. E opções `disabled=True` são **puladas pela navegação**: com um título de grupo em `disabled`, o destaque inicial cai na primeira matéria e as setas nunca param no título.
- `Widget.loading` existe como `Reactive` e aceita atribuição direta.
- `check_action` decide entre esconder e mostrar, não entre habilitado e apagado: `False` **esconde** a tecla do `Footer` e bloqueia a ação; `None` **mostra** a tecla e bloqueia em silêncio; `True` libera. Nenhum retorno produz "visível porém apagado" — `FooterKey.disabled` nunca fica verdadeiro. O guarda usa `False`, que é o que dá o rodapé encolhendo do desenho.

## Decisões

### A tela é uma só, e a lista de matérias não sai dela

Lista à esquerda, painel da matéria à direita, `Footer` embaixo. Trocar de matéria passa a ser uma seta, não voltar dois menus — é o único desenho que paga a migração. As alternativas (replicar o fluxo de hoje em `Screen`s empilhadas, ou tela única com modal de seleção) manteriam exatamente o custo que motivou a mudança.

### Mover o cursor nunca toca a rede

`OptionHighlighted` lê só do SQLite e preenche o painel; `OptionSelected` (`⏎`) e `r` são os únicos gatilhos de rede. Numa lista onde a seta move o cursor, carregar no destaque significaria até 27 requisições ao AVA só de rolar a lista — e a 0001 já decidiu que "atualizar é ato explícito". Matéria nunca sincronizada mostra estado vazio com a chamada para ação, o que torna a regra visível em vez de implícita.

### O app inteiro vira async, sem thread nenhuma

`ava_client()` devolve `httpx.AsyncClient`, `AvaSession.get` e os dois `fetch` viram `async def`, e os dois `service.sync` também. Nenhum `asyncio.to_thread`, nenhum `@work(thread=True)`: o `check_same_thread=False` medido acima significa que uma `Session` cruzando thread não avisa, e a alternativa de manter o domínio síncrono custaria exatamente essa armadilha. O custo assumido é reescrever a camada `crawler` que a 0003 acabou de arrumar, sem nenhuma requisição paralela para justificar o ganho — é uniformidade, não desempenho.

### O SQLite acompanha, com AsyncSession e aiosqlite

`api/db.py` passa a `create_async_engine("sqlite+aiosqlite:///...")` e `AsyncSession`; os dois repositories e os dois services ganham `await`. O `SQLModel.metadata.create_all` deixa de aceitar o engine direto e vira `async with engine.begin() as conn: await conn.run_sync(SQLModel.metadata.create_all)`.

Nada disso é ganho de velocidade — o banco tem 24KB e `aiosqlite` é um wrapper de thread por dentro. É consistência: com o `crawler` async, deixar `sessao.exec()` síncrono no event loop seria a única chamada bloqueante sobrando, e ninguém lembraria por quê. As entities e o schema não mudam.

### A sessão desliga o `expire_on_commit`

`AsyncSession(engine, expire_on_commit=False)`. O padrão do SQLAlchemy expira toda instância depois de um commit, e o próximo acesso a atributo dispara um refresh preguiçoso — que sob async não é lento, é `MissingGreenlet`. Encontrado na primeira execução do estágio 2: `atividades_db.list_all(materia)` logo depois de `service.sync()` estourava ao ler `materia.id`.

Desligar é o que o app quer de todo jeito: as entities são snapshots entregues à tela, e nada aqui depende de o commit trazer valores novos do disco. É a única linha da migração que ganhou comentário, porque é uma quirk da biblioteca que ninguém deduz lendo este repositório.

### `main.py` continua o composition root

`main.py` abre os recursos com `async with` e entrega services prontos ao construtor da App, que sobe por `run_async()` dentro de um `asyncio.run(main())`. A App não importa `httpx`, `sqlmodel` nem `settings` — a seta "cli → api, nunca crawler" da 0003 sobrevive intacta.

O ganho concreto está no teste: `App.run_test()` recebe services falsos por construtor, e o e2e da 0002 deixa de precisar de monkeypatch. A alternativa — a App abrindo tudo num `AsyncExitStack` no `on_mount` — encolheria o `main.py` a três linhas ao preço de furar a fronteira entre camadas.

### O pacote continua `cli/`, recortado por domínio

```
cli/
  app.py         UninterApp: layout, bindings, workers, guarda
  materias.py    MateriaList, MateriaHeader
  atividades.py  AtividadeTable, MediaBar
  format.py      format_number, short_periodo, humanize_age
  app.tcss
```

`prompts.py` morre com o `questionary`; `render.py` deixa de ser um módulo de funções e vira widget. O nome `cli` fica menos exato depois desta mudança — não há mais linha de comando nenhuma —, mas renomear para `tui/` reapontaria import em todo lugar e mexeria na 0003 e na 0002 por um ganho de vocabulário. O recorte por domínio espelha `api/materias/` e `api/atividades/`, que é o eixo que o repositório já usa.

### Um `OptionList` e um `Static` — um focável só

`MateriaList` estende `OptionList`, que é o análogo direto do `questionary.select`: tem separador para os grupos EM CURSO e FINALIZADAS e emite as duas mensagens que a decisão do cursor precisa. `AtividadeTable` é um `Static` que recebe o `rich.Table` de `build_table`, então esse código sobrevive quase inteiro e o golden do render continua sendo um arquivo de texto conferível no diff.

O `DataTable` seria o caminho idiomático, mas entra na ordem de foco e disputa `↑↓` com a lista — num master-detail, a seta precisa significar sempre a mesma coisa. Com um único widget focável isso é estrutural, não convenção.

### Cada linha da lista é um renderable, não uma string

Cada opção é um `Table.grid()` de duas colunas: nome com `overflow="ellipsis"` à esquerda, período à direita. O painel reflui quando a janela muda de tamanho, e a largura deixa de ser um número no código.

A consequência é que `truncate` e `NAME_WIDTH` ficam órfãos — `truncate` só tinha um chamador, `ask_materia`. Saem de `format.py` no mesmo commit, e os casos deles saem da camada 1 da 0002. As outras três funções puras ficam onde estão, sem edição.

### `LoginRejected` deixa de ser fatal

Hoje ele é capturado no topo de `run()`, imprime e encerra o processo. Passa a ser um `notify()` de erro com o app vivo: o cache no SQLite continua legível, e matar a sessão por causa de uma senha errada no `.env` joga fora tudo que já foi sincronizado. Carregamento é `loading` no painel que espera; desfecho de sync — o `aluno` e o total que hoje saem em `render_sync_summary` — é toast de sucesso.

A exceção é o primeiro run com banco vazio: aí não há cache para navegar, e a tela mostra um estado vazio explicando, em vez de uma lista de zero itens.

### Um sinal de "sincronizando" desabilita as teclas

Um reactive `sincronizando` no app, e `check_action` recusando `refresh`, `sync` e `open` enquanto ele está ligado. O `Footer` reflete isso sozinho, então o guarda fica visível em vez de silencioso.

**A flag é ligada junto com a tecla, não dentro do worker.** `@work` apenas agenda a corrotina, então ligar `sincronizando` no corpo dela deixa uma janela em que duas teclas despachadas antes de o worker começar passam as duas pelo `check_action` — reproduzido, dois fetches onde devia haver um. Quem liga a flag é o método síncrono que cria o worker; o worker só a desliga, no `finally`.

Isso existe porque a tela não-bloqueante abre três caminhos reais para dois syncs simultâneos: a janela de ~14s do sync geral, `r` batido duas vezes dentro do meio segundo do fetch, e `⏎` em duas matérias seguidas. Nos três, duas corrotinas tocam a mesma `AsyncSession` e o SQLAlchemy levanta; em dois deles o login preguiçoso do `AvaSession` dispara duas vezes. Um lock que enfileira resolveria a sessão mas transformaria `r` batido em N requisições ao AVA, e sem sinal no rodapé a tecla pareceria não ter funcionado. Nenhuma das duas operações ganha nada rodando em paralelo — são requisições sequenciais ao mesmo servidor.

### O selo de nunca sincronizada é a única coisa nova

Um `●` na linha das matérias com `atividades_sincronizadas_em is None`. Custa três linhas agora que a opção é um renderable, e é o que torna o estado descobrível antes de o usuário chegar nele — sem isso, só se sabe que uma matéria está vazia depois do `⏎`. Fora dele, o primeiro corte é paridade: nada de filtro, nada de ordenação, nada de detalhe por atividade.

### O menu de topo evapora

`VIEW_ATIVIDADES` some porque a lista já está na tela, `BACK` some porque não há para onde voltar, e `SYNC_MATERIAS`, `REFRESH` e `QUIT` viram bindings: `s`, `r` e `q`. `⏎` fica **fora** do `BINDINGS`: o `OptionList` já o consome para emitir `OptionSelected`, e declarar o mesmo atalho no app só o mostraria no rodapé sem ser ele quem dispara. O guarda do `⏎` mora no handler da mensagem; quem anuncia a tecla é o estado vazio da matéria nunca sincronizada, que já diz "⏎ para buscar no AVA". `render_goodbye` também sai — o Textual restaura o terminal na saída, e imprimir depois disso é ruído.

### A 0002 é reescrita, não emendada

Cinco seções dela deixam de valer: Ferramental (`pytest-asyncio` entra, contra o "pytest sozinho"), a árvore de `tests/` (`cli/test_render` vira `test_atividades` mais `test_app`), a camada 5 inteira — os três mecanismos que ela nomeia, stub de `questionary.select`, `render.console` com largura fixa e o pty evitado, todos deixam de existir —, Determinismo, e o golden. As camadas 2, 3, 4 e 7 mantêm as asserções e só viram `async def`; as camadas 1 e 6 quase não mudam. O mapa de risco ganha uma entrada: o guarda de sync cedendo é risco novo, e é o único cujo teste mora na camada da interface.

A reescrita também corrige uma afirmação falsa que a 0002 carrega desde que foi escrita: ela diz que o golden do render "já existe", gerado durante a refatoração da 0003. Não existe — nem no repositório, nem no histórico do git. Passa a ser um arquivo para gerar e conferir à mão, o que muda a razão pela qual a 0002 recusa `syrupy`.

### O banco não é tocado

`Materia` e `Atividade` não mudam de nome nem de campo, e o dialeto `sqlite+aiosqlite` lê o mesmo arquivo. `uninter.db` segue válido; se um `select` quebrar, é `await` faltando, não schema.

### Os quatro defeitos conhecidos continuam de pé

Os defeitos listados na 0002 — 404 apagando o cache, `Materia.oferta` com `or`, matéria removida que nunca sai do banco, `save` mutando os objetos do chamador — são preservados de propósito, como a 0003 fez. Eles esperam teste vermelho primeiro, e uma migração em que nada de comportamento muda é uma migração que se revisa lendo os handlers.

## Rejeitados

- **`asyncio.to_thread` só na rede, mantendo o domínio síncrono.** Era o menor raio de alteração: dois `service.sync` async, `crawler` intacto, `Session` nunca cruzando thread. Descartado em favor de uniformidade — um app onde metade das assinaturas é async e a outra não obriga a lembrar de qual é qual em cada chamada.
- **`@work(thread=True)` com uma sessão por operação.** Zero async no domínio, mas o composition root deixaria de entregar instâncias e passaria a entregar fábricas, com duas conexões SQLite vivas e entities de uma sessão morta chegando na UI.
- **`@work(exclusive=True)` por grupo, sem guarda explícito.** Idiomático, mas grupos distintos (sync geral e sync de matéria) continuam concorrendo na mesma `AsyncSession`, e cancelar um worker no meio de `replace()` deixa a sessão suja precisando de rollback.
- **Login eager no boot para matar a race do `_stamp`.** Resolve, e faz o app abrir sempre com uma requisição de rede — a 0001 decidiu o contrário ("a rede só entra quando o usuário pede"), e senha errada passaria a impedir até de ver o cache.
- **`DataTable` no painel de atividades.** Scroll e listras nativos, mas `build_table` reescrito, golden refeito, e um segundo focável que precisa de `can_focus = False` para não roubar `↑↓`. Nada se faz com uma linha selecionada.
- **`ListView` com item composto na lista de matérias.** Daria estilo por elemento via TCSS, mas não tem separador — os grupos EM CURSO e FINALIZADAS viriam como itens desabilitados na mão — e é mais código que o `OptionList`.
- **Renomear `cli/` para `tui/`.** O nome ficou impreciso, e essa foi exatamente a crítica que a 0003 fez ao `infra/`. Mas ali o nome escondia uma fronteira de camada; aqui esconde só o formato da interface, e o preço é reapontar import em todo o `src/` mais duas specs. Revisitar se aparecer uma segunda interface.
- **Modal bloqueante durante o sync.** Mais fiel ao comportamento atual e sem nenhuma dúvida sobre estado inconsistente na tela, porque não há estado a inconsistir. Descartado porque 14 segundos de tela travada é o que a migração deveria eliminar.
- **Sync automático com debounce ao parar o cursor.** Preencheria o banco navegando e removeria o passo do `⏎`. É a mesma releitura silenciosa da rede que a 0001 rejeitou ao chamar atualizar de ato explícito.
- **Filtro por digitação na lista.** Útil quando a lista crescer, mas introduz um segundo focável — que é justamente o que a escolha de `OptionList` + `Static` evita — mais um modo (`/` entra, `esc` sai) e estado de filtro para conciliar com o guarda de sync. 27 itens cabem em duas telas.
- **Duas specs, uma para o async e outra para o Textual.** Duas revisões independentes, cada uma com estado verde. Mas o async não tem motivação própria: existe só porque o event loop do Textual exige. Uma spec que justificasse "vira async" sem poder citar o Textual escreveria o porquê errado, e se o Textual fosse abandonado o async sobraria sem razão no repositório.
- **Emenda cirúrgica na 0002 em vez de reescrita.** Menor diff e o revisor vê o que mudou. Mas cinco seções mudam, e um documento cujo header manda "ler antes de escrever qualquer teste" não deveria precisar que o leitor cruze duas specs para saber quais parágrafos ainda valem.
- **String pré-formatada em cada linha da lista.** Manteria `format.py` intacto e a camada 1 da 0002 inteira, levantando o corpo de `ask_materia` como está. Perdido para o reflow ao redimensionar; fica registrado como fallback caso `OptionList` não aceite renderable.

## Ordem de execução

Três estágios de código, cada um com o app rodando ao fim. Nos dois primeiros a CLI de `questionary` continua no lugar: `main.py` vira `asyncio.run(main())` e os prompts síncronos seguem funcionando dentro da corrotina — bloqueiam o loop, mas não há concorrência a proteger ainda.

**`questionary` sai no estágio 3, não no 1.** Tirá-lo antes quebra `cli/prompts.py` no mesmo instante e derruba justamente o estado verde que os dois primeiros estágios existem para preservar.

1. **`crawler/` async.** `+textual` e `+aiosqlite` no `pyproject`; `rich` continua explícito (`build_table` e as linhas da lista importam `rich.Table`). `ava_client` devolve `AsyncClient`, `AvaSession.get` e os dois `fetch` ganham `async`/`await`. `cli/app.py` e `main.py` acompanham com `await`.
2. **`api/` async.** `db.py` com `create_async_engine`, `run_sync` no `create_all` e `expire_on_commit=False`; `AsyncSession` nos dois repositories, `await` nos dois services. Como os dois context managers agora são async, o `main.py` volta a ter um `async with` só.
3. **`cli/` em Textual.** `app.py` com o layout, os bindings e o guarda; `materias.py` e `atividades.py`; `app.tcss`; `truncate` e `NAME_WIDTH` fora de `format.py`; `prompts.py` e `render.py` apagados; `questionary` fora do `pyproject`.
4. **0002 reescrita**, no commit do estágio 3.

Verificação, em vez de abrir a CLI a cada estágio: `pyright` em `strict` sobre `src/` — com tudo async, `await` faltando é o erro que passa em silêncio no runtime — mais um roteiro headless por estágio, com `MockTransport` no lugar do AVA e o banco em diretório temporário. O estágio 3 usa `App.run_test()` com Pilot, que é o mesmo ferramental que a camada 5 da [0002](../pending/0002-estrategia-de-testes.md) vai usar. Nada disso vira teste commitado aqui: os testes são trabalho da 0002, depois desta spec.

## O que a execução corrigiu

Registrado porque cada item era uma afirmação errada desta spec, não uma surpresa do Textual:

- **`expire_on_commit`** não estava previsto e é obrigatório. Virou decisão acima.
- **A ordem do `questionary`** estava contraditória, corrigida acima.
- **A flag do guarda** ligada dentro do worker deixava passar dois fetches. Virou parágrafo na decisão do guarda.
- **`MateriaList.show` restaurava o destaque por índice**, e depois de um resync o índice podia cair num título de grupo `disabled` — `em_foco` devolvia `None` e `r` virava um no-op silencioso. Passa a restaurar pelo id da matéria, com a primeira matéria como fallback.
- **O estado vazio nunca aparecia no `LoginRejected` do primeiro run**, porque o worker levantava antes de `reload_materias`. O `on_mount` passa a pintar o estado antes de sincronizar, e o `except` repinta.
- **`overflow="ellipsis"` sozinho não corta no `rich`**: sem `no_wrap=True` o nome comprido quebra em duas linhas em vez de virar elipse.
