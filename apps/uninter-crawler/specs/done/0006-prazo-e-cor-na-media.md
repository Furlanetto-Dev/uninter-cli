---
name: prazo-e-cor-na-media
description: Duas colunas de informação que já estavam no banco e não apareciam — o prazo de cada atividade e a situação da média pelas faixas do próprio AVA, com a régua escrita na tela. Traz a escala 0–100 da nota, a faixa 67–69 que o AVA não cobre e por que a média parcial fica sem cor. Ler antes de mexer em cli/atividades.py ou em qualquer coisa que pinte nota.
projects: [frontend]
status: done
created_at: 2026-09-02
---

# Prazo e cor na média

A tabela da matéria mostra nome, situação, nota, peso e contribuição. Faltam as duas coisas que o aluno de fato quer saber ao abrir uma matéria: **até quando** cada atividade vale, e se a média **passa**. A primeira já está no banco desde o começo e nunca foi desenhada; a segunda precisa de uma régua, e o AVA publica a dele.

Esta spec mexe só no que a tela desenha: nenhuma requisição nova, nenhuma coluna nova no banco, nenhuma assinatura alterada. O que o projeto é está em [CONTEXT.md](../../../../CONTEXT.md), a interface em [0004](0004-tui-em-textual.md) e os testes em [0002](../pending/0002-estrategia-de-testes.md).

## Comportamento observado

Medido em 2026-09-02 contra o `uninter.db` real da conta, com 26 matérias e 37 atividades:

- **`inicio` e `fim` vêm preenchidos em 37 de 37.** São persistidos desde a [0001](0001-crawler-de-atividades-do-ava.md) e nunca foram exibidos. O tipo continua opcional, mas na prática o dado sempre está lá.
- **A nota é 0–100, não 0–10.** Os valores da conta vão de 60 a 100, e `contribuicao = nota × peso / 100` — nota 100 com peso 15 dá contribuição 15,0; nota 70 com peso 40 dá 28,0. Como `Media.valor` é a soma das contribuições, **a média já está na mesma escala 0–100 dos critérios do AVA**, sem conversão nenhuma.
- **Situação e prazo discordam.** 8 atividades com status `Aguardando início` têm `fim` no passado, e 7 `Finalizada` têm `fim` no futuro. A coluna de prazo não pode ser estilizada a partir do `status`: "vencida" só sai de comparar `fim` com o relógio.
- **O AVA publica os próprios critérios de aprovação** na tela da sala virtual, em "Critérios de aprovação (período Regular)": `de 70 até 100` APR.MÉDIA, `de 30 até 66` EM EXAME, `de 0 até 29` REP.MÉDIA. A tela tem três abas — Regular, Exame e Recuperação —, cada uma com sua tabela.
- **A tabela publicada pula 67, 68 e 69.** Vai de "até 66" direto para "de 70", e nenhuma das três situações cobre essa faixa.
- **Só 2 das 5 matérias com atividades têm 100% do peso lançado.** As outras três estão em 30%, 0% e 0% — o estado parcial é o normal, não a exceção.

Não medido: os critérios vieram da tela, não de um endpoint capturado. As faixas de Exame e Recuperação não foram vistas.

## Decisões

### O prazo é uma coluna, e vem de `fim`

Uma coluna `Prazo` no fim da tabela, com `fim` formatado como `dd/mm/aa`. O ano é obrigatório: as atividades da conta vão de 2025 a 2026 e um `dd/mm` seco seria ambíguo entre semestres.

Vencida e não realizada aparece em vermelho; vencida e realizada, apagada, porque o prazo já não decide nada. O corte sai da comparação com o relógio, não do `status` — pelo dado observado, os dois discordam em 15 das 37 atividades.

### A cor da média usa a régua do próprio AVA

`≥ 70` verde, `30–69` amarelo, `< 30` vermelho.

O 70 não é escolha nossa: é o que o AVA publica na tela da sala virtual, com nome próprio — APR.MÉDIA. A cor copia a classificação da instituição em vez de propor uma.

O que a cor **não** faz é projetar: nada de calcular quanto falta para passar, nada de simular cenário com as atividades que ainda não têm nota. Ela classifica o que já está lançado, e só isso.

### A faixa 67–69 fecha para baixo

A tabela do AVA não cobre 67, 68 e 69. Fechamos o intervalo do exame para cima — `30–69` — em vez de deixar três valores sem cor. É a leitura conservadora: um 68 não é aprovação por média em lugar nenhum da tabela, e pintá-lo de verde afirmaria mais do que o AVA afirma.

Fica registrado como divergência consciente da fonte, e não como leitura dela.

### Média parcial não recebe cor

