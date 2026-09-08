---
name: fila-em-background-e-reset
description: A fila que busca as atividades de todas as matérias sozinha e o comando que apaga o banco — as duas mudanças que alteram quando a rede roda e o que o cache significa. Traz o custo medido da varredura, a preempção da fila pelo usuário e por que apagar o arquivo obriga a App a reiniciar. Ler antes de mexer no guarda da 0004, em main.py ou em qualquer coisa que sincronize sozinha.
projects: [frontend, api]
status: done
created_at: 2026-09-02
---

# Fila em background e reset do banco

Duas mudanças que parecem independentes e são a mesma decisão vista de dois lados: **quando a rede roda sem ninguém pedir**, e **o que faz o cache valer de novo**. Hoje abrir uma matéria nunca visitada custa meio segundo de espera, e não existe forma de recomeçar do zero a não ser apagar `uninter.db` na mão, por fora do app.

Depois desta spec o banco se enche sozinho depois do primeiro sync, e uma tecla o zera inteiro. As duas coisas se encontram no mesmo ponto: zerar o banco com a fila ligada dispara justamente a varredura completa.

O que o projeto é está em [CONTEXT.md](../../../../CONTEXT.md), as decisões de desenho em [0001](0001-crawler-de-atividades-do-ava.md), a interface e o guarda de sync em [0004](0004-tui-em-textual.md), e os trabalhos em [0005](0005-trabalhos.md).

## Comportamento observado

**Apagar `uninter.db` com a sessão aberta deixa o app meio morto.** Medido: depois do `unlink`, as leituras **continuam funcionando** e devolvem dados do inode órfão, como se nada tivesse acontecido; as escritas falham com `OperationalError: attempt to write a readonly database`; e o arquivo não é recriado. O banco só aparece vazio quando uma sessão nova abre. É o pior estado possível — a tela mostra dado que não existe mais em disco e o próximo sync morre com erro de SQLite. Qualquer reset precisa reciclar o engine, não só apagar o arquivo.

**Dois syncs concorrentes na mesma `AsyncSession` quebram, leituras concorrentes não.** Medido na [0004](0004-tui-em-textual.md): 25 rodadas de três `sync()` simultâneos deram 74 falhas (`IllegalStateChangeError`, `ResourceClosedError`, `PendingRollbackError`); um `sync()` contra 40 `list_all()` simultâneos deu zero. A fila tem que ser serial, e navegar durante ela é seguro.

**A varredura completa custa cerca de 13 segundos.** São 26 matérias a meio segundo cada, das quais 6 devolvem 404 legítimo — matéria sem atividade, indistinguível de falha, como a [0001](0001-crawler-de-atividades-do-ava.md) registrou.

## Decisões

### A fila varre todas as matérias sem cache

Depois que o sync de matérias termina, uma fila enfileira **todas** as matérias sem carimbo, vigentes primeiro. Ao fim da primeira execução o app está completo offline.

O custo da varredura é o mesmo de sempre — 26 matérias a meio segundo cada. O que muda é quem espera por ele: em background, os 13 segundos não estão na frente de ninguém, e o app deixa de depender de ter visitado a matéria antes para funcionar offline.

O que não muda é o princípio: o SQLite continua sendo a fonte de leitura, e a rede nunca entra no caminho de uma tecla.

### Mover o cursor continua sem tocar a rede

A [0004](0004-tui-em-textual.md) decidiu que o destaque lê só do banco, e isso não muda. A fila não é disparada pelo cursor, não sabe onde ele está e não muda de ordem por causa dele. Quem move o cursor durante a fila vê o cache que existir — inclusive o estado "nunca sincronizada", se aquela matéria ainda não chegou a vez.

### Nenhuma tecla é bloqueada; a fila é que serializa

O `sincronizando` da [0004](0004-tui-em-textual.md) desabilitava `r`, `s` e `⏎` via `check_action`. Mantê-lo assim durante a fila trancaria o teclado por 13 segundos, e fazê-lo piscar por item acenderia e apagaria o rodapé 26 vezes.

Os dois problemas somem quando **toda** sincronização — a da lista, a de uma matéria, a da fila — passa por um consumidor serial único. Não há mais o que bloquear: o que garante que não existem dois commits simultâneos é haver um só consumidor, não a tecla estar apagada. `check_action` sai, e `sincronizando` fica sendo apenas o sinal de "há um item em voo" que acende o indicador de carregamento.

O guarda deixa de ser visível no rodapé, e o que aparece no lugar é melhor: o cabeçalho mostra quantos itens faltam.

### O trabalho do usuário cancela o item de fundo em voo

