import dataclasses
import json
from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple, Protocol, cast

MISSING = "—"


class Fetched(Protocol):
    @property
    def item(self) -> object | None: ...

    @property
    def status(self) -> int | None: ...

    @property
    def url(self) -> str: ...

    @property
    def at(self) -> datetime | None: ...

    @property
    def error(self) -> str | None: ...

    @property
    def missing(self) -> str: ...


class Stored(Protocol):
    @property
    def label(self) -> str: ...

    @property
    def fields(self) -> Sequence[tuple[str, str]]: ...

    @property
    def json(self) -> str | None: ...


class DebugSource(Protocol):
    async def debug_view(self) -> tuple[Fetched, Stored] | None: ...


class FetchedItem(NamedTuple):
    item: object | None = None
    status: int | None = None
    url: str = ""
    at: datetime | None = None
    error: str | None = None
    missing: str = MISSING


class StoredRecord(NamedTuple):
    label: str = ""
    fields: Sequence[tuple[str, str]] = ()
    json: str | None = None


def _names(record: object) -> Sequence[str]:
    model_fields = getattr(type(record), "model_fields", None)
    if isinstance(model_fields, dict):
        return list(cast(dict[str, object], model_fields))
    if dataclasses.is_dataclass(record) and not isinstance(record, type):
        return [field.name for field in dataclasses.fields(record)]
    return list(vars(record))


def _json(record: object) -> str | None:
    dump = getattr(record, "model_dump_json", None)
    if callable(dump):
        return cast(str, dump(indent=2))
    if dataclasses.is_dataclass(record) and not isinstance(record, type):
        return json.dumps(
            dataclasses.asdict(record), indent=2, ensure_ascii=False, default=str
        )
    return None


def stored_record(label: str, record: object | None) -> StoredRecord:
    if record is None:
        return StoredRecord(label=label)
    fields = [(name, repr(getattr(record, name))) for name in _names(record)]
    return StoredRecord(label, fields, _json(record))
