from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple
from urllib.parse import parse_qs, urlsplit

from api.atividades.entity import AWAITING_START
from api.materias.entity import Materia
from api.provas.entity import LETTERS, Alternativa, Prova, Questao

MATERIA_ID = -1
OFERTA = -1
NOME = "Matéria Mockada"
PERIODO = "M Fase I 2026 - Regular"
FINISHED = "Finalizada"
CATEGORIA = "Avaliação"
ATIVIDADES_PATH = "/bqs/AvaliacaoUsuario/"
CREATE_PATH = "/bqs/AvaliacaoUsuario/0/tentativa/"
TRABALHOS_PATH = "/interacao/TrabalhoEtapa/"
PROVA_PATH = "/bqs/AvaliacaoUsuarioHistorico/"
PROVA_SUFFIX = "/Avaliacao"
ACCEPTED: dict[str, object] = {"exception": None, "mensagens": []}
NO_ATTEMPT = 0
STARTED_AGO = timedelta(minutes=25)
ENTREGAS_PATH = "/interacao/TrabalhoEntrega/-"
ETIQUETAS_PATH = "/interacao/TrabalhoCorrecaoEtiqueta/-"
FIGURES_URL = "https://ava.uninter.com/conteudo/questoes/"
FIGURES_ROOT: Path = Path(__file__).resolve().parent
MOMENT = "%Y-%m-%dT%H:%M:%S"
USUARIO_ID_BASE = 100
HISTORICO_ID_BASE = 1000
FULL_NOTA = 100.0
FULL_PERCENT = 100
NO_PERCENT = 0

DAY = timedelta(days=1)


def _now() -> datetime:
    return datetime.now()


def materia() -> Materia:
    return Materia(
        id=MATERIA_ID,
        nome=NOME,
        periodo=PERIODO,
        vigente=True,
        concluida=False,
        oferta_flexivel=False,
        oferta_atual=OFERTA,
        oferta_aproveitamento=None,
        mockada=True,
    )


