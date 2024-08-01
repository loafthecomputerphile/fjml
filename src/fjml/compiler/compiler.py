import io, os, json, time, operator, functools
from typing import(
    Any, Union, 
    Final, Callable, 
    Sequence, Mapping, 
    Generator, Type, 
    TypeAlias
)

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

import flet as ft

from ..display.builder import Backend
from ..object_enums import *
from ..registry.control_register import ControlRegistryOperations
from ..utils import Utilities, import_module
from . import checks
from .. import (
    data_types as dt,
    error_types as errors, 
    operation_classes as opc,
    constant_controls,
    constants,
    utils
)


def timeit(func: Callable) -> Callable:
    @functools.wraps(func)
    def timeit_wrapper(*args, **kwargs) -> Any:
        start_time: float = time.perf_counter()
        result: Any = func(*args, **kwargs)
        end_time: float = time.perf_counter()
        print(f"Took {(end_time - start_time):.4f} seconds")
        return result

    return timeit_wrapper


Tools: Utilities = Utilities()
CompileHandler: utils.CompiledFileHandler = utils.CompiledFileHandler()
MarkupType: TypeAlias = Union[Sequence[dt.JsonDict], dt.JsonDict]
VALID_KEYS: Final[Sequence[str]] = [
    MarkupKeys.UI, MarkupKeys.IMPORTS, 
    MarkupKeys.CONTROLS, MarkupKeys.HEADER
]
valid_imports: tuple[dt.ThirdPartyExtension, dt.UIImports] = (dt.ThirdPartyExtension, dt.UIImports)

