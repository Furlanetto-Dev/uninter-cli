---
name: camadas-crawler-api-cli
description: Reorganização de src/ em três camadas — crawler (requests e DTOs do AVA), api (entities, repositories, services) e cli. Traz o mapa origem/destino de cada arquivo, os renomes de tipo e a direção aceita das dependências. Ler antes de criar módulo novo ou decidir onde um arquivo mora.
projects: [all]
status: done
created_at: 2026-09-02
---

# Camadas: crawler, api e cli

Hoje `src/` se organiza por domínio: `materias/` e `atividades/` guardam lado a lado a entity que vira tabela, o payload que vem do AVA e o service que costura os dois. Funciona, mas apaga justamente a fronteira que mais importa aqui — a que separa o que a Uninter devolve do que nós modelamos. Um alias de JSON e uma coluna de SQLite não deveriam ser vizinhos de pasta.

A reorganização troca o eixo: primeiro a camada, depois o domínio. Nenhum comportamento muda; é mover, renomear e reapontar import. O vocabulário está em [CONTEXT.md](../../../../CONTEXT.md), as decisões de desenho em [0001](0001-crawler-de-atividades-do-ava.md) e os testes planejados em [0002](../pending/0002-estrategia-de-testes.md).

## A estrutura alvo

```
src/
  main.py                     composition root, inalterado no conteúdo
  settings.py                 RU, senha, id_curso e APP_ROOT
  crawler/                    tudo que fala com o AVA
    session.py                ava_client, AvaSession, LoginRejected
    dto.py                    AvaDTO (base), LoginDTO, UsuarioDTO
    materias/
      dto.py                  MateriaDTO, MateriasDTO
      request.py              MateriaRequest
    atividades/
      dto.py                  ProvaDTO, AtividadeDTO, AtividadesDTO
      request.py              AtividadeRequest
  api/                        o que é nosso: o que persiste e o que decide
    db.py                     db_session, DATABASE_PATH, MAPPED_TABLES
    materias/
      entity.py  repository.py  service.py
    atividades/
      entity.py  media.py  repository.py  service.py
  cli/                        inalterado
    app.py  format.py  prompts.py  render.py
```

O pacote `infra/` desaparece. Ele nunca foi uma camada: era o pouso de dois arquivos que não cabiam em `materias/` nem em `atividades/`, e cada um pertence a um lado diferente da nova fronteira.

## De onde para onde

| Hoje | Depois |
| --- | --- |
| `infra/ava.py` | `crawler/session.py` + `crawler/dto.py` |
| `materias/gateway.py` | `crawler/materias/dto.py` + `crawler/materias/request.py` |
| `atividades/gateway.py` | `crawler/atividades/dto.py` + `crawler/atividades/request.py` |
| `infra/db.py` | `api/db.py` |
| `materias/{entity,repository,service}.py` | `api/materias/` |
| `atividades/{entity,media,repository,service}.py` | `api/atividades/` |
| `cli/*`, `main.py`, `settings.py` | no lugar |

Renomes que acompanham a mudança: `AvaPayload` → `AvaDTO`, `LoginPayload` → `LoginDTO`, `UsuarioPayload` → `UsuarioDTO`, `_MateriaPayload` → `MateriaDTO`, `_MateriasPayload` → `MateriasDTO`, `_ProvaPayload` → `ProvaDTO`, `_AtividadePayload` → `AtividadeDTO`, `_AtividadesPayload` → `AtividadesDTO`, `MateriaGateway` → `MateriaRequest`, `AtividadeGateway` → `AtividadeRequest`.

## Decisões

### DTO é o nome, e ele deixa de ser privado

`Payload` descrevia a origem do dado; `DTO` descreve o papel — o objeto que atravessa a fronteira e morre logo depois, convertido em entity. O prefixo `_` existia para marcar como privado dentro de `gateway.py`; num módulo chamado `dto.py` esses tipos são o conteúdo, não um detalhe escondido, e os testes da camada 2 de [0002](../pending/0002-estrategia-de-testes.md) precisam nomeá-los.

### Request, não gateway

