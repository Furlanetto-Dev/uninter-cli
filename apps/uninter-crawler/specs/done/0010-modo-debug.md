---
name: modo-debug
description: Modo debug na TUI — comando na paleta, `d` no rodapé, painel com a resposta bruta do AVA ao lado do que foi gravado no SQLite; exige a entity `Captura`, escrita em todo sync. Ler antes de mexer no retorno de `AvaSession.get` e dos `fetch`, ou no layout do painel de detalhe.
projects: [crawler, api, frontend]
status: done
created_at: 2026-09-08
---

# Modo debug

## TL;DR
- Toda resposta do AVA passa a ser gravada na entity `Captura` (recurso, matéria, URL, status, corpo), no mesmo commit das entities.
- Um comando na paleta liga o modo debug; ligado, `d` aparece no rodapé.
- `d` abre no painel da matéria uma tabela: bruto do AVA à esquerda, linha gravada à direita, uma linha por objeto.
- Terminal com 40 linhas ou mais: o painel fica embaixo da média. Menos: substitui a tabela de atividades.

Hoje o corpo da resposta morre dentro do `fetch`, e quando um valor parece errado não dá para saber se a culpa é do AVA, do DTO ou da tela. Contexto em [CONTEXT.md](../../../../CONTEXT.md); 404 na [0001](0001-crawler-de-atividades-do-ava.md), camadas na [0003](0003-camadas-crawler-api-cli.md), `check_action` na [0004](0004-tui-em-textual.md), paleta na [0007](0007-fila-em-background-e-reset.md), nomes na [0009](../pending/0009-english-code-portuguese-domain.md), fixtures na [0002](../pending/0002-estrategia-de-testes.md).

## Comportamento observado
- `AvaSession.get` devolve só o JSON parseado, ou `None` no 404; URL, status e texto se perdem. Lido no código.
- Terminal de 44 linhas deixa umas 26 vazias sob a média; de 17, a tabela sozinha enche o painel. Duas capturas de tela.
- Textual 8.2.8: `VERTICAL_BREAKPOINTS` põe uma classe na `Screen` por faixa de altura a cada `Resize`. Verificado no fonte.
- `check_action` devolvendo `False` esconde a tecla do `Footer` (medido na 0004); mudar a condição exige `refresh_bindings()`.
- Um item bruto de atividade tem uns 160 campos (0002). Inferência, não medida: cerca de 1 MB de banco com as 26 matérias.

## Decisões

### O modo é um `reactive` da sessão, ligado pela paleta
`debug_mode = reactive(False)` na App; comando em `AppCommands` com rótulo "Enable/Disable debug mode" conforme o estado — os comandos da paleta são em inglês. Nasce desligado e não persiste: debug é reação, não configuração. Desligar fecha o painel.

### `d` só existe no rodapé com o modo ligado
`("d", "debug", "debug")` em `BINDINGS`; `check_action` devolve `False` com o modo desligado e `watch_debug_mode` chama `refresh_bindings()`. `d` alterna o painel.

### O painel mora em `#detail` e segue o cursor
`DebugPanel` (`cli/debug/panel.py`) depois da `MediaBar`, alimentado por `show_materia`. Não é `Screen`: tela empilhada congela a matéria, e a seta trocar de matéria é o que a 0004 comprou. `MateriaHeader` fica visível nos dois modos.

### Dois modos por altura do terminal, por breakpoint
`VERTICAL_BREAKPOINTS = [(0, "-short"), (TALL_TERMINAL_ROWS, "-tall")]`, com `TALL_TERMINAL_ROWS = 40`; painel aberto põe `-debug` na `Screen`. Em `-tall` o painel é `1fr` sob a média; em `-short` o CSS esconde `#grades`, o `Vertical` que passa a envolver tabela e média. A conta: 21 linhas ocupadas na pior matéria mais 15 legíveis de painel dá 36, arredondado para 40.
`#grades` existe porque `MediaBar.show()` seta `display` inline, que vence CSS; esconder o pai resolve.

