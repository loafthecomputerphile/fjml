from typing import Final, Any
import pathlib as Path

module_dir: str = Path.PurePath(__file__).parent

ARCHIVE_FORMAT: Final[str] = "zip"
OPERATION_ARGS: Final[list[str]] = ["make", "register"]
CONTROL_REGISTRY_PATH: Final[str] = str(Path.PurePath(module_dir,"registry\\control_registry.json"))
RANGE_PARAM_LENGTH: Final[set[int]] = {1,2,3}

FUNCTION_FILE_TEXT: Final[str] = """import flet as ft
from fjml import data_types as dt

class Actions(dt.EventContainer):
    
    async def _importer(self):
        ...
    
    async def _page_setup(self):
        ...
    
    async def _on_close(self):
        ...
"""

IMPORT_FILE_TEXT: Final[dict] = {
    "Controls":[
        {
            "var_name":"text",
            "control_type":"Text",
            "settings":{
                "value":"Hello World",
                "size":"20",
                "weight":"w800",
            }
        }
    ]
}

USER_INTEFACE_FILE_TEXT: Final[dict[str, Any]] = {
    "Imports":[
        {"source":"import1"}
    ],
    "Controls":[
        
    ],
    "UI":[
        {
            "route":"Home",
            "views":{
                "control_type":"Container",
                "settings":{
                    "content":{"ref":"text"},
                    "bgcolor":"grey50",
                    "alignment":{
                        "control_type":"align_center",
                        "settings":{}
                    },
                    "expand":True
                }
            }
        }
    ]
}