`crawler/materias/request.py` guarda `MateriaRequest`, com o mesmo `fetch()` de sempre. "Gateway" era o nome genérico de porta de saída; agora a camada inteira já diz que é saída, e o que sobra para o arquivo nomear é o que ele de fato é — uma requisição ao AVA, com a URL montada e a resposta validada. Substantivo em português, método em inglês, como no resto do repositório.

### A conversão continua no DTO

`MateriaDTO.to_materia()` e `AtividadeDTO.to_atividade()` ficam onde estão. Quem conhece o formato torto do AVA é o DTO; mover o mapeamento para o request só espalharia o conhecimento dos aliases por dois arquivos.

### As dependências apontam para `api`, com uma exceção assumida

- `cli` → `api` para tudo que é dado, e `crawler.session` para uma única coisa: `LoginRejected`, que ela captura para renderizar o motivo da recusa.
- `crawler` → `api`, só as entities, por causa dos `to_materia`/`to_atividade`.
- `api/*/service.py` → `crawler`, para anotar o request e o `AvaSession` que recebe por construtor.
- `main.py` → todos, que é o trabalho dele.

A terceira seta é a suja: um service do domínio importando o adaptador. Aceita porque o único jeito de eliminá-la é declarar Protocols para dois objetos com um método cada. Não há ciclo de import hoje — as entities não importam services — mas ele passa a ser possível, então **entity nunca importa service ou request**.

A primeira seta tem a exceção do `LoginRejected` porque exceção atravessa camada por natureza: quem sabe que o AVA recusou o login é o crawler, e quem sabe o que fazer com isso é a tela. Traduzir para um erro de `api` seria uma classe a mais que só repassaria a mensagem.

### O banco não é tocado

O nome da tabela sai do nome da classe, e nem `Materia` nem `Atividade` mudam de nome ou de campo. `uninter.db` segue válido depois da mudança; se um `select` quebrar, é import errado, não schema.

### 0002 é atualizado no mesmo commit

A seção "Onde os testes moram" espelha `src/` e passa a mentir no minuto seguinte a esta mudança. A árvore de `tests/` acompanha as camadas: `tests/crawler/`, `tests/api/`, `tests/cli/`. Os testes ainda não existem, então é edição de spec, não de código.

## Rejeitados

- **Protocols em `api` para inverter a dependência do service.** Purista e defensável, mas custa duas classes de um membro cada para um projeto com dois requests, e afasta o tipo real do lugar onde o erro apareceria. Se um terceiro gateway surgir, revisitar.
- **`crawler/materias.py` e `crawler/atividades.py`, com DTO e request no mesmo arquivo.** Duas pastas a menos, mas repete o defeito que a reorganização vem consertar: o formato do AVA e a chamada HTTP colados. E a pasta por domínio é o idioma que o repositório já usa.
- **Um `crawler/dto.py` único com todos os payloads.** O de atividade tem três classes aninhadas e vai crescer quando alguém quiser mais campos; misturar com matéria transforma o arquivo num depósito.
- **Manter `infra/` para `db.py` e `session.py`.** Junta de novo, sob um rótulo vago, exatamente os dois arquivos que pertencem a camadas opostas.
- **Mover `settings.py` para dentro de alguma camada.** É lido por `api/db.py` (via `APP_ROOT`) e por `main.py`; na raiz de `src/` ele não pertence a ninguém, que é o correto.
- **Aproveitar a mudança para corrigir os quatro defeitos conhecidos.** Estão listados em [0002](../pending/0002-estrategia-de-testes.md) e esperam teste vermelho primeiro. Uma reorganização em que nada de comportamento muda é uma reorganização que se revisa lendo os imports.

## Ordem de execução

1. **`crawler/`** — `session.py` e `dto.py` a partir de `infra/ava.py`, depois os dois pares `dto`/`request` a partir dos `gateway.py`.
2. **`api/`** — `db.py`, e as entities, repositories, services e `media.py` movidos sem edição além do import.
3. **`cli/` e `main.py`** — só reapontar import; `render.py` e `prompts.py` passam a importar de `api.*`.
4. **Limpeza e conferência** — apagar `infra/`, `materias/`, `atividades/` e os `__pycache__` órfãos, rodar `pdm run start` e abrir uma matéria com e outra sem cache.
5. **0002** — atualizar a árvore de `tests/` para as três camadas.
