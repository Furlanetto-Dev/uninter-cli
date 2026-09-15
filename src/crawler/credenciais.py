class NotLoggedIn(Exception):
    pass


def _required[T](value: T | None) -> T:
    if value is None:
        raise NotLoggedIn
    return value


class Credenciais:
    def __init__(
        self,
        ru: str | None = None,
        password: str | None = None,
        course_id: int | None = None,
    ) -> None:
        self._ru = ru
        self._password = password
        self._course_id = course_id

    @property
    def filled(self) -> bool:
        return (
            self._ru is not None
            and self._password is not None
            and self._course_id is not None
        )

    @property
    def ru(self) -> str:
        return _required(self._ru)

    @property
    def password(self) -> str:
        return _required(self._password)

    @property
    def course_id(self) -> int:
        return _required(self._course_id)

    def fill(self, ru: str, password: str, course_id: int) -> None:
        self._ru = ru
        self._password = password
        self._course_id = course_id

    def clear(self) -> None:
        self._ru = None
        self._password = None
        self._course_id = None