A cor só entra quando `peso_lancado` chega a 100. Análise e Modelagem tem média 22,5 com 30% do peso lançado: pelas faixas isso é REP.MÉDIA, mas a matéria mal começou e o aluno vai a 75% do que já foi corrigido. Os critérios do AVA classificam o **fechamento** da matéria; aplicá-los a uma soma incompleta é usá-los fora de contexto, e transformaria "vermelho" no estado normal de quem ainda não fez prova.

O custo aceito é que hoje só 2 das 5 matérias mostrariam cor. O `(30% do peso lançado)` que já está na tela continua sendo o que explica a ausência.

### Os critérios ficam escritos abaixo da média

Uma linha permanente sob a `MediaBar`, com cada faixa na sua própria cor:

```
média 76,0  (100% do peso lançado)
≥ 70 aprovado · 30–69 exame · < 30 reprovado
```

Fica ao lado do número que ela explica, não exige descobrir tecla nenhuma, e ocupa uma linha que hoje está vazia. Como a régua é a mesma para toda matéria, repeti-la por matéria não incomoda — e sem ela a cor seria um código sem legenda.

### Só o período Regular

As abas Exame e Recuperação têm critérios próprios que não foram capturados, e nenhum campo da API diz em que período o aluno está numa matéria. A linha de legenda não promete mais do que sabe.

### As faixas são constantes do módulo, não descoberta

Os três limites moram em constantes nomeadas em `cli/atividades.py`. Não se sai atrás do endpoint que serve essa tabela: é a regra do projeto, e o que falta vira configuração ou pergunta. Se as faixas mudarem, muda-se a constante — e a única forma de descobrir que mudaram é a mesma tela de onde elas vieram.

## Rejeitados

- **Colorir a média parcial com as mesmas faixas.** É "pintar de acordo" ao pé da letra e a cor nunca falta. Mas hoje pintaria Análise e Modelagem de vermelho por causa de 70% de peso ainda não lançado, e vermelho viraria o estado padrão do meio do semestre.
- **Colorir a parcial em tom apagado.** Manteria uma regra só, com a incerteza no tom em vez da ausência. Descartado porque `dim` já significa "não realizada" na coluna Situação, e porque nem todo tema de terminal separa bem dim de normal.
- **Colorir pelo aproveitamento (`valor / peso_lancado`).** Resolveria a parcial sem perder a cor — 22,5 em 30% viraria 75%. Mas inventa uma métrica que o AVA não publica e que não corresponde a situação nenhuma da tabela dele; a cor deixaria de significar APR/EXAME/REP.
- **Colorir também a coluna Nota de cada atividade.** A nota já é 0–100 e caberia na mesma faixa, e acharia na hora quem puxou a média para baixo. Descartado porque a coluna Situação já usa verde e dim com outro significado, e dois sistemas de cor lado a lado competem em vez de informar.
- **Legenda atrás de uma tecla de ajuda.** Deixaria a tela de leitura limpa e teria lugar para crescer quando Exame e Recuperação forem capturados. Mas esconde justamente o que dá sentido à cor, e paga um atalho a mais no Footer por isso.
- **Escrever a situação (`APR.MÉDIA`) ao lado do número, sem as faixas.** Usa o vocabulário do próprio AVA e responde direto à pergunta do aluno. Perdido para a legenda porque a cor continuaria sem régua visível — e porque a situação de uma média parcial seria uma afirmação que a decisão acima recusa fazer.
- **Prazo relativo ("vence em 3d").** Mais legível para o que está perto, e `humanize_age` já faz o análogo para o passado. Mas a maior parte das atividades da conta está a meses de distância, onde "em 87d" informa menos que a data, e o relativo obriga a reformatar a tela conforme o relógio anda.
- **Mostrar também `inicio`.** Está preenchido em 37 de 37 e caberia como "janela". Fora de escopo: o pedido é data de expiração, e uma segunda coluna de data numa tabela de cinco colunas custa largura que o nome da atividade usa melhor.

## O que a execução corrigiu

- **`Situação` passou a quebrar em duas linhas.** A sexta coluna apertou a tabela, e `Aguardando início` — que é o status de 27 das 37 atividades — virava linha dupla. A coluna ganhou `no_wrap`; o nome da atividade continua sendo o único que dobra.
- **Abaixo de ~120 colunas a tabela degrada**, com o nome dobrando e o cabeçalho `Contribuição` truncando. Aceito: o `rich` resolve sozinho e a leitura continua possível.

## Ordem de execução

1. **A coluna Prazo.** `format.py` ganha a formatação de data e o predicado de vencimento; `build_table` ganha a coluna. Nada mais muda.
2. **As faixas e a cor.** Constantes e a função que mapeia média em faixa; `MediaBar.show` passa a colorir, e só quando `media.parcial` é falso.
3. **A linha de legenda**, abaixo da média.
4. **0002**: a camada 1 ganha os casos das duas funções puras novas, e o golden de `build_table` é regerado com a coluna a mais.