QUESTOES = (
    (
        """
            <p style="text-align: justify;">Quando se desenvolve um sistema
            computacional é necessário após os levantamentos iniciais e a elaboração
            da documentação, decidir qual sistema gerenciador de banco de dados será
            utilizado para o armazenamento dos dados. Quando falamos em sistemas
            gerenciadores de banco de dados relacionais, existem várias opções no
            mercado que atendem perfeitamente as necessidades de armazenamento dos
            sistemas administrativos.</p>
        """,
        """
            <strong>Podemos citar como os principais e mais conhecidos do mercado os
            seguintes SGBD:</strong>
        """,
        (
            "Java, Python, PHP e Javascript",
            "Windows, Linux, Android e iOS",
            "SQL Server, MySQL, PostgreSQL e Oracle",
            "Word, Excel, Power Point e Access",
        ),
    ),
    (
        """
            <p style="text-align: justify;">Para utilizar um sistema de banco de
            dados é necessário criar um usuário para que ele faça a conexão. O setor
            de Tecnologia da Informação recebeu uma solicitação para criar um
            usuário para o Sr. Francisco que será o novo desenvolvedor, com senha
            Fran345.</p>
        """,
        "<strong>Para a realização dessa tarefa comando de criação é o:</strong>",
        (
            "insert user fran345 senha francisco",
            "insert user ‘francisco’@’localhost’ identified by‘Fran345’",
            "create user fran345 senha francisco@localhost",
            "create user ‘francisco’@’localhost’ identified by ‘Fran345’",
        ),
    ),
    (
        """
            <p style="text-align: justify;">A criação de objetos em um banco de
            dados é uma situação muito importante, pois é a partir dos objetos que
            os dados serão controlados, armazenados e extraídos. Em virtude disso é
            importante ter alguns cuidados ao nomear um objeto na hora da sua
            criação, analise as assertivas que seguem e marque V para as asserções
            verdadeiras, e F para as asserções falsas.<br /><br />I. ( ) Sempre
            utilizar nomes significativos. Embora não seja obrigatório, pode ajudar
            a prevenir erros</p> <p>II. ( ) Não é obrigatório iniciar o nome de uma
            tabela e de um campo com uma letra</p> <p>III. ( ) O nome de um objeto
            não pode ser igual a uma palavra reservada da linguagem SQL, por
            exemplo: CREATE, SELECT, DROP, INTEGER, entre outras</p> <p>IV. ( ) É
            permitido a utilização de espaços em branco, ponto (.) ou hífen (-) no
            nome dos objetos</p>
        """,
        """
            <p><strong>Agora, assinale a alternativa que apresenta a sequência
            correta:</strong></p>
        """,
        (
            "V – F – V – F",
            "V – F – F – V",
            "V – V – F – V",
            "F – F – F – F",
        ),
    ),
    (
        """
            <p style="text-align: justify;">Os comandos para a manipulação dos dados
            de um SGBD servem para manipular os dados armazenados além de permitirem
            que sejam recuperados depois de serem tratados. É a partir dessa
            recuperação e tratamento que é possível extrair informação e gerar
            conhecimento, que será sempre o objetivo principal quando se trabalha
            com o gerenciamento de banco de dados. </p>
        """,
        """
            <strong>Essa manipulação de dados é realizada, entre outros, por quatro
            comandos principais que são:</strong>
        """,
        (
            "add, select, drop e alter",
            "create, drop, alter e select",
            "insert, delete, update e select",
            "select, create, update, drop",
        ),
    ),
    (
        """
            <p style="text-align: justify;">O comando select recupera os dados de
            uma ou mais tabelas, sendo um dos comandos mais simples e, ao mesmo
            tempo, mais extenso da SQL devido as suas funções, operandos, comandos,
            sub-comandos e cláusulas não obrigatórias. Para essa atividade vamos
            considerar a tabela funcionário que pode ser vista a seguir:</p> <p>
            </p> <table> <tr> <td> <p>CODIGO</p> </td> <td> <p>NOME</p> </td> <td>
            <p>CPF</p> </td> <td> <p>DATA_NCTO</p> </td> <td> <p>SALARIO</p> </td>
            <td> <p>DEPTO</p> </td> <td> <p>CARGO</p> </td> </tr> <tr> <td> <p>1</p>
            </td> <td> <p>JOSÉ</p> </td> <td> <p>1234567</p> </td> <td>
            <p>17/01/1960</p> </td> <td> <p> 5.000,00</p> </td> <td> <p>TI</p> </td>
            <td> <p>DBA</p> </td> </tr> <tr> <td> <p>2</p> </td> <td> <p>MARIA</p>
            </td> <td> <p>456789</p> </td> <td> <p>21/11/1965</p> </td> <td> <p>
            6.000,00</p> </td> <td> <p>RH</p> </td> <td> <p>GERENTE</p> </td> </tr>
            <tr> <td> <p>3</p> </td> <td> <p>JOÃO</p> </td> <td> <p>8777666</p>
            </td> <td> <p>30/04/1971</p> </td> <td> <p> 3.000,00</p> </td> <td>
            <p>ADM</p> </td> <td> <p>OPERACIONAL</p> </td> </tr> </table> <p>Fonte:
            o Autor</p>
        """,
        """
            <p>Relacione corretamente os comandos de select da SQL às suas
            respectivas características:</p> <ol> <li>select nome, cpf, salario from
            funcionario where salario &gt; 5000</li> <li>select nome, cargo, salario
            from funcionario where depto = ‘TI’</li> <li>select nome, depto, salario
            + 5000 from funcionario where cargo = ‘DBA’</li> <li>select nome,
            data_ncto from funcionario where month(data_ncto) = 11</li> <li>select
            nome, dpto, cargo, salario + 5000 from funcionario order by nome</li>
            </ol> <p> </p> <p>( ) Seleciona o nome e a data de nascimento dos
            funcionários nascidos no mês de novembro</p> <p>( ) Seleciona o nome, o
            cargo e o salário dos funcionários que trabalham no departamento de
            Tecnologia da Informação</p> <p>( ) Seleciona o nome, o departamento, o
            cargo e o salário com R$ 5.000,00 dos funcionários, ordenando a seleção
            pelo nome do funcionário</p> <p>( ) Seleciona o nome, o depto e o
            salário com R$ 5.000,00 dos funcionários com cargo de Data Base
            Administrador</p> <p>( ) Seleciona o nome, o cpf e o salário dos
            funcionários que recebem mais do que R$ 5.000,00</p> <p> </p>
            <p><strong>Agora, selecione a alternativa que apresenta a sequência
            correta:</strong></p>
        """,
        (
            "1 – 2 – 4 – 3 – 5",
            "2 – 4 – 3– 5- 1",
            "4 – 2 – 3 – 5 – 1",
            "4 – 2 – 5 – 3 – 1",
        ),
    ),
    (
        """
            <p style="text-align: justify;">Para inserir registros em uma tabela
            através da linguagem SQL, é utilizado o comando INSERT INTO com a
            seguinte sintaxe: INSERT INTO &lt;tabela&gt; (campo1, campo2, ...)
            VALUES (Valor1, Valor2, ...). Cada campo especificado na instrução
            INSERT deve ter um valor correspondente na lista de valores. A lista de
            valores deve estar na mesma ordem que a lista de campos, analise as
            assertivas que seguem para a tabela aluno (código, nome, endereço,
            município e data_nasc) e marque V para as asserções verdadeiras, e F
            para as asserções falsas.</p>
        """,
        """
            <p> I. ( ) INSERT INTO aluno (1, ‘Maria da Silva’, ‘Rua XV, 125’,
            ‘Curitiba’, ‘1966/07/17’)</p> <p>II. ( ) INSERT INTO Aluno (Codigo,
            Nome, Endereco, Municipio, Data_Nasc) VALUES (1, ‘Maria da Silva’, ‘Rua
            XV, 125’, ‘Curitiba’, ‘1966/07/17’)</p> <p>III. ( ) INSERT INTO Aluno
            (Codigo, Nome, Endereco, Municipio, Data_Nasc) VALUES (1, ‘Maria da
            Silva’, ‘Curitiba’, ‘1966/07/17’)</p> <p>IV. ( ) INSERT INTO Aluno
            (Nome, Endereco, Municipio, Data_Nasc) VALUES (‘Maria da Silva’, ‘Rua
            XV, 125’, ‘Curitiba’, ‘1966/07/17’)<br /><br /></p> <p><strong>Agora,
            assinale a alternativa que apresenta a sequência correta:</strong></p>
        """,
        (
            "V – F – V – V",
            "F – V – F – V",
            "V – F – F – V",
            "F – F – F - V",
        ),
    ),
    (
        """
            <p style="text-align: justify;">Um banco de dados pode ser criado
            através de scripts, sendo possível configurar alguns itens, como os
            caracteres que serão utilizados conforme o idioma do local e encriptação
            de dados. Porém, em alguns casos, como na criação de um banco de dados
            de desenvolvimento, que é um DB utilizado para os testes quando da
            criação de um sistema, é possível utilizar um comando de criação de
            banco de dados sem nenhum parâmetro de configuração.</p>
        """,
        """
            <p><strong>Esse comando de criação simples, sem parâmetros de
            configuração é o:</strong></p>
        """,
        (
            "insert database",
            "create database NOME_BANCO_DE_DADOS",
            "create table NOME_BANCO_DE_DADOS",
            "drop database NOME_BANCO_DE_DADOS",
        ),
    ),
    (
        """
            <p style="text-align: justify;">As funções agrupadoras permitem agrupar
            valores de uma tabela com conteúdo numérico. São muito uteis para a
            emissão de relatórios gerenciais pois permitem de forma reduzida mostrar
            informações contidas no banco de dados, não como uma lista, mas como
            valores que podem representar o total de vendas mensal, ou a quantidade
            de produtos vendidos, valores médios, além de maiores e menores valores
            de uma seleção, analise as afirmativas a seguir que contemplem tais
            funções agrupadoras e suas funcionalidades:<br /><br /><br />I-COUNT
            Conta o número de registros de uma seleção<br /><br />II-SUM Soma os
            valores de uma seleção<br /><br />III-AVG Calcula Automaticamente o
            Valor Geral de uma seleção</p> IV-MAX Retorna o valor máximo em uma
            seleção<br /><br />V-MIN Retorna o valor menos repetido em uma
            seleção<br /> <p> </p>
        """,
        "<p><strong>São corretas apenas as afirmativas:</strong></p>",
        (
            "I e II",
            "I, II e V",
            "I, II e IV",
            "I, III e IV",
        ),
    ),
    (
        """
            <p style="text-align: justify;">Sabendo que o dado, que é o elemento
            principal de um banco de dados, possui um ciclo de vida, que se inicia
            com a sua produção, podendo se dar por vários dispositivos de produção,
            como um editor de texto, uma planilha de cálculo, um sensor presencial,
            um formulário HTML, uma câmera digital ou ainda através de uma página de
            mídia social. </p>
            <p><img src="https://ava.uninter.com/conteudo/questoes/ciclo-de-vida-do-dado.png" alt="Ciclo de vida do dado" /></p>
            <p>Fonte: o Autor</p>
        """,
        """
            <strong>Logo após a sua produção, seguindo o seu ciclo de vida, o dado
            deverá ser:</strong>
        """,
        (
            "Descartado pois já cumpriu o seu papel.",
            "Copiado para outro servidor.",
            '<img src="https://ava.uninter.com/conteudo/questoes/'
            'alternativa-armazenada.png" alt="Armazenado para posterior consulta" />',
            "Enviado para o usuário para verificação.",
        ),
    ),
    (
        """
            <p style="text-align: justify;">Para a manipulação de objetos em um
            sistema gerenciador de banco de dados, usamos instruções que são
            destinadas à criação e manutenção de banco de dados, tabelas, índices,
            entre outros. Os principais comandos de definição de dados são: create,
            drop e alter. Essas instruções são importantes e devem ser conhecidas
            pelos administradores de banco de dados, pois é através da criação
            dessas instruções que é possível otimizar o gerenciamento dos objetos em
            vários locais.</p>
        """,
        "<strong>Para essa manipulação de objetos usamos as instruções:</strong>",
        (
            "SQL (Structure Query Language)",
            "DML (Data Manipulation Language)",
            "OOP (Object-oriented programming).",
            "DDL (Data Definition Language)",
        ),
    ),
)


