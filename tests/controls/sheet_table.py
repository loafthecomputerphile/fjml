import time
from sys import getsizeof
import asyncio
from dataclasses import dataclass, field
from typing import (
    Final, 
    Any, 
    Type, 
    Union,
    Optional,
    Iterator,
    NoReturn,
    Callable
)
from copy import deepcopy
from methodtools import lru_cache
from functools import partial
import pandas as pd
import numpy as np
import nest_asyncio
import flet as ft
from .theme import ThemeSettings
from modules import (
    BookFactory, BaseBook, 
    OpenpyxlBookModel, XlwingsBookModel, 
    UndoRedoBuffer, Info, 
    UndoData, RedoData, 
    InputData, 
)

nest_asyncio.apply()
OptionalNum = Union[int, float, None]
OptionalStr = Optional[str]
OptionalBoolNum = Union[int, float, bool, None]
OptionalInt = Optional[int]


async def test_sheet(page: ft.Page) -> NoReturn:
    page.theme_mode = ThemeSettings.MODE
    page.bgcolor = ft.colors.GREY_50
    page.title = "Development Program"
    page.horizontal_alignment = "center"
    page.fonts = ThemeSettings.FONTS
    page.theme = ThemeSettings.THEME
     
    page.update()
    
    table: SheetTable = SheetTable(
        engine="openpyxl",
        letters=["A", "B", "C", "D", "E", "F", "G", "H", "I"],
        titles=["Species", "Leaf Color", "Height", "Species", "Leaf Color", "Height", "Species", "Leaf Color", "Height"],
        start_row=2,
        end_row=140,
        editable_letters=[],
        filename="test_data.xlsx",
    )
    
    print(getsizeof(table))
    
    await page.add_async(table)


@dataclass
class IteratorTracker:
    sheet_iterator: list[str] = field(default_factory=list)
    table_iterator: list[str] = field(default_factory=list)
    last_sheet_index: int = 0
    last_table_index: int = 0
    
    def new_sheet_index(self, data) -> int:
        self.last_sheet_index = self.sheet_iterator.index(data)
        return self.last_sheet_index
    
    def new_table_index(self, data) -> int:
        self.last_table_index = self.table_iterator.index(data)
        return self.last_table_index


COL_SPACING: int = 36
TABLE_BGCOLOR: str = "white"
SHEET_BTN_STYLE: ft.ButtonStyle = ft.ButtonStyle(
    color="green700",
    bgcolor={
        "pressed":"green50",
        "":"white"
    },
    side=ft.BorderSide(1.2, "black"),
    shape=ft.RoundedRectangleBorder(radius=8),
)


