import flet as ft
from src.fjml import data_types as dt

class Actions(dt.EventContainer):
    
    async def _importer(self):
        self.months_values: list[str] = [["MAR", 2], ["APR", 5], ["MAY", 8]]
        self.set_object("make_label", self.make_label)
    
    async def _page_setup(self):
        ...
    
    async def _on_close(self):
        ...
    
    def make_label(self, text: str) -> ft.Container:
        return ft.Container(
            ft.Text(
                value=text,
                **self.text_settings
            ),
            margin=ft.margin.only(top=10)
        )
        