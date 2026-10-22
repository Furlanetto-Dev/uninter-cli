from datetime import date

import pytest
from textual.app import App, ComposeResult

from cli.pages.agendamento.components.datepicker import (
    Availability,
    DatePicker,
    shift_month,
)

TODAY = date(2026, 10, 12)


class PickerHost(App[None]):
    def __init__(self, is_available: Availability | None = None) -> None:
        super().__init__()
        self._is_available = is_available
        self.chosen: list[date] = []
        self.highlighted: list[date] = []

    def compose(self) -> ComposeResult:
        yield DatePicker(TODAY, is_available=self._is_available)

    def on_mount(self) -> None:
        self.query_one(DatePicker).focus()

    def on_date_picker_chosen(self, event: DatePicker.Chosen) -> None:
        self.chosen.append(event.day)

    def on_date_picker_highlighted(self, event: DatePicker.Highlighted) -> None:
        self.highlighted.append(event.day)


def theme_colour(app: App[None], variable: str) -> str:
    return app.get_css_variables()[variable].lower()


def painted_lines(picker: DatePicker) -> list[str]:
    return [picker.render_line(y).text for y in range(picker.size.height)]


def background_of_day(picker: DatePicker, day: int) -> str:
    for y in range(picker.size.height):
        for segment in picker.render_line(y):
            if (
                segment.text.strip() == str(day)
                and segment.style
                and segment.style.bgcolor
            ):
                return segment.style.bgcolor.name
    raise AssertionError(f"day {day} is not painted")


async def pick(*keys: str, is_available: Availability | None = None) -> PickerHost:
    app = PickerHost(is_available)
    async with app.run_test(size=(80, 30)) as pilot:
        await pilot.pause()
        for key in keys:
            await pilot.press(key)
            await pilot.pause()
    return app


@pytest.mark.parametrize(
    ("day", "months", "expected"),
    [
        (date(2026, 10, 12), 1, date(2026, 11, 12)),
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
        (date(2026, 12, 15), 1, date(2027, 1, 15)),
        (date(2026, 1, 15), -1, date(2025, 12, 15)),
    ],
)
def test_shifting_a_month_keeps_the_day_when_it_exists(
    day: date, months: int, expected: date
) -> None:
    assert shift_month(day, months) == expected


async def test_enter_chooses_today() -> None:
    app = await pick("enter")
    assert app.chosen == [date(2026, 10, 12)]


async def test_arrows_walk_days_and_weeks() -> None:
    app = await pick("right", "down", "enter")
    assert app.chosen == [date(2026, 10, 20)]


async def test_walking_off_the_month_turns_the_page() -> None:
    app = await pick("down", "down", "down", "enter")
    assert app.chosen == [date(2026, 11, 2)]


async def test_page_down_jumps_a_month() -> None:
    app = await pick("pagedown", "enter")
    assert app.chosen == [date(2026, 11, 12)]


async def test_a_past_day_cannot_be_chosen() -> None:
    app = await pick("left", "enter")
    assert app.chosen == []


async def test_only_offered_days_can_be_chosen() -> None:
    offered = {date(2026, 10, 14)}
    app = await pick(
        "right", "enter", "right", "enter", is_available=offered.__contains__
    )
    assert app.chosen == [date(2026, 10, 14)]


async def test_moving_the_cursor_announces_the_day_it_lands_on() -> None:
    app = await pick("right", "down")
    assert app.highlighted == [date(2026, 10, 13), date(2026, 10, 20)]


async def test_the_month_and_its_days_are_on_screen() -> None:
    app = PickerHost()
    async with app.run_test(size=(80, 30)) as pilot:
        await pilot.pause()
        lines = painted_lines(app.query_one(DatePicker))
    assert lines[0].strip() == "outubro 2026"
    assert lines[1].split() == ["D", "S", "T", "Q", "Q", "S", "S"]
    assert lines[2].split() == ["1", "2", "3"]
    assert lines[-1].split() == ["25", "26", "27", "28", "29", "30", "31"]


async def test_the_cursor_day_is_painted_in_the_accent() -> None:
    app = PickerHost()
    async with app.run_test(size=(80, 30)) as pilot:
        await pilot.pause()
        picker = app.query_one(DatePicker)
        assert background_of_day(picker, 12) == theme_colour(app, "accent")