### Tabela de duas colunas, uma linha por objeto
`VerticalScroll` com uma `rich.Table`: cabeçalho com URL, status e hora; a matéria (entrada de `salaVirtuais` | `Materia.model_dump()`); uma linha por atividade (`avaliacaoUsuarios[i]` | `Atividade` de `posicao == i`). Bruto com `JSON.from_data`, gravado com `Pretty`. O painel não conhece alias, então serve para trabalhos quando a 0005.1 chegar.
Sem captura: "sem resposta gravada · `r` para buscar". 404: status e texto à esquerda, linhas gravadas à direita — deixa visível o defeito 1 da 0002 sem consertá-lo.

### `d` abre o painel sem roubar o foco; `tab` entra nele, `esc` volta
As setas continuam trocando a matéria, e o painel acompanha. Para rolar o JSON, `tab` ou a roda do mouse levam o foco ao painel, e `("escape", "app.focus_materias", "voltar")` o devolve à lista — a ação é da App, para o painel não conhecer a lista. As colunas rolam juntas para manter o alinhamento.

### A resposta é gravada sempre, na entity `Captura`
`api/capturas/entity.py`: `id`, `recurso`, `materia_id | None`, `url`, `status`, `corpo`, `recebida_em`. É entity, logo português (0009). `CapturaRepository.replace` apaga por `(recurso, materia_id)` e insere; `find` alimenta o painel. Grava com debug ligado ou não: quem enche o banco é a fila da 0007, e o reset já apaga tudo. Bônus: são as fixtures reais que a 0002 pede.

### O corpo atravessa as camadas junto com as entities
`AvaSession.get` devolve `AvaResponse(url, status, text, json)`; cada `fetch` devolve `FetchResult(response, entities)`; `AvaResponse.to_captura(recurso, materia_id)` cria a entity como `to_atividade` faz. Os services gravam captura e entities na mesma transação (`_store`, sob o `shield`). Muda a assinatura de `fetch`, que a camada 2 da 0002 testa.

## Rejeitados
- **Só em memória.** Vazio depois de reiniciar.
- **Capturar só com debug ligado.** A fila faz a maioria dos syncs; o painel ficaria vazio.
- **Observer em `AvaSession`.** Só conhece a URL, e bruto e gravado cairiam em commits separados.
- **Coluna bruta em `Materia`.** Coluna nova exige reset; não serve para a lista nem para trabalhos.
- **`Screen` ou `ModalScreen`.** Congela a matéria.
- **Medir o espaço depois do layout.** Depende de layout assentado e pisca um frame.
- **Tabela campo a campo.** Introspecção de alias e 160 linhas por atividade. Evolução possível.
- **Empilhar bruto sobre gravado, ou rolagem por coluna.** Perde o alinhamento.
- **`d` focar o painel ao abrir.** Foi a primeira versão: roubava as setas da lista a cada abertura, e quem abre o debug quer continuar navegando.
- **`j`/`k` na App, `UNINTER_DEBUG`, breakpoint horizontal.** Gasta rodapé; debug é reação; o painel tem 90+ colunas nas capturas.

## O que a execução corrigiu
- `debug` colide com `App.debug` do Textual (o modo debug do framework): o reactive virou `debug_mode`.
- `cli/` foi reorganizado em diretórios por contexto — `materias/`, `atividades/`, `commands/`, `animations/`, `debug/` — antes desta spec; o painel mora em `cli/debug/panel.py` e o rótulo da paleta em `cli/debug/command.py`.
- Verificado sem rede, com `run_test` e requests falsos: captura gravada e substituída, 404 com o texto, `d` escondida e visível, painel seguindo o cursor e refeito depois de `r`, `#grades` sumindo em 24 linhas.
- A etapa da 0002 ficou para quando os testes existirem, como na 0007.
