---
name: trabalhos
description: Trabalhos de uma matéria e suas correções — a cadeia etapa → entrega → etiqueta, as três tabelas, o sync em cascata e quais "detalhes" da tela do AVA são alcançáveis. Ler antes de mexer em qualquer coisa sob crawler/trabalhos ou api/trabalhos.
projects: [crawler, api]
status: done
created_at: 2026-09-02
---

# Trabalhos e suas correções

Uma matéria tem atividades e trabalhos. As atividades já são espelhadas; os trabalhos não, e é neles que mora a entrega prática do aluno — protocolo, anexos, nota e o comentário de quem corrigiu. Esta spec cobre **apenas crawler e api**: nada de interface, e nenhuma mudança na TUI da [0004](../done/0004-tui-em-textual.md). O que o projeto é está em [CONTEXT.md](../../../../CONTEXT.md), as decisões de desenho em [0001](../done/0001-crawler-de-atividades-do-ava.md), as camadas em [0003](../done/0003-camadas-crawler-api-cli.md) e os testes em [0002](../pending/0002-estrategia-de-testes.md).

## Comportamento observado

Verificado contra a API real em 2026-09-02, com login novo e a conta inteira varrida. Onde for dedução, está dito.

- **A cadeia é auto-suficiente.** Todo id que o passo seguinte precisa vem da resposta anterior: `trabalhoEtapas[].id` e `trabalhoEtapas[].idTrabalhoVinculadoEtapa` montam a URL da entrega; `trabalhoEntregas[].idTrabalhoCorrecao` monta a URL das etiquetas. Nada precisa ser adivinhado nem configurado.
- **A listagem quer as duas ofertas, em posições diferentes**: `oferta_atual` no path, `oferta_aproveitamento` na query. É o oposto do endpoint de atividades, que só aceita a resolvida — e por isso `Materia.oferta` não serve aqui.
- **Quando não há oferta de aproveitamento, passar a atual nas duas posições funciona.** Verificado nas duas matérias da conta em que ela é nula; ambas devolveram trabalhos.
- **404 significa "matéria sem trabalho"**, e é o caso de 13 das 26 matérias. Mesma ambiguidade da [0001](../done/0001-crawler-de-atividades-do-ava.md): erro real e ausência chegam iguais.
- **O leque é pequeno.** 19 etapas na conta inteira: a maioria das matérias tem 1, uma tem 2 e duas têm 4. Oito têm entrega feita. As 26 matérias foram varridas em 1,6s.
- **`totalRegistros` mente.** Vem 0 na listagem de etapas e nas etiquetas, mesmo com registro na resposta. Não serve para detectar vazio.
- **A etiqueta não sabe de quem é.** `trabalhoCorrecaoEtiquetas[].idTrabalhoEntrega` vem 0. Só quem fez a requisição sabe a qual correção o resultado pertence.
- **`aprovadoEtapa` é tri-estado.** Vem `true`/`false` nos 8 trabalhos avaliados e `null` nos 11 que não foram. O `default=` do Pydantic não cobre isso: ele só vale quando a chave falta, não quando o valor é nulo. Varridos os 19, também aceitam nulo `dataInicio`, `dataFim`, `dataEntrega`, `notaEtapa` e `mensagemErro`; nenhum campo de entrega ou de etiqueta veio nulo nas 8 amostras.
- **O texto da etiqueta é HTML.** A devolutiva do tutor vem com `<br />` e entidades como `&gt;`, às vezes com milhares de caracteres. Guardamos cru; converter é problema de quem for exibir.
- **A correção não é recurso próprio.** Seu resumo — corretor, RU do corretor, data, contagem de arquivos — vem embutido na entrega. Só as etiquetas têm endpoint.
- **O próprio AVA trata as duas como coisas separadas.** O menu lateral da sala virtual lista "Atividades" e "Trabalhos" como seções irmãs, cada uma com sua tela.
- **A nota do trabalho não aparece entre as atividades.** Em Engenharia de Software o trabalho tem nota 100, e nenhuma das 7 atividades da matéria corresponde a ele; os pesos das atividades somam 70%. A entrega traz `idAvaliacaoUsuario`, mas o id não bate com nenhuma atividade retornada para a matéria.

