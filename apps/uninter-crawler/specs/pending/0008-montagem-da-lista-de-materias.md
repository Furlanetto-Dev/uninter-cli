---
name: montagem-da-lista-de-materias
description: MateriaList.show deixa de ser um laço aninhado sobre ((True, "EM CURSO"), (False, "FINALIZADAS")) e vira três frases — um MateriaAggregate por vigência em api/materias, montado por filtros nomeados, build_options que gera as opções, e um context manager que preserva o destaque. Ler antes de mexer em como a lista de matérias é montada, em como o destaque sobrevive a um resync, ou de propor um terceiro grupo.
projects: [api, frontend]
status: pending
created_at: 2026-09-07
---

# Montagem da lista de matérias

`MateriaList.show` é o método que reconstrói a lista a cada sync, e hoje ele faz cinco coisas num corpo só:

```python
def show(self, materias: list[Materia]) -> None:
    anterior = self.em_foco
    self.clear_options()
    self._materias = {}
    for vigente, titulo in GRUPOS:
        grupo = [materia for materia in materias if materia.vigente is vigente]
        if not grupo:
            continue
        if self.option_count:
            self.add_option(None)
        self.add_option(Option(f"[dim]{titulo}[/dim]", disabled=True))
        for materia in grupo:
            chave = str(materia.id)
            self._materias[chave] = materia
            self.add_option(Option(_linha(materia, self._selo(materia)), id=chave))
    self._focar(anterior)
```

Guarda o destaque, zera o widget, particiona as matérias, desenha três tipos de linha e mantém o índice `id → Materia` — tudo entrelaçado em dois níveis de laço. O critério da partição é `GRUPOS = ((True, "EM CURSO"), (False, "FINALIZADAS"))`, uma tupla que só faz sentido para quem já sabe que `True` é `Materia.vigente`; a comprehension que a consome compara booleanos por identidade; o separador depende de o widget já ter linhas; e o índice é preenchido como efeito colateral do desenho.

Depois desta spec o método só exibe matérias já agrupadas. Agrupar é de um `MateriaAggregate` que mora em `api/materias/`, montado por funções de filtro com nome; desenhar é uma função pura da TUI; e nenhuma comprehension fica solta no corpo de um método.

A interface está descrita em [0004](../done/0004-tui-em-textual.md), que fixou os dois grupos, o título `disabled` como separador e a restauração do destaque por id; o que o projeto é está em [CONTEXT.md](../../../../CONTEXT.md).

## Decisões

### `show` só exibe, em três frases

```python
def show(self, materias: list[Materia]) -> None:
    with self._keeping_focus():
        self._materias = index_by_id(materias)
        self.clear_options()
        self.add_options(build_options(aggregate_materias(materias), self._selo))
```

Índice, limpeza, montagem — dentro de um bloco que devolve o destaque ao sair. Cada linha chama uma função com nome; nenhuma decide quem entra em qual grupo nem como um grupo vira linha. `GRUPOS` deixa de existir.

**A ordem dentro do bloco importa.** `em_foco` resolve o destaque atual consultando `_materias`, então o índice só pode ser substituído depois que o context manager já capturou a matéria em foco — isto é, dentro do `with`, não antes dele. Fora dessa restrição as três linhas são independentes.

### Cada grupo é um `MateriaAggregate` em `api/materias`, chaveado por `Vigencia`

```python
class Vigencia(Enum):
    VIGENTE = "vigente"
    FINALIZADA = "finalizada"


@dataclass(frozen=True)
class MateriaAggregate:
    vigencia: Vigencia
    materias: list[Materia]

    @property
    def vazio(self) -> bool:
        return not self.materias


def filter_vigentes(materias: list[Materia]) -> list[Materia]:
    return [materia for materia in materias if materia.vigente]


def filter_finalizadas(materias: list[Materia]) -> list[Materia]:
    return [materia for materia in materias if not materia.vigente]


def aggregate_materias(materias: list[Materia]) -> list[MateriaAggregate]:
    agregados = [
        MateriaAggregate(Vigencia.VIGENTE, filter_vigentes(materias)),
        MateriaAggregate(Vigencia.FINALIZADA, filter_finalizadas(materias)),
    ]
    return [agregado for agregado in agregados if not agregado.vazio]
```

