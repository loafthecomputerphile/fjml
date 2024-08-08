from typing import Final, Sequence, Mapping
import pathlib as Path


MODULE_PATH: str = Path.PurePath(__file__).parent

OPERATION_ARGS: Final[Sequence[str]] = ["make", "registry"]
MARKUP_SPECIFIC_CONTROLS: Final[Sequence[str]] = ["loop", "loop_index"]
CONTROL_REGISTRY_PATH: Final[str] = str(
    Path.PurePath(MODULE_PATH, "registry\\control_registry")
)

NULL: Final[str] = "<NULL>"
INVALID_STYLE_KEYS: Final[Sequence[str]] = ["refs", "code_refs", "styling", "func", "route", "call", "_unpack"]
RANGE_PARAM_LENGTH: Final[Sequence[int]] = [1, 2, 3]
EMPTY_REGISTRY_FILE: Final[Mapping] = {
    "Controls": [],
    "ControlTypes": [],
}

FUNCTION_FILE_TEXT: Final[str] = """import flet as ft
from fjml import data_types as dt

class Actions(dt.EventContainer):
    
    def _importer(self):
        ...
    
    def _page_setup(self):
        ...
"""

STYLE_SHEET_TEXT: Final[Mapping] = {
    "base_text_style":{
        "size": 40,
        "weight": "w800",
        "color":{
            "control_type":"colors",
            "attr":"RED_700"
        }
    }
}


IMPORT_FILE_TEXT: Final[Mapping] = {
    "Controls": [
        {
            "var_name": "text",
            "control_type": "Text",
            "settings": {
                "value": "Hello World",
                "_unpack":{"styling":"base_text_style"}
            },
        }
    ]
}

USER_INTERFACE_FILE_TEXT: Final[Mapping] = {
    "Header":{
        "import_folder":"extra",
        "program_name":"program",
        "style_sheet_name":"style_sheet",
        "action_import":{
            "import":"Actions",
            "from":".ui_test_program.func"
        },
        "extensions":[]
    },
    "Imports": [{"source": "import1"}],
    "Controls": [],
    "UI": [
        {
            "route": "/",
            "settings": {
                "controls":[
                    {
                        "control_type": "Container",
                        "settings": {
                            "content": {"refs": "text"},
                            "bgcolor": "grey50",
                            "alignment": {
                                "control_type": "alignment.center"
                            },
                            "expand": True,
                        }
                    }
                ]
            },
        }
    ],
}