## Decisões

### Trabalho pendura na matéria, ao lado de atividade

A URL da listagem só pede as ofertas da matéria, e a nota do trabalho não tem correspondente na lista de atividades. São duas coleções irmãs, e sincronizar trabalhos não depende de haver atividade nenhuma no banco.

### `idAvaliacaoUsuario` não vira chave estrangeira

O campo existe na entrega e é tentador, mas o id não resolve para nenhuma atividade que a API devolva para aquela matéria. Persistir como FK criaria referência pendurada. Fica de fora até que alguém demonstre para onde ele aponta.

### Três tabelas, espelhando os três endpoints

`trabalho` para a etapa, `trabalho_entrega` para a entrega com o resumo da correção achatado dentro — porque é assim que o AVA a entrega —, e `trabalho_etiqueta` para os itens do formulário de correção. A etiqueta é chaveada pelo `correcao_id` que originou a requisição, já que a resposta não o traz.

Seguindo a [0001](../done/0001-crawler-de-atividades-do-ava.md), guardamos só o que a tela usa: 14 dos 33 campos da etapa, 13 dos 48 da entrega, 3 da etiqueta.

### O sync desce a cascata inteira, por matéria

Um método, um carimbo, uma transação. Sincronizar uma matéria custa de 2 a 3 requisições e menos de 200ms — o argumento que justificou o sob-demanda das atividades (27 matérias a meio segundo cada) não se aplica a um leque de 1 a 4 trabalhos. Em troca, nunca existe trabalho meio sincronizado no banco.

### O carimbo é próprio

`materia.trabalhos_sincronizados_em`, separado do carimbo das atividades. As duas coleções vêm de endpoints diferentes, com custos diferentes, e uma pode estar fresca com a outra velha.

### Anexos e gabarito ficam de fora

A entrega diz **quantos** arquivos existem (`totalArquivosEntrega`, `totalArquivosCorrecao`), mas listá-los exige um endpoint que não foi capturado. O mesmo vale para o gabarito. Pela regra do projeto não se sai procurando endpoint: ambos ficam registrados como pendência de captura.

## Os "detalhes" da tela, e de onde cada um vem

| detalhe | origem | alcançável |
|---|---|---|
| Detalhes da etapa | `trabalhoEtapas[]` — nome, `dataInicio`, `dataFim`, `nomePeriodo`, `nomeTrabalhoTipo`, `ordemTrabalho` | sim |
| Detalhes da entrega | `trabalhoEntregas[]` — `protocolo`, `dataCriacao`, `nomeTrabalhoStatus`, `tentativa`, `finalizadoTrabalhoStatus` | sim |
| Bloco Correção | `trabalhoEntregas[]` — `nomeUsuarioCorretor`, `RUUsuarioCorretor`, `dataCriacaoCorrecao` | sim |
| Detalhes da correção | `trabalhoCorrecaoEtiquetas[]` — `constante`, `texto` | sim |
| Anexos | só o contador `totalArquivosEntrega` | **falta captura** |
| Gabarito | — | **falta captura** |
| Editar | operação de escrita, sinalizada por `podeEditar` | fora de escopo |

## As tabelas

