---
name: building-the-materias-list
description: MateriaList.show stops being a nested loop over ((True, "EM CURSO"), (False, "FINALIZADAS")) and becomes three sentences — one MateriaAggregate per Vigencia in api/materias, built by named filters, build_options yielding the options, and a context manager that keeps the highlight. Read before touching how the matérias list is built, how the highlight survives a resync, or before proposing a third group.
projects: [api, frontend]
status: done
created_at: 2026-09-07
---

# Building the matérias list

`MateriaList.show` is the method that rebuilds the list on every sync, and today it does five things in a single body:

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

It saves the highlight, clears the widget, partitions the matérias, draws three kinds of row and keeps the `id → Materia` index — all woven together across two levels of loop. The partition criterion is `GRUPOS = ((True, "EM CURSO"), (False, "FINALIZADAS"))`, a tuple that only makes sense to whoever already knows that `True` is `Materia.vigente`; the comprehension that consumes it compares booleans by identity; the separator depends on the widget already having rows; and the index is filled as a side effect of drawing.

After this spec the method only displays matérias that are already grouped. Grouping belongs to a `MateriaAggregate` that lives in `api/materias/`, built by named filter functions; drawing is a pure function of the TUI; and no comprehension is left loose in the body of a method.

The interface is described in [0004](0004-textual-tui.md), which fixed the two groups, the `disabled` title as separator and restoring the highlight by id; what the project is lives in [CONTEXT.md](../../CONTEXT.md).

## Decisions

### `show` only displays, in three sentences

```python
def show(self, materias: list[Materia]) -> None:
    with self._keeping_focus():
        self._materias = index_by_id(materias)
        self.clear_options()
        self.add_options(build_options(aggregate_materias(materias), self._selo))
```

Index, clear, build — inside a block that gives the highlight back on exit. Each line calls a named function; none decides who goes into which group nor how a group becomes rows. `GRUPOS` ceases to exist.

**The order inside the block matters.** `em_foco` resolves the current highlight by looking up `_materias`, so the index can only be replaced after the context manager has already captured the focused matéria — that is, inside the `with`, not before it. Outside that constraint the three lines are independent.

### Each group is a `MateriaAggregate` in `api/materias`, keyed by `Vigencia`

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

Which matérias go together, and in what order, is a domain decision, not a screen one — which is why the aggregate lives in `api/materias/aggregate.py`, next to `Media` in `api/atividades/media.py`, which is the same kind of object: a frozen value derived from a list of entities, with no identity and no mutation. [0003](0003-crawler-api-cli-layers.md) puts in `api` "what persists and what decides"; grouping decides.

The key of each aggregate is `Vigencia`, not a boolean nor a string. `VIGENTE` comes from the field the AVA sends under that name in the matérias payload; `FINALIZADA` is the word [0004](0004-textual-tui.md) already used for the other group. `Materia.vigente` remains a `bool` — the enum names the two sides of the partition, it does not replace the field.

The two partition criteria become `filter_vigentes` and `filter_finalizadas`. That is what takes the comprehension comparing `vigente` out of the body of any function: the factory reads "vigentes on one side, finalizadas on the other" and nothing else. "Vigentes first" is the order in which the two lines appear, and an empty group disappears in the factory — not in whoever draws. `vazio` exists so that whoever consumes the aggregate need not know that "empty" means a list with no elements.

The cost is walking the list twice. It is the right price for a partition that is binary by construction — `vigente` is a `bool` in the DTO, in the entity and in the database — and for 26 matérias.

### The titles are a map from `Vigencia` to text, in the TUI

```python
TITULOS = {Vigencia.VIGENTE: "EM CURSO", Vigencia.FINALIZADA: "FINALIZADAS"}
```

"EM CURSO" and "FINALIZADAS" are screen text — upper case, plural — and stay in `materias.py`, next to `SELO_PENDENTE` and `QUADROS`, as `atividades.py` does with `SEM_ATIVIDADES`. The map is keyed by a named enum, and that is the difference from the `dict[bool, str]` rejected below: whoever reads `TITULOS[Vigencia.VIGENTE]` knows what is being translated.

### Drawing is a pure function that yields the options

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

The separator is "between aggregates", decided by the `enumerate`, not "if the widget already has rows". Title and row have their own constructors, so the loop reads like the screen: separator, title, one option per matéria. The badge comes in as a function because it depends on widget state — `_sincronizando` and `_quadro`, from [0007](0007-background-queue-and-reset.md) — and is the only point where drawing touches that state.

