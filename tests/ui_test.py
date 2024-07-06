from fjml import load_program, Compiler, data_types as dt
from .controls import test_controls as tc
from .ui_test_program.func import Actions
import enum
import flet as ft


class Paths(enum.StrEnum):
    PROGRAM: str = "tests\\ui_test_program"
    COMPILED: str = "tests\\ui_test_program\\compiled.fjml"


class App:
    
    def __init__(self, run_compiler: bool = False) -> None:
        compiler: Compiler
        
        if run_compiler:
            compiler = Compiler(
                dt.ParamGenerator(Paths.PROGRAM, Paths.COMPILED)
            )
            compiler.compile()
        
    async def run(self, page: ft.Page):
        page = load_program(Paths.COMPILED, Actions, page)
        page.go("/")


if __name__ == "__main__":
    app: App = App()
    ft.app(target=app.run)