def prova(atividade_id: int, respostas: dict[int, int]) -> Prova:
    questoes: list[Questao] = []
    for ordem, (enunciado, comando, alternativas) in enumerate(QUESTOES, start=1):
        base = ordem * 10
        questoes.append(
            Questao(
                id=-base,
                ordem=ordem,
                enunciado=enunciado,
                comando=comando,
                alternativas=tuple(
                    Alternativa(id=-(base + position), letra=letra, texto=texto)
                    for position, (letra, texto) in enumerate(
                        zip(LETTERS, alternativas), start=1
                    )
                ),
            )
        )
    return Prova(
        atividade_id=atividade_id, questoes=tuple(questoes), respostas=respostas
    )


def _moment(moment: datetime) -> str:
    return moment.strftime(MOMENT)


class Correcao(NamedTuple):
    letra: str
    comentario: str


CORRECOES = (
    Correcao(
        "c",
        "A resposta correta é a letra C, conforme o item 1.1 do Tema 1 da Aula 1. "
        "Java, Python e PHP são linguagens de programação, e Word e Excel são "
        "aplicativos de escritório: nenhum deles gerencia um banco de dados.",
    ),
    Correcao(
        "d",
        "A resposta correta é a letra D, conforme o item 2.3 do Tema 2 da Aula 2. "
        "A criação de um usuário usa create user, e a senha vem depois de "
        "identified by; insert grava registros, não cria usuários.",
    ),
    Correcao(
        "c",
        "A resposta correta é a letra C, conforme o item 1.4 do Tema 1 da Aula 3. "
        "Só a terceira afirmativa é falsa: as demais seguem as regras de "
        "nomenclatura apresentadas no tema.",
    ),
    Correcao(
        "c",
        "A resposta correta é a letra C, conforme o item 3.1 do Tema 3 da Aula 2. "
        "create, drop e alter definem objetos e não manipulam os dados guardados "
        "neles.",
    ),
    Correcao(
        "d",
        "A resposta correta é a letra D, conforme o item 2.2 do Tema 2 da Aula 4. "
        "A ordem acompanha as cláusulas do select apresentadas no quadro do tema.",
    ),
    Correcao(
        "b",
        "A resposta correta é a letra B, conforme o item 1.3 do Tema 1 da Aula 5. "
        "As instruções I e III não nomeiam os campos antes de values, o que basta "
        "para invalidá-las.",
    ),
    Correcao(
        "b",
        "A resposta correta é a letra B, conforme o item 1.2 do Tema 1 da Aula 2. "
        "drop database apaga o banco, e create table cria uma tabela dentro dele.",
    ),
    Correcao(
        "c",
        "A resposta correta é a letra C, conforme o item 4.1 do Tema 4 da Aula 4. "
        "A afirmativa III confunde count com sum, e a V descreve uma cláusula de "
        "ordenação.",
    ),
    Correcao(
        "c",
        "A resposta correta é a letra C, conforme o item 1.1 do Tema 1 da Aula 1. "
        "O ciclo de vida do dado segue da produção para o armazenamento; o descarte "
        "é a última etapa, não a primeira.",
    ),
    Correcao(
        "d",
        "A resposta correta é a letra D, conforme o item 3.2 do Tema 3 da Aula 2. "
        "create, drop e alter formam a DDL; a DML manipula os dados já armazenados.",
    ),
)