Quais matérias andam juntas, e em que ordem, é decisão de domínio, não de tela — por isso o agregado mora em `api/materias/aggregate.py`, ao lado de `Media` em `api/atividades/media.py`, que é o mesmo tipo de objeto: um valor congelado derivado de uma lista de entidades, sem identidade nem mutação. A [0003](../done/0003-camadas-crawler-api-cli.md) põe em `api` "o que persiste e o que decide"; agrupar decide.

A chave de cada agregado é `Vigencia`, não um booleano nem um texto. `VIGENTE` vem do campo que o AVA manda com esse nome no payload de matérias; `FINALIZADA` é a palavra que a [0004](../done/0004-tui-em-textual.md) já usava para o outro grupo. `Materia.vigente` continua sendo `bool` — o enum nomeia os dois lados da partição, não substitui o campo.

Os dois critérios de partição viram `filter_vigentes` e `filter_finalizadas`. É o que tira do corpo de qualquer função a comprehension que compara `vigente`: a fábrica lê "vigentes de um lado, finalizadas do outro" e nada mais. "Vigentes primeiro" é a ordem em que as duas linhas aparecem, e grupo vazio some na fábrica — não em quem desenha. `vazio` existe para que quem consome o agregado não precise saber que "vazio" significa lista sem elementos.

O custo é percorrer a lista duas vezes. É o preço certo para uma partição que é binária por construção — `vigente` é um `bool` no DTO, na entity e no banco — e para 26 matérias.

### Os títulos são um mapa de `Vigencia` para texto, na TUI

```python
TITULOS = {Vigencia.VIGENTE: "EM CURSO", Vigencia.FINALIZADA: "FINALIZADAS"}
```

"EM CURSO" e "FINALIZADAS" são texto de tela — maiúsculo, no plural — e ficam em `materias.py`, ao lado de `SELO_PENDENTE` e `QUADROS`, como `atividades.py` faz com `SEM_ATIVIDADES`. O mapa é chaveado por um enum com nome, e essa é a diferença para o `dict[bool, str]` rejeitado abaixo: quem lê `TITULOS[Vigencia.VIGENTE]` sabe o que está sendo traduzido.

### Desenhar é uma função pura que gera as opções

```python
def _titulo(agregado: MateriaAggregate) -> Option:
    return Option(f"[dim]{TITULOS[agregado.vigencia]}[/dim]", disabled=True)


def _opcao(materia: Materia, selo: str) -> Option:
    return Option(_linha(materia, selo), id=str(materia.id))


def build_options(
    agregados: list[MateriaAggregate], selo: Callable[[Materia], str]
) -> Iterator[Option | None]:
    for indice, agregado in enumerate(agregados):
        if indice:
            yield None
        yield _titulo(agregado)
        for materia in agregado.materias:
            yield _opcao(materia, selo(materia))
```

O separador é "entre agregados", decidido pelo `enumerate`, e não "se o widget já tem linhas". Título e linha têm construtores próprios, então o laço lê como a tela: separador, título, uma opção por matéria. O selo entra como função porque depende de estado do widget — `_sincronizando` e `_quadro`, da [0007](../done/0007-fila-em-background-e-reset.md) — e é o único ponto em que o desenho toca esse estado.

`OptionList.add_options` aceita qualquer iterável de opções e separadores; verificado na assinatura do Textual 8.2.8 instalado, `Iterable[OptionListContent]`. O gerador entra direto, sem virar lista.

`build_options` segue `build_table` de `atividades.py`: função de módulo, entrada é dado, saída é o que o widget recebe. É o mesmo desenho que a [0004](../done/0004-tui-em-textual.md) escolheu para o painel de detalhe, agora aplicado à lista.

### O índice é uma função, fora do desenho

`index_by_id(materias)` devolve o `dict[str, Materia]` que `materia()` e `em_foco` consultam. Toda matéria cai em exatamente um agregado, então o índice de "todas as matérias" e o índice de "todas as matérias desenhadas" são o mesmo — não precisa ser preenchido linha a linha dentro do laço.

### Preservar o destaque é um context manager

```python
@contextmanager
def _keeping_focus(self) -> Generator[None]:
    anterior = self.em_foco
    yield
    self._focar(anterior)
```

