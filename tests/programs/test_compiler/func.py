from flet import FilePicker, Text, ElevatedButton, TextButton, AlertDialog
#from fjml.src.fjml.parsers.utils import Validator

class Actions:

    async def _importer(self):
        self.file_path = "./tests/test_files/test_data.xlsx"

    async def _page_setup(self):
        ...

    async def _on_close(self):
        ...

    def pick_file(self, e):
        self.dlg_modal.open = False
        self.page.update()
        self.pick_files_dialog.pick_files(allowed_extensions=["xlsx"])
        


    async def get_file_path(self, e) -> None:
        self.file_path: str = e.files[0].path
        await self.sheet.load_new_file(self.file_path, None, True)
        self.page.update()
        

    def close_dlg(self, e):
        self.dlg_modal.open = False
        self.page.update()


    async def submit_row(self, e): 
        print(self.sheet.content.height)
        inputs = ["input1", "input2", "input3", "input4"]
        if not all([self.get_attr(val).is_valid for val in inputs]):
            return

        await self.sheet.append([
            self.input1.value, self.input2.value,
            self.input3.value, self.input4.value
        ])

        self.input1.value = ""
        self.input2.value = ""
        self.input3.value = ""
        self.input4.value = ""

        self.update()



