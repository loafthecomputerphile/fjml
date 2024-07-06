from typing import Final, Any, Sequence, Mapping
import pathlib as Path


module_dir: str = Path.PurePath(__file__).parent

ARCHIVE_FORMAT: Final[str] = "zip"
OPERATION_ARGS: Final[Sequence[str]] = ["make", "register"]
MARKUP_SPECIFIC_CONTROLS: Final[Sequence[str]] = ["loop", "loop_index"]
CONTROL_REGISTRY_PATH: Final[str] = str(
    Path.PurePath(module_dir, "registry\\control_registry.json")
)

NULL: Final[str] = "<NULL>"
INVALID_STYLE_KEYS: Final[Sequence[str]] = ["refs", "code_refs", "styling", "func", "route", "call", "unpack"]
RANGE_PARAM_LENGTH: Final[Sequence[int]] = [1, 2, 3]
EMPTY_REGISTRY_FILE: Final[Mapping] = {
    "Controls": [],
    "ControlTypes": [],
}

FUNCTION_FILE_TEXT: Final[str] = """
import flet as ft
from fjml import data_types as dt

class Actions(dt.EventContainer):
    
    def _importer(self):
        ...
    
    def _page_setup(self):
        ...
"""

STYLE_SHEET_TEXT: Final[Mapping] = {
    "base_text_style":{
        "size": "20",
        "weight": "w800"
    }
}


IMPORT_FILE_TEXT: Final[Mapping] = {
    "Controls": [
        {
            "var_name": "text",
            "control_type": "Text",
            "settings": {
                "value": "Hello World",
                "unpack":{"styling":"base_text_style"}
            },
        }
    ]
}

USER_INTEFACE_FILE_TEXT: Final[Mapping] = {
    "Header":{
        "import_folder":"extra",
        "program_name":"program",
        "style_sheet_name":"style_sheet",
        "extentions":[]
    },
    "Imports": [{"source": "import1"}],
    "Controls": [],
    "UI": [
        {
            "route": "Home",
            "views": {
                "control_type": "Container",
                "settings": {
                    "content": {"refs": "text"},
                    "bgcolor": "grey50",
                    "alignment": {
                        "control_type": "align_center",
                        "settings": {},
                    },
                    "expand": True,
                },
            },
        }
    ],
}

STAGNANT_KEYS: Final[Sequence[str]] = [
    "view_operations",
    "control_loader",
    "tools",
    "compiled_program",
    "object_bucket",
    "style_sheet",
    "setup_func_caller",
    "add_property",
    "add_methods",
    "update",
    "change_route",
    "get_current_route",
    "create_ui",
    "get_attr",
    "set_attr",
    "property_bucket",
    "dependency_bucket",
    "preserve_control_bucket",
    "_importer",
    "_page_setup",
    "initialize",
]

PRIMARY_STAGNANT_KEYS: Final[Sequence[str]] = [
    "view_operations",
    "control_loader",
    "tools",
    "compiled_program",
    "object_bucket",
    "style_sheet",
    "setup_func_caller",
    "add_property",
    "add_methods",
    "update",
    "change_route",
    "get_current_route",
    "create_ui",
    "get_attr",
    "set_attr",
    "property_bucket",
    "dependency_bucket",
    "preserve_control_bucket",
]
