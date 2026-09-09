---
name: novo-plano
description: "Cria uma spec nova em specs/pending com o header, a numeração e a estrutura da casa. Use quando o usuário pedir um plano, uma spec, um ADR ou um documento de decisão para um app deste repo."
---

Você vai escrever uma spec nova. Neste repo, "plano", "spec" e "documento de decisão" são a mesma coisa: um arquivo markdown em `specs/`.

# Onde o arquivo vai

`specs/pending/NNNN-<slug>.md`

- **Sempre `pending`.** `done` é para spec cujo trabalho já está feito; uma spec nova nunca nasce lá.
- `NNNN` é o próximo número livre, contando `done` **e** `pending` juntos, com 4 dígitos:
  `ls specs/done specs/pending | grep -oE '^[0-9]{4}' | sort -n | tail -1`
- **Continuação de uma spec existente usa `NNNN.M`**, como `0005.1`. Serve para o que ficou de fora da spec NNNN e depende dela: o número diz de quem é filha. Assunto novo ganha número inteiro.
- `<slug>` é o título em kebab-case, sem acento e sem artigo: `estrategia-de-testes`, não `a-estrategia-de-testes`.

# O header

YAML frontmatter no formato de skill, com cinco campos obrigatórios e nesta ordem:

```yaml
---
name: <slug, igual ao do nome do arquivo, sem o NNNN>
description: <ver abaixo>
projects: [<ver abaixo>]
status: pending
created_at: <hoje, ISO, via `date +%F`>
---
```

- `name` casa com o slug do arquivo. Sem número, sem acento.
- `projects` é um array com as partes que a spec toca. Valores válidos: `crawler`, `api`, `frontend` e `all`. Use a ordem do sentido do dado — `crawler`, depois `api`, depois `frontend`. `all` é exclusivo: ou a spec toca tudo, ou você lista as partes; nunca os dois.
- `status` usa o mesmo vocabulário do diretório — `pending` ou `done`, nunca `aceito`/`proposto`. A informação vive nos dois lugares; vocabulário idêntico é o que impede de divergirem.
- `created_at` vem de `date +%F`. Nunca chute a data.
- **Nada de `Status:` nem de data no corpo.** O header é a única fonte.

## Como escolher os projects

Liste o que a spec **muda**, não o assunto dela. Uma spec sobre a interface que migra o app inteiro para async toca os três, mesmo que o título fale só de tela.

- `crawler` — requests e DTOs do AVA, sessão HTTP
- `api` — entities, repositories, services, banco
- `frontend` — a TUI em `cli/`
- `all` — toca os três; sozinho no array

## A description é um gatilho, não um resumo

Escreva quando **abrir** a spec, não só o que ela contém. Uma frase com o conteúdo, outra começando com "Ler antes de...". É o que faz a description ser útil para quem (ou o que) está decidindo se precisa ler o arquivo.

Bom: `Decisões de desenho do crawler — cookie x-time, regra aproveitamento-ou-atual, 404 indistinguível de vazio. Ler antes de mexer em request, dto ou na resolução de oferta.`

Ruim: `Documento sobre o crawler.`

# A estrutura do corpo

Comece do [template](./template.md). Nem toda seção é obrigatória, mas a ordem é:

1. `# Título` em prosa, com acento — não é o slug.
2. `## TL;DR`, em lista: uma linha por mudança, até cinco. Quem lê só isso sabe o que a spec faz.
3. Uma ou duas frases dizendo **por que a spec existe**: o problema, e o que muda quando ela for executada. Linke o [CONTEXT.md](../../CONTEXT.md) e as specs relacionadas aqui.
4. **Comportamento observado**, quando houver sistema externo envolvido. Uma linha por fato, com o que o prova. Marque o que é inferência.
5. **Decisões**, cada uma num `###` cujo título é a decisão afirmada, não o assunto. `### O banco guarda só os campos que a tela usa`, não `### Sobre os campos`.
6. **Rejeitados**, em lista. Uma linha por item: a alternativa e o porquê de não.

## Links relativos

De `specs/pending/` até a raiz do repo são dois níveis:

- descrição do projeto: `[CONTEXT.md](../../CONTEXT.md)`
- spec irmã em done: `[0001](../done/0001-<slug>.md)`

Confira que resolvem antes de terminar.

# A régua de tamanho

**Mais de 70 linhas de texto é sinal de enrolação.** É régua, não lei: o validador conta só o que está fora de blocos cercados e avisa. Se a spec que você está escrevendo aparecer no aviso, releia procurando ideia repetida; se não houver, o tamanho está justificado.