class Avaliacao(NamedTuple):
    nome: str
    tipo: str
    status: str
    peso: int
    tentativa: int
    tentativa_total: int
    inicio: timedelta
    fim: timedelta
    erros: tuple[int, ...] = ()
    em_branco: tuple[int, ...] = ()
    orientacao: str | None = None
    tempo_total: int | None = None
    presencial: bool = False
    criada: bool = False
    iniciada: bool = False


AVALIACOES = (
    Avaliacao(
        nome="APOL Objetiva 1 (Mockada)",
        tipo="APOL Objetiva",
        status=AWAITING_START,
        orientacao="Uma avaliação que existe só no dev mode.",
        peso=10,
        tentativa=1,
        tentativa_total=3,
        inicio=-10 * DAY,
        fim=30 * DAY,
        criada=True,
        iniciada=True,
    ),
    Avaliacao(
        nome="APOL Objetiva 2 (Mockada)",
        tipo="APOL Objetiva",
        status=FINISHED,
        peso=10,
        erros=(4, 9),
        tentativa=2,
        tentativa_total=3,
        inicio=-30 * DAY,
        fim=-2 * DAY,
    ),
    Avaliacao(
        nome="APOL Objetiva 3 (Mockada)",
        tipo="APOL Objetiva",
        status=FINISHED,
        orientacao="Finalizada, com tentativa e prazo de sobra.",
        peso=10,
        erros=(2, 5, 7),
        em_branco=(3, 10),
        tentativa=1,
        tentativa_total=3,
        inicio=-10 * DAY,
        fim=20 * DAY,
    ),
    Avaliacao(
        nome="Prova Atividade Prática (Mockada)",
        tipo="Prova Atividade Prática",
        status=FINISHED,
        peso=15,
        erros=(),
        tentativa=1,
        tentativa_total=1,
        inicio=-20 * DAY,
        fim=15 * DAY,
    ),
    Avaliacao(
        nome="Prova Objetiva (Mockada)",
        tipo="Prova Objetiva",
        status=AWAITING_START,
        presencial=True,
        peso=20,
        tentativa=1,
        tentativa_total=1,
        inicio=-5 * DAY,
        fim=45 * DAY,
    ),
    Avaliacao(
        nome="Prova Objetiva (Segunda Chamada) (Mockada)",
        tipo="Prova Objetiva",
        status=FINISHED,
        presencial=True,
        peso=10,
        erros=(),
        em_branco=(2, 3, 4, 5, 6, 7, 8, 9, 10),
        tentativa=1,
        tentativa_total=1,
        inicio=-60 * DAY,
        fim=-30 * DAY,
    ),
    Avaliacao(
        nome="Prova Discursiva (Mockada)",
        tipo="Prova Discursiva",
        status=AWAITING_START,
        orientacao="Dez questões, todas respondíveis.",
        tempo_total=60,
        peso=15,
        tentativa=1,
        tentativa_total=2,
        inicio=-5 * DAY,
        fim=45 * DAY,
    ),
    Avaliacao(
        nome="Exame Final (Mockado)",
        tipo="Exame",
        status=AWAITING_START,
        peso=10,
        tentativa=1,
        tentativa_total=1,
        inicio=-40 * DAY,
        fim=-7 * DAY,
    ),
    Avaliacao(
        nome="APOL Objetiva 4 (Mockada)",
        tipo="APOL Objetiva",
        status=AWAITING_START,
        orientacao="Tentativa criada no AVA, ainda não iniciada.",
        peso=10,
        tentativa=1,
        tentativa_total=3,
        inicio=-3 * DAY,
        fim=30 * DAY,
        criada=True,
    ),
)


