from fjml import Build, ProgramLoader, data_types as dt
from programs.excel_to_word.func import Actions
#from programs.test_compiler.func import Actions
import flet as ft

custom_data = [
  {
    "name":"CustomButton",
    "source":"controls",
    "attr":"CustomButton",
    "is_awaitable":False
  },
  {
    "name":"ContentColumn",
    "source":"controls",
    "attr":"ContentColumn",
    "is_awaitable":False
  },
  {
    "name":"ContentRow",
    "source":"controls",
    "attr":"ContentRow",
    "is_awaitable":False
  },
  {
    "name":"ContentDivider",
    "source":"controls",
    "attr":"ContentDivider",
    "is_awaitable":False
  },
  {
    "name":"SheetTable",
    "source":"controls",
    "attr":"SheetTable",
    "is_awaitable":False
  },
  {
    "name":"CustomDropdown",
    "source":"controls",
    "attr":"CustomDropdown",
    "is_awaitable":False
  },
  {
    "name":"CustomSwitch",
    "source":"controls",
    "attr":"CustomSwitch",
    "is_awaitable":False
  },
  {
    "name":"CustomTextField",
    "source":"controls",
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
            program_name="test_compiler",
            imports_path="programs\\test_compiler\\extra",
            custom_controls=custom_data,
            methods=Actions,
            ui_code="programs\\test_compiler\\ui.json"
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
    
    page.go(page.route)

if __name__ == "__main__":
    ft.app(target=main)