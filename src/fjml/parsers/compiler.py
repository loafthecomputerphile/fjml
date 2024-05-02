import asyncio
import json
import io
from typing import (
    Any, 
    Optional, 
    Union,
    Type,
    Final,
    NoReturn
)
import types
import flet as ft


from .. import constant_controls

from .builder import Build
from .control_register import ControlRegistryOperations
from ..constants import CONTROL_REGISTRY_PATH
from .. import data_types as dt
from .. import error_types as errors
from ..utils import Utilities, import_module, RegistryFileOperations

Tools: Utilities = Utilities()

VALID_KEYS: Final[list[str]] = ["UI", "Imports", "Controls"]
MARKUP_SPECIFIC_CONTROLS: Final[list[str]] = [
    "loop", "ref", "loop_index"
]

class Compiler:
    
    __slots__ = (
        "control_settings", "control_registry_path", "code", 
        "controls", "parsed_controls", "parsed_ui",
        "control_awaitable", "program_name", "program", 
        "used_controls", "routes", "custom_controls",
        "control_bundles", "methods", "imports_path", "controls_registry",
        "are_registries_joined", "style_sheet"
    )
    
    def __init__(
        self, program_name: str, code_input: dict[str, Any], 
        custom_controls: list[dt.ControlRegisterInterface] = [], imports_path: str = "",
        style_sheet: dt.JsonDict = {}
    ) -> NoReturn:
        """
        __init__ _summary_

        Args:
            program_name (str): _description_
        """
        self.used_controls: set[str] = set()
        self.style_sheet: dt.StyleSheet = dt.StyleSheet(style_sheet)
        self.update_used_controls(self.style_sheet.data)
        custom_controls = self.add_constant_controls(custom_controls)
        self.custom_controls: dt.ControlRegistryJsonScheme
        if custom_controls:
            self.custom_controls = ControlRegistryOperations.generate_dict(
                [dt.ControlRegistryModel(**control) for control in custom_controls],
                True
            )
        self.are_registries_joined: bool = False
        self.imports_path: str = imports_path
        self.program_name: str = program_name
        self.controls_registry: dt.ControlRegistryJsonScheme = dt.ControlRegistryJsonScheme()
        self.code: dt.JsonDict = code_input
        self.routes: set[str] = set()
        self.methods: dt.EventContainer
        self.controls: dt.ControlMap = dt.TypeDict({}, (ft.Control, types.FunctionType, object))
        self.control_bundles: set[str] = set()
        self.control_awaitable: dict[str, bool] = dt.TypeDict({}, bool)
        self.control_settings: dict[str, list[str]] = dt.TypeDict({}, list)
        self.parsed_controls: dt.ParsedControls = dt.TypeDict({}, dt.ControlModel)
        self.parsed_ui: dt.ParsedUserInterface = dt.TypeDict({}, dt.UserInterfaceViews)
    
    def validate_imports(self, file_name: str, data: dt.JsonDict) -> NoReturn:
        keys: list[str]
        
        if data.get("Controls", None) == None:
            raise errors.InvalidMarkupFormatError(file_name, "Controls")
        keys = list(data.keys())
        
        try:
            keys.remove("Controls")
        except:
            pass
        
        if len(keys) == 0: return
        raise errors.InvalidMarkupContainerError(file_name, keys[0])
    
    def validate_main_file(self) -> NoReturn:
        key: str
        
        for key in VALID_KEYS:
            if self.code.get(key, None) == None:
                raise errors.InvalidMarkupFormatError("ui.json", key)
        
        for key in self.code.keys():
            if key not in VALID_KEYS:
                raise errors.InvalidMarkupContainerError("ui.json", key)
    
    def add_constant_controls(self, custom_controls: list[dt.ControlRegisterInterface]) -> list[dt.ControlRegisterInterface]:
        name: str
        for name in constant_controls.CONSTANT_CONTROLS:
            obj = getattr(constant_controls, name)
            custom_controls.append(
                dt.ControlRegisterInterface(
                    name=name,
                    source=dt.ObjectSource(
                        obj, obj.__module__
                    ),
                    attr=name,
                    is_awaitable=False
                )
            )
        
        return custom_controls
    
    def control_loader(self, control_scheme: dt.ControlRegistryJsonScheme) -> NoReturn:
        name: str
        control: dt.ControlJsonScheme
        control_keys: set[str] = set(self.controls.keys())
        
        for name in self.used_controls:
            if name in control_keys or name in MARKUP_SPECIFIC_CONTROLS: 
                continue
            if name in control_scheme["Controls"]:
                control = control_scheme["ControlTypes"][
                    control_scheme["Controls"].index(name)
                ]
                self.controls[name] = getattr(
                    import_module(control["source"], None),
                    control["attr"]
                )
                
                control_keys.add(name)
                self.control_awaitable[name] = control["awaitable"]
                self.control_settings[name] = control["valid_settings"]
                continue
            
            raise ImportError(f"Control named, \"{name}\", is not registered")
    
    def __load_controls(self) -> NoReturn:
        if not self.controls_registry:
            self.controls_registry = RegistryFileOperations.load_file()
        
        if self.custom_controls and not self.are_registries_joined:
            self.controls_registry = ControlRegistryOperations.join_registry(
                self.controls_registry, self.custom_controls
            )
            self.are_registries_joined = True
            
        self.control_loader(self.controls_registry)
    
    def __load_program(self) -> NoReturn:
        self.__load_controls()
        self.update_used_controls(self.code)
        self.__parse_imports()
    
    def compile(self) -> dt.CompiledModel:
        self.__load_program()
        self.parsed_controls.update(
            self.__parse_controls(self.code["Controls"])
        )
        self.validate_main_file()
        self.__parse_ui(self.code["UI"])
        
        return dt.CompiledModel(
            self.parsed_controls, self.style_sheet, self.parsed_ui,
            self.control_awaitable, self.controls,
            self.routes, self.control_bundles
        )
    
    def __parse_imports(self) -> NoReturn:
        import_data: list[dt.ImportDict] = self.code.get("Imports", None)
        data: dt.JsonDict
        program: io.TextIOWrapper
        source: str
        file: list[dt.NamedControlDict]
        jsondata: list[list[dt.NamedControlDict]] = []
        
        if not import_data:
            self.__load_controls()
            return
        
        for data in import_data:
            name = data.get("source")
            source = f"{name}.json"
            with open(f"{self.imports_path}/{source}", 'r') as program:
                file = json.load(program)
                self.validate_imports(source, file)
                self.update_used_controls(file["Controls"])
                jsondata.append(file["Controls"])
                continue
            raise FileNotFoundError(f"File at path, \"{self.imports_path}\{source}.json\" does not exist")
        
        self.__load_controls()
        if not jsondata:
            return
            
        for data in jsondata:
            self.parsed_controls.update(
                self.__parse_controls(data)
            )
    
    def update_used_controls(self, data: Union[list[dt.JsonDict], dt.JsonDict]) -> NoReturn:
        self.used_controls.update(
            Tools.find_values(
                data, "control_type"
            )
        )
    
    def __parse_controls(self, control_data: list[dt.NamedControlDict]) -> dt.ParsedControls:
        parsed_data: dt.ParsedControls = dt.TypeDict({}, dt.ControlModel)
        var_name: str
        bundle_name: str
        bundles: list[str] = []
        control_type: str
        data: dt.NamedControlDict
        
        
        for data in control_data:
            var_name = data["var_name"]
            control_type = data["control_type"]
            settings = data.get("settings", {})
            
            if control_type == "ref":
                parsed_data[var_name] = dt.ControlModel(
                    name=var_name,
                    control_name=control_type,
                    settings=settings
                )
                continue
            
            bundle_name = data.get("bundle_name", "")
            parsed_data[var_name] = dt.ControlModel(
                name=var_name,
                bundle_name=bundle_name,
                control_name=control_type,
                control=self.controls[control_type],
                settings=settings,
                valid_settings=self.control_settings[control_type]
            )
            
            if bundle_name:
                bundles.append(bundle_name)
            
        self.control_bundles.update(bundles)
        return parsed_data
    
    def __parse_ui(self, ui_data: list[dt.RouteDict]) -> NoReturn:
        route_dict: dt.RouteDict
        route: str
        settings: dt.ControlSettings
        
        for route_dict in ui_data:
            route = route_dict["route"]
            settings = route_dict["settings"]
            
            self.routes.add(route)
            self.parsed_ui[route] = dt.UserInterfaceViews(
                route,
                settings
            )
        
        self.__load_controls()
    
    def return_build(self, page: ft.Page, methods: dt.EventContainer, user_build: Optional[Type[Build]] = None) -> Build:
        """
        return_build _summary_
        
        Args:
            UserBuild (Optional[Build], optional): _description_. Defaults to None.
        
        Returns:
            Build: _description_
        """
        compiled_program: dt.CompiledModel = self.compile()
        build: Build
        
        if not user_build:
            user_build = Build
        
        build = user_build(compiled_program, page)
        build.initialize()
        
        if methods:
            build.add_methods(methods)
        
        build.run_setup()
        return build



def ProgramLoader(params: dt.LoaderParameters) -> Build:
    compiler: Compiler = Compiler(
        params.program_name, params.ui_code,
        params.custom_controls, params.imports_path,
        params.style_sheet
    )
    
    return compiler.return_build(
        params.page, params.methods, params.UserBuild
    )