def _avaliacao_id(position: int) -> int:
    return -(position + 1)


def _usuario_id(position: int) -> int:
    return -(USUARIO_ID_BASE + position + 1)


def _avaliacao_cid(position: int) -> str:
    return f"mockada+{position + 1}/=="


def _vinculada_cid(position: int) -> str:
    return f"vinculada+{position + 1}/=="


def _historico_id(position: int, ordem: int) -> int:
    return -(HISTORICO_ID_BASE + (position + 1) * 100 + ordem)


def _respondeu(avaliacao: Avaliacao, ordem: int) -> bool:
    return ordem not in avaliacao.em_branco


def _acertou(avaliacao: Avaliacao, ordem: int) -> bool:
    return _respondeu(avaliacao, ordem) and ordem not in avaliacao.erros


def _nota_da_questao() -> float:
    return FULL_NOTA / len(QUESTOES)


def _acertos(avaliacao: Avaliacao) -> int:
    return sum(1 for ordem in range(1, len(QUESTOES) + 1) if _acertou(avaliacao, ordem))


def _nota(avaliacao: Avaliacao) -> float | None:
    if avaliacao.status != FINISHED:
        return None
    return _acertos(avaliacao) * _nota_da_questao()


def _contribuicao(avaliacao: Avaliacao) -> float | None:
    nota = _nota(avaliacao)
    return None if nota is None else nota * avaliacao.peso / FULL_NOTA


