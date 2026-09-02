---
name: fila-em-background-e-reset
description: A fila que busca as atividades de todas as matérias sozinha e o comando que apaga o banco — as duas mudanças que alteram quando a rede roda e o que o cache significa. Traz a reversão explícita da 0001, a preempção da fila pelo usuário e por que apagar o arquivo obriga a App a reiniciar. Ler antes de mexer no guarda da 0004, em main.py ou em qualquer coisa que sincronize sozinha.
projects: [frontend, api]
status: pending
created_at: 2026-09-02
---

# Fila em background e reset do banco

Duas mudanças que parecem independentes e são a mesma decisão vista de dois lados: **quando a rede roda sem ninguém pedir**, e **o que faz o cache valer de novo**. Hoje abrir uma matéria nunca visitada custa meio segundo de espera, e não existe forma de recomeçar do zero a não ser apagar `uninter.db` na mão, por fora do app.

Depois desta spec o banco se enche sozinho depois do primeiro sync, e uma tecla o zera inteiro. As duas coisas se encontram no mesmo ponto: zerar o banco com a fila ligada dispara justamente a varredura completa.

O que o projeto é está em [CONTEXT.md](../../../../CONTEXT.md), as decisões de desenho em [0001](../done/0001-crawler-de-atividades-do-ava.md), a interface e o guarda de sync em [0004](../done/0004-tui-em-textual.md), e os trabalhos em [0005](../done/0005-trabalhos.md).

## Comportamento observado

**Apagar `uninter.db` com a sessão aberta deixa o app meio morto.** Medido: depois do `unlink`, as leituras **continuam funcionando** e devolvem dados do inode órfão, como se nada tivesse acontecido; as escritas falham com `OperationalError: attempt to write a readonly database`; e o arquivo não é recriado. O banco só aparece vazio quando uma sessão nova abre. É o pior estado possível — a tela mostra dado que não existe mais em disco e o próximo sync morre com erro de SQLite. Qualquer reset precisa reciclar o engine, não só apagar o arquivo.

**Dois syncs concorrentes na mesma `AsyncSession` quebram, leituras concorrentes não.** Medido na [0004](../done/0004-tui-em-textual.md): 25 rodadas de três `sync()` simultâneos deram 74 falhas (`IllegalStateChangeError`, `ResourceClosedError`, `PendingRollbackError`); um `sync()` contra 40 `list_all()` simultâneos deu zero. A fila tem que ser serial, e navegar durante ela é seguro.

**A varredura completa custa cerca de 13 segundos.** São 26 matérias a meio segundo cada, das quais 6 devolvem 404 legítimo — matéria sem atividade, indistinguível de falha, como a [0001](../done/0001-crawler-de-atividades-do-ava.md) registrou.

## Decisões

### A fila varre todas as matérias sem cache

Depois que o sync de matérias termina, uma fila enfileira **todas** as matérias sem carimbo, vigentes primeiro. Ao fim da primeira execução o app está completo offline.

Isso **reverte uma decisão registrada**, e é preciso dizer com todas as letras: a [0001](../done/0001-crawler-de-atividades-do-ava.md) aceitou como consequência que "só funciona offline aquilo que já foi visitado", e justificou o sob-demanda com o custo de sincronizar tudo de uma vez. O custo não mudou — 26 matérias a meio segundo cada. O que mudou é quem espera por ele: em background, os 13 segundos não estão na frente de ninguém.

O que sobrevive intacto da 0001 é o que importa: o SQLite continua sendo a fonte de leitura, e a rede nunca entra no caminho de uma tecla.

### Mover o cursor continua sem tocar a rede

A [0004](../done/0004-tui-em-textual.md) decidiu que o destaque lê só do banco, e isso não muda. A fila não é disparada pelo cursor, não sabe onde ele está e não muda de ordem por causa dele. Quem move o cursor durante a fila vê o cache que existir — inclusive o estado "nunca sincronizada", se aquela matéria ainda não chegou a vez.

### O guarda passa a valer por item, não pela fila inteira

O `sincronizando` da [0004](../done/0004-tui-em-textual.md) desabilita `r`, `s` e `⏎` enquanto está ligado. Mantê-lo ligado durante os 13 segundos da fila trancaria o teclado por 13 segundos, que é o oposto de "background".

A flag passa a cobrir **um item**, os cerca de 500ms de uma requisição, e cai entre um item e o outro. O que ela protege continua sendo o que precisa de proteção: dois commits simultâneos na mesma sessão. Para o rodapé não piscar 26 vezes, o estado da fila é mostrado à parte, como progresso, e não apagando atalho.

