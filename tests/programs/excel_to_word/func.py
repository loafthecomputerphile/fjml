import flet as ft
from src.fjml.data_types import EventContainer
from typing import NoReturn, Any
from ...modules import WordTemplateWriter

class Actions(EventContainer):
    
    async def _page_setup(self) -> NoReturn:
        self.page.overlay.extend([
            self.save_file_dialog, 
            self.pick_excel_file_dialog, 
            self.pick_docx_file_dialog
        ])
        self.update()
    
    async def _on_close(self) -> NoReturn:
        ...
    
    async def pick_path(self, e: ft.ControlEvent) -> NoReturn:
        self.save_file_dialog.save_file()
    
    async def get_excel_path(self, e: ft.ControlEvent) -> NoReturn:
        self.pick_excel_file_dialog.pick_files()
    
    async def get_docx_path(self, e: ft.ControlEvent) -> NoReturn:
        self.pick_docx_file_dialog.pick_files()
    
    async def on_excel_textfield_change(self, e: ft.ControlEvent) -> NoReturn:
        self.excel_file_path_var: str = self.excel_file_path.content.value
    
    async def on_docx_textfield_change(self, e: ft.ControlEvent) -> NoReturn:
        self.docx_file_path: str = self.docx_file_path.content.value
    
    async def get_save_path(self, e: ft.ControlEvent) -> NoReturn:
        self.save_path = e.path
        #self.word_template.implement_changes()
        #self.word_template.save_file(self.save_path)
        await self.submit_data(self.save_path)
        self.reset_controls()
    
    async def get_excel_file_path(self, e: ft.ControlEvent) -> NoReturn:
        self.excel_file_path_var = e.files[0].path
        self.excel_file_path.content.value = self.excel_file_path_var
        self.update()
    
    async def get_docx_file_path(self, e: ft.ControlEvent) -> NoReturn:
        self.docx_file_path_var = e.files[0].path
        self.docx_file_path.content.value = self.docx_file_path_var
        self.update()
    
    async def get_to_excel_view(self, e: ft.ControlEvent) -> NoReturn:
        if self.excel_file_path_var:
            self.sheet.load_new_file(self.excel_file_path_var)
            self.page.go("/Excel_View")
    
    async def set_sheet_data(self, e: ft.ControlEvent) -> NoReturn:
        self.sheet_data = self.sheet.row_data
        self.page.go("/")
    
    async def _importer(self) -> NoReturn:
        print("hello")
        # import and initialize modules and or classes here using self.load_object and self.import_module
        self.constants: list[tuple[str, str]] = []
        self.sheet_data: Union[pd.DataFrame, None] = None
        self.processor_kwargs: dict[str, Any] = {}
        self.selected_func_name: str = ""
        self.save_path: str = ""
        self.docx_file_path: str = ""
        self.excel_file_path_var: str = ""
        self.docx_file_path_var: str = ""
        self.save_file_dialog: ft.FilePicker = ft.FilePicker(on_result=self.get_save_path)
        self.pick_excel_file_dialog: ft.FilePicker = ft.FilePicker(on_result=self.get_excel_file_path)
        self.pick_docx_file_dialog: ft.FilePicker = ft.FilePicker(on_result=self.get_docx_file_path)
        #self.add_controls(["NumbersOnlyInputFilter", "InputFilter"], self.control_registry)
        
        self.stagnant_kwargs: dict[str, Any] = dict(
            text_size=16,
            height=40,
            border_width=1.6,
            border_color="grey900",
            content_padding=ft.padding.symmetric(4,10),
            on_change=self.on_change,
            border_radius=10,
            expand=1
        )
        
        self.type_to_control: dict[str, Callable[[str], ft.Container]] = {
            "string":lambda name: ft.Container(
                ft.TextField(
                    label=name,
                    **self.stagnant_kwargs
                ),
                padding=4
            ),
            "integer":lambda name: ft.Container(
                ft.TextField(
                    label=name,
                    input_filter=ft.NumbersOnlyInputFilter(),
                    **self.stagnant_kwargs
                ),
                padding=4
            ),
            "float":lambda name: ft.Container(
                ft.TextField(
                    label=name,
                    input_filter=ft.InputFilter(
                        r"[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)",
                        True,
                        ""
                    )
                    **self.stagnant_kwargs
                ),
                padding=4
            )
        }
        
        self.word_template = WordTemplateWriter
        
        def preprocessors(self) -> list[tuple[int, str]]:
            return [(i, processor.name) for i, processor in enumerate(self.word_template.preprocessor_functions)]
        
        self.add_property("preprocessors", preprocessors)
    
    async def submit_data(self, path: str) -> NoReturn:
        constants: dict[str, str] = dict(self.constants)
        self.template: object = self.word_template(self.docx_file_path_var, constants)
        self.template.add_data("content", self.sheet_data, self.selected_func_name, self.processor_kwargs)
        self.template.implement_changes()
        self.template.save_file(path)
    
    async def on_change(self, e: ft.ControlEvent) -> NoReturn:
        self.processor_kwargs[e.control.label] = e.control.value
    
    async def processor_selected(self, e: ft.ControlEvent) -> NoReturn:
        self.processor_kwargs = {}
        idx: int = e.control.data
        kwargs: dict[str, str] = self.word_template.preprocessor_functions[idx].params_spec
        self.selected_func_name = self.word_template.preprocessor_functions[idx].func_name
        controls: list[ft.Control] = []
        
        for name, _type in kwargs.items():
            controls.append(
                self.type_to_control[_type](name)
            )
        
        self.preprocessor_kwargs.content.controls = controls
        self.update()
    
    def create_constants_entry(self, key: str, value: str) -> ft.Control:
        params: dict[str, Any] = self.textfield_params
        #del params["height"]
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.TextField(
                        label="Constant Name",
                        disabled=True,
                        value=key,
                        **self.textfield_params
                    ),
                    ft.TextField(
                        label="Constant Value",
                        disabled=True,
                        value=value,
                        **self.textfield_params
                    ),
                    ft.FilledButton(
                        data=(key, value),
                        style=self.submit_btn_style,
                        text="Edit",
                        on_click=self.constant_edit,
                        **self.constants_btn_ui_constants
                    ),
                    ft.FilledButton(
                        data=(key, value),
                        style=self.delete_btn_style,
                        text="Delete",
                        on_click=self.constant_delete,
                        **self.constants_btn_ui_constants
                    )
                ],
                vertical_alignment="center",
                alignment="center",
                spacing=5
            ),
            padding=ft.padding.symmetric(4, 10),
            height=70,
            border_radius=10,
            bgcolor="grey50",
            alignment=ft.alignment.center
        )
    
    def reset_controls(self) -> NoReturn:
        self.constants_name.value = ""
        self.constants_value.value = ""
        self.constants_view.content.controls = []
        self.preprocessor_kwargs.content.controls = []
        self.excel_file_path.content.value = ""
        self.docx_file_path.content.value = ""
        self.constants = []
        self.sheet_data = None
        self.processor_kwargs = {}
        self.selected_func_name = ""
        self.save_path = ""
        self.excel_file_path_var = ""
        self.docx_file_path_var = ""
        self.template.reset()
        self.word_template = WordTemplateWriter
        
        def preprocessors(self) -> list[tuple[int, str]]:
            return [(i, processor.name) for i, processor in enumerate(self.word_template.preprocessor_functions)]
        
        self.add_property("preprocessors", preprocessors)
        self.update()
    
    async def submit_entry(self, e: ft.ControlEvent) -> NoReturn:
        data: tuple[str, str] = (self.constants_name.value, self.constants_value.value)
        if not data[0] or data[0] in [i[0] for i in self.constants]:
            return
        
        self.constants.append(data)
        self.constants_view.content.controls.append(
            self.create_constants_entry(*data)
        )
        
        self.constants_name.value = ""
        self.constants_value.value = ""
        self.update()
    
    async def constant_delete(self, e: ft.ControlEvent):
        idx: int = self.constants.index(e.control.data)
        
        del self.constants[idx]
        del self.constants_view.content.controls[idx]
        
        self.update()
    
    async def constant_edit(self, e: ft.ControlEvent) -> NoReturn:
        control_data = e.control.data
        idx = self.constants.index(control_data)
        inputs = self.constants_view.content.controls[idx].content.controls
        key, value = inputs[0].value, inputs[1].value
        
        if all([field.disabled for field in inputs[:2]]):
            inputs[1].disabled = inputs[0].disabled = False
            inputs[2].text = "Submit"
            self.constants_entry.disabled = True
            self.update()
            return
        
        if key in [i[0] for i in self.constants] and key != control_data:
            return
        
        inputs[0].disabled = inputs[1].disabled = True
        inputs[2].text = "Edit"
        self.constants[idx] = inputs[3].data = inputs[2].data = (key, value)
        self.constants_entry.disabled = False
        self.update()
