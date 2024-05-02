from argparse import Namespace, ArgumentParser
from typing import Final, Any, Optional
import os
import shutil
import json
import inspect
try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

from ..constants import (
    USER_INTEFACE_FILE_TEXT, 
    IMPORT_FILE_TEXT, 
    FUNCTION_FILE_TEXT, 
    ARCHIVE_FORMAT, 
    OPERATION_ARGS
)
from enum import Enum
import operator as op 
import flet as ft
from flet.matplotlib_chart import MatplotlibChart
from flet.plotly_chart import PlotlyChart
from .control_register import  ControlRegistryOperations
from ..registry import other_controls_registry
from .. import data_types as dt

def splitter(data: str, sep:str="."):
    data = data.split(sep)
    if len(data) < 2: return data[0]
    return data[1]

invalid_sources: list[str] = [
    "utils", "pubsub", 
    "connection", "protocol", 
    "event_handler", "local_connection", 
    "locks", "querystring",
    "session_storage", "template_route",
    "event", "control_event",
    "tests"
]

def update_register() -> NoReturn:
    added_names: list[str] = []
    populous: list[dt.ControlRegisterInterface] = []
    #other_controls_registry.others
    for name, obj in inspect.getmembers(ft):
        if inspect.isclass(obj) and name not in added_names:
            obj_source = dt.ObjectSource(obj, "flet")
            populous.append(
                dt.ControlRegisterInterface(
                    name=name,
                    source=obj_source,
                    attr=name,
                    is_awaitable=False
                )
            )
            added_names.append(name)
    
    
    for name, obj in inspect.getmembers(ft): 
        if inspect.ismodule(obj) and name not in invalid_sources:
            for name1, obj1 in inspect.getmembers(obj):
                if not hasattr(obj1, "__module__"): continue
                if (inspect.isclass(obj1) or inspect.isfunction(obj1) or type(obj1) != type) and splitter(obj1.__module__) == splitter(obj.__name__):
                    obj_source = dt.ObjectSource(obj1, obj1.__module__)
                    if inspect.isclass(obj1) and name1 not in added_names:
                        populous.append(
                            dt.ControlRegisterInterface(
                                name=name1,
                                source=obj_source,
                                attr=name1,
                                is_awaitable=False
                            )
                        )
                        added_names.append(name1)
                    elif inspect.isfunction(obj1) and f"{name}.{name1}" not in added_names:
                        populous.append(
                            dt.ControlRegisterInterface(
                                name=f"{name}.{name1}",
                                source=obj_source,
                                attr=name1,
                                is_awaitable=False
                            )
                        )
                        added_names.append(f"{name}.{name1}")
                    elif type(obj1) != type and f"{name}.{name1}" not in added_names and not callable(obj1):
                        populous.append(
                            dt.ControlRegisterInterface(
                                name=f"{name}.{name1}",
                                source=obj_source,
                                attr=name1,
                                is_awaitable=False
                            )
                        )
                        added_names.append(f"{name}.{name1}")

    for name, obj in inspect.getmembers(ft.canvas):
        if inspect.isclass(obj) and name not in added_names:
            obj_source = dt.ObjectSource(obj, "flet.canvas")
            populous.append(
                dt.ControlRegisterInterface(
                    name=name,
                    source=obj_source,
                    attr=name,
                    is_awaitable=False
                )
            )
            added_names.append(name)

    populous.extend([
        dt.ControlRegisterInterface(
            name="MatplotlibChart",
            source=dt.ObjectSource(
                MatplotlibChart, 
                "flet.matplotlib_chart"
            ),
            attr="MatplotlibChart",
            is_awaitable=False
        ),
        dt.ControlRegisterInterface(
            name="PlotlyChart",
            source=dt.ObjectSource(
                PlotlyChart, 
                "flet.plotly_chart"
            ),
            attr="PlotlyChart",
            is_awaitable=False
        )
    ])
    
    ControlRegistryOperations.generate_dict([
        dt.ControlRegistryModel(**content) 
        for content in populous
    ])

def make_python_file(path: str, filename: str, code: str) -> NoReturn:
    file_path: str = os.path.join(path, filename)
    with open(file_path, 'w') as f:
        f.write(code)

def make_json_file(path: str, filename: str, data: dict) -> NoReturn:
    file_path: str = os.path.join(path, filename)
    with open(file_path, 'w') as f:
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

    # Make Python file
    make_python_file(project_path, "func.py", FUNCTION_FILE_TEXT)

    # Make subfolder
    subfolder_path: str = os.path.join(project_path, "extra")
    make_folder(subfolder_path)

    # Make JSON file inside the subfolder
    make_json_file(subfolder_path, "import1.json", IMPORT_FILE_TEXT)


class Packer:
    
    __slots__ = ("project_path", "zip_path", "project_name", "parser")
    
    def __init__(self, parser: ArgumentParser, path: str, project_name: str) -> NoReturn:
        self.parser: ArgumentParser = parser
        self.project_name: str = project_name
        self.project_path: str = os.path.join(path, project_name)
        self.zip_path: str = os.path.join(path, project_name)
    
    def pack(self) -> NoReturn:
        try:
            shutil.make_archive(self.zip_path, ARCHIVE_FORMAT, self.project_path)
        except FileExistsError:
            os.remove(f"{self.zip_path}.zip")
            shutil.make_archive(self.zip_path, ARCHIVE_FORMAT, self.project_path)
        
        try:
            os.rename(f"{self.zip_path}.zip", f"{self.zip_path}.gui")
        except FileExistsError:
            os.remove(f"{self.zip_path}.gui")
            os.rename(f"{self.zip_path}.zip", f"{self.zip_path}.gui")
    
    def unpack(self, output_dir: str) -> NoReturn:
        out: str = os.path.join(output_dir, self.project_name)
        archive: str = f"{self.zip_path}.gui"
        if not os.path.exists(archive):
            self.parser.error(f"File with name \"{self.project_name}\" does not exist")
        try:
            shutil.unpack_archive(
                archive, out, ARCHIVE_FORMAT
            )
        except FileExistsError:
            os.remove(out)
            shutil.unpack_archive(
                archive, out, ARCHIVE_FORMAT
            )


def main() -> NoReturn:
    
    current_directory: str = os.getcwd()
    
    parser: ArgumentParser = ArgumentParser(prog="FastFlet", description='Generate a project.')
    parser.add_argument('operation', type=str, help='Path where the project will be created.', choices=OPERATION_ARGS)
    parser.add_argument('--path', type=str, help='Path where the project will be created.', default=current_directory)
    parser.add_argument('--name', type=str, help='Name of the project.', default="project")

    args: Namespace = parser.parse_args()
    packer: Packer = Packer(parser, args.path, args.name)
    
    if args.operation == OPERATION_ARGS[0]:
        generate_project(args.path, args.name)
    elif args.operation == OPERATION_ARGS[1]:
        update_register()

'''
if __name__ == "__main__":
    main()'''