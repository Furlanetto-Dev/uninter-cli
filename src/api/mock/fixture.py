import json
from datetime import datetime, timedelta

from api.atividades.entity import AWAITING_START, Atividade
from api.capturas.entity import ATIVIDADES, TRABALHOS, Captura
from api.capturas.lookup import KEYS
from api.materias.entity import Materia
from api.provas.entity import LETTERS, Alternativa, Prova, Questao
from api.trabalhos.entity import Trabalho

MATERIA_ID = -1
OFERTA = -1
NOME = "Matéria Mockada"
PERIODO = "M Fase I 2026 - Regular"
FINISHED = "Finalizada"
STARTED = "Iniciada"
URL = "mock://uninter/{recurso}"

DAY = timedelta(days=1)


def _now() -> datetime:
    return datetime.now()


def materia() -> Materia:
    moment = _now()
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
        atividades_sincronizadas_em=moment,
        trabalhos_sincronizados_em=moment,
    )


def atividades() -> list[Atividade]:
    moment = _now()
    return [
        Atividade(
            materia_id=MATERIA_ID,
            id=-1,
            posicao=0,
            nome="APOL Objetiva 1 (Mockada)",
            tipo="APOL Objetiva",
            categoria="Avaliação",
            periodo=PERIODO,
            orientacao="Uma avaliação que existe só no dev mode.",
            tempo_total=None,
            peso=15,
            status=AWAITING_START,
            tentativa=1,
            tentativa_total=3,
            inicio=moment - 10 * DAY,
            fim=moment + 30 * DAY,
        ),
        Atividade(
            materia_id=MATERIA_ID,
            id=-2,
            posicao=1,
            nome="APOL Objetiva 2 (Mockada)",
            tipo="APOL Objetiva",
            categoria="Avaliação",
            periodo=PERIODO,
            peso=15,
            status=FINISHED,
            nota=85.0,
            contribuicao=12.75,
            tentativa=2,
            tentativa_total=3,
            inicio=moment - 30 * DAY,
            fim=moment - 2 * DAY,
        ),
        Atividade(
            materia_id=MATERIA_ID,
            id=-3,
            posicao=2,
            nome="Prova Objetiva (Mockada)",
            tipo="Prova Objetiva",
            categoria="Avaliação",
            presencial=True,
            periodo=PERIODO,
            peso=30,
            status=AWAITING_START,
            tentativa=1,
            tentativa_total=1,
            inicio=moment - 5 * DAY,
            fim=moment + 45 * DAY,
        ),
        Atividade(
            materia_id=MATERIA_ID,
            id=-4,
            posicao=3,
            nome="Prova Discursiva (Mockada)",
            tipo="Prova Discursiva",
            categoria="Avaliação",
            periodo=PERIODO,
            orientacao="Dez questões, todas respondíveis.",
            tempo_total=60,
            peso=30,
            status=AWAITING_START,
            tentativa=1,
            tentativa_total=2,
            inicio=moment - 5 * DAY,
            fim=moment + 45 * DAY,
        ),
        Atividade(
            materia_id=MATERIA_ID,
            id=-5,
            posicao=4,
            nome="Exame Final (Mockado)",
            tipo="Exame",
            categoria="Avaliação",
            periodo=PERIODO,
            peso=10,
            status=AWAITING_START,
            tentativa=1,
            tentativa_total=1,
            inicio=moment - 40 * DAY,
            fim=moment - 7 * DAY,
        ),
    ]


def trabalhos() -> list[Trabalho]:
    moment = _now()
    return [
        Trabalho(
            materia_id=MATERIA_ID,
            id=-1,
            vinculado_etapa=1,
            nome="Trabalho aprovado (Mockado)",
            tipo="Trabalho",
            ordem=1,
            periodo=PERIODO,
            inicio=moment - 30 * DAY,
            fim=moment - 10 * DAY,
            entregue_em=moment - 12 * DAY,
            nota=90.0,
            aprovado=True,
            pode_entregar=False,
        ),
        Trabalho(
            materia_id=MATERIA_ID,
            id=-2,
            vinculado_etapa=2,
            nome="Trabalho reprovado (Mockado)",
            tipo="Trabalho",
            ordem=2,
            periodo=PERIODO,
            inicio=moment - 30 * DAY,
            fim=moment - 8 * DAY,
            entregue_em=moment - 9 * DAY,
            nota=20.0,
            aprovado=False,
            pode_entregar=False,
        ),
        Trabalho(
            materia_id=MATERIA_ID,
            id=-3,
            vinculado_etapa=3,
            nome="Trabalho em correção (Mockado)",
            tipo="Trabalho",
            ordem=3,
            periodo=PERIODO,
            inicio=moment - 20 * DAY,
            fim=moment - 1 * DAY,
            entregue_em=moment - 2 * DAY,
            pode_entregar=False,
        ),
        Trabalho(
            materia_id=MATERIA_ID,
            id=-4,
            vinculado_etapa=4,
            nome="Trabalho aberto (Mockado)",
            tipo="Trabalho",
            ordem=4,
            periodo=PERIODO,
            inicio=moment - 5 * DAY,
            fim=moment + 15 * DAY,
            pode_entregar=True,
        ),
        Trabalho(
            materia_id=MATERIA_ID,
            id=-5,
            vinculado_etapa=5,
            nome="Trabalho não entregue (Mockado)",
            tipo="Trabalho",
            ordem=5,
            periodo=PERIODO,
            inicio=moment - 40 * DAY,
            fim=moment - 20 * DAY,
            pode_entregar=False,
        ),
    ]


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
            "Armazenado para posterior consulta.",
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


def _atividade_item(atividade: Atividade) -> dict[str, object]:
    return {
        "id": atividade.id,
        "nome": atividade.nome,
        "status": atividade.status,
        "peso": atividade.peso,
        "avaliacao": {"avaliacaoPresencial": atividade.presencial},
    }


def _trabalho_item(trabalho: Trabalho) -> dict[str, object]:
    return {
        "id": trabalho.id,
        "nome": trabalho.nome,
        "ordem": trabalho.ordem,
        "aprovado": trabalho.aprovado,
    }


def capturas() -> list[Captura]:
    moment = _now()
    bodies = {
        ATIVIDADES: {KEYS[ATIVIDADES]: [_atividade_item(a) for a in atividades()]},
        TRABALHOS: {KEYS[TRABALHOS]: [_trabalho_item(t) for t in trabalhos()]},
    }
    return [
        Captura(
            recurso=recurso,
            materia_id=MATERIA_ID,
            url=URL.format(recurso=recurso),
            status=200,
            corpo=json.dumps(body, ensure_ascii=False, indent=2),
            recebida_em=moment,
        )
        for recurso, body in bodies.items()
    ]
