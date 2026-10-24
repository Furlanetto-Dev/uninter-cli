from api.credenciais.repository import CredencialRepository
from crawler.credenciais import Credenciais
from settings import Settings


def from_env(settings: Settings) -> Credenciais:
    if settings.ru is None or settings.password is None:
        return Credenciais()
    return Credenciais(settings.ru, settings.password)


async def stored(
    credenciais: Credenciais, credenciais_db: CredencialRepository
) -> Credenciais:
    if credenciais.filled:
        return credenciais
    remembered = await credenciais_db.find()
    if remembered is None:
        return credenciais
    return Credenciais(remembered.ru, remembered.password, remembered.course_id)