def atividades(criadas: set[int], iniciadas: dict[int, datetime]) -> dict[str, object]:
    moment = _now()
    return {
        "avaliacaoUsuarios": [
            {
                "id": _usuario_id(position) if position in criadas else NO_ATTEMPT,
                "idAvaliacao": _avaliacao_id(position),
                "cIdAvaliacao": _avaliacao_cid(position),
                "cIdAvaliacaoVinculada": _vinculada_cid(position),
                "horarioInicio": _moment(iniciadas[position])
                if position in iniciadas
                else None,
                "status": avaliacao.status,
                "nota": _nota(avaliacao),
                "notaMedia": _contribuicao(avaliacao),
                "tentativa": avaliacao.tentativa,
                "tentativaTotal": avaliacao.tentativa_total,
                "dataInicio": _moment(moment + avaliacao.inicio),
                "dataFim": _moment(moment + avaliacao.fim),
                "avaliacao": {
                    "id": _avaliacao_id(position),
                    "nome": avaliacao.nome,
                    "nomeAvaliacaoTipo": avaliacao.tipo,
                    "nomeAvaliacaoTipoCategoria": CATEGORIA,
                    "pesoMedia": avaliacao.peso,
                    "avaliacaoPresencial": avaliacao.presencial,
                    "periodo": PERIODO,
                    "orientacao": avaliacao.orientacao,
                    "tempoTotal": avaliacao.tempo_total,
                },
            }
            for position, avaliacao in enumerate(AVALIACOES)
        ]
    }


