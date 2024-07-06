from argparse import Namespace, ArgumentParser
from typing import Final, Any, Optional, Callable, Sequence, Mapping
import os
import shutil
import json
import inspect
from types import MethodType
from enum import Enum
from functools import partial

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

import flet as ft
from flet.matplotlib_chart import MatplotlibChart
from flet.plotly_chart import PlotlyChart

from .control_register import ControlRegistryOperations
from .. import data_types as dt, utils
from ..constants import (
    USER_INTEFACE_FILE_TEXT,
    IMPORT_FILE_TEXT,
    FUNCTION_FILE_TEXT,
    ARCHIVE_FORMAT,
    OPERATION_ARGS,
)

Tools: utils.Utilities = utils.Utilities()

def icons() -> MethodType:
    return ft.icons

def colors() -> MethodType:
    return ft.colors


def splitter(data: str, sep: str = "."):
    data = data.split(sep)
    if len(data) < 2:
        return data[0]
    return data[1]


invalid_sources: Sequence[str] = [
    "utils",
    "pubsub",
    "connection",
    "protocol",
    "event_handler",
    "local_connection",
    "locks",
    "querystring",
    "session_storage",
    "template_route",
    "event",
    "control_event",
    "tests",
]

not_type: Callable = lambda obj: type(obj) != type
is_class_func: Callable = lambda obj: inspect.isclass(obj) or inspect.isfunction(obj)
def module_check(obj1: Any, obj2: Any) -> bool:
    return splitter(obj2.__module__) == splitter(obj1.__name__)


def make_inteface(obj: Any, name: str, module: str) -> dt.ControlRegisterInterface:
    return dt.ControlRegisterInterface(
        name=name, source=dt.ObjectSource(obj, module), attr=name
    )

def update_register() -> NoReturn:
    inter = dt.ControlRegisterInterface
    ret_partial: Callable
    added_names: Sequence[str] = []
    obj_source: dt.ObjectSource
    attr_name: str
    module_attr_name: str
    flet_attr: Any
    module_attr: Any
    is_type: bool
    kwargs: Mapping
    populous: Sequence[dt.ControlRegisterInterface] = []
    module_map = {"flet":ft, "ft.canvas":ft.canvas}
    
    for module_name, module in module_map.items():
        maker = partial(make_inteface, module=module_name)
        for attr_name, flet_attr in inspect.getmembers(module):
            
            if not inspect.isclass(flet_attr) or attr_name in added_names:
                continue
            
            populous.append(
                maker(flet_attr, attr_name)
            )
            added_names.append(attr_name)

    for attr_name, flet_attr in inspect.getmembers(ft):
        
        if not inspect.ismodule(flet_attr) or attr_name in invalid_sources:
            continue
            
        for module_attr_name, module_attr in inspect.getmembers(flet_attr):
            
            is_type = not_type(module_attr)
            if not hasattr(module_attr, "__module__"):
                continue
            if not (is_class_func(module_attr) or is_type) or not module_check(flet_attr, module_attr):
                continue
            
            ret_partial: Callable = partial(
                Tools.control_to_registry_interface, 
                control=module_attr, 
                use_source=True, 
                try_name=module_attr_name
            )
            
            cond2: bool = f"{attr_name}.{module_attr_name}" not in added_names
            cond1: bool = module_attr_name not in added_names
            
            if inspect.isclass(module_attr) and cond1:
                populous.append(ret_partial())
                added_names.append(module_attr_name)
                continue
            elif inspect.isfunction(module_attr) and cond2:
                populous.append(ret_partial(use_module_name=True))
            elif is_type and cond2 and not callable(module_attr):
                populous.append(ret_partial(use_module_name=True))
                
            added_names.append(f"{attr_name}.{module_attr_name}")

    populous.extend(
        [
            
            dt.ControlRegisterInterface(
                name="MatplotlibChart",
                source=dt.ObjectSource(MatplotlibChart),
                attr="MatplotlibChart",
            ),
            dt.ControlRegisterInterface(
                name="PlotlyChart",
                source=dt.ObjectSource(PlotlyChart),
                attr="PlotlyChart",
            ),
            dt.ControlRegisterInterface(
                name="colors",
                source=dt.ObjectSource(None, "flet_core"),
                attr="colors",
            ),
            dt.ControlRegisterInterface(
                name="icons",
                source=dt.ObjectSource(None, "flet_core"),
                attr="icons",
            ),
        ]
    )

    ControlRegistryOperations.generate_dict(
        [dt.ControlRegistryModel(**content) for content in populous],
        True
    )


def make_python_file(path: str, filename: str, code: str) -> NoReturn:
    file_path: str = os.path.join(path, filename)
    with open(file_path, "w") as file:
        file.write(code)


def make_json_file(path: str, filename: str, data: dt.JsonDict) -> NoReturn:
    file_path: str = os.path.join(path, filename)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def make_folder(path_with_name: str) -> NoReturn:
    os.makedirs(path_with_name)


def generate_project(path: str, name: str) -> NoReturn:
    project_path: str = os.path.join(path, name)
    try:
        make_folder(project_path)
    except FileExistsError:
        shutil.rmtree(project_path, ignore_errors=False)
        make_folder(project_path)

    # Make JSON file
    make_json_file(project_path, "ui.json", USER_INTEFACE_FILE_TEXT)
    make_json_file(project_path, "style_sheet.style.json", USER_INTEFACE_FILE_TEXT)

    # Make Python file
    make_python_file(project_path, "func.py", FUNCTION_FILE_TEXT)

    # Make subfolder
    subfolder_path: str = os.path.join(project_path, "extra")
    make_folder(subfolder_path)

    # Make JSON file inside the subfolder
    make_json_file(subfolder_path, "import1.json", IMPORT_FILE_TEXT)


def main() -> NoReturn:

    current_directory: str = os.getcwd()

    parser: ArgumentParser = ArgumentParser(
        prog="FJML", description="Generate a project."
    )
    parser.add_argument(
        "operation",
        type=str,
        help="Path where the project will be created.",
        choices=OPERATION_ARGS,
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Path where the project will be created.",
        default=current_directory,
    )
    parser.add_argument(
        "--name", type=str, help="Name of the project.", default="project"
    )

    args: Namespace = parser.parse_args()
    packer: Packer = Packer(parser, args.path, args.name)

    if args.operation == OPERATION_ARGS[0]:
        generate_project(args.path, args.name)
    elif args.operation == OPERATION_ARGS[1]:
        update_register()


"""
if __name__ == "__main__":
    main()"""