- Não existe mínimo de texto por parágrafo, seção ou decisão. Se a ideia cabe em uma linha, é uma linha.
- Um diagrama `mermaid` que substitui parágrafos é bem-vindo — fluxo, camadas, estados, layout. Mostra mais com menos texto, e não conta na régua.
- Decisão é o que e o porquê, em uma ou duas frases. Custo só entra se não for óbvio.
- Rejeitado é a alternativa e o motivo, em uma linha.
- Fato observado é o fato e a prova, em uma linha. Só entra o que muda uma decisão.
- Sem introdução que repete o título, sem retórica, sem código que a implementação vai reescrever. Código só quando o nome ou a assinatura é a decisão.
- Não é telegrama: frases inteiras, em português normal. Concisão é cortar ideia repetida, não artigo e verbo.

# A régua de qualidade

- **Decida, não enumere.** Uma spec registra a escolha e o motivo. Se você ainda está pesando alternativas, pergunte ao usuário em vez de listar as opções no arquivo — o lugar de opção descartada é a seção Rejeitados, com o porquê.
- **Afirme o que foi verificado e marque o resto.** Se você não mediu, escreva que é inferência.
- **Sem enfeite.** Nada de "este documento visa", nada de repetir o título no primeiro parágrafo.
- Escreva em português. O tom é o das specs existentes; o tamanho não — elas são anteriores à régua de tamanho.

# Antes de terminar

Rode a validação:

```bash
python3 - <<'PY'
import re
from datetime import date
from pathlib import Path

REQUIRED = ("name", "description", "projects", "status", "created_at")
PROJETOS_VALIDOS = {"crawler", "api", "frontend", "all"}
LIMITE_DE_LINHAS = 70


def projetos_invalidos(bruto):
    if not (bruto.startswith("[") and bruto.endswith("]")):
        return ["projects nao e um array [a, b]"]
    itens = [i.strip() for i in bruto[1:-1].split(",") if i.strip()]
    if not itens:
        return ["projects vazio"]
    fora = [i for i in itens if i not in PROJETOS_VALIDOS]
    if fora:
        return [f"projects invalido: {fora}"]
    if "all" in itens and len(itens) > 1:
        return ["projects: 'all' nao combina com outros"]
    return []


def linhas_de_texto(text):
    dentro = False
    total = 0
    for linha in text.splitlines():
        if linha.startswith("```"):
            dentro = not dentro
            continue
        if not dentro:
            total += 1
    return total


ok = True
for p in sorted(Path("specs").glob("*/*.md")):
    text = p.read_text()
    linhas = linhas_de_texto(text)
    if p.parent.name == "pending" and linhas > LIMITE_DE_LINHAS:
        print(f"{p}: AVISO {linhas} linhas de texto, acima de {LIMITE_DE_LINHAS}")
    if p.parent.name == "pending" and "## TL;DR" not in text:
        print(f"{p}: AVISO sem ## TL;DR")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        print(f"{p}: FRONTMATTER AUSENTE"); ok = False; continue
    fields = dict(l.split(": ", 1) for l in m.group(1).split("\n") if ": " in l)
    for problema in (
        [f"falta {k}" for k in REQUIRED if k not in fields]
        + ([f"name {fields.get('name')!r} != slug do arquivo"]
           if fields.get("name") != re.sub(r"^\d+(\.\d+)?-", "", p.stem) else [])
        + ([f"status {fields.get('status')!r} != pasta {p.parent.name!r}"]
           if fields.get("status") != p.parent.name else [])
        + ([f"Status:/data no corpo"] if re.search(r"^Status:|^(Aceito|Proposto) em", text, re.M) else [])
        + projetos_invalidos(fields.get("projects", ""))
    ):
        print(f"{p}: {problema}"); ok = False
    try:
        date.fromisoformat(fields.get("created_at", ""))
    except ValueError:
        print(f"{p}: created_at invalido"); ok = False
    for label, target in re.findall(r"\[([^\]]+)\]\((\.[^)]+)\)", text):
        if not (p.parent / target).resolve().exists():
            print(f"{p}: link quebrado -> {target}"); ok = False
print("tudo consistente" if ok else "HA PROBLEMAS")
PY
```

Aviso na spec que você escreveu é seu: adicione o TL;DR, e corte ideia repetida — ou conclua que o tamanho se justifica. Aviso em spec antiga fica para quando ela for tocada.

Depois diga ao usuário o caminho do arquivo criado. Não faça commit a menos que ele peça.

# Promover para done

Quando o trabalho de uma spec terminar, mover não basta — `status` e diretório precisam andar juntos:

```bash
git mv specs/pending/NNNN-<slug>.md specs/done/
sed -i 's/^status: pending$/status: done/' specs/done/NNNN-<slug>.md
```

E arrume os links relativos de quem apontava para a spec em `pending`.