### O trabalho do usuário fura a fila

`⏎` ou `r` numa matéria entram na frente do que estiver enfileirado, e a fila retoma depois. Quem está olhando uma matéria não deve esperar as outras 25.

Como a flag agora cai entre itens, a tecla do usuário quase sempre pega a fila entre uma requisição e outra. Quando pegar no meio de uma, é bloqueada como hoje — meio segundo, não treze.

### O reset apaga o arquivo e reinicia a App

O comando descarta `uninter.db` inteiro e sobe tudo de novo. É o único reset que limpa schema órfão, o que deixa de ser detalhe agora que a [0005](../done/0005-trabalhos.md) soma três tabelas ao banco.

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

É o que resolve o inode órfão medido acima sem tocar em repository, service ou no construtor da App — a injeção por construtor da [0004](../done/0004-tui-em-textual.md) continua de pé, e a [0005](../done/0005-trabalhos.md) não precisa mudar uma linha da task list dela. O preço é a tela piscar e o cursor voltar ao topo, que para "apagar o banco" é o que se espera de qualquer forma.

### O reset pede confirmação

Um modal de sim ou não antes de apagar. Nada é perdido para sempre — o AVA reconstrói —, mas uma tecla batida sem querer custa 13 segundos de rede e a lista inteira sumindo da tela, e isso é surpresa demais para um atalho de uma letra.

## Rejeitados

- **Enfileirar só as matérias vigentes.** Seria o menor desvio da [0001](../done/0001-crawler-de-atividades-do-ava.md) — 2 ou 3 requisições em vez de 26 — e manteria as finalizadas sob demanda. Descartado por decisão explícita: o objetivo é o app completo offline, não só o semestre corrente.
- **Disparar pelo cursor parado, com debounce.** Faria o trabalho seguir a atenção do usuário e nunca buscar o que ele não olhou. É o mesmo debounce que a [0004](../done/0004-tui-em-textual.md) já recusou: reabre rolar-a-lista virando requisição, e não é background, é sob demanda com atraso.
- **Fila paralela, com várias requisições em voo.** Cortaria os 13 segundos para uns 3. Impossível sem uma sessão por worker: está medido que três `sync()` concorrentes na mesma `AsyncSession` produzem 74 falhas em 25 rodadas.
- **Manter `sincronizando` ligado durante a fila inteira.** Uma linha a menos e nenhum risco de concorrência. Descartado porque tranca `r`, `s` e `⏎` por 13 segundos e transforma o background em primeiro plano com outro nome.
- **Reset zerando só os carimbos.** Um `UPDATE`, nenhum `DELETE`, e o dado velho sobrevive a uma queda de rede logo depois. Perde para o arquivo porque não limpa schema, que é o que a [0005](../done/0005-trabalhos.md) torna relevante.
- **Reset apagando as linhas de atividade e mantendo as matérias.** Evitaria o restart e a lista continuaria na tela. Mas é literalmente o defeito 1 da [0002](0002-estrategia-de-testes.md) — "404 apaga o cache" — promovido a funcionalidade, e ainda deixaria o schema intocado.
- **Um `Banco` injetado nos repositories, com `recycle()`.** Recicla a sessão sem reiniciar e preserva o cursor. Custa mudar os dois repositories de hoje e os três que a [0005](../done/0005-trabalhos.md) ainda vai escrever, além de uma indireção em toda leitura.
- **A App recebendo serviços novos de uma fábrica.** Também evita o restart e não toca nos repositories. Descartado porque afrouxa a injeção por construtor, que é a costura de que o `run_test()` da camada 5 da [0002](0002-estrategia-de-testes.md) depende.

## Ordem de execução

1. **O guarda por item.** Separar o estado da fila do `sincronizando`, que passa a cobrir uma requisição. Sem fila ainda: só a mudança de escopo da flag, com os três caminhos da [0004](../done/0004-tui-em-textual.md) reconferidos.
2. **A fila.** Serial, alimentada depois do sync de matérias, com preempção pelo usuário e progresso na tela.
3. **O reset.** Sinal na App, modal de confirmação, e o laço no `main.py`.
4. **0002**: a camada 5 ganha os casos da fila (preempção, serialidade, cursor livre durante a varredura) e o mapa de risco ganha a entrada do reset — apagar o arquivo com a sessão viva é o defeito que esta spec existe para não cometer.
