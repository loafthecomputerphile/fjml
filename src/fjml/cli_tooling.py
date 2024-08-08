import argparse, inspect
from typing import Any, Callable, Sequence
import itertools, json, os, io, operator
from functools import partial

interface_data: list[tuple] = [
    (None, "colors", "flet_core"),
    (None, "icons", "flet_core")
]

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

import flet as ft

try:
    from flet.matplotlib_chart import MatplotlibChart
    interface_data.append(
        (MatplotlibChart, "MatplotlibChart")
    )
except ImportError:
    pass

try:
    from flet.plotly_chart import PlotlyChart
    interface_data.append(
        (PlotlyChart, "PlotlyChart")
    )
except ImportError:
    pass


from .object_enums import *
from .registry.control_register import ControlRegistryOperations
from . import data_types as dt, utils
from .constants import (
    USER_INTERFACE_FILE_TEXT,
    IMPORT_FILE_TEXT,
    FUNCTION_FILE_TEXT,
    CONTROL_REGISTRY_PATH, 
    STYLE_SHEET_TEXT
)



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


ACTION_CHOICES: tuple[str, str] = (
    RegistryAction.RESET, RegistryAction.DELETE
)

def not_type(obj: Any) -> bool:
    return type(obj) != type

def is_class_func(obj: Any) -> bool:
    return inspect.isclass(obj) or inspect.isfunction(obj)

class Update:
    
    __slots__ = ("populous", "added_names", "tools")
    
    def __init__(self) -> NoReturn:
        self.tools: utils.Utilities = utils.Utilities()
        self.populous: Sequence[dt.ControlRegisterInterface] = list(itertools.starmap(
            self.make_interface, interface_data
        ))
        
        self.added_names: Sequence[str] = list(
            map(operator.itemgetter(1), interface_data)
        )
        
        self.first_populate()
        self.second_populate()
        self.generate()
    
    def generate(self) -> NoReturn:
        ControlRegistryOperations.generate_dict(
            map(lambda control: dt.ControlRegistryModel(**control), self.populous),
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
                    self.tools.control_to_registry_interface, 
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
        self.generate_project(path, name.strip())

    def make_python_file(self, path: str, filename: str, code: str) -> NoReturn:
        file: io.TextIOWrapper
        
        if os.path.exists(os.path.join(path, filename)):
            return
        
        with open(os.path.join(path, filename), "w") as file:
            file.write(code)

    def make_json_file(self, path: str, filename: str, data: dt.JsonDict) -> NoReturn:
        file: io.TextIOWrapper
        with open(os.path.join(path, filename), "w") as file:
            json.dump(data, file, indent=4)

    def make_folder(self, path_with_name: str) -> NoReturn:
        if not os.path.exists(path_with_name):
            os.makedirs(path_with_name)

    def generate_project(self, path: str, name: str) -> NoReturn:
        folder_name: str = name.replace(" ", "_").lower()
        
        project_path: str = os.path.join(path, folder_name)
            
        self.make_folder(project_path)

        # Make JSON file
        USER_INTERFACE_FILE_TEXT[MarkupKeys.HEADER]["program_name"] = name
        USER_INTERFACE_FILE_TEXT[MarkupKeys.HEADER]["action_import"]["from"] = (
            f"{folder_name}.func"
        )
        
        self.make_json_file(project_path, "ui.json", USER_INTERFACE_FILE_TEXT)
        self.make_json_file(project_path, "style_sheet.style.json", STYLE_SHEET_TEXT)
        self.make_python_file(project_path, "func.py", FUNCTION_FILE_TEXT)
        self.make_python_file(project_path, "__init__.py", "")

        # Make subfolder
        subfolder_path: str = os.path.join(project_path, "extra")
        self.make_folder(subfolder_path)
        self.make_json_file(subfolder_path, "import1.json", IMPORT_FILE_TEXT)


def registry_action(action: str) -> NoReturn:
    if action == ACTION_CHOICES[1]:
        if os.path.exists(CONTROL_REGISTRY_PATH):
            os.remove(CONTROL_REGISTRY_PATH)
        return
    elif action == ACTION_CHOICES[0]:
        if os.path.exists(CONTROL_REGISTRY_PATH):
            os.remove(CONTROL_REGISTRY_PATH)
        return Update()
  
    raise argparse.ArgumentError(
        message=f"Invalid subparser argument for `registry`. Valid choices are: {ACTION_CHOICES}"
    )


def main() -> NoReturn:
    parser: argparse.ArgumentParser
    update_parser: argparse.ArgumentParser
    project_parser: argparse.ArgumentParser
    subparsers: argparse._SubParsersAction
    
    parser = argparse.ArgumentParser(
        prog="FJML", description="Generate an FJML project or update/delete registry file"
    )
    subparsers = parser.add_subparsers(dest="parser_type")
    
    update_parser = subparsers.add_parser(CommandType.REGISTRY)
    
    update_parser.add_argument(
        "action",
        choices=ACTION_CHOICES,
        help="Updates or deletes the control registry file",
    )
    
    project_parser = subparsers.add_parser(CommandType.MAKE)
    
    project_parser.add_argument(
        "--name",
        help="Name of the project.",
        default="new_project"
    )
    project_parser.add_argument(
        "--path",
        help="Path where the project will be created",
        default=os.getcwd()
    )

    args: argparse.Namespace = parser.parse_args()

    if args.parser_type == CommandType.MAKE:
        if not args.name:
            argparse.ArgumentError(
                message="Argument 'name' for subparser 'make' is empty. Argument 'name' is a required argument"
            )
        
        return ProjectMaker(args.path, args.name)
    elif args.parser_type == CommandType.REGISTRY:
        return registry_action(args.action)
        
    raise argparse.ArgumentError(
        message="No subparsers where used. Please use either 'registry' or 'make' as a subparser"
    )

if __name__ == "__main__":
    main()