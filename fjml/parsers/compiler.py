import io, os, json, time, inspect
from typing import(
    Any, Union, 
    Final, Callable, 
    Sequence, Mapping, 
    Generator, Type, 
    TypeAlias
)
from functools import wraps

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

import flet as ft
from .builder import Backend
from .control_register import ControlRegistryOperations
from ..utils import Utilities, import_module
from .. import (
    data_types as dt, 
    object_enums as onums,
    error_types as errors, 
    operation_classes as opc,
    constant_controls,
    constants,
    utils,
    checks
)


def timeit(func: Callable) -> Callable:
    @wraps(func)
    def timeit_wrapper(*args, **kwargs) -> Any:
        start_time: float = time.perf_counter()
        result: Any = func(*args, **kwargs)
        end_time: float = time.perf_counter()
        print(f"Took {(end_time - start_time):.4f} seconds")
        return result

    return timeit_wrapper


Tools: Utilities = Utilities()
CompileHandler: utils.CompiledFileHandler = utils.CompiledFileHandler()
VALID_KEYS: Final[Sequence[str]] = [
    onums.MarkupKeys.UI, onums.MarkupKeys.IMPORTS, 
    onums.MarkupKeys.CONTROLS, onums.MarkupKeys.HEADER
]
MarkupType: TypeAlias = Union[Sequence[dt.JsonDict], dt.JsonDict]

