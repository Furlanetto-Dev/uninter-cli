# Uninter

Espelha o que o AVA da Uninter (Univirtus) sabe sobre a vida acadêmica de um aluno, para consulta fora do navegador.

## Language

### Estrutura acadêmica

**Matéria**:
Uma disciplina que o aluno cursa ou cursou. É a unidade que o aluno escolhe para ver suas avaliações.
_Avoid_: Sala virtual, oferta, disciplina, curso

**Período**:
Quando a matéria foi ofertada, no formato "B Fase II 2026 - Regular". É o que distingue duas matérias de mesmo nome.
_Avoid_: Módulo, oferta, fase, semestre

**Avaliação**:
Uma prova, APOL ou simulado que vale nota para o aluno em uma matéria. É a única coisa que o AVA expõe como "atividade" do aluno.
_Avoid_: Atividade, tarefa, trabalho, exercício

### Notas

**Peso**:
Quanto uma avaliação vale na média da matéria, em porcentagem. Cuidado: no JSON do AVA isso é `pesoMedia`; o campo chamado `peso` vale 100 em toda avaliação e não tem relação com a média.

**Contribuição**:
O quanto uma avaliação já rendeu para a média — nota vezes peso. Só existe depois que a avaliação recebe nota.
_Avoid_: Nota média, notaMedia, nota ponderada

**Média**:
A soma das contribuições das avaliações já realizadas de uma matéria. É parcial enquanto houver peso não lançado.
