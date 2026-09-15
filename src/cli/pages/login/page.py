from api.credenciais.repository import CredencialRepository
from crawler.credenciais import Credenciais
from crawler.session import AvaSession, AvaUnreachable, LoginRejected
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Header, Input, Label, Static

from cli.components.footer import Footer
from cli.components.loading import Loading
from cli.pages.curso.page import ExplainCursoId

TITLE = "Entrar no AVA"
RU_LABEL = "RU"
SENHA_LABEL = "Senha"
CURSO_LABEL = "CursoId"
REMEMBER = "Lembrar de mim"
SUBMIT = "Entrar"
SIGNING_IN = "entrando no AVA"
INCOMPLETE = "[$text-error]Preencha RU, senha e CursoId.[/]"
EXPLAIN = "o que é isso"
HELP_KEY = "question_mark"
BOX_ID = "login-box"
RU_ID = "login-ru"
SENHA_ID = "login-senha"
CURSO_ID = "login-curso"
REMEMBER_ID = "login-remember"
SUBMIT_ID = "login-submit"
MESSAGE_ID = "login-message"
LOADING_ID = "login-loading"


class CursoIdInput(Input):
    def __init__(self, id: str) -> None:
        super().__init__(type="integer", id=id)

    def check_consume_key(self, key: str, character: str | None = None) -> bool:
        # Textual drops a screen binding whose key the focused widget claims, and
        # Input claims every printable one. Disowning "?" is what lets it through.
        if key == HELP_KEY:
            return False
        return super().check_consume_key(key, character)


class LoginPage(Screen[None]):
    BINDINGS = [
        Binding("escape", "app.quit", "sair"),
        Binding("enter", "submit", "entrar", show=False),
        Binding(HELP_KEY, "explain_curso", EXPLAIN, key_display="?", priority=True),
    ]

    def __init__(
        self,
        host: App[None],
        ava: AvaSession,
        credenciais: Credenciais,
        credenciais_db: CredencialRepository,
    ) -> None:
        super().__init__()
        self._host = host
        self._ava = ava
        self._credenciais = credenciais
        self._credenciais_db = credenciais_db

    def compose(self) -> ComposeResult:
        yield Header()
        yield Loading(SIGNING_IN, id=LOADING_ID)
        with Vertical(id=BOX_ID):
            yield Static(f"[bold]{TITLE}[/bold]")
            yield Label(RU_LABEL)
            yield Input(id=RU_ID)
            yield Label(SENHA_LABEL)
            yield Input(password=True, id=SENHA_ID)
            yield Label(CURSO_LABEL)
            yield CursoIdInput(CURSO_ID)
            yield Checkbox(REMEMBER, value=True, id=REMEMBER_ID)
            yield Static(id=MESSAGE_ID)
            yield Button(SUBMIT, id=SUBMIT_ID)
        yield Footer()

    async def on_mount(self) -> None:
        stored = await self._credenciais_db.find()
        if self._credenciais.filled:
            self.fill_form(
                self._credenciais.ru,
                str(self._credenciais.course_id),
                stored is not None,
            )
            self.attempt()
            return
        if stored is not None:
            self.fill_form(stored.ru, str(stored.course_id), True)
        self.show_form()

    def show_form(self) -> None:
        self.query_one(f"#{LOADING_ID}", Loading).display = False
        self.query_one(f"#{BOX_ID}", Vertical).display = True
        self.field(RU_ID).focus()

    def show_loading(self) -> None:
        self.query_one(f"#{BOX_ID}", Vertical).display = False
        self.query_one(f"#{LOADING_ID}", Loading).display = True

    def fill_form(self, ru: str, course_id: str, remembered: bool) -> None:
        self.field(RU_ID).value = ru
        self.field(CURSO_ID).value = course_id
        self.query_one(f"#{REMEMBER_ID}", Checkbox).value = remembered

    def field(self, id: str) -> Input:
        return self.query_one(f"#{id}", Input)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "explain_curso":
            return self.focused is self.field(CURSO_ID)
        return True

    def action_explain_curso(self) -> None:
        self._host.push_screen(ExplainCursoId())

    def message(self, text: str) -> None:
        self.query_one(f"#{MESSAGE_ID}", Static).update(text)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.action_submit()

    def action_submit(self) -> None:
        ru = self.field(RU_ID).value.strip()
        password = self.field(SENHA_ID).value
        course_id = self.field(CURSO_ID).value.strip()
        if not (ru and password and course_id):
            self.message(INCOMPLETE)
            return
        self._credenciais.fill(ru, password, int(course_id))
        self._ava.forget()
        self.attempt()

    @work
    async def attempt(self) -> None:
        self.show_loading()
        try:
            await self._ava.log_in()
        except LoginRejected as rejection:
            self.refuse(str(rejection))
            return
        except AvaUnreachable:
            # Reading what is already stored is the point of the app; a dark AVA
            # is not a reason to lock the student out of it. Nothing is written:
            # credentials the AVA never saw are credentials nobody verified.
            self.dismiss()
            return
        await self.remember()
        self.dismiss()

    def refuse(self, reason: str) -> None:
        self.show_form()
        self.message(f"[$text-error]{reason}[/]")
        self.field(SENHA_ID).value = ""
        self.field(SENHA_ID).focus()

    async def remember(self) -> None:
        if self.query_one(f"#{REMEMBER_ID}", Checkbox).value:
            await self._credenciais_db.remember(
                self._credenciais.ru,
                self._credenciais.password,
                self._credenciais.course_id,
            )
        else:
            await self._credenciais_db.forget()