def trabalhos() -> dict[str, object]:
    moment = _now()
    etapas = [
        ("Trabalho aprovado (Mockado)", 30, 10, 12, 90.0, True, False),
        ("Trabalho reprovado (Mockado)", 30, 8, 9, 20.0, False, False),
        ("Trabalho em correção (Mockado)", 20, 1, 2, None, None, False),
        ("Trabalho aberto (Mockado)", 5, -15, None, None, None, True),
        ("Trabalho não entregue (Mockado)", 40, 20, None, None, None, False),
    ]
    return {
        "trabalhoEtapas": [
            {
                "id": -(ordem + 1),
                "idTrabalhoVinculadoEtapa": ordem + 1,
                "nome": nome,
                "nomeTrabalhoTipo": "Trabalho",
                "ordemTrabalho": ordem + 1,
                "nomePeriodo": PERIODO,
                "dataInicio": _moment(moment - inicio * DAY),
                "dataFim": _moment(moment - fim * DAY),
                "dataEntrega": None
                if entrega is None
                else _moment(moment - entrega * DAY),
                "notaEtapa": nota,
                "aprovadoEtapa": aprovado,
                "podeEntregar": pode_entregar,
            }
            for ordem, (
                nome,
                inicio,
                fim,
                entrega,
                nota,
                aprovado,
                pode_entregar,
            ) in enumerate(etapas)
        ]
    }


def _atributo(nome: str, valor: str) -> dict[str, object]:
    return {"nomeAtributo": nome, "valor": valor}


def questoes(
    position: int, iniciada_em: datetime, respostas: dict[int, int]
) -> dict[str, object]:
    return {
        "avaliacaoUsuarioHistoricos": [
            {
                "id": questao.id,
                "idAvaliacaoUsuario": _usuario_id(position),
                "ordem": questao.ordem,
                "dataCriacao": _moment(iniciada_em),
                "idQuestaoAlternativa": respostas.get(questao.id),
                "questao": questao.enunciado,
                "comando": questao.comando,
                "alternativas": [
                    {
                        "id": alternativa.id,
                        "ativa": True,
                        "questaoAlternativaAtributos": [
                            _atributo("texto", alternativa.texto)
                        ],
                    }
                    for alternativa in questao.alternativas
                ],
            }
            for questao in prova(_avaliacao_id(position), {}).questoes
        ]
    }


def _correta(questao: Questao, correcao: Correcao) -> Alternativa:
    return questao.alternativas[LETTERS.index(correcao.letra)]


def _escolhida(questao: Questao, correta: Alternativa, acertou: bool) -> Alternativa:
    if acertou:
        return correta
    seguinte = (questao.alternativas.index(correta) + 1) % len(questao.alternativas)
    return questao.alternativas[seguinte]


def _alternativa_corrigida(
    questao: Questao,
    alternativa: Alternativa,
    correta: Alternativa,
    correcao: Correcao,
) -> dict[str, object]:
    atributos = [_atributo("texto", alternativa.texto)]
    if alternativa is correta:
        atributos = [
            _atributo("correta", "true"),
            *atributos,
            _atributo("comentário", correcao.comentario),
        ]
    return {
        "id": alternativa.id,
        "idQuestao": questao.id,
        "ativa": True,
        "questaoAlternativaAtributos": atributos,
    }


def gabarito(position: int, avaliacao: Avaliacao) -> dict[str, object]:
    questoes_da_prova = prova(_avaliacao_id(position), {}).questoes
    corrigidas: list[dict[str, object]] = []
    for questao, correcao in zip(questoes_da_prova, CORRECOES, strict=True):
        acertou = _acertou(avaliacao, questao.ordem)
        correta = _correta(questao, correcao)
        escolhida = (
            _escolhida(questao, correta, acertou)
            if _respondeu(avaliacao, questao.ordem)
            else None
        )
        corrigidas.append(
            {
                "id": _historico_id(position, questao.ordem),
                "idAvaliacaoUsuario": _usuario_id(position),
                "tentativa": avaliacao.tentativa,
                "ordem": questao.ordem,
                "idQuestao": questao.id,
                "questao": questao.enunciado,
                "comando": questao.comando,
                "idQuestaoAlternativa": None if escolhida is None else escolhida.id,
                "percentualAcerto": FULL_PERCENT if acertou else NO_PERCENT,
                "notaQuestao": _nota_da_questao() if acertou else 0.0,
                "anulada": False,
                "idQuestaoTipo": 1,
                "alternativas": [
                    _alternativa_corrigida(questao, alternativa, correta, correcao)
                    for alternativa in questao.alternativas
                ],
            }
        )
    return {"avaliacaoUsuarioHistoricos": corrigidas}


