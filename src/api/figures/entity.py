from datetime import datetime

from sqlmodel import Field, SQLModel


class Figure(SQLModel, table=True):
    url: str = Field(primary_key=True)
    data: bytes
    fetched_at: datetime
