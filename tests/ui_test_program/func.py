import flet as ft
from typing import Awaitable, Coroutine

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

from src.fjml import data_types as dt
from ..controls import ThemeSettings


class TestData:
    group_test = [0, {"test":"Test Passed"}, {"test2":[0, "Test Passed"]}]
    

class Actions(dt.EventContainer):
    
    async def test_object_calling(self, data: int) -> Coroutine[int, None, None]:
        data = data*2
        return data
    
    def callable_loop_test_func(self, name: str) -> ft.Chip:
        return ft.Chip(
            label=ft.Text(name),
            bgcolor="green200",
            disabled_color="green100",
            autofocus=True,
            on_select=lambda _: self.page.update(),
        )
    
    def _importer(self) -> NoReturn:
        self.i: int = 0
        def test_property_func() -> list[tuple[int, str]]:
            return ["sheesh"]
        self.txt_size: list[int] = [30]
        self.loop_test_content: list[str] = ["test", "has", "passed"]
        self.object_bucket.set_object("test_object_calling", self.test_object_calling)
        self.object_bucket.set_object("callable_loop_test_func", self.callable_loop_test_func)
        self.property_bucket.add("test_property_func", test_property_func)
        self.test_data: TestData = TestData()
        self.test_data_2 = {"test":"Test Passed"}
        self.test_data_1 = [0, "Test Passed"]
        
    
    def _page_setup(self) -> NoReturn:
        self.group_assign(
            self.page,
            {
                "theme_mode":ThemeSettings.MODE,
                "bgcolor":"grey50",
                "horizontal_alignment":"center",
                "fonts":ThemeSettings.FONTS,
                "theme":ThemeSettings.THEME
            }
        )
    