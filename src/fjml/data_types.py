from __future__ import annotations
import io, json, types, inspect, os, enum, importlib
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import (
    Any,
    TypedDict,
    Union,
    TypeAlias,
    NoReturn,
    Callable,
    Awaitable,
    TYPE_CHECKING,
    NotRequired,
    Type,
    Sequence,
    Mapping
)


import flet as ft

from . import utils

if TYPE_CHECKING:
    from . import operation_classes as opc

Tools: utils.Utilities = utils.Utilities()

JsonDict: TypeAlias = dict[str, Any]
IndexType: TypeAlias = Union[str, int, None]
TypeHints: TypeAlias = Mapping[str, Type]
TypeHintMap: TypeAlias = Mapping[str, TypeHints]
ControlType: TypeAlias = Union[ft.Control, enum.Enum, types.FunctionType]
ControlMap: TypeAlias = dict[str, ControlType]

class ImportKeys(enum.StrEnum):
    IMPORT: str = "import"
    FROM: str = "from"
    USING: str ="using"


class ControlRegisterInterface(TypedDict):
    name: str
    source: str
    attr: str


class ControlJsonScheme(TypedDict):
    name: str
    source: str
    attr: str
    valid_settings: Sequence[str]
    type_hints: TypeHints
    control: Callable


class ControlRegistryJsonScheme(TypedDict):
    Controls: Sequence[str]
    ControlTypes: Sequence[ControlJsonScheme]


class ControlDict(TypedDict):
    control_type: str
    settings: ControlSettings


class NamedControlDict(TypedDict):
    var_name: str
    control_type: str
    settings: ControlSettings


class LoopDict(TypedDict):
    control_type: str
    depth: int
    iterator: Union[Sequence, Mapping]
    control: Union[ControlDict, NamedControlDict]


ControlSettings: TypeAlias = dict[
    str, Union[
        None, str, int, 
        float, bool, Sequence, Mapping
    ]
]


class RouteDict(TypedDict):
    route: str
    settings: ControlSettings


ImportDict: TypedDict = TypedDict(
    'ImportDict', 
    {'source': Union[str, Sequence[str]], 'from': NotRequired[str]}
)


class UserInterfaceDict(TypedDict):
    Header: JsonDict
    Imports: Sequence[ImportDict]
    Controls: Sequence[NamedControlDict]
    UI: Sequence[RouteDict]


class UIViews:
    __slots__ = ["route", "settings"]
    def __init__(self, route: str, settings: ControlSettings = {}) -> NoReturn:
        self.route: str = route
        self.settings: ControlSettings = settings

UIViewMap: TypeAlias = Mapping[str, UIViews]


class ControlModel:
    __slots__ = [
        "name", "control_name", "bundle_name", 
        "control", "settings", "valid_settings"
    ]
    
    def __init__(
        self, name: str = "", control_name: str = "",
        control: ControlType = None, settings: ControlSettings = ControlSettings(), 
        valid_settings: Sequence[str] = []
    ) -> NoReturn:
        self.name: str = name
        self.control_name: str = control_name
        self.control: ControlType = control
        self.settings: ControlSettings = settings
        self.valid_settings: Sequence[str] = valid_settings


ParsedUserInterface: TypeAlias = dict[str, UIViews]
ParsedControls: TypeAlias = dict[str, ControlModel]
AnyCallable: TypeAlias = Union[Callable[[...], Any], Awaitable[Callable[[...], Any]]]


