from sqlmodel import Field, SQLModel

REMEMBERED_ID = 1


class Credencial(SQLModel, table=True):
    id: int = Field(default=REMEMBERED_ID, primary_key=True)
    ru: str
    password: str
    course_id: int
