from __future__ import annotations
import io, json, types, inspect, os, enum
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    TypedDict,
    Union,
    TypeAlias,
    Callable,
    Awaitable,
    TYPE_CHECKING,
    NotRequired,
    Type,
    Sequence,
    Mapping
)

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

import flet as ft

from . import utils
from .object_enums import *

if TYPE_CHECKING:
    from .display.renderer import Renderer
    from . import operation_classes as opc


Tools: utils.Utilities = utils.Utilities()

CallableInstance: TypeAlias = Any
JsonDict: TypeAlias = dict[str, Any]
IndexType: TypeAlias = Union[str, int, None]
TypeHints: TypeAlias = Mapping[str, Type]
SerializedTypeHints: TypeAlias = Mapping[str, str]
TypeHintMap: TypeAlias = Mapping[str, TypeHints]
ControlType: TypeAlias = Union[ft.Control, enum.Enum, types.FunctionType, CallableInstance]
ControlMap: TypeAlias = dict[str, ControlType]

class ControlRegisterInterface(TypedDict):
    name: str
    source: str
    attr: str


class ControlJsonScheme(TypedDict):
    name: str
    source: str
    attr: str
    valid_settings: Sequence[str]
    type_hints: SerializedTypeHints
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
    {
        'source': Union[str, Sequence[str]], 
        'from': NotRequired[str]
    }
)


class UserInterfaceDict(TypedDict):
    Header: JsonDict
    Imports: Sequence[ImportDict]
    Controls: Sequence[NamedControlDict]
    UI: Sequence[RouteDict]


class NestedControlModel:
    
    __slots__ = ("control_name", "control", "settings")
    
    def __init__(
        self, control_name: str = "",
        control: ControlType = None, settings: ControlSettings = {}
    ) -> NoReturn:
        self.control_name: str = control_name
        self.control: ControlType = control
        self.settings: ControlSettings = settings
    
    def build(self, parser: types.MethodType[Renderer]) -> ControlType:
        if callable(self.control):
            return self.control(
                **parser(
                    self.settings,
                    types=self.control_name,
                    ignore=True
                )
            )
            
        return self.control

class ControlModel:
    
    __slots__ = ("name", "control_name", "control", "settings")
    
    def __init__(
        self, name: str = "", control_name: str = "",
        control: ControlType = None, settings: NestedControlModel = NestedControlModel()
    ) -> NoReturn:
        self.name: str = name
        self.control_name: str = control_name
        self.control: ControlType = control
        self.settings: NestedControlModel = settings
    
    def build(self, parser: types.MethodType[Renderer]) -> ControlType:
        if callable(self.control):
            return self.control(
                **parser(
                    self.settings,
                    types=self.control_name,
                    ignore=True
                )
            )
            
        return self.control
    


class UIViews:
    __slots__ = ["route", "settings"]
    def __init__(self, route: str, settings: ControlSettings = {}, valid_settings: Sequence[str] = []) -> NoReturn:
        ...
    
    def build(self, parser: types.MethodType[Renderer]) -> ft.View:
        ...


UIViewMap: TypeAlias = Mapping[str, UIViews]

ParsedUserInterface: TypeAlias = dict[str, UIViews]
ParsedControls: TypeAlias = dict[str, ControlModel]
AnyCallable: TypeAlias = Union[Callable[[...], Any], Awaitable[Callable[[...], Any]]]


class ParamGenerator:
    __slots__ = (
        "header", "program_path", "custom_controls", "style_sheet", 
        "imports_path", "ui_code", "compile_path", "program_name",
        "extensions", "action_code"
    )
    
    def __init__(self, program_path: str, compile_path: str) -> NoReturn:
        self.custom_controls: Sequence[ControlJsonScheme]
        self.program_name: str
        self.program_path: str = program_path
        self.compile_path: str = compile_path
        self.style_sheet: JsonDict = {}
        self.imports_path: str = ""
        self.action_code: bytes
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
    
    def parse_extensions(self) -> NoReturn:
        self.header.parse_extensions(
            inspect.currentframe().f_back.f_back.f_globals
        )
        self.custom_controls = self.header.extensions
        self.action_code = self.header.action
    
    def setup(self) -> NoReturn:
        file: io.TextIOWrapper
        ui_code_path: str = self.join("ui.json")
        
        if not os.path.exists(ui_code_path):
            raise FileNotFoundError(
                f'File, "ui.json" in path "{self.program_path}" does not exist'
            )
        
        with open(ui_code_path, "r") as file:
            self.ui_code = json.load(file)
            self.validate_ui_format()
            self.header.load_dict(self.ui_code[MarkupKeys.HEADER])
        
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
        
        if MarkupKeys.HEADER not in self.ui_code:
            raise KeyError("Key, 'Header' was not found")