class SheetTable(ft.Container):
    
    GET: tuple[str, ...] = (
        "value"
    )
    
    POST: tuple[str, ...] = (
        "value"
    )
    
    CALL: tuple[str, ...] = (
        "append"
    )
    
    LINK_NAME: Final[str] = "SheetTable"
    
    def __init__(
        self, filename: str, engine: OptionalStr = "openpyxl", sheet_textstyle: Optional[ft.TextStyle] = None, sheet_bgcolor: OptionalStr = "white",
        sheet_params: list[dict[str, Any]] = None, table_params: list[dict[str, Any]] = None,
        restricted_sheets: list[str] = [], *args, **kwargs
    ) -> NoReturn:
        super().__init__( *args, **kwargs)
        
        """ Book Model variables """
        self.filename: str = filename
        self.book_type: str = engine
        self.last_clicked_sheet: Any
        self.tracker: IteratorTracker
        self.table_iterator: list[str]
        self.sheet_iterator: list[str]
        self.on_table: bool = False
        self.sheet_slider: ft.Container
        self.table_slider: ft.Container
        self.rows: list[ft.DataRow]
        self.table_title: ft.DataTable
        self.data_table: ft.DataTable
        self.table_conainer: ft.Container
        self.sheet_rows: ft.Row
        self.table_rows: ft.Row
        self.col_title_ui: ft.Container
        self.sheet_params: list[dict[str, Any]] = sheet_params
        self.table_params: list[dict[str, Any]] = table_params
        self.selected_row: int = 0
        self.restricted_sheets: list[str] = restricted_sheets
        self.book_params: dict[str, Any] = dict(
            engine = self.book_type,
            sheet_params = self.sheet_params,
            table_params = self.table_params
        )
        self.past_selected_row: int = 0
        
        factory: BookFactory = BookFactory()
        self.book: Union[OpenpyxlBookModel, XlwingsBookModel] = factory.create_book(
            self.book_params
        )
    
    def build(self) -> NoReturn:
        super().build()
        self.load_new_file(self.filename, self.restricted_sheets)
    
    def load_new_file(self, file_name, restricted_sheets = [], mounted=False) -> NoReturn:
        if not restricted_sheets:
            restricted_sheets = self.restricted_sheets
            
        asyncio.run(self.book.load_book(file_name, restricted_sheets))
        self.rows: list[ft.DataRow] = asyncio.run(self.generate_sheet("Sheet"))
        
        self.sheet_slider: ft.Container = asyncio.run(self.create_slider_ui("Sheets", self.book.sheet_names))
        
        self.table_slider: ft.Container = ft.Container(visible=False)
        if self.on_table:
            self.table_slider: ft.Container = asyncio.run(self.create_slider_ui("Tables", self.book.table_names))
            
        self.tracker = IteratorTracker(self.book.sheet_names, self.book.table_names, 0, 0)
        
        self.table_title: ft.DataTable = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Container(
                        ft.Text(title, theme_style=ft.TextThemeStyle.LABEL_MEDIUM, selectable=True),
                        alignment=ft.alignment.center_left
                    )
                    
                ) for title in self.book.column_names
            ], 
            column_spacing=COL_SPACING,
            #heading_text_style=ft.TextStyle(size=16, color="black", weight="w600"),
            heading_row_height=28
        )
        
        self.data_table: ft.DataTable = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("")) for _ in self.book.column_names
            ],
            column_spacing=COL_SPACING,
            heading_row_height=0,
            rows=self.rows,
            #data_text_style=ft.TextStyle(size=12, color="grey900", weight="w600"),
            data_row_max_height=24,
            data_row_min_height=24,
            data_row_color={
                ft.MaterialState.HOVERED : "green50",
                ft.MaterialState.PRESSED : "green50",
            }
        )
        
        self.table_conainer: ft.Container = self.create_table_ui(self.data_table, False)
        self.col_title_ui: ft.Container = self.create_table_ui(self.table_title)
        
        self.content: ft.Container = ft.Container(
            ft.Column(
                controls=[
                    self.sheet_slider,
                    (ft.Divider(color="Transparent", height=2)  if self.table_slider.visible else ft.Divider(visible=False)),
                    self.table_slider,
                    ft.Divider(color="Transparent", height=4),
                    self.col_title_ui,
                    self.table_conainer
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="grey100", 
            border_radius=16, 
            padding=10,
            margin=ft.margin.symmetric(vertical=4, horizontal=8)
        )
        
    
    @lru_cache(maxsize=128)
    def make_cell(self, cell_data: str) -> ft.DataCell:
        return ft.DataCell(
            content=ft.Container(
                ft.Text(cell_data, theme_style=ft.TextThemeStyle.BODY_MEDIUM, selectable=True),
                alignment=ft.alignment.center_left
            )
        )
    
    @lru_cache(maxsize=128)
    def make_row(self, row: tuple[str], idx: int) -> ft.DataRow:
        return ft.DataRow(
            data=idx,
            on_select_changed=self.select_row_event,
            cells=[self.make_cell(data) for data in row]
        )
    
    async def generate_sheet(self, name: str, use_table: bool = False) -> list[ft.DataRow]:
        
        self.row_data = (
            await self.book.switch_sheet(name) 
            if not use_table else 
            await self.book.select_table(name)
        )
        
        return [
            self.make_row(data, idx) 
            for idx, data in enumerate(self.row_data.itertuples(index=False, name=None))
        ]
    
    async def open_sheet(self, e: ft.ControlEvent) -> NoReturn:
        self.click_focus(e, True)
        new_sheet: str = e.control.data
        self.on_table = self.book.in_table
        self.data_table.rows = await self.generate_sheet(new_sheet)
        #await asyncio.sleep(.01)
        self.data_table.update()
    
    async def open_table(self, e: ft.ControlEvent) -> NoReturn:
        self.click_focus(e, False)
        new_table: str = e.control.data
        self.data_table.rows = await self.generate_sheet(new_table, True)
        #await asyncio.sleep(.01)
        self.data_table.update()
    
    async def _edit_row_data(self, row: int = None, row_data: list[str] = [], cell_idx: int = None, cell_data: str = "") -> NoReturn:
        row = row if row else self.past_selected_row
        if cell_idx:
            self.data_table.rows[row].cells[cell_idx] = self.make_cell(cell_data)
            self.data_table.update()
            return 
        
        self.data_table.rows[row].cells = [
            self.make_cell(cell) for cell in row_data
        ]
        self.data_table.update()
    
    async def select_row_event(self, e: ft.ControlEvent) -> NoReturn:
        data = e.control.data
        e.control.color = "green100"
        e.control.update()
        if (self.past_selected_row != data):
            self.data_table.rows[self.past_selected_row].color = None
            self.past_selected_row = data
        
            self.book.current_row = data+self.book.start_row
            self.data = await self.book.get_row_data()
            self.data_table.update()
        
    async def switch_row(self) -> NoReturn:
        self.data_table.rows[self.past_selected_row].color = None
        self.past_selected_row += 1
        self.data_table.rows[self.past_selected_row].color = "green100"
        self.data = await self.book.get_row_data()
        self.data_table.update()
    
    async def refresh_data(self, data: list[Any]) -> NoReturn:
        for cell in data:
            self.row_data.iat[cell.row, cell.col] = cell.value
            self.data_table.rows[cell.row].cells[cell.col] = self.make_cell(
                cell.value
            )
        
        self.data_table.update()
    
    async def append(self, data) -> InputData:
        past_row_data: np.ndarray = await self.book.get_row_data()
        current_row_data: pd.DataFrame = await self.book.append_row(data, self.row_data)
        # preprocessing data for the undo redo buffer
        current_data: Info = Info(self.book.current_row, current_row_data)
        prev_data: Info = Info(self.book.current_row, past_row_data)
        # registers the data in the input block
        input_data: InputData = InputData(
            self.LINK_NAME, 
            self.CALL[0], 
            current_data, 
            prev_data
        )
        #edits row
        
        #await self._edit_row_data(row_data=current_row_data)
        await self.refresh_data(current_row_data)
        if self.book.current_row < self.book.end_row:
            self.book.increment_currrent_row()
            await self.switch_row()
        return input_data
    
    async def refresh(self):
        ...
    
    async def undo(self, undo_object: Optional[UndoData]) -> NoReturn:
        if not undo_object:
            return
        
        if not isinstance(undo_object, UndoData):
            raise TypeError(f"Variable undo_object is type {type(undo_object)} function expected a type of UndoData")
        
        if undo_object.form == self.input_forms[0]:
            self.book.current_row = undo_object.data.position
            row_data = undo_object.data.value
            await self.book.append(row_data)
            await self._edit_row_data(row_data=row_data)
    
    async def redo(self, redo_object: Optional[RedoData]) -> NoReturn:
        if not redo_object:
            return
        
        if not isinstance(redo_object, RedoData):
            raise TypeError(f"Variable redo_object is type {type(redo_object)} function expected a type of RedoData")
        
        if redo_object.form == self.input_forms[0]:
            self.book.current_row = redo_object.data.position
            row_data = redo_object.data.value
            await self.book.append(row_data)
            await self._edit_row_data(row_data=row_data)
    
    def create_table_ui(self, table: ft.DataTable, is_title: bool = True) -> ft.Container:
        pad = ft.padding.only(top=4, left=10, right=10)
        radius = ft.border_radius.vertical(top=8)
        expand = None
        
        if not is_title:
            pad = ft.padding.only(bottom=4, left=10, right=10)
            radius = ft.border_radius.vertical(bottom=8)
            expand = 1
        
        return ft.Container(
            ft.ListView(
                controls=[
                    table
                ]
            ),
            expand=expand,
            padding=pad,
            bgcolor=TABLE_BGCOLOR,
            border_radius=radius,
            alignment=ft.alignment.center
        )
        
    async def save_sheet(self) -> NoReturn:
        await self.book.save()
        
    def click_focus(self, e: ft.ControlEvent, sheet_click: bool) -> NoReturn:
        i: int
        data: str = e.control.data
        sheet_index, table_index = self.tracker.last_sheet_index, self.tracker.last_table_index
        
        if sheet_click:
            i = self.tracker.new_sheet_index(data)
            self.tracker.last_table_index = 0
            self.sheet_rows.controls[sheet_index].style.bgcolor = "white"
            self.sheet_rows.controls[i].style.bgcolor = "green50"
            self.sheet_rows.update()
            if self.on_table:
                self.table_rows.controls[table_index].style.bgcolor = "white"
                self.table_rows.controls[0].style.bgcolor = "green50"
                self.table_rows.update()
        else:
            i = self.tracker.new_table_index(data)
            self.table_rows.controls[table_index].style.bgcolor = "white"
            self.table_rows.controls[i].style.bgcolor = "green50"
            self.table_rows.update()
        
        
    async def create_slider_ui(self, name: str, iterator: Iterator) -> ft.Container:
        if name.lower() == "sheets":
            self.sheet_iterator = iterator
            self.sheet_rows = ft.Row(
                controls=[
                    ft.OutlinedButton(
                        content=ft.Text(
                            sheet, theme_style=ft.TextThemeStyle.BODY_MEDIUM, 
                            color="green700", weight="w600"
                        ),
                        data=sheet,
                        style=deepcopy(SHEET_BTN_STYLE),
                        height=24,
                        on_click=self.open_sheet
                    ) for sheet in iterator
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
                height=32
            )
            
        if name.lower() == "tables":
            self.table_iterator = iterator
            self.table_rows = ft.Row(
                controls=[
                    ft.OutlinedButton(
                        content=ft.Text(
                            sheet, theme_style=ft.TextThemeStyle.BODY_MEDIUM, 
                            color="green700", weight="w600"
                        ),
                        data=sheet,
                        style=deepcopy(SHEET_BTN_STYLE),
                        height=24,
                        on_click=self.open_table
                    ) for sheet in iterator
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
                height=32
            )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        ft.Container(
                            ft.Text(f"{name} ", theme_style=ft.TextThemeStyle.BODY_LARGE),
                            alignment=ft.alignment.center,
                            padding=ft.padding.symmetric(1, 10),
                            width=80
                        ),
                        bgcolor=TABLE_BGCOLOR,
                        padding=ft.padding.symmetric(2, 6),
                        border_radius=8,
                        height=32,
                        alignment=ft.alignment.center
                    )
                    ,
                    ft.Container(
                        ft.VerticalDivider(width=8, thickness=1.2),
                        height=32
                    ),
                    ft.Container(
                        (self.sheet_rows if name.lower() == "sheets" else self.table_rows),
                        bgcolor=TABLE_BGCOLOR,
                        padding=ft.padding.symmetric(0, 6),
                        border_radius=8,
                        expand=True
                    )
                ],
                spacing=0
            )
        )
        
    def __has_attr(self, attr: str) -> bool:
        return hasattr(self, attr)
    
    def __get_attr(self, attr: str) -> Any:
        return getattr(self, attr, None)
    
    def __set_attr(self, attr: str, value: Any) -> NoReturn:
        setattr(self, attr, value)

__all__ = ["SheetTable"]