from argparse import Namespace, ArgumentParser, _SubParsersAction
from typing import Any, Callable, Sequence, Mapping
import operator, itertools
import os, io, time, shutil
import json
import inspect
from functools import partial

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

import flet as ft
from flet.matplotlib_chart import MatplotlibChart
from flet.plotly_chart import PlotlyChart

from .registry.control_register import ControlRegistryOperations
from . import data_types as dt, utils
from .constants import (
    USER_INTERFACE_FILE_TEXT,
    IMPORT_FILE_TEXT,
    FUNCTION_FILE_TEXT,
    OPERATION_ARGS,
    CONTROL_REGISTRY_PATH
)

Tools: utils.Utilities = utils.Utilities()

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

def not_type(obj: Any) -> bool:
    return type(obj) != type

def is_class_func(obj: Any) -> bool:
    return inspect.isclass(obj) or inspect.isfunction(obj)

class Update:
    
    __slots__ = ("populous", "added_names")
    
    def __init__(self) -> NoReturn:
        self.populous: Sequence[dt.ControlRegisterInterface] = list(itertools.starmap(
            self.make_interface,
            (
                (MatplotlibChart, "MatplotlibChart"),
                (PlotlyChart, "PlotlyChart"),
                (None, "colors", "flet_core"),
                (None, "icons", "flet_core"),
            )
        ))
        self.added_names: Sequence[str] = list(map(operator.itemgetter("name"), self.populous))
        self.first_populate()
        self.second_populate()
        self.generate()
    
    def generate(self) -> NoReturn:
        ControlRegistryOperations.generate_dict(
            [dt.ControlRegistryModel(**content) for content in self.populous],
            True
        )
    
    def module_check(self, obj1: Any, obj2: Any) -> bool:
        return self.splitter(obj2.__module__) == self.splitter(obj1.__name__)
    
    def first_populate(self) -> NoReturn:
        flet_attr: Any
        module_attr: Any
        attr_name: str
        module_name: str
        maker: Callable
    
        for module_name, module_attr in {"flet":ft, "ft.canvas":ft.canvas}.items():
            maker = partial(self.make_interface, module=module_name)
            for attr_name, flet_attr in inspect.getmembers(module_attr):
                if not inspect.isclass(flet_attr) or attr_name in self.added_names:
                    continue
                
                self.populous.append(
                    maker(flet_attr, attr_name)
                )
                self.added_names.append(attr_name)
    
    def second_populate(self) -> NoReturn:
        ret_partial: Callable
        obj_source: dt.ObjectSource
        attr_name: str
        module_attr_name: str
        flet_attr: Any
        module_attr: Any
        is_type: bool
        cond1: bool
        cond2: bool
        
        for attr_name, flet_attr in inspect.getmembers(ft):
        
            if not inspect.ismodule(flet_attr) or attr_name in invalid_sources:
                continue
                
            for module_attr_name, module_attr in inspect.getmembers(flet_attr):
                is_type = not_type(module_attr)
                if not hasattr(module_attr, "__module__"):
                    continue
                if not (is_class_func(module_attr) or is_type) or not self.module_check(flet_attr, module_attr):
                    continue
                
                ret_partial = partial(
                    Tools.control_to_registry_interface, 
                    control=module_attr, 
                    use_source=True, 
                    try_name=module_attr_name
                )
                
                cond2, cond1 = (
                    f"{attr_name}.{module_attr_name}" not in self.added_names, 
                    module_attr_name not in self.added_names
                )
                
                if inspect.isclass(module_attr) and cond1:
                    self.populous.append(ret_partial())
                    self.added_names.append(module_attr_name)
                    continue
                elif inspect.isfunction(module_attr) and cond2:
                    self.populous.append(ret_partial(use_module_name=True))
                elif is_type and cond2 and not callable(module_attr):
                    self.populous.append(ret_partial(use_module_name=True))
                    
                self.added_names.append(f"{attr_name}.{module_attr_name}")
        
    def make_interface(self, obj: Any, name: str, module: str = "") -> dt.ControlRegisterInterface:
        return dt.ControlRegisterInterface(
            name=name, 
            source=dt.ObjectSource(obj, module), 
            attr=name
        )
    
    def splitter(self, data: str, sep: str = ".") -> str:
        data = data.split(sep)
        if len(data) < 2:
            return data[0]
        return data[1]


class ProjectMaker:
    
    def __init__(self, path: str, name: str) -> NoReturn:
        self.generate_project(path, name)

    def make_python_file(self, path: str, filename: str, code: str) -> NoReturn:
        file: io.TextIOWrapper
        with open(os.path.join(path, filename), "w") as file:
            file.write(code)

    def make_json_file(self, path: str, filename: str, data: dt.JsonDict) -> NoReturn:
        file: io.TextIOWrapper
        with open(os.path.join(path, filename), "w") as file:
            json.dump(data, file, indent=4)

    def make_folder(self, path_with_name: str) -> NoReturn:
        os.makedirs(path_with_name)

    def generate_project(self, path: str, name: str) -> NoReturn:
        project_path: str = os.path.join(path if path else os.getcwd(), name)
        try:
            self.make_folder(project_path)
        except (FileExistsError, OSError):
            return print("Directory already exists")

        # Make JSON file
        USER_INTERFACE_FILE_TEXT["Header"]["action_import"]["from"] = f".{name}.func"
        self.make_json_file(project_path, "ui.json", USER_INTERFACE_FILE_TEXT)
        self.make_json_file(project_path, "style_sheet.style.json", USER_INTERFACE_FILE_TEXT)
        self.make_python_file(project_path, "func.py", FUNCTION_FILE_TEXT)

        # Make subfolder
        subfolder_path: str = os.path.join(project_path, "extra")
        self.make_folder(subfolder_path)
        self.make_json_file(subfolder_path, "import1.json", IMPORT_FILE_TEXT)


def registry_action(action: str) -> NoReturn:
    if action == "update":
        Update()
    elif action == "delete":
        if os.path.exists(CONTROL_REGISTRY_PATH):
            os.remove(CONTROL_REGISTRY_PATH)
    elif action == "reset":
        if os.path.exists(CONTROL_REGISTRY_PATH):
            os.remove(CONTROL_REGISTRY_PATH)
        Update()


def main() -> NoReturn:
    parser: ArgumentParser = ArgumentParser(
        prog="FJML", description="Generate an FJML project or update/delete registry file"
    )
    subparsers: _SubParsersAction = parser.add_subparsers(dest="parser_type")
    
    update_parser: ArgumentParser = subparsers.add_parser("registry")
    update_parser.add_argument(
        "action",
        choices=["update", "delete", "reset"],
        help="Updates or deletes the control registry file",
    )
    
    project_parser: ArgumentParser = subparsers.add_parser("make")
    project_parser.add_argument(
        "--name",
        help="Name of the project.",
    )
    project_parser.add_argument(
        "--path",
        help="Path where the project will be created",
    )

    args: Namespace = parser.parse_args()

    if args.parser_type == OPERATION_ARGS[0]:
        ProjectMaker(args.path, args.name)
    elif args.parser_type == OPERATION_ARGS[1]:
        registry_action(args.action)

if __name__ == "__main__":
    main()