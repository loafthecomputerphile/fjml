from src.fjml import Build, ProgramLoader, data_types as dt
from .programs.excel_to_word.func import Actions
from . import controls
#from programs.test_compiler.func import Actions
import flet as ft

custom_data = [
    {
        "name":"SheetTable",
        "source":dt.ObjectSource(
            getattr(controls, "SheetTable"),
            "tests.controls"
        ),
        "attr":"SheetTable",
        "is_awaitable":False
    },
    {
        "name":"CustomDropdown",
        "source":dt.ObjectSource(
            getattr(controls, "CustomDropdown"),
            "tests.controls"
        ),
        "attr":"CustomDropdown",
        "is_awaitable":False
    },
    {
        "name":"CustomSwitch",
        "source":dt.ObjectSource(
            getattr(controls, "CustomSwitch"),
            "tests.controls"
        ),
        "attr":"CustomSwitch",
        "is_awaitable":False
    },
    {
        "name":"CustomTextField",
        "source":dt.ObjectSource(
            getattr(controls, "CustomTextField"),
            "tests.controls"
        ),
        "attr":"CustomTextField",
        "is_awaitable":False
    }
]



async def main(page: ft.Page):
    page.theme_mode = controls.ThemeSettings.MODE
    page.bgcolor = ft.colors.GREY_50
    page.title = "Development Program"
    page.horizontal_alignment = "center"
    page.fonts = controls.ThemeSettings.FONTS
    page.theme = controls.ThemeSettings.THEME
    build: Build = ProgramLoader(
        dt.LoaderParameters(
            page=page,
            program_name="test_compiler_graph",
            imports_path="tests\\programs\\excel_to_word\\extra",
            custom_controls=custom_data,
            methods=Actions,
            ui_code="tests\\programs\\excel_to_word\\ui.json"
        )
    )
    '''
    build: Build = ProgramLoader(
        LoaderParameters(
            page=page,
            program_name="excel_to_word",
            imports_path="programs\\excel_to_word\\extra",
            custom_controls=custom_data,
            methods=Actions,
            ui_code="programs\\excel_to_word\\ui.json"
        )
    )
    '''
    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)
    
    page.on_view_pop = view_pop
    
    page.go("/")

if __name__ == "__main__":
    ft.app(target=main)