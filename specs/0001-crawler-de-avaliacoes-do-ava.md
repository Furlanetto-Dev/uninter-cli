# Crawler de avaliações do AVA

Status: aceito · 2026-08-28

Consultar nota no AVA da Uninter exige navegar num SPA lento, matéria por matéria. Este projeto espelha essas informações num SQLite local e as expõe por uma CLI interativa. O vocabulário está em [CONTEXT.md](../CONTEXT.md); aqui ficam as decisões e o porquê delas.

## Comportamento observado do AVA

Restrições verificadas contra a API real, não deduzidas da documentação (que não existe). Elas explicam boa parte das decisões abaixo.

- O login devolve `usuario.time`, um timestamp que é **o nome do cookie de sessão**. Toda requisição seguinte precisa mandar o cookie e repetir esse mesmo valor no header `x-time`. A sessão vale 4 horas.
- Cada matéria carrega duas ofertas, e só uma delas devolve avaliações: a de aproveitamento quando existe, a atual caso contrário. Verificado nas 27 salas da conta, nos dois sentidos, sem contraexemplo.
- Lista vazia e erro chegam iguais: **HTTP 404 com corpo em texto puro**, apesar do `content-type: application/json`. Não há como distinguir "matéria sem avaliação" de falha real, e 6 das 27 salas caem nesse caso legitimamente.
- O `idCurso` no path é ignorado sempre que `idUsuarioCurso` tem valor real, e vice-versa — mas pelo menos um dos dois precisa ser verdadeiro, e nenhum vem na resposta do login.
- A resposta traz `peso` e `pesoMedia`. O primeiro vale 100 em toda avaliação e não tem relação com a média; o peso real é `pesoMedia`.

## Decisões

### Atividade é avaliação, e nada além disso

"Listar as atividades de uma matéria" quer dizer listar APOLs, provas e simulados — o que o endpoint `AvaliacaoUsuario` devolve. Aulas, fóruns, materiais e trabalhos ficam fora do escopo, porque exigiriam endpoints que não foram capturados.

### A oferta nunca aparece para o usuário

Matéria é a unidade que o aluno escolhe; a oferta é detalhe de integração resolvido pela regra `aproveitamento ?? atual`. Expor as duas significaria oferecer uma opção que sempre retorna 404.

### O banco guarda só os campos que a tela usa

Uma avaliação chega com cerca de 160 campos entre o objeto e seus aninhados, quase todos tripa interna do AVA. Persistimos doze; incluir um campo novo depois custa uma linha e um novo sync, porque a API responde em meio segundo e não é um arquivo morto.

### O SQLite é a fonte de leitura, não um subproduto

A CLI lê do banco; a rede só entra quando o usuário pede. Isso mantém a navegação instantânea e faz o cookie de 4 horas importar apenas no momento do sync.

### Matérias no sync, avaliações sob demanda

Sincronizar as 27 matérias de uma vez custaria uns 14 segundos a cada execução. As avaliações são buscadas quando a matéria é aberta pela primeira vez, e ficam cacheadas. A consequência aceita é que só funciona offline aquilo que já foi visitado.

### Cache servido de imediato; atualizar é ato explícito

Abrir uma matéria já visitada mostra o que está no banco, com a idade do dado à vista, e uma opção de atualizar. Nota muda com o tempo, mas releitura silenciosa da rede transformaria o banco no subproduto que a decisão anterior rejeitou.

### O seletor esconde o que não é matéria

O AVA devolve 27 salas, e uma delas é o canal de comunicação com o coordenador — sem período, sem datas, sem avaliação. Pelo glossário isso não é Matéria, então não entra na lista. As vigentes vêm primeiro.

### A tela soma a média

A contribuição de cada avaliação já vem calculada pelo AVA, e a soma é a média parcial da matéria. Exibimos também quanto do peso já foi lançado, porque em algumas matérias as avaliações realizadas não fecham 100% e uma média solta mentiria.

### A CLI não tem argumentos

Nem flags, nem subcomandos: `python main.py` abre um menu e tudo acontece por ele. Segue a convenção do repositório e é o que "cli interativa" pede.

### Credenciais só em `.env`

RU, senha e `idCurso` vêm de um `pydantic-settings` lendo `.env`; os curls de exemplo carregam placeholders. A senha estava commitada em texto puro e foi removida do histórico com BFG — o repositório não tinha remote, então nunca saiu da máquina.

### O `idCurso` é configuração, não descoberta

Não há endpoint conhecido que produza `idCurso` ou `idUsuarioCurso`, e procurá-lo significaria fazer engenharia reversa do SPA. Fica como variável de ambiente até que alguém capture a requisição no DevTools.

## Rejeitados

- **Descobrir os ids varrendo o SPA.** Tentado e abandonado: os módulos RequireJS que respondem pela tela inicial já recebem o `idCurso` pronto. Custo alto, ruído no servidor da faculdade, benefício nenhum.
- **Um único conjunto de models servindo API e banco.** É o uso natural do SQLModel, mas aninhar um model `table=True` dentro de outro model faz o Pydantic construí-lo pelo `__init__`, onde o SQLModel desliga a validação: campos obrigatórios chegam nulos, sem erro. A fronteira com o AVA são models Pydantic; as tabelas são preenchidas por mapeamento explícito.
- **Histórico append-only de notas.** Guardar um snapshot datado por sync mostraria a nota mudando ao longo do tempo, mas exigiria chave composta com data e filtro por snapshot mais recente em toda leitura. Custo alto para um ganho que ninguém pediu.
- **Projetar quanto falta para passar.** A nota de corte não existe em campo nenhum da API; seria um 70 chutado dentro do código.