`⏎` ou `r` numa matéria a colocam na frente da fila **e abortam a requisição de background que estiver em voo**. Sem isso, "furar a fila" ainda deixava o usuário esperando o fetch corrente terminar — o trabalho de background atrapalhando o trabalho pedido, que é justamente o que não pode acontecer. A matéria interrompida volta para logo depois da do usuário e é refeita em seguida.

**A escrita não é cancelável.** Cancelar dentro do `commit` deixa a sessão num estado que nem `rollback()` recupera — dá `IllegalStateChangeError`, que é o mesmo risco que a [0004](0004-tui-em-textual.md) citou ao rejeitar `exclusive=True`. Por isso `AtividadeSyncService.sync` embrulha a fase de banco num `asyncio.shield`: o cancelamento sempre pega o fetch, e a gravação, se já começou, termina.

Duas consequências que só aparecem na implementação: uma matéria **já enfileirada** precisa ser promovida para a frente quando o usuário a pede, em vez de ignorada por já estar na fila; e pedir a mesma matéria várias vezes seguidas não pode enfileirar várias cópias. Com isso, `r` batido sete vezes vale uma requisição, e `⏎` em três matérias vale três, uma de cada vez.

### A fila espera um segundo entre uma matéria e outra

`PAUSA_ENTRE_MATERIAS = 1.0`, aplicada entre itens consecutivos. A varredura completa passa de 13 para uns 40 segundos, e é esse o ponto: em background ninguém está esperando por ela, então não há motivo para despejar 26 requisições seguidas no servidor da faculdade. O que era uma rajada vira um gotejamento.

**A pausa é interrompida por pedido do usuário.** Sem isso, `⏎` numa matéria sem cache ficaria parado esperando trabalho que ninguém pediu. A espera é um `wait_for` sobre um evento que o enfileiramento com prioridade dispara, então o pedido do usuário corta a pausa no instante em que chega.

### O que está sincronizando aparece no selo da própria matéria

A coluna de um caractere que mostra `●` para "nunca sincronizada" passa a mostrar um spinner na matéria que está sendo buscada. É o único lugar da tela onde a informação cabe sem competir com nada, e diz **qual** matéria a fila está processando — coisa que um indicador no painel não diz.

Com isso o painel de detalhe **deixa de ser coberto** durante um sync de atividades: quem está lendo uma matéria continua lendo enquanto o fundo trabalha. A cobertura sobra só para o sync da lista de matérias, onde a lista inteira vai ser substituída de qualquer forma, e ali entra o `Carregando` — uma onda de blocos — devolvido por `get_loading_widget`.

E a linha é redesenhada sozinha, por `replace_option_prompt`, sem reconstruir a lista: reconstruir movia o destaque e redesenhava o painel debaixo de quem estava navegando.

### O reset apaga o arquivo e reinicia a App

O comando descarta `uninter.db` inteiro e sobe tudo de novo. É o único reset que limpa schema órfão, o que deixa de ser detalhe agora que a [0005](0005-trabalhos.md) soma três tabelas ao banco.

Zerar só os carimbos seria mais conservador e reversível, mas deixaria as linhas antigas no banco e não é o que "invalidar todo o cache" quer dizer. E nada se perde de verdade: o AVA é a fonte, e com a fila ligada o banco se reconstrói sozinho em 27 requisições logo depois de subir.

### Quem apaga e remonta é o `main.py`, não a App

A App só sinaliza. O `main.py` ganha um laço: roda a App, e se ela pediu reset, apaga o arquivo **fora** do `async with` — com o engine já descartado e a sessão fechada — e monta tudo outra vez.

```python
async def main() -> None:
    while True:
        async with ava_client() as http, db_session() as sessao:
            ...
            app = UninterApp(...)
            await app.run_async()
            if not app.resetar:
                return
        DATABASE_PATH.unlink(missing_ok=True)
```

É o que resolve o inode órfão medido acima sem tocar em repository, service ou no construtor da App — a injeção por construtor da [0004](0004-tui-em-textual.md) continua de pé, e a [0005](0005-trabalhos.md) não precisa mudar uma linha da task list dela. O preço é a tela piscar e o cursor voltar ao topo, que para "apagar o banco" é o que se espera de qualquer forma.

### O reset mora na paleta de comandos, não numa tecla

`ctrl+p` e o comando "Apagar o banco", registrado por um `Provider` próprio. Apagar o banco é raro e destrutivo: gastar uma das poucas teclas do rodapé com ele coloca a operação mais perigosa do app à distância de um dedo errado, ao lado de `r` e `s`, que são as duas mais frequentes.

A paleta ainda dá o que uma letra não dá — nome por extenso, descrição do que vai acontecer e busca —, e o rodapé volta a listar só o que se usa o tempo todo.

### O reset pede confirmação