def asked_prova(url: str) -> int | None:
    _, _, tail = url.partition(PROVA_PATH)
    path = tail.split("?")[0]
    if not path.endswith(PROVA_SUFFIX):
        return None
    asked = path.removesuffix(PROVA_SUFFIX)
    return int(asked) if asked.startswith("-") and asked[1:].isdigit() else None


def figure(url: str) -> bytes | None:
    prefix, _, name = url.partition(FIGURES_URL)
    path = FIGURES_ROOT / name
    if prefix or not name or "/" in name or not path.is_file():
        return None
    return path.read_bytes()


def _position_of_usuario(usuario_id: int) -> int | None:
    for position in range(len(AVALIACOES)):
        if usuario_id == _usuario_id(position):
            return position
    return None


def _position_of_cid(cid: str) -> int | None:
    for position in range(len(AVALIACOES)):
        if cid == _avaliacao_cid(position):
            return position
    return None


def _first(values: dict[str, list[str]], key: str) -> str:
    found = values.get(key)
    return found[0] if found else ""


def _integer(text: str) -> int | None:
    return int(text) if text.lstrip("-").isdigit() else None


class MockedAva:
    def __init__(self) -> None:
        started_at = _now() - STARTED_AGO
        self._criadas = {
            position
            for position, avaliacao in enumerate(AVALIACOES)
            if avaliacao.criada or avaliacao.status == FINISHED
        }
        self._iniciadas = {
            position: started_at
            for position, avaliacao in enumerate(AVALIACOES)
            if avaliacao.iniciada
        }
        self._respostas: dict[int, dict[int, int]] = {}

    def payload(self, url: str, body: str) -> dict[str, object] | None:
        if ATIVIDADES_PATH in url and f"idSalaVirtual={MATERIA_ID}&" in url:
            return atividades(self._criadas, self._iniciadas)
        if f"{TRABALHOS_PATH}{OFERTA}/" in url:
            return trabalhos()
        if CREATE_PATH in url:
            return self._create(url)
        asked = asked_prova(url)
        if asked is not None:
            return self._prova_ou_gabarito(asked)
        if url.split("?")[0].endswith(PROVA_PATH):
            return self._answer(body)
        if ENTREGAS_PATH in url:
            return {"trabalhoEntregas": []}
        if ETIQUETAS_PATH in url:
            return {"trabalhoCorrecaoEtiquetas": []}
        return None

    def _create(self, url: str) -> dict[str, object] | None:
        query = parse_qs(urlsplit(url).query)
        position = _position_of_cid(_first(query, "cIdAvaliacao"))
        if position is None:
            return None
        self._criadas.add(position)
        return dict(ACCEPTED)

    def _prova_ou_gabarito(self, usuario_id: int) -> dict[str, object] | None:
        position = _position_of_usuario(usuario_id)
        if position is None or position not in self._criadas:
            return None
        avaliacao = AVALIACOES[position]
        if avaliacao.status == FINISHED:
            return gabarito(position, avaliacao)
        iniciada_em = self._iniciadas.setdefault(position, _now())
        return questoes(position, iniciada_em, self._respostas.get(position, {}))

    def _answer(self, body: str) -> dict[str, object] | None:
        form = parse_qs(body)
        usuario_id = _integer(_first(form, "idAvaliacaoUsuario"))
        questao_id = _integer(_first(form, "id"))
        alternativa_id = _integer(_first(form, "idQuestaoAlternativa"))
        position = None if usuario_id is None else _position_of_usuario(usuario_id)
        if position is None or questao_id is None or alternativa_id is None:
            return None
        self._respostas.setdefault(position, {})[questao_id] = alternativa_id
        return dict(ACCEPTED)