`OptionList.add_options` accepts any iterable of options and separators; checked in the signature of the installed Textual 8.2.8, `Iterable[OptionListContent]`. The generator goes straight in, without becoming a list.

`build_options` follows `build_table` from `atividades.py`: a module function, input is data, output is what the widget receives. It is the same design [0004](0004-textual-tui.md) chose for the detail panel, now applied to the list.

### The index is a function, outside the drawing

`index_by_id(materias)` returns the `dict[str, Materia]` that `materia()` and `em_foco` look up. Every matéria falls into exactly one aggregate, so the index of "all matérias" and the index of "all drawn matérias" are the same — it need not be filled row by row inside the loop.

### Keeping the highlight is a context manager

```python
@contextmanager
def _keeping_focus(self) -> Generator[None]:
    anterior = self.em_foco
    yield
    self._focar(anterior)
```

Saving before and restoring after are two lines that only make sense together, and the `with` is the language construct for exactly that: whoever reads `show` sees that the whole block runs "keeping the focus", without having to find the pair at the end of the method.

The cost is hiding control flow behind an idiom. It is worth it because the pair has to stay paired through any future change to `show`, and because it takes out of the method the only two lines that are not about building the list. `_focar` and `em_foco` do not change; restoring is still by id, with the first matéria as fallback, as [0004](0004-textual-tui.md) fixed.

### Verification is pyright, the screen and a headless harness

There is no test file in the app today, and none covers `MateriaList`. The change is checked with `pyright` passing in strict mode and with the app open showing the same two groups, in the same order, with the separator between them, the highlight landing on the first matéria and surviving `r`.

Equivalence with the previous code was measured off the screen, with Textual's `run_test()`: the two versions of `MateriaList` produced the same sequence of options, the same highlight and the same fallback in seven scenarios — a list with both groups, only one group, empty, a resync with the focused matéria kept, a resync with it removed, and a resync during an in-flight sync.

`aggregate_materias`, `filter_vigentes` and `filter_finalizadas` in `api`, `index_by_id` and `build_options` in the TUI, are pure. When the strategy in [0002](../rejected/0002-testing-strategy.md) reaches the TUI, they are the ones tested without bringing up a widget.

## Rejected

- **`Grupo` as a `NamedTuple` of title and matérias, with the comprehensions inline in the factory.** It was the first version of this spec. An anonymous pair does not say what it is, and the comprehension inside the factory only moved the `if materia.vigente` that was meant to be named. The aggregate gets a name of its own, `vazio`, and is built by filter functions.
- **`MateriaAggregate` in the TUI, with the title inside.** It was the second version. It joins in a single class what is domain — which matérias go together — and what is screen — what the group is called —, and leaves in `cli/` a decision that [0003](0003-crawler-api-cli-layers.md) sends to `api/`.
- **A single aggregate with `vigentes` and `finalizadas` as fields, in the exact mould of `Media`.** Drops the enum, but the screen would have to rebuild the title-list pairs and handle the separator between empty groups with extra helpers. One aggregate per group keeps `build_options` in a single loop.
- **Keeping the loop and only extracting `_add_grupo(titulo, grupo)`.** The tuple goes away, but the separator still depends on `option_count`, the drawing stays inside the widget, and `show` is still the one that knows a group is a title plus rows. It is a patch in the same shape.
- **Pure functions without the context manager, with `anterior = self.em_foco` and `self._focar(anterior)` inline.** Leaves `show` with five lines instead of three, two of them about focus and three about the list, and depends on whoever edits the method keeping the pair at the ends. The `with` makes the pairing structural.
- **`dict[bool, str]` in place of the tuple of tuples.** Only changes the shape: the boolean is still the key, and whoever reads `{True: "EM CURSO"}` still does not know that `True` is `vigente`.
- **`MateriaAggregate` with a predicate instead of a list.** Lambdas in a module constant for a partition that only has two sides. If one day there is a third group, `vigente` stops being a `bool` and the change is one of domain, not of list.
- **`itertools.groupby` over the order the repository already returns.** `MateriaRepository.list_all` orders by `vigente desc, nome`, so the list arrives grouped. Leaning the screen on that couples the widget to another layer's `ORDER BY`: changing the ordering there would duplicate titles here, with no error to warn.
- **Promoting `vigente` to an enum on the entity.** Touches DTO, entity, repository and schema to fix a TUI method. `Vigencia` is the aggregate's key, not a field of the matéria: DTO, entity and database do not change.
- **A `Materia.situacao` property returning the title.** Puts screen text inside the entity, which [0003](0003-crawler-api-cli-layers.md) keeps unaware that an interface exists.