```
trabalho                          de trabalhoEtapas[]
  materia_id     FK materia.id
  id             PK  (= trabalhoEtapas[].id)
  vinculado_etapa    idTrabalhoVinculadoEtapa, monta a URL da entrega
  nome, tipo         nome, nomeTrabalhoTipo
  ordem, periodo     ordemTrabalho, nomePeriodo
  inicio, fim        dataInicio, dataFim
  entregue_em        dataEntrega
  nota, aprovado     notaEtapa, aprovadoEtapa
  pode_entregar      podeEntregar
  mensagem           mensagemErro

trabalho_entrega                  de trabalhoEntregas[]
  trabalho_id    FK trabalho.id
  id             PK
  tentativa, protocolo, criado_em
  status, finalizado    nomeTrabalhoStatus, finalizadoTrabalhoStatus
  nota                  notaEtapa
  correcao_id           idTrabalhoCorrecao
  corretor, corrigido_em  nomeUsuarioCorretor, dataCriacaoCorrecao
  anexos_entrega, anexos_correcao

trabalho_etiqueta                 de trabalhoCorrecaoEtiquetas[]
  correcao_id    FK trabalho_entrega.correcao_id
  id             PK
  constante, texto
```

## As tarefas

Cada uma é pequena e verificável sozinha. A ordem respeita as dependências.

**Preparação**

1. Trocar o cookie de sessão vivo nos três curls de `uninter-endpoints/trabalhos/` por placeholders, como nos demais.

**Camada crawler**

2. `crawler/trabalhos/dto.py`: `TrabalhoEtapaDTO` e `TrabalhoEtapasDTO`, com `to_trabalho(materia_id)`.
3. `crawler/trabalhos/request.py`: `TrabalhoRequest.fetch(materia)`, montando path com `oferta_atual` e query com `oferta_aproveitamento or oferta_atual`, 404 → lista vazia.
4. `EntregaDTO` e `EntregasDTO`, com `to_entrega(trabalho_id)`.
5. `EntregaRequest.fetch(trabalho)`, usando `trabalho.id` e `trabalho.vinculado_etapa`.
6. `EtiquetaDTO` e `EtiquetasDTO`, com `to_etiqueta(correcao_id)`.
7. `EtiquetaRequest.fetch(correcao_id)`.

**Camada api**

8. `api/trabalhos/entity.py`: `Trabalho`.
9. `api/trabalhos/entity.py`: `TrabalhoEntrega`.
10. `api/trabalhos/entity.py`: `TrabalhoEtiqueta`.
11. Coluna `trabalhos_sincronizados_em` em `Materia`, e o par `mark_trabalhos_synced` no `MateriaRepository`.
12. Registrar as três tabelas em `MAPPED_TABLES` (`api/db.py`).
13. `api/trabalhos/repository.py`: `list_all(materia)`, `replace(materia, trabalhos)`, e as leituras de entrega e etiqueta.
14. `api/trabalhos/service.py`: `TrabalhoSyncService.sync(materia)` descendo a cascata e commitando uma vez.

Levar os trabalhos até a tela e capturar os endpoints de anexo e gabarito ficam na [0005.1](../pending/0005.1-trabalhos-na-interface.md).

## Rejeitados

- **Trabalho como filho de atividade.** A API não aceita id de atividade em lugar nenhum da URL, a nota do trabalho não aparece na lista de atividades, e o próprio AVA separa as duas em seções distintas do menu. A ligação teria que ser inventada por nome ou peso.
- **Uma tabela achatada.** Cabe hoje, porque toda etapa da conta tem no máximo uma entrega. Mas o campo `tentativa` e o rótulo "1ª entrega" da tela dizem que existe N, e achatar agora significa migração quando aparecer a segunda.
- **Etiquetas como JSON numa coluna da entrega.** Evitaria uma tabela e um join, ao custo de não dar para filtrar por `constante` em SQL e de introduzir o único campo-documento do schema.
- **Sync sob demanda por nível.** Seguiria o padrão das atividades ao pé da letra, com três carimbos e três métodos. Economiza uma ou duas requisições por matéria e paga com "trabalho meio sincronizado" virando estado normal do banco.
- **Varrer a conta inteira num comando.** 53 requisições e uns 4 segundos para o banco completo, sendo 13 delas garantidamente 404. Contraria a decisão da [0001](../done/0001-crawler-de-atividades-do-ava.md) de que a rede só entra quando o usuário pede aquela matéria.
- **Procurar os endpoints de anexo e gabarito.** Exigiria engenharia reversa do SPA. Ficam pendentes de captura no DevTools.
