from __future__ import annotations
from functools import partial
from copy import deepcopy
from typing import (
    Any,
    Union,
    Callable,
    NoReturn,
    Sequence,
    Mapping,
    Generator,
    TypeAlias,
    TYPE_CHECKING,
    TypeVar
)

import flet as ft

from .. import (
    data_types as dt,
    operation_classes as opc,
    utils,
    constants
)
if TYPE_CHECKING:
    from .builder import Backend

Tools: utils.Utilities = utils.Utilities()
NullOrStr: tuple[type, type] = (str, type(None))
is_null_string: Callable[[Any], bool] = lambda obj: isinstance(obj, NullOrStr)


loop_refs_check: Callable[[Mapping], str] = partial(
    Tools.multi_dict_get, items=["refs", "code_refs"]
)

ParsedLoopItem: TypeAlias = Union[ft.Control, dt.ControlDict]

class Renderer:
    
    __slots__ = (
        "backend", "update", "get_attr",
        "set_attr", "has_attr", "change_route",
        "control_loader", "tools", "page", "references", "eparser",
        "use_bucket", "type_check", "get_ref",
        "control_names", "depth_count", "__loop_depth",
        "__loop_values", "unpack_function"
    )

    def __init__(self, backend: Backend) -> NoReturn:
        self.type_check: Callable[[dt.ControlSettings, dt.TypeHints], dt.ControlSettings]
        self.unpack_function: Callable[[dt.ControlSettings], dt.ControlSettings]
        self.depth_count: int = 0
        self.__loop_depth: int = None
        self.__loop_values: Sequence = None
        self.backend: Backend = backend
        self.get_attr: Callable[[Backend, str, Any], Any] = self.backend.get_attr
        self.set_attr: Callable[[Backend, str, Any], NoReturn] = self.backend.set_attr
        self.has_attr: Callable[[Backend, str], bool] = self.backend.has_attr
        self.control_loader: opc.ControlLoader = opc.ControlLoader(self.backend)
        self.tools: utils.Utilities = self.backend.tools
        self.get_ref: Callable[[Mapping], Any] = opc.Reference(self).get_ref
        self.eparser: opc.EventParser = opc.EventParser(self)
        self.use_bucket: Sequence[str] = []
        self.control_names: Sequence[str] = []
        self.unpack_function = opc.Unpacker(self).unpack
        self.type_check = opc.TypeCheck.type_rectification
    
    @property
    def property_bucket(self) -> opc.PropertyContainer:
        return self.backend.property_bucket
    
    @property
    def object_bucket(self) -> opc.ObjectContainer:
        return self.backend.object_bucket
    
    @property
    def style_sheet(self) -> opc.StyleSheet:
        return self.backend.style_sheet
    
    @property
    def compiled_program(self) -> dt.CompiledModel:
        return self.backend.compiled_program
    
    @property
    def _ui(self) -> Mapping[str, dt.UIViews]:
        return self.backend.compiled_program.ui
    
    @property
    def _control_map(self) -> dt.ControlMap:
        return self.backend.compiled_program.control_map
    
    @property
    def _controls(self) -> dt.ParsedControls:
        return self.backend.compiled_program.controls
    
    @property
    def type_hints(self) -> dt.TypedDict:
        return self.backend.compiled_program.type_hints
        
    @property
    def loop_values(self) -> Sequence:
        return self.__loop_values
    
    @property
    def control_settings(self) -> Sequence[str]:
        return self.backend.compiled_program.control_settings

    def get_dependent_controls(self) -> Sequence[str]:
        data: Sequence[str] = self.use_bucket
        data.extend(self.backend.preserve_control_bucket.data)
        return data

    def clear_unecessary(self, valid_vars: Sequence[str] = []) -> NoReturn:
        var_name: str
        for var_name in self._controls.keys():
            if var_name not in valid_vars:
                self.set_attr(var_name)

    def init_controls(self) -> NoReturn:
        var_name: str
        for var_name in self._controls.keys():
            self.control_names.append(var_name)
            if not self.has_attr(var_name):
                self.set_attr(var_name)
    
    def control_gen(self, names: Sequence[str]) -> Generator[tuple[str, dt.ControlModel], None, None]:
        name: str
        return ((name, self._controls[name]) for name in names if name in self._controls)
    
    def get_hints(self, name: str) -> Mapping[str, type]:
        return self.type_hints.get(name, {})

    def create_controls(self) -> NoReturn:
        model: dt.ControlModel
        var_name: str
        data: Sequence[str] = self.get_dependent_controls()
        self.clear_unecessary(data)
        
        for var_name, model in self.control_gen(data):
            self.set_attr(
                var_name, 
                model.control(
                    **self.settings_object_parsers(
                        model.settings, 
                        model.valid_settings,
                        self.get_hints(model.control_name)
                    )
                )
            )

    def ui_parser(self, control: dt.ControlDict) -> dt.ControlType:
        self.register_controls(control)
        self.backend.preserve_control_bucket.group_add(
            self.tools.find_values(control.get("settings", {}), "refs")
        )
        return self.create_control(control)

    def register_controls(self, control: dt.ControlDict) -> NoReturn:
        self.control_loader.add_controls(
            self.tools.find_values(
                json_obj=control, 
                key="control_type", 
                ignore=constants.MARKUP_SPECIFIC_CONTROLS
            )
        )

    def loop_init(self, data: dt.LoopDict) -> NoReturn:
        if not self.__loop_values:
            depth: int = data.get("depth", 1)
            
            if not isinstance(depth, int):
                depth = 0
            
            self.__loop_depth = depth
            self.__loop_values = [None for _ in range(depth)]
            self.depth_count = 0

    def run_ui_loop(self, data: dt.LoopDict) -> Sequence[ParsedLoopItem]:
        control_list: Sequence[ParsedLoopItem] = []
        control: Mapping
        content: str
        value: Any
        call_name: str
        reference: Any
        
        self.loop_init(data)
        if not self.__loop_depth:
            return []
        
        self.depth_count += 1
        iterator: Sequence = self.tools.process_loop_itertor(self, data["iterator"])
        for value in iterator:
            control = deepcopy(data["control"])
            self.__loop_values[self.depth_count - 1] = value
            
            if loop_refs_check(control):
                reference = self.tools.parse_reference(self, control)
                if not reference: continue
                control_list.append(reference)
            else:
                content = control.get("control_type", None)
                call_name = control.get("call", None)
                if not (is_null_string(content) and is_null_string(call_name)):
                    return []
                
                if content == "loop":
                    return_val.append(self.run_ui_loop(control))
                    continue
                
                control_list.append(
                    self.generate_list_control(
                        call_name,
                        control
                    )
                )

        return control_list

    def generate_list_control(self, call_name: str, control: dt.JsonDict) -> ParsedLoopItem:
        
        if not call_name:
            control["settings"] = self.tools.search_and_sanitize(
                control.get("settings", {}), self.depth_count, self.__loop_values
            )
            return control
        
        return self.get_attr(call_name)(
            **self.settings_object_parsers(
                self.tools.search_and_sanitize(
                    control.get("settings", {}), 
                    self.depth_count,
                    self.__loop_values
                ),
                ignore=True
            )
        )

    def create_control(self, code: dt.ControlDict) -> dt.ControlType:
        control: dt.ControlType = self._control_map[
            code["control_type"]
        ]
        
        return (
            control 
            if not callable(control) else
            control(
                **self.settings_object_parsers(
                    code.get("settings", {}), 
                    self.control_settings[code["control_type"]],
                    self.type_hints.get(code["control_type"], {})
                )
            )
        )
        
    
    def settings_object_parsers(
        self, settings: dt.ControlSettings, valid_settings: Sequence[str] = [], types: dt.TypeHints = {}, ignore: bool = False
    ) -> dt.ControlSettings:
        data: Any
        i: int
        key: str
        
        if not ignore:
            valid_settings.append("unpack")
            
            settings = self.tools.valid_param_filter(
                settings, valid_settings
            )
        
        if not settings:
            return {}
        
        settings = self.events(
            self.unpack_function(
                settings
            )
        )
        
        for key in self.tools.get_keys_with_dict(settings):
            if self.call_references(settings, key, settings[key], True):
                pass
            elif self.settings_to_controls(settings, key, settings[key], True):
                pass
        
        for key in self.tools.get_keys_with_list(settings):
            for i, data in enumerate(settings[key]):
                if not isinstance(data, Mapping):
                    pass
                elif self.call_references(settings[key], i, data):
                    pass
                elif self.settings_to_controls(settings[key], i, data):
                    pass
        
        if not types:
            return settings
        return self.type_check(settings, types)

    def call_references(
        self,
        container: Union[Sequence, Mapping],
        key: Union[int, str],
        data: Mapping,
        use_style: bool = False,
    ) -> bool:
        
        if self.tools.refs_type(data):
            ref: Any = self.get_ref(data)
            if not ref:
                return True
            container[key] = ref
            return True
        
        if not use_style:
            return False

        if data.get("styling", constants.NULL) != constants.NULL:
            container[key] = self.style_sheet.get_style(data["styling"])
            return True

        return False

    def settings_to_controls(
        self,
        container: Union[Sequence, Mapping],
        key: Union[int, str],
        data: Mapping,
        use_loop: bool = False,
    ) -> bool:
        if data.get("control_type", constants.NULL) == constants.NULL:
            return False
        
        if use_loop:
            if data["control_type"] == "loop":
                container[key] = self.run_ui_loop(data)
                self.depth_count, self.__loop_values = 0, []
                return True

        container[key], change = self.try_get_attribute(data)
        if change:
            return True

        container[key] = self.create_control(data)
        if not isinstance(container[key], Mapping):
            return True

        return False

    def events(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        key: str
        data: Any
        i: int
        
        for key in self.tools.get_keys_with_dict(settings):
            if self.eparser.route(key, settings[key], settings):
                pass
            elif self.eparser.func(key, settings[key], settings):
                pass
            elif self.eparser.call(key, settings[key], settings):
                pass
            elif self.eparser.eval(key, settings[key], settings):
                pass
        
        for key in self.tools.get_keys_with_list(settings):
            for i, data in enumerate(settings[key]):
                if not isinstance(data, Mapping):
                    pass
                elif self.eparser.call(key, data, settings):
                    pass
                elif self.eparser.eval(key, data, settings):
                    pass

        return settings

    def try_get_attribute(self, data: dt.JsonDict) -> tuple[Any, bool]:
        if data.get("attr", constants.NULL) == constants.NULL:
            return data, False

        attr: Any = getattr(
            self._control_map[data["control_type"]], 
            data["attr"], 
            constants.NULL
        )
        if attr == constants.NULL:
            return None, True

        return attr, True