class Compiler:

    __slots__ = (
        "control_settings",
        "control_registry_path",
        "code",
        "controls",
        "parsed_controls",
        "parsed_ui",
        "control_awaitable",
        "program_name",
        "program",
        "used_controls",
        "routes",
        "custom_controls",
        "control_bundles",
        "methods",
        "imports_path",
        "controls_registry",
        "are_registries_joined",
        "style_sheet",
        "dependent_refs",
        "params",
        "control_param_types"
    )

    def __init__(self, params: dt.ParamGenerator) -> NoReturn:
        self.params: dt.ParamGenerator = params
        params.parse_extentions(
            inspect.currentframe().f_back.f_globals
        )
        self.used_controls: set[str] = set()
        self.style_sheet: opc.StyleSheet
        self.custom_controls: dt.ControlRegistryJsonScheme
        self.dependent_refs: opc.ControlDependencies = opc.ControlDependencies()
        self.are_registries_joined: bool = False
        self.imports_path: str = self.params.imports_path
        self.program_name: str = self.params.program_name
        self.controls_registry: dt.ControlRegistryJsonScheme = (
            dt.ControlRegistryJsonScheme()
        )
        self.code: dt.JsonDict = self.params.ui_code
        self.routes: set[str] = set()
        self.methods: Type[dt.EventContainer]
        self.controls: dt.ControlMap = dt.ControlMap()
        self.control_param_types: Mapping[str, dt.TypeHints] = {}
        self.control_awaitable: Mapping[str, bool] = {}
        self.control_settings: Mapping[str, Sequence[str]] = {}
        self.parsed_controls: dt.ParsedControls = {}
        self.parsed_ui: dt.ParsedUserInterface = {}
        self.setup()
    
    
    def setup(self) -> NoReturn:
        self.style_sheet = opc.StyleSheet(self.params.style_sheet)
        custom_controls: Sequence[dt.ControlRegisterInterface] = self.add_constant_controls(
            self.parse_custom_controls(self.params.custom_controls)
        )
        if custom_controls:
            self.custom_controls = ControlRegistryOperations.generate_dict(
                [dt.ControlRegistryModel(**control) for control in custom_controls]
            )
    
    def parse_custom_controls(self, data: Sequence[Union[dt.ThirdPartyExtention, dt.UIImports]]) -> Sequence[dt.ControlRegisterInterface]:
        value: Union[dt.ThirdPartyExtention, dt.UIImports]
        result: Sequence[dt.ControlRegisterInterface] = []
        
        for value in data:
            if isinstance(value, (dt.ThirdPartyExtention, dt.UIImports)):
                result.extend(value.extensions())
            
        return result

    def validate_imports(self, file_name: str, data: dt.JsonDict) -> NoReturn:
        keys: Sequence[str]

        if data.get(onums.MarkupKeys.CONTROLS, None) == None:
            raise errors.InvalidMarkupFormatError(file_name, onums.MarkupKeys.CONTROLS)
        keys = list(data.keys())

        try:
            keys.remove(onums.MarkupKeys.CONTROLS)
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

    def add_constant_controls(
        self, custom_controls: Sequence[dt.ControlRegisterInterface]
    ) -> Sequence[dt.ControlRegisterInterface]:
        name: str
        
        for name in constant_controls.CONSTANT_CONTROLS:
            custom_controls.append(
                dt.ControlRegisterInterface(
                    name=name,
                    source=dt.ObjectSource(
                        getattr(constant_controls, name)
                    ),
                    attr=name,
                    control=None
                )
            )
        
        return custom_controls

    def control_loader(self, control_scheme: dt.ControlRegistryJsonScheme) -> NoReturn:
        name: str
        control: dt.ControlJsonScheme
        control_keys: set[str] = set(self.controls.keys())

        for name in self.used_controls:
            if name in control_keys or name in constants.MARKUP_SPECIFIC_CONTROLS:
                continue
            
            if name not in control_scheme[onums.ControlRegKeys.CONTROLS]:
                continue

            control = control_scheme[onums.ControlRegKeys.CONTROL_TYPES][
                control_scheme[onums.ControlRegKeys.CONTROLS].index(name)
            ]
            
            control_keys.add(name)
            self.controls[name] = getattr(
                import_module(control[onums.ControlRegKeys.SOURCE], None), 
                control[onums.ControlRegKeys.ATTR]
            )
            
            self.control_param_types[name] = utils.TypeHintSerializer.deserialize(
                control[onums.ControlRegKeys.TYPE_HINTS]
            )
            self.control_settings[name] = control[onums.ControlRegKeys.VALID_SETTINGS]

    def __load_controls(self) -> NoReturn:
        if not self.controls_registry:
            self.controls_registry = utils.RegistryFileOperations.load_file()

        if self.custom_controls and not self.are_registries_joined:
            self.controls_registry = ControlRegistryOperations.join_registry(
                self.controls_registry, self.custom_controls
            )
            self.are_registries_joined = True

        self.control_loader(self.controls_registry)

    def __load_program(self) -> NoReturn:
        self.__load_controls()
        self.__parse_imports()
        self.update_used_controls(self.style_sheet.data)
        self.update_used_controls(self.code)

    def compile(self) -> dt.CompiledModel:
        self.__load_program()
        self.parsed_controls.update(
            self.__parse_controls(self.code[onums.MarkupKeys.CONTROLS])
        )
        self.validate_main_file()
        self.__parse_ui(self.code[onums.MarkupKeys.UI])
        
        self.dependent_refs.update_cache()
        
        model: dt.CompiledModel = dt.CompiledModel(
            self.parsed_controls, self.style_sheet,
            self.parsed_ui, self.controls,
            self.routes, self.control_settings, self.dependent_refs,
            self.control_param_types, self.params.action_code, 
            self.params.program_name
        )
        
        self.params.save_program(model)
    
    def load_file(self, source: str) -> Sequence[dt.NamedControlDict]:
        program: io.TextIOWrapper
        file: Sequence[dt.NamedControlDict]
        path: str = f"{self.imports_path}\\{source}"
        
        if not os.path.exists(path):
            return []
        
        with open(path, "r") as program:
            file = json.load(program)
            self.validate_imports(source, file)
            self.update_used_controls(file[onums.MarkupKeys.CONTROLS])
            return file[onums.MarkupKeys.CONTROLS]
            
        return []

    def __parse_imports(self) -> NoReturn:
        import_data: Sequence[dt.ImportDict] = self.code.get(onums.MarkupKeys.IMPORTS, None)
        data: dt.JsonDict
        source: str
        paths: Sequence[str] = []
        jsondata: Sequence[Sequence[dt.NamedControlDict]] = []

        if not import_data:
            self.__load_controls()
            return

        for data in import_data:
            source = data.get(onums.ImportKeys.SOURCE, "")
            if not source:
                continue
            if utils.is_sequence_not_str(source):
                if not data.get(onums.ImportKeys.FROM, None):
                    continue
                for i in source:
                    paths.append(f"{data[onums.ImportKeys.FROM]}\\{i}.json")
            else:
                paths.append(f"{source}.json")
                
        for path in paths:
            data = self.load_file(path)
            if not data:
                continue
            jsondata.append(data)

        self.__load_controls()
        if not jsondata:
            return

        for data in jsondata:
            self.parsed_controls.update(self.__parse_controls(data))

    def update_used_controls(self, data: MarkupType) -> NoReturn:
        self.used_controls.update(
            Tools.find_values(
                data, onums.ControlKeys.CONTROL_TYPE, 
                constants.MARKUP_SPECIFIC_CONTROLS
            )
        )

    def __parse_controls(
        self, controls: Sequence[dt.NamedControlDict]
    ) -> dt.ParsedControls:
        parsed_data: dt.ParsedControls = {}
        data: dt.NamedControlDict

        for data in self.parse_iterator(controls, checks.NamedControlCheck):
            self.dependent_refs.add_dependencies(
                data[onums.ControlKeys.VAR_NAME], 
                data.get(onums.ControlKeys.SETTINGS, {})
            )
            parsed_data[data[onums.ControlKeys.VAR_NAME]] = self.make_control_model(
                data
            )

        return parsed_data
    
    def make_control_model(self, data: dt.NamedControlDict) -> dt.ControlModel:
        return dt.ControlModel(
            name=data[onums.ControlKeys.VAR_NAME],
            control_name=data[onums.ControlKeys.CONTROL_TYPE],
            control=self.controls[data[onums.ControlKeys.CONTROL_TYPE]],
            settings=data.get(onums.ControlKeys.SETTINGS, {}),
            valid_settings=self.control_settings[
                data[onums.ControlKeys.CONTROL_TYPE]
            ]
        )

    def __parse_ui(self, ui_data: Sequence[dt.RouteDict]) -> NoReturn:
        route_dict: dt.RouteDict
        data: tuple[str, dt.JsonDict]

        for route_dict in self.parse_iterator(ui_data, checks.RouteCheck):
            self.routes.add(route_dict[onums.ControlKeys.ROUTE])
            self.dependent_refs.add_dependencies(
                route_dict[onums.ControlKeys.ROUTE], 
                route_dict[onums.ControlKeys.SETTINGS]
            )
            self.parsed_ui[route_dict[onums.ControlKeys.ROUTE]] = dt.UIViews(**route_dict)

        self.__load_controls()
    
    def parse_iterator(self, data: Sequence[Mapping], checker: type[checks.Checker]) -> Generator[Mapping, None, None]:
        value: Mapping
        res: Union[Mapping, None]
        
        for value in data:
            res = checker.correct(value, self)
            if not res: continue
            del res["<SKIP>"]
            yield res


@timeit
def load_program(compiled_path: str, page: ft.Page) -> ft.Page:
    compiled_data: dt.CompiledModel
    backend: Backend
    
    compiled_data = CompileHandler.load(compiled_path)
    backend = Backend(compiled_data, page)
    
    return backend.initialize(
        compiled_data.methods
    )