class Compiler:

    __slots__ = (
        "control_settings",
        "code",
        "controls",
        "parsed_controls",
        "parsed_ui",
        "program",
        "used_controls",
        "routes",
        "custom_controls",
        "imports_path",
        "controls_registry",
        "are_registries_joined",
        "style_sheet",
        "dependent_refs",
        "params",
        "control_param_types"
    )

    def __init__(self, program_path: str, compile_path: str) -> NoReturn:
        self.params: dt.ParamGenerator = dt.ParamGenerator(program_path, compile_path)
        self.params.parse_extensions()
        self.imports_path: str = self.params.imports_path
        self.code: dt.JsonDict = self.params.ui_code
        self.style_sheet: opc.StyleSheet
        self.used_controls: set[str] = set([ControlKeys.VIEW])
        self.custom_controls: dt.ControlRegistryJsonScheme
        self.dependent_refs: opc.ControlDependencies = opc.ControlDependencies()
        self.are_registries_joined: bool = False
        self.controls_registry: dt.ControlRegistryJsonScheme = (
            dt.ControlRegistryJsonScheme()
        )
        self.routes: set[str] = set()
        self.controls: dt.ControlMap = dt.ControlMap()
        self.control_param_types: Mapping[str, dt.TypeHints] = {}
        self.control_settings: Mapping[str, Sequence[str]] = {}
        self.parsed_controls: dt.ParsedControls = {}
        self.parsed_ui: dt.ParsedUserInterface = {}
        self.setup()
    
    def setup(self) -> NoReturn:
        self.style_sheet: opc.StyleSheet = opc.StyleSheet(self.params.style_sheet)
        custom_controls: Sequence[dt.ControlRegisterInterface] = self.add_constant_controls(
            self.parse_custom_controls(self.params.custom_controls)
        )
        
        if custom_controls:
            self.custom_controls = ControlRegistryOperations.generate_dict(
                map(lambda control: dt.ControlRegistryModel(**control), custom_controls)
            )
    
    def parse_custom_controls(self, data: Sequence[dt.ExtensionType]) -> Sequence[dt.ControlRegisterInterface]:
        value: dt.ExtensionType
        func: Callable[[Any], bool] = lambda x: isinstance(
            x, valid_imports
        )
        
        return functools.reduce(
            operator.concat, 
            [value.extensions() for value in filter(func, data)]
        )

    def validate_imports(self, file_name: str, data: dt.JsonDict) -> NoReturn:
        keys: Sequence[str]

        if MarkupKeys.CONTROLS not in data:
            raise errors.InvalidMarkupFormatError(file_name, MarkupKeys.CONTROLS)
        keys = list(data.keys())

        try:
            keys.remove(MarkupKeys.CONTROLS)
        except:
            pass

        if len(keys) == 0: return
        
        raise errors.InvalidMarkupContainerError(file_name, keys[0])

    def validate_main_file(self) -> NoReturn:
        key: str

        for key in VALID_KEYS:
            if key not in self.code:
                raise errors.InvalidMarkupFormatError("ui.json", key)

        for key in self.code:
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
            
            if name not in control_scheme[ControlRegKeys.CONTROLS]:
                continue

            control = control_scheme[ControlRegKeys.CONTROL_TYPES][
                control_scheme[ControlRegKeys.CONTROLS].index(name)
            ]
            control_keys.add(name)
                
            self.controls[name] = getattr(
                import_module(control[ControlRegKeys.SOURCE], None), 
                control[ControlRegKeys.ATTR]
            )
            
            self.control_param_types[name] = utils.TypeHintSerializer.deserialize(
                control[ControlRegKeys.TYPE_HINTS]
            )
            
            self.control_settings[name] = control[ControlRegKeys.VALID_SETTINGS]

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

    def compile(self) -> NoReturn:
        self.__load_program()
        self.parsed_controls.update(
            self.__parse_controls(self.code[MarkupKeys.CONTROLS])
        )
        self.validate_main_file()
        self.__parse_ui(self.code[MarkupKeys.UI])
        
        self.dependent_refs.update_cache()
        
        self.params.save_program(
            dt.CompiledModel(
                self.parsed_controls, self.style_sheet,
                self.parsed_ui, self.controls,
                self.routes, self.control_settings, self.dependent_refs,
                self.control_param_types, self.params.action_code, 
                self.params.program_name
            )
        )
    
    def load_file(self, source: str) -> Sequence[dt.NamedControlDict]:
        program: io.TextIOWrapper
        file: Sequence[dt.NamedControlDict]
        path: str = os.path.join(self.imports_path, source)
        
        if not os.path.exists(path):
            return []
        
        with open(path, "r") as program:
            file = json.load(program)
            self.validate_imports(source, file)
            self.update_used_controls(file[MarkupKeys.CONTROLS])
            return file[MarkupKeys.CONTROLS]
            
        return []

    def __parse_imports(self) -> NoReturn:
        import_data: Sequence[dt.ImportDict] = self.code.get(
            MarkupKeys.IMPORTS, None
        )
        data: dt.JsonDict
        source: str
        paths: Sequence[str] = []
        json_data: Sequence[Sequence[dt.NamedControlDict]] = []

        if not import_data:
            return self.__load_controls()

        for data in import_data:
            source = data.get(ImportKeys.SOURCE, "")
            if not source:
                continue
            if utils.is_sequence_not_str(source):
                if ImportKeys.FROM not in data:
                    continue
                for i in source:
                    paths.append(os.path.join(data[ImportKeys.FROM], f"{i}.json"))
            else:
                paths.append(f"{source}.json")
                
        for path in paths:
            data = self.load_file(path)
            if not data:
                continue
            json_data.append(data)

        self.__load_controls()
        if not json_data:
            return

        for data in json_data:
            self.parsed_controls.update(self.__parse_controls(data))

    def update_used_controls(self, data: MarkupType) -> NoReturn:
        self.used_controls.update(
            Tools.find_values(
                data, ControlKeys.CONTROL_TYPE, 
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
                data[ControlKeys.VAR_NAME], 
                data.get(ControlKeys.SETTINGS, {})
            )
            parsed_data[data[ControlKeys.VAR_NAME]] = self.make_control_model(data)

        return parsed_data

    def parse_nest(self, data: dt.ControlSettings) -> dt.ControlSettings:
        key: str
        item: Mapping
        i: int
        
        if not data:
            return {}
        
        for key in Tools.get_keys_with_dict(data):
            if ControlKeys.CONTROL_TYPE not in data[key]:
                continue
            
            if data[key][ControlKeys.CONTROL_TYPE] in constants.MARKUP_SPECIFIC_CONTROLS:
                continue
            
            data[key] = self.make_nested_control(data[key])
        
        for key in Tools.get_keys_with_list(data):
            for i, item in filter(lambda x: isinstance(x[1], Mapping), enumerate(data[key])):
                if ControlKeys.CONTROL_TYPE not in item:
                    continue
                
                if item[ControlKeys.CONTROL_TYPE] in constants.MARKUP_SPECIFIC_CONTROLS:
                    continue
                
                data[key][i] = self.make_nested_control(item)
    
        return data

    def make_nested_control(self, data: Mapping) -> dt.NestedControlModel:
        control_name: str = data[ControlKeys.CONTROL_TYPE]
        return dt.NestedControlModel(
            control_name=control_name,
            control=self.controls[control_name],
            settings=self.parse_nest(
                self.param_filter(control_name, data)
            )
        )

    def make_control_model(self, data: dt.NamedControlDict) -> dt.ControlModel:
        control_name: str = data[ControlKeys.CONTROL_TYPE]
        return dt.ControlModel(
            control_name=control_name,
            name=data[ControlKeys.VAR_NAME],
            control=self.controls[control_name],
            settings=self.parse_nest(
                self.param_filter(control_name, data)
            )
        )
    
    def param_filter(self, name: str, data: dt.ControlDict) -> dt.ControlSettings:
        return Tools.valid_param_filter(
            data.get(ControlKeys.SETTINGS, {}), 
            self.control_settings[name], 
            ControlKeys.UNPACK
        )

    def __parse_ui(self, ui_data: Sequence[dt.RouteDict]) -> NoReturn:
        route_dict: dt.RouteDict
        data: tuple[str, dt.JsonDict]

        for route_dict in self.parse_iterator(ui_data, checks.RouteCheck):
            self.routes.add(route_dict[ControlKeys.ROUTE])
            self.dependent_refs.add_dependencies(
                route_dict[ControlKeys.ROUTE], 
                route_dict[ControlKeys.SETTINGS]
            )
            self.parsed_ui[route_dict[ControlKeys.ROUTE]] = opc.UIViews(
                route_dict[ControlKeys.ROUTE], 
                self.parse_nest(
                    self.param_filter(ControlKeys.VIEW, route_dict)
                )
            )

        self.__load_controls()
    
    def parse_iterator(self, data: Sequence[Mapping], checker: type[checks.Checker]) -> Generator[Mapping, None, None]:
        value: Mapping
        res: Union[Mapping, None]
        is_route: bool = checker == checks.RouteCheck
        
        for value in data:
            res = checker.correct(value, self)
            if not res: continue
            del res[MarkupKeys.SKIP]
            yield res


@timeit
def load_program(compiled_path: str, page: ft.Page) -> ft.Page:
    return Backend(
        CompileHandler.load(compiled_path), 
        page
    ).initialize()