class ObjectSource:
    
    __slots__ = ("obj", "source", "is_class")
    
    def __init__(self, obj: Any, source: str = "") -> NoReturn:
        self.obj: Any = obj
        self.source: str = source
        self.is_class: bool
        
        if not self.source:
            self.source = self.obj.__module__
            
        self.is_class = inspect.isclass(self.obj)

    
class ControlRegistryModel:
    
    __slots__ = ("name", "source", "attr", "is_awaitable", "object_args", "return_dict")

    def __init__(
        self, name: str, attr: str, source: ObjectSource = ObjectSource(type(None)), 
        control: ControlType = None, serialize: bool = True
    ) -> NoReturn:
        self.name: str = name
        self.source: Union[ObjectSource, str] = source 
        if control:
            self.source = ObjectSource(control)
        self.attr: str = attr
        self.object_args: Sequence[str]
        hints: SerializedTypeHints = {}
        
        if not self.source.is_class:
            self.object_args = self.generate_args()
            hints = self.serialize() if serialize else Tools.get_hints(self.source.obj)
        elif issubclass(self.source.obj, enum.Enum):
            self.object_args = []
        else:
            self.object_args = self.generate_args()
            hints = self.serialize() if serialize else Tools.get_hints(self.source.obj)

        self.source = self.source.source

        self.return_dict: ControlJsonScheme = ControlJsonScheme(
            name=self.name,
            source=self.source,
            attr=self.attr,
            valid_settings=self.object_args,
            type_hints=hints,
            control=control
        )
    
    def serialize(self) -> TypeHints:
        return utils.TypeHintSerializer.serialize(
            Tools.get_hints(self.source.obj)
        )
    
    def generate_args(self, is_enum: bool = False) -> Sequence[str]:
        obj: Any = self.source.obj
        return Tools.get_object_args(obj) if callable(obj) else []


class BlockAssignment:
    __slots__ = ["__PRIMARY", "__SECONDARY"]

    def __init__(self) -> NoReturn:
        self.__PRIMARY: bool = False
        self.__SECONDARY: bool = False
    
    @property
    def PRIMARY(self) -> bool:
        return self.__PRIMARY
        
    @property
    def SECONDARY(self) -> bool:
        return self.__SECONDARY

    def switch_primary(self) -> NoReturn:
        if self.__PRIMARY:
            return
        self.__PRIMARY = True
    
    def switch_secondary(self) -> NoReturn:
        if self.__SECONDARY:
            return
        self.__SECONDARY = True
    
    def __in_class_scope(self) -> bool:
        return isinstance(
            inspect.currentframe().f_back.f_back.f_locals.get("self", None), 
            type(self)
        )
    
    def __setattr__(self, name: str, value: Any) -> NoReturn:
        block = [
            "_BlockAssignment__SECONDARY", "_BlockAssignment__PRIMARY", 
            "__in_class_scope"
        ]
        if name in block and not self.__in_class_scope():
            return
        super().__setattr__(name, value)
    
    def __getattribute__(self, name: str) -> Any:
        block = [
            "_BlockAssignment__SECONDARY", "_BlockAssignment__PRIMARY", 
            "__in_class_scope"
        ]
        if name in block and not self.__in_class_scope():
            return
        return super().__getattribute__(name)


class CompiledModel:
    __slots__ = [
        "controls", "style_sheet", "ui", 
        "control_awaitable", "control_map", "routes", 
        "dependencies", "type_hints", "program_name",
        "control_settings", "methods"
    ]
    def __init__(
        self, controls: ParsedControls, style_sheet: opc.StyleSheet, 
        ui: Mapping[str, UIViews], 
        control_map: ControlMap, routes: Sequence[str], control_settings: Sequence[str],
        dependencies: opc.ControlDependencies, type_hints: TypeHintMap, 
        methods: Type[EventContainer], program_name: str = ""
    ) -> NoReturn:
        
        self.methods: bytes = methods
        self.controls: ParsedControls = controls
        self.style_sheet: opc.StyleSheet = style_sheet
        self.ui: Mapping[str, UIViews] = ui
        self.control_map: ControlMap = control_map
        self.routes: Sequence[str] = routes
        self.program_name: str = program_name
        self.type_hints: TypeHintMap = type_hints
        self.dependencies: opc.ControlDependencies = dependencies
        self.control_settings: Mapping[str, Sequence[str]] = control_settings

