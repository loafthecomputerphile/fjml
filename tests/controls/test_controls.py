import flet as ft
from typing import Union

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn


class TestContainer(ft.Container):

    def __init__(self, *args, **kwargs):
        super().__init__(
            data=["Test Passed", {"test":"Test Passed"}, {"test2":[0, "Test Passed"]}]
        )
        self.data2: str = "Test Passed"

class RouteBtn(ft.ElevatedButton):
    
    def __init__(
        self, text: str, route_path: str = "", use_route: bool = True,
        expand: Union[int, bool] = 1, expand_loose: Union[int, bool] = True
    ) -> NoReturn:
        super().__init__(on_click=self.click_event if use_route else None)
        self.content: ft.Text
        self.style: ft.ButtonStyle
        self.route_path: str = route_path
        self.expand: Union[int, bool] = expand
        self.expand_loose: Union[int, bool] = expand_loose
        self.height: int = 40
        self.width: int = 150
        self.make_style()
        self.content = ft.Text(
            value=text,
            color="white",
            size=18
        )
    
    def click_event(self, e) -> NoReturn:
        e.page.go(self.route_path)
    
    def make_style(self) -> NoReturn:
        self.style = ft.ButtonStyle(
            color="white",
            bgcolor="green700",
            elevation=0,
            shape=ft.ContinuousRectangleBorder(
                radius=16
            )
        )