Guardar antes e restaurar depois são duas linhas que só fazem sentido juntas, e o `with` é a construção da linguagem para exatamente isso: quem lê `show` vê que o bloco inteiro roda "mantendo o foco", sem precisar achar o par no fim do método.

O custo é esconder controle de fluxo atrás de um idioma. Vale a pena porque o par tem que continuar pareado em qualquer mudança futura de `show`, e porque tira do método as duas únicas linhas que não são sobre montar a lista. `_focar` e `em_foco` não mudam; a restauração continua por id, com a primeira matéria como fallback, como a [0004](../done/0004-tui-em-textual.md) fixou.

### A verificação é o pyright, a tela e um harness sem tela

Não há arquivo de teste no app hoje, e nenhum cobre `MateriaList`. A mudança é conferida com `pyright` em modo strict passando e com o app aberto mostrando os mesmos dois grupos, na mesma ordem, com o separador entre eles, o destaque caindo na primeira matéria e sobrevivendo a `r`.

A equivalência com o código anterior foi medida fora da tela, com `run_test()` do Textual: as duas versões de `MateriaList` produziram a mesma sequência de opções, o mesmo destaque e o mesmo fallback em sete cenários — lista com os dois grupos, só um grupo, vazia, resync com a matéria em foco mantida, resync com ela removida, e resync durante um sync em voo.

`aggregate_materias`, `filter_vigentes` e `filter_finalizadas` em `api`, `index_by_id` e `build_options` na TUI, são puras. Quando a estratégia da [0002](0002-estrategia-de-testes.md) chegar à TUI, são elas que se testam sem subir widget.

## Rejeitados

- **`Grupo` como `NamedTuple` de título e matérias, com as comprehensions inline na fábrica.** Foi a primeira versão desta spec. Um par anônimo não diz o que é, e a comprehension dentro da fábrica só mudava de lugar o `if materia.vigente` que se queria nomear. O agregado ganha nome próprio, `vazio`, e é montado por funções de filtro.
- **`MateriaAggregate` na TUI, com o título dentro.** Foi a segunda versão. Junta numa classe só o que é domínio — quais matérias andam juntas — e o que é tela — como o grupo se chama —, e deixa em `cli/` uma decisão que a [0003](../done/0003-camadas-crawler-api-cli.md) manda para `api/`.
- **Um agregado único com `vigentes` e `finalizadas` como campos, no molde exato de `Media`.** Dispensa o enum, mas a tela precisaria remontar os pares título-lista e tratar o separador entre grupos vazios com helpers a mais. Um agregado por grupo mantém `build_options` num laço só.
- **Manter o laço e só extrair `_add_grupo(titulo, grupo)`.** Some a tupla, mas o separador continua dependendo de `option_count`, o desenho continua dentro do widget, e `show` continua sendo quem sabe que um grupo é título mais linhas. É um remendo na mesma forma.
- **Funções puras sem o context manager, com `anterior = self.em_foco` e `self._focar(anterior)` inline.** Deixa `show` com cinco linhas em vez de três, duas delas sobre foco e três sobre lista, e depende de quem editar o método manter o par nas pontas. O `with` faz o pareamento estrutural.
- **`dict[bool, str]` no lugar da tupla de tuplas.** Só troca a forma: o booleano continua sendo a chave, e quem lê `{True: "EM CURSO"}` continua sem saber que `True` é `vigente`.
- **`MateriaAggregate` com predicado em vez de lista.** Lambdas em constante de módulo para uma partição que só tem dois lados. Se um dia houver um terceiro grupo, `vigente` deixa de ser `bool` e a mudança é de domínio, não de lista.
- **`itertools.groupby` sobre a ordem que o repository já devolve.** `MateriaRepository.list_all` ordena por `vigente desc, nome`, então a lista chega agrupada. Apoiar a tela nisso acopla o widget ao `ORDER BY` de outra camada: trocar a ordenação lá duplicaria títulos aqui, sem erro para avisar.
- **Promover `vigente` a um enum na entity.** Toca DTO, entity, repository e schema para consertar um método da TUI. `Vigencia` é a chave do agregado, não um campo da matéria: DTO, entity e banco não mudam.
- **Uma property `Materia.situacao` devolvendo o título.** Põe texto de tela dentro da entity, que a [0003](../done/0003-camadas-crawler-api-cli.md) mantém sem saber que existe interface.
