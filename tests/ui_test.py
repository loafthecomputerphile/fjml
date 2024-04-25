from src.fjml import Build, ProgramLoader, data_types as dt
from .programs.test_compiler_graph.func import Actions
from .controls import ThemeSettings
#from programs.test_compiler.func import Actions
import flet as ft

custom_data = [
  {
    "name":"SheetTable",
    "source":"tests.controls",
    "attr":"SheetTable",
    "is_awaitable":False
  },
  {
    "name":"CustomDropdown",
    "source":"tests.controls",
    "attr":"CustomDropdown",
    "is_awaitable":False
  },
  {
    "name":"CustomSwitch",
    "source":"tests.controls",
    "attr":"CustomSwitch",
    "is_awaitable":False
  },
  {
    "name":"CustomTextField",
    "source":"tests.controls",
    "attr":"CustomTextField",
    "is_awaitable":False
  }
]



async def main(page: ft.Page):
    page.theme_mode = ThemeSettings.MODE
    page.bgcolor = ft.colors.GREY_50
    page.title = "Development Program"
    page.horizontal_alignment = "center"
    page.fonts = ThemeSettings.FONTS
    page.theme = ThemeSettings.THEME
    build: Build = ProgramLoader(
        dt.LoaderParameters(
            page=page,
            program_name="test_compiler_graph",
            imports_path=None,
            custom_controls=custom_data,
            methods=Actions,
            ui_code="tests\\programs\\test_compiler_graph\\ui.json"
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