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

import flet as ft

from fjml import (
    Build,
    CONSTANT_CONTROLS,
    generate_dict
)
from fjml.constants import CONTROL_REGISTRY_PATH
import fjml.data_types as dt
import fjml.error_types as errors
from fjml.utils import Utilities, import_module, RegistryOperations

Tools: Utilities = Utilities()

VALID_KEYS: Final[list[str]] = ["UI", "Imports", "Controls"]

class Compiler:
    
    __slots__ = (
        "control_settings", "control_registry_path", "code", 
        "controls", "parsed_controls", "parsed_ui",
        "control_awaitable", "program_name", "program", 
        "used_controls", "routes", "custom_controls",
        "control_bundles", "methods", "imports_path", "controls_registry",
        "custom_controls_added"
    )
    
    def __init__(
        self, program_name: str, code_input: dict[str, Any], 
        custom_controls: list[dt.ControlJsonScheme] = [], imports_path: str = ""
    ) -> NoReturn:
        """
        __init__ _summary_

        Args:
            program_name (str): _description_
        """
        self.used_controls: set[str] = set()
        custom_controls = self.add_constant_controls(custom_controls)
        self.custom_controls: dt.ControlRegistryJsonScheme = {}
        if custom_controls:
            self.custom_controls = generate_dict(
                [dt.ControlRegistryModel(**control) for control in custom_controls],
                True
            )
        self.custom_controls_added: bool = False
        self.imports_path: str = imports_path
        self.program_name: str = program_name
        self.controls_registry: list[dt.ControlJsonScheme] = None
        self.code: dt.JsonDict = code_input
        self.routes: set[str] = set()
        self.methods: dt.EventContainer
        self.controls: dt.ControlMap = dt.ControlMap()
        self.control_bundles: set[str] = set()
        self.control_awaitable: dict[str, bool] = dict()
        self.control_settings: dict[str, list[str]] = dict()
        self.parsed_controls: dt.ParsedControls = dt.ParsedControls()
        self.parsed_ui: dt.ParsedUserInterface = {}
    
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
    
    def add_constant_controls(self, custom_controls: list[dt.ControlJsonScheme]) -> list[dt.ControlRegistryDictPreview]:
        name: str
        for name in CONSTANT_CONTROLS:
            custom_controls.append({
                "name":name,
                "source":"fjml.src.fjml.constant_controls",
                "attr":name,
                "is_awaitable":False
            })
        
        return custom_controls
    
    def control_loader(self, control_scheme: dt.ControlRegistryJsonScheme) -> NoReturn:
        name: str
        control: dt.ControlJsonScheme
        control_keys: set[str] = set(self.controls.keys())
        
        for name in self.used_controls:
            if name in control_keys: 
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
        controls_registry: dt.ControlRegistryJsonScheme
        registry: io.TextIOWrapper
        
        if not self.controls_registry:
            self.controls_registry = RegistryOperations.load_file()
        
        self.control_loader(self.controls_registry)
        
        if self.custom_controls and not self.custom_controls_added:
            self.control_loader(self.custom_controls)
            self.custom_controls_added = True
    
    def __load_program(self) -> NoReturn:
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
            self.parsed_controls, self.parsed_ui,
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
        parsed_data: dt.ParsedControls = dt.ParsedControls()
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
    
    def return_build(self, page: ft.Page, methods: dt.EventContainer, UserBuild: Optional[Type[Build]] = None) -> Build:
        """
        return_build _summary_
        
        Args:
            UserBuild (Optional[Build], optional): _description_. Defaults to None.
        
        Returns:
            Build: _description_
        """
        compiled_program: dt.CompiledModel = self.compile()
        build: Build
        
        if not UserBuild:
            UserBuild = Build
        
        build = UserBuild(compiled_program, page)
        build.initialize()
        
        if methods:
            build.add_methods(methods)
        
        build.run_setup()
        import_module.clear_cache()
        return build



def ProgramLoader(params: dt.LoaderParameters) -> Build:
    compiler: Compiler = Compiler(
        params.program_name, 
        params.ui_code,
        params.custom_controls,
        params.imports_path
    )
    
    return compiler.return_build(
        params.page, 
        params.methods,
        params.UserBuild
    )