Um modal de sim ou não depois de escolher o comando. Nada é perdido para sempre — o AVA reconstrói —, mas a lista inteira some da tela e o app reinicia, e isso merece um passo a mais mesmo vindo da paleta.

## Rejeitados

- **Enfileirar só as matérias vigentes.** Duas ou três requisições em vez de 26, e as finalizadas seguiriam sob demanda. Descartado por decisão explícita: o objetivo é o app completo offline, não só o semestre corrente.
- **Disparar pelo cursor parado, com debounce.** Faria o trabalho seguir a atenção do usuário e nunca buscar o que ele não olhou. É o mesmo debounce que a [0004](0004-tui-em-textual.md) já recusou: reabre rolar-a-lista virando requisição, e não é background, é sob demanda com atraso.
- **Fila paralela, com várias requisições em voo.** Cortaria os 13 segundos para uns 3. Impossível sem uma sessão por worker: está medido que três `sync()` concorrentes na mesma `AsyncSession` produzem 74 falhas em 25 rodadas.
- **Manter `sincronizando` ligado durante a fila inteira.** Uma linha a menos e nenhum risco de concorrência. Descartado porque tranca `r`, `s` e `⏎` por 13 segundos e transforma o background em primeiro plano com outro nome.
- **Reset zerando só os carimbos.** Um `UPDATE`, nenhum `DELETE`, e o dado velho sobrevive a uma queda de rede logo depois. Perde para o arquivo porque não limpa schema, que é o que a [0005](0005-trabalhos.md) torna relevante.
- **Reset apagando as linhas de atividade e mantendo as matérias.** Evitaria o restart e a lista continuaria na tela. Mas é literalmente o defeito 1 da [0002](../pending/0002-estrategia-de-testes.md) — "404 apaga o cache" — promovido a funcionalidade, e ainda deixaria o schema intocado.
- **Um `Banco` injetado nos repositories, com `recycle()`.** Recicla a sessão sem reiniciar e preserva o cursor. Custa mudar os dois repositories de hoje e os três que a [0005](0005-trabalhos.md) ainda vai escrever, além de uma indireção em toda leitura.
- **A App recebendo serviços novos de uma fábrica.** Também evita o restart e não toca nos repositories. Descartado porque afrouxa a injeção por construtor, que é a costura de que o `run_test()` da camada 5 da [0002](../pending/0002-estrategia-de-testes.md) depende.

## O que a execução corrigiu

- **A flag do consumidor, ligada dentro do worker, criava vários consumidores.** `@work` só agenda, então dois enfileiramentos seguidos disparavam duas filas paralelas — e paralelas é exatamente o que não pode. É a mesma lição que a [0004](0004-tui-em-textual.md) já tinha registrado para o guarda dela: quem liga a flag é o método síncrono, não o worker.
- **A deduplicação matava a preempção.** Pular o que já está na fila é o que faz `r` batido valer uma requisição, mas aplicado sem exceção fazia o pedido do usuário ser ignorado quando a matéria já estava enfileirada no fim. Pedido do usuário passa a promover; o resto continua sendo pulado.
- **O guarda por tecla foi substituído pelo consumidor serial**, e não estreitado como esta spec previa. Está reescrito na decisão acima.
- **O widget de loading não aparece em `query`.** O Textual o monta como *cover*, fora da árvore normal, então quem for testá-lo olha `_cover_widget` — vale para a camada 5 da [0002](../pending/0002-estrategia-de-testes.md).
- **`$accent` não é markup do `rich`.** As linhas da lista são renderables do `rich`, não do Textual: variável de CSS ali dentro vira `MarkupError` no fechamento da tag. Cor de selo é nome de cor do `rich`.
- **Cancelar o fetch exigiu blindar a escrita.** A primeira tentativa cancelava e dava `rollback()`, e colidia com o próprio cancelamento (`IllegalStateChangeError`). Virou `asyncio.shield`, descrito na decisão acima.

## Ordem de execução

1. **O consumidor serial.** Um worker único que drena a fila, com `sincronizando` reduzido a sinal de carregamento e `check_action` removido.
2. **A fila.** Serial, alimentada depois do sync de matérias, com preempção pelo usuário e progresso na tela.
3. **A pausa e a animação.** `PAUSA_ENTRE_MATERIAS` entre itens, interrompível por pedido do usuário, e o `Carregando` em `get_loading_widget`.
4. **O reset.** Comando na paleta, sinal na App, modal de confirmação, e o laço no `main.py`.
5. **0002**: a camada 5 ganha os casos da fila (preempção, serialidade, cursor livre durante a varredura) e o mapa de risco ganha a entrada do reset — apagar o arquivo com a sessão viva é o defeito que esta spec existe para não cometer.
