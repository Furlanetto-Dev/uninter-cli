---
name: navegar-no-uninter
description: Como mexer na tela do app Uninter aberto ao lado (open_materia, open_questao, go_back, read_screen) quando os dados não vêm das ferramentas de leitura. Use só em último caso, depois de tentar list_*, get_transcricoes, get_current_screen e get_open_prova.
---

# Navegar no app Uninter

O aluno está com o app Uninter aberto ao lado deste terminal, e as ferramentas `uninter` leem o que o app guarda. Mudar a tela dele é o último recurso.

## Ordem de preferência

1. **Dados direto do banco do app:** `list_materias`, `list_atividades`, `list_trabalhos`, `list_aulas`, `get_transcricoes`, `list_agendamentos`. Respondem sem tocar na tela.
2. **O que o aluno está vendo:** `get_current_screen` (matéria, aba, questão aberta) e `get_open_prova` (todas as questões da prova aberta, com a alternativa marcada em cada uma). Também não mudam a tela.
3. **Só se o dado não vier de nenhuma das anteriores:** `open_materia`, `open_questao`, `go_back` e `read_screen`.

Exemplos: para explicar outra questão da prova, use `get_open_prova`, não `open_questao`. Para notas e prazos, use `list_atividades`, não `open_materia` seguido de `read_screen`.

## Antes de mudar a tela

- Avise o aluno em uma frase que vai mudar a tela dele e por quê.
- Guarde onde ele estava com `get_current_screen`.

## Ao mudar

- Cada ferramenta devolve a tela depois de agir. Confira se chegou onde queria antes do próximo passo.
- `read_screen` devolve o texto que o app pinta. Use para ler o que só aparece na tela.
- Uma recusa ("há uma janela aberta…", "use go_back antes") é para respeitar: não insista nem dê a volta por outro caminho.

## Ao terminar

Volte para onde o aluno estava: a mesma matéria e aba com `open_materia`, a mesma questão com `open_questao`, ou `go_back` para fechar o que você abriu.

## O que estas ferramentas não fazem

Nenhuma começa prova, marca alternativa, entrega prova nem agenda. Abrir uma atividade "Aguardando início" começaria a tentativa no AVA, e isso é só do aluno. Para agendar e cancelar existem `book_prova` e `cancel_agendamento`, que o aluno confirma no app.
