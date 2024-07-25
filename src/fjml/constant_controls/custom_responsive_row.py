from typing import Optional, Callable, Final, Any

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

import flet as ft
from functools import cache

from .size_aware_control import SizeAwareControl


SIZE_NAMES: Final[list[str]] = ["xs", "sm", "md", "lg", "xl", "xxl"]
EMPTY_SIZES: Final[dict[str, int]] = dict(xs=0, sm=0, md=0, lg=0, xl=0, xxl=0)


@cache
def assign_size(width: int) -> str:
    if width < 576:
        return "xs"
    if width >= 576 and width < 768:
        return "sm"
    if width >= 768 and width < 992:
        return "md"
    if width >= 992 and width < 1200:
        return "lg"
    if width >= 1200 and width < 1400:
        return "xl"
    if width >= 1400:
        return "xxl"


valid_size_filter: Callable[[dict[str, Any]], dict[str, Any]] = lambda data: dict(
    filter((lambda x: (x[0] in SIZE_NAMES)), data.items())
)


def fill_forward(data: dict[str, int], column_const: int) -> dict[str, int]:
    key: str
    val: int = column_const

    for key in data.keys():
        if data[key] == 0:
            data[key] = val
            continue
        val = data[key]

    return data


def return_new_width(
    parent_width: float,
    column_const: float,
    assignments: Optional[dict[str, int]],
    spacing: float,
) -> float:
    sizes: dict[str, int]

    if not assignments:
        return parent_width

    sizes = dict(EMPTY_SIZES)
    sizes.update(assignments)
    assignments = fill_forward(valid_size_filter(sizes), column_const)

    return (
        (parent_width - spacing)
        * (assignments[assign_size(int(parent_width))] / column_const)
    ) - spacing * 2


class CustomResponsiveRow(SizeAwareControl):

    def __init__(
        self,
        controls: list[ft.Control] = [],
        columns: int = 12,
        spacing: int = 10,
        run_spacing: int = 10,
        scroll: ft.ScrollMode = ft.ScrollMode.ALWAYS,
        alignment: ft.MainAxisAlignment = ft.MainAxisAlignment.START,
        vertical_alignment: ft.CrossAxisAlignment = ft.CrossAxisAlignment.START,
        max_height: int = -1,
        min_height: int = -1,
        **kwargs,
    ) -> NoReturn:
        super().__init__(**kwargs)
        self.max_height: int = max_height
        self.min_height: int = min_height
        self.resize_interval: int = 10
        self.scroll: ft.ScrollMode = scroll
        self.columns: int = columns
        self.spacing: int = spacing
        self.controls: list[Control] = [
            self.preset_height(control) for control in controls
        ]
        self.vertical_alignment: ft.CrossAxisAlignment = vertical_alignment
        self.alignment: ft.MainAxisAlignment = alignment
        self.run_spacing: int = run_spacing
        self.on_resize: Optional[Callable[[ControlEvent], NoReturn]] = (
            self.__handle_canvas_resize
        )

        self.content: ft.Container = ft.Container(
            ft.Row(
                controls=self.controls,
                spacing=self.spacing,
                run_spacing=self.run_spacing,
                vertical_alignment=self.vertical_alignment,
                wrap=True,
                expand=True,
                scroll=self.scroll,
            ),
            alignment=ft.alignment.center,
            expand=True,
        )

    def __handle_canvas_resize(self, e: ft.ControlEvent) -> NoReturn:
        self.size = (e.width, e.height)
        self.controls = [
            self.change_control_width(control) for control in self.controls
        ]
        e.page.update()

    def change_control_width(self, control: ft.Control) -> ft.Control:
        control.width = return_new_width(
            self.get_width, self.columns, control.col, self.spacing
        )

        if self.get_height > self.max_height and self.max_height >= 0:
            control.height = self.max_height
            return control

        if self.get_height < self.min_height and self.min_height >= 0:
            control.height = self.min_height
            return control

        control.height = self.get_height
        return control

    def preset_height(self, control: ft.Control) -> ft.Control:
        try:
            control.height = 400
        except AttributeError:
            return control
        return control
