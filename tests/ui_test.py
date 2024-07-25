from src.fjml import load_program, Compiler, data_types as dt
from .controls import test_controls as tc
import flet as ft


class Paths:
    PROGRAM: str = "tests\\ui_test_program"
    COMPILED: str = "tests\\ui_test_program\\compiled.fjml"


class App:
    
    def __init__(self, run_compiler: bool = False) -> None:
        if run_compiler:
            Compiler(
                Paths.PROGRAM, 
                Paths.COMPILED
            ).compile()
        
    async def run(self, page: ft.Page):
        page = load_program(Paths.COMPILED, page)
        page.go("/")


if __name__ == "__main__":
    app: App = App()
    ft.app(target=app.run)