@dataclass
class Header:
    action_import: Mapping = field(default_factory=dict)
    program_name: str = field(default="")
    import_folder: str = field(default="")
    style_sheet_name: str = field(default="")
    extensions: list[Mapping] = field(default_factory=list)
    
    def __post_init__(self) -> NoReturn:
        self.action: Union[Type[EventContainer], None] = None
        self.attrs: Sequence[str] = list(
            filter(lambda x: x[:2] != "__", dir(self))
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
    
    def get_file(self, global_data: Mapping) -> NoReturn:
        
        if not isinstance(self.action_import, Mapping):
            self.action = BlankEventContainer()
        elif ImportKeys.IMPORT not in self.action_import:
            self.action = BlankEventContainer()
        elif ImportKeys.FROM not in self.action_import:
            self.action = BlankEventContainer()
            
        if self.action:
            return
        
        self.action = Importer(global_data).import_attr(
            self.action_import[ImportKeys.FROM],
            self.action_import[ImportKeys.IMPORT]
        )
        
        del self.action_import
        
    
    def parse_extensions(self, global_data: Mapping) -> NoReturn:
        self.get_file(global_data)
        result: Sequence[UIImports] = []
        ext: Sequence[JsonDict]
        imports: Union[Sequence, str]
        
        for data in self.extensions:
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
        
        self.extensions = result


class ThirdPartyExtension:
    
    __slots__ = ["module", "imports", "prefix"]
    
    def __init__(self, module_name: str, imports: Sequence[str], module_prefix: str = "") -> NoReturn:
        self.module: str = module
        self.imports: Sequence[str] = imports
        self.prefix: str = module_prefix
    
    def get_obj(self, name: str) -> Any:
        return getattr(self.module, name, None)
    
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


class Importer:
    
    __slots__ = ("outer_global")
    
    def __init__(self, outer_global: Mapping) -> NoReturn:
        self.outer_global: Mapping = outer_global
    
    def import_module(self, module_name: str) -> types.ModuleType:
        loc: Mapping = {}
        if module_name.strip().startswith("."):
            name_split: str = module_name.split(".")
            exec(f"from {'.'.join(name_split[:-1])} import {name_split[-1]} as module", self.outer_global, loc)
            return loc["module"]
        
        exec(f"import {module_name} as module", self.outer_global, loc)
        return loc["module"]
    
    def import_attr(self, module_name: str, attr: str) -> Any:
        return getattr(self.import_module(module_name), attr, None)


class UIImports:
    
    __slots__ = ("module", "imports", "prefix", "module_name", "importer")
    
    def __init__(self, module_name: str, imports: Sequence[str], outer_global: dict, module_prefix: str = "") -> NoReturn:
        self.module_name: str = module_name
        self.module: types.ModuleType
        self.imports: Sequence[str] = imports
        self.prefix: str = module_prefix
        self.importer: Importer = Importer(outer_global)
    
    def get_obj(self, name: str) -> Any:
        return getattr(self.module, name, None)
    
    def extensions(self) -> Sequence[ControlRegisterInterface]:
        result: Sequence[ControlRegisterInterface] = []
        obj_name: str
        obj: Any
        
        self.module = self.importer.import_module(self.module_name)
        if not self.module:
            return []
        
        for obj_name in self.imports:
            obj = self.get_obj(obj_name)
            if not callable(obj): continue
            
            result.append(
                Tools.control_to_registry_interface(
                    obj, self.prefix, try_name=obj_name
                )
            )
        
        return result


ExtensionType: TypeAlias = Union[ThirdPartyExtension, UIImports]

class EventContainer(metaclass=ABCMeta):
    
    client_storage: ft.Page.client_storage
    session: ft.Page.session
    eval_locals: opc.EvalLocalData
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
    

class BlankEventContainer(EventContainer):
    
    def _page_setup(self) -> NoReturn: 
        ...

    def _imports(self) -> NoReturn: 
        ...