class ParamGenerator:
    __slots__ = [
        "header", "program_path", "custom_controls", "style_sheet", 
        "imports_path", "ui_code", "compile_path", "program_name",
        "extentions"
    ]
    
    def __init__(
        self, program_path: str, compile_path: str
    ) -> NoReturn:
        self.program_name: str
        self.program_path: str = program_path
        self.custom_controls: Sequence[ControlJsonScheme]
        self.compile_path: str = compile_path
        self.style_sheet: JsonDict = {}
        self.imports_path: str = ""
        self.ui_code: JsonDict = {}
        self.header: Header = Header()
        if not self.program_path_check:
            raise FileNotFoundError(
                f'File path, "{self.program_path}", does not exist'
            )
        self.setup()
        
    @property
    def program_path_check(self) -> bool:
        return os.path.exists(self.program_path)
    
    def join(self, end_path: str) -> str:
        return os.path.join(self.program_path, end_path)
    
    def save_program(self, compiled_program: CompiledModel) -> NoReturn:
        utils.CompiledFileHandler.save(self.compile_path, compiled_program)
    
    def parse_extentions(self, global_data):
        self.header.parse_extentions(global_data)
        self.custom_controls = self.header.extentions
        
    
    def setup(self) -> NoReturn:
        file: io.TextIOWrapper
        ui_code_path: str = self.join("ui.json")
        
        if not os.path.exists(ui_code_path):
            raise FileNotFoundError(
                f'File, "ui.json" in path "{self.program_path}" does not exist'
            )
        
        with open(ui_code_path, "r") as file:
            #print(type(file))
            self.ui_code = json.load(file)
            self.validate_ui_format()
            self.header.load_dict(self.ui_code["Header"])
        
        self.program_name = self.header.program_name
        
        self.imports_path: str = self.join(self.header.import_folder)
        if not os.path.exists(self.imports_path):
            raise FileNotFoundError(
                f'Folder, "{self.header.import_folder}" in path "{self.program_path}" does not exist'
            )

        style_path: str = self.join(f"{self.header.style_sheet_name}.style.json")
        if os.path.exists(style_path):
            with open(style_path, "r") as file:
                self.style_sheet = json.load(file)
    
    def validate_ui_format(self) -> NoReturn:
        if not isinstance(self.ui_code, Mapping):
            raise TypeError("File, ui.json, is not of type dict")
        
        if "Header" not in self.ui_code:
            raise KeyError("Key, 'Header' was not found")


class ObjectSource:
    __slots__ = ["obj", "source", "is_class"]
    def __init__(self, obj: Any, source: str = "") -> NoReturn:
        self.obj: Any = obj
        self.source: str = source
        self.is_class = False
        
        if not self.source:
            self.source = self.obj.__module__
            
        self.is_class = inspect.isclass(self.obj)

    
class ControlRegistryModel:
    __slots__ = ["name", "source", "attr", "is_awaitable", "object_args", "return_dict"]

    def __init__(self, name: str, attr: str, source: ObjectSource = ObjectSource(type(None)), control: ControlType = None) -> NoReturn:
        self.name: str = name
        self.source: Union[ObjectSource, str] = source 
        if control:
            self.source = ObjectSource(control)
        self.attr: str = attr
        self.object_args: Sequence[str] =  []
        hints: TypeHintMap = {}
        
        self.object_args = self.generate_args()
        if not self.source.is_class:
            hints = utils.TypeHintSerializer.serialize(
                Tools.get_hints(self.source.obj)
            )
        elif issubclass(self.source.obj, enum.Enum):
            self.object_args = []
        else:
            hints = utils.TypeHintSerializer.serialize(
                Tools.get_hints(self.source.obj)
            )

        self.source = self.source.source

        self.return_dict: ControlJsonScheme = ControlJsonScheme(
            name=self.name,
            source=self.source,
            attr=self.attr,
            valid_settings=self.object_args,
            type_hints=hints,
            control=control
        )

    def generate_args(self, is_enum: bool = False) -> Sequence[str]:
        if callable(self.source.obj):
            return Tools.get_object_args(self.source.obj)
        return []


class BlockAssignment:
    __slots__ = ["__PRIMARY", "__SECONDARY"]

    def __init__(self) -> NoReturn:
        self.__PRIMARY: bool = False
        self.__SECONDARY: bool = False
    
    @property
    def PRIMARY(self):
        return self.__PRIMARY
    
    @property
    def SECONDARY(self):
        return self.__SECONDARY

    def switch_primary(self):
        if self.__PRIMARY:
            return
        self.__PRIMARY = True
    
    def switch_secondary(self):
        if self.__SECONDARY:
            return
        self.__SECONDARY = True


class CompiledModel:
    __slots__ = [
        "controls", "style_sheet", "ui", 
        "control_awaitable", "control_map", "routes", 
        "dependencies", "type_hints", "program_name",
        "control_settings"
    ]
    def __init__(
        self, controls: ParsedControls, style_sheet: opc.StyleSheet, 
        ui: Mapping[str, UIViews], 
        control_map: ControlMap, routes: Sequence[str], control_settings: Sequence[str],
        dependencies: opc.ControlDependencies, type_hints: TypeHintMap, program_name: str = ""
    ) -> NoReturn:
    
        self.controls: ParsedControls = controls
        self.style_sheet: opc.StyleSheet = style_sheet
        self.ui: Mapping[str, UIViews] = ui
        self.control_map: ControlMap = control_map
        self.routes: Sequence[str] = routes
        self.program_name: str = program_name
        self.type_hints: TypeHintMap = type_hints
        self.dependencies: opc.ControlDependencies = dependencies
        self.control_settings: Sequence[str] = control_settings

@dataclass
class Header:
    program_name: str = field(default="")
    import_folder: str = field(default="")
    style_sheet_name: str = field(default="")
    extentions: list = field(default_factory=list)
    
    def __post_init__(self) -> NoReturn:
        func: Callable = lambda x: x[:2] != "__"
        self.attrs: Sequence[str] = list(
            filter(func, dir(self))
        )
    
    def load_dict(self, data: JsonDict) -> NoReturn:
        name: str
        attr: Any
        
        for name in self.attrs:
            attr = getattr(self, name)
            if callable(attr) or isinstance(attr, property):
                continue
            elif name in data:
                setattr(self, name, data[name])
    
    def parse_extentions(self, global_data: Mapping) -> NoReturn:
        result: Sequence[UIImports] = []
        ext: Sequence[JsonDict]
        imports: Union[Sequence, str]
        
        for data in self.extentions:
            ext = []
            if not isinstance(data, Mapping):
                continue
            if ImportKeys.IMPORT not in data or ImportKeys.FROM not in data:
                continue
            
            if not isinstance(data.get(ImportKeys.USING, None), str):
                data[ImportKeys.USING] = ""
            
            if not isinstance(data.get(ImportKeys.FROM, None), str):
                continue
            
            imports = data.get(ImportKeys.IMPORT, None)
            if isinstance(imports, str):
                ext.append(imports)
            elif isinstance(imports, Sequence):
                ext.extend(imports)
            else:
                continue
            
            result.append(
                UIImports(
                    data[ImportKeys.FROM], 
                    ext, 
                    global_data, 
                    data[ImportKeys.USING]
                )
            )
        
        self.extentions = result


class ThirdPartyExtention:
    
    __slots__ = ["module", "imports", "prefix"]
    
    def __init__(self, module_name: str, imports: Sequence[str], module_prefix: str = "") -> NoReturn:
        self.module: str = module
        self.imports: Sequence[str] = imports
        self.prefix: str = module_prefix
    
    def get_obj(self, name: str) -> Any:
        return getattr(self.module, name, None)
    
    @property
    def extensions(self) -> Sequence[ControlRegisterInterface]:
        result: Sequence[ControlRegisterInterface] = []
        obj_name: str
        obj: Any
        
        for obj_name in self.imports:
            obj = self.get_obj(obj_name)
            if not callable(obj): continue
            
            result.append(
                Tools.control_to_registry_interface(
                    obj, self.prefix, try_name=obj_name
                )
            )
        
        return result


class UIImports:
    
    __slots__ = ["module", "imports", "prefix", "module_name", "outer_global"]
    
    def __init__(self, module_name: str, imports: Sequence[str], outer_global: dict, module_prefix: str = "") -> NoReturn:
        self.outer_global = outer_global
        self.module_name: str = module_name
        self.module: types.ModuleType
        self.imports: Sequence[str] = imports
        self.prefix: str = module_prefix
    
    def get_obj(self, name: str) -> Any:
        return getattr(self.module, name, None)
    
    def importer(self, relative: bool = False) -> types.ModuleType:
        loc: Mapping = {}
        if relative:
            name_split: str = self.module_name.split(".")
            exec(f"from {'.'.join(name_split[:-1])} import {name_split[-1]} as module", self.outer_global, loc)
            return loc["module"]
        
        exec(f"import {self.module_name} as module", self.outer_global, loc)
        return loc["module"]
        
    
    def run_import(self) -> NoReturn:
        if self.module_name.strip().startswith("."):
            self.module = self.importer(True)
            return
        self.module = self.importer()
    
    @property
    def extensions(self) -> Sequence[ControlRegisterInterface]:
        result: Sequence[ControlRegisterInterface] = []
        obj_name: str
        obj: Any
        
        self.run_import()
        
        for obj_name in self.imports:
            obj = self.get_obj(obj_name)
            if not callable(obj): continue
            
            result.append(
                Tools.control_to_registry_interface(
                    obj, self.prefix, try_name=obj_name
                )
            )
        
        return result


class EventContainer(metaclass=ABCMeta):

    style_sheet: opc.StyleSheet
    object_bucket: opc.ObjectContainer
    view_operations: opc.ViewOperations
    property_bucket: opc.PropertyContainer
    page: ft.Page
    update: Callable[[...], NoReturn]
    dict_to_control: Callable[[ControlDict], ControlType]
    group_assign: Callable[[Any, Mapping[str, Any]], NoReturn]
    setup_functions: opc.SetupFunctions

    @abstractmethod
    def _page_setup(self) -> NoReturn: ...

    @abstractmethod
    def _imports(self) -> NoReturn: ...
    
