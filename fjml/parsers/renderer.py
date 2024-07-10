from __future__ import annotations
from functools import partial
from copy import deepcopy
import enum
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
    TypeVar,
    Iterator
)

import flet as ft

from .. import (
    data_types as dt,
    object_enums as onums,
    operation_classes as opc,
    utils,
    constants
)
if TYPE_CHECKING:
    from .builder import Backend

Tools: utils.Utilities = utils.Utilities()
NullOrStr: tuple[type, type] = (str, type(None))
ParsedLoopItem: TypeAlias = Union[ft.Control, dt.ControlDict]


class RefrenceBooleanParams(enum.Enum):
    STYLING: tuple[str, ...] = (onums.RefsKeys.REFS, onums.RefsKeys.CODE_REFS, onums.RefsKeys.STYLING)
    NO_STYLING: tuple[str, ...] = (onums.RefsKeys.REFS, onums.RefsKeys.CODE_REFS)


class LambdaHelpers:
    __slots__ = ("is_null_string", "control_model_filter", "control_model_map")
    def __init__(self, cls: Renderer) -> NoReturn:
        self.is_null_string: Callable[[Any], bool] = lambda obj: isinstance(obj, NullOrStr)
        self.control_model_filter = lambda name: name in cls._controls
        self.control_model_map = lambda name: (name, cls._controls[name])


loop_refs_check: Callable[[Mapping], str] = partial(
    Tools.multi_dict_get, items=[onums.RefsKeys.REFS, onums.RefsKeys.CODE_REFS]
)


class Renderer:
    
    __slots__ = (
        "backend", "update", "get_attr",
        "set_attr", "has_attr", "change_route",
        "control_loader", "tools", "page", "references", "eparser",
        "use_bucket", "type_check", "get_ref",
        "control_names", "depth_count", "__loop_depth",
        "__loop_values", "unpack_function",
        "control_model_filter", "control_model_map",
        "lambdas"
    )
    
    def __init__(self, backend: Backend) -> NoReturn:
        self.control_model_filter: Callable[[str], bool]
        self.control_model_map: Callable[[str], tuple[str, dt.ControlModel]]
        self.type_check: Callable[[dt.ControlSettings, dt.TypeHints], dt.ControlSettings]
        self.unpack_function: Callable[[dt.ControlSettings], dt.ControlSettings]
        self.backend: Backend = backend
        self.depth_count: int = 0
        self.__loop_depth: int = 0
        self.__loop_values: Sequence = []
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
        self.lambdas: LambdaHelpers = LambdaHelpers(self)
        
    
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
        x: str
        list(map(
            self.set_attr, 
            filter(
                lambda x: x not in valid_vars, 
                self._controls
            )
        ))

    def init_controls(self) -> NoReturn:
        var_name: str
        for var_name in self._controls:
            self.control_names.append(var_name)
            if not self.has_attr(var_name):
                self.set_attr(var_name)
    
    def control_gen(self, names: Sequence[str]) -> Iterator[tuple[str, dt.ControlModel]]:
        return map(
            self.lambdas.control_model_map, 
            filter(self.lambdas.control_model_filter, names)
        )
    
    def get_hints(self, name: str) -> dt.TypeHints:
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
            self.tools.find_values(
                control.get(onums.ControlKeys.SETTINGS, {}), 
                onums.RefsKeys.REFS
            )
        )
        return self.create_control(control)

    def register_controls(self, control: dt.ControlDict) -> NoReturn:
        self.control_loader.add_controls(
            self.tools.find_values(
                json_obj=control, 
                key=onums.ControlKeys.CONTROL_TYPE, 
                ignore=constants.MARKUP_SPECIFIC_CONTROLS
            )
        )

    def loop_init(self, data: dt.LoopDict) -> NoReturn:
        if not self.__loop_values:
            depth: int = data.get(onums.LoopKeys.DEPTH, 1)
            
            if not isinstance(depth, int):
                depth = 0
            
            self.__loop_depth = depth
            self.__loop_values = [None for _ in range(depth)]
            self.depth_count = 0

    def run_ui_loop(self, data: dt.LoopDict) -> Sequence[ParsedLoopItem]:
        control_list: Sequence[ParsedLoopItem] = []
        control: Mapping
        content: Union[str, None]
        value: Any
        call_name: Union[str, None]
        reference: Any
        
        self.loop_init(data)
        if not self.__loop_depth:
            return control_list
        
        self.depth_count += 1
        iterator: Sequence = self.tools.process_loop_itertor(self, data[onums.LoopKeys.ITERATOR])
        for value in iterator:
            control = deepcopy(data[onums.LoopKeys.CONTROL])
            self.__loop_values[self.depth_count - 1] = value
            
            if loop_refs_check(control):
                reference = self.tools.parse_reference(self, control)
                if not reference: continue
                control_list.append(reference)
            else:
                content = control.get(onums.ControlKeys.CONTROL_TYPE, None)
                call_name = control.get(onums.EventKeys.CALL, None)
                if not (self.lambdas.is_null_string(content) and self.lambdas.is_null_string(call_name)):
                    return []
                
                if content == onums.ControlKeys.LOOP:
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
            control[onums.ControlKeys.SETTINGS] = self.tools.search_and_sanitize(
                control.get(onums.ControlKeys.SETTINGS, {}), 
                self.depth_count, self.__loop_values
            )
            return control
        
        return self.get_attr(call_name)(
            **self.settings_object_parsers(
                self.tools.search_and_sanitize(
                    control.get(onums.ControlKeys.SETTINGS, {}), 
                    self.depth_count,
                    self.__loop_values
                ),
                ignore=True
            )
        )

    def create_control(self, code: dt.ControlDict) -> dt.ControlType:
        control: dt.ControlType = self._control_map[
            code[onums.ControlKeys.CONTROL_TYPE]
        ]
        
        return (
            control 
            if not callable(control) else
            control(
                **self.settings_object_parsers(
                    code.get(onums.ControlKeys.SETTINGS, {}), 
                    self.control_settings[code[onums.ControlKeys.CONTROL_TYPE]],
                    self.type_hints.get(code[onums.ControlKeys.CONTROL_TYPE], {})
                )
            )
        )
        
    
    def settings_object_parsers(
        self, settings: dt.ControlSettings, valid_settings: Sequence[str] = [], 
        types: dt.TypeHints = {}, ignore: bool = False
    ) -> dt.ControlSettings:
        data: Any
        i: int
        key: str
        
        if not settings:
            return {}
        
        if not ignore:
            valid_settings.append(onums.ControlKeys.UNPACK)
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
            if self.tools.mass_any_contains(RefrenceBooleanParams.STYLING.value, settings[key]):
                self.call_references(settings, key, settings[key], True)
            elif onums.ControlKeys.CONTROL_TYPE in settings[key]:
                self.settings_to_controls(settings, key, settings[key], True)
        
        for key in self.tools.get_keys_with_list(settings):
            for i, data in enumerate(settings[key]):
                if not isinstance(data, Mapping): continue
                
                if self.tools.mass_any_contains(RefrenceBooleanParams.NO_STYLING.value, data):
                    self.call_references(settings[key], i, data)
                elif onums.ControlKeys.CONTROL_TYPE in data:
                    self.settings_to_controls(settings[key], i, data)
        
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

        if data.get(onums.RefsKeys.STYLING, constants.NULL) != constants.NULL:
            container[key] = self.style_sheet.get_style(data[onums.RefsKeys.STYLING])
            return True

        return False

    def settings_to_controls(
        self,
        container: Union[Sequence, Mapping],
        key: Union[int, str],
        data: Mapping,
        use_loop: bool = False,
    ) -> bool:
        if data.get(onums.ControlKeys.CONTROL_TYPE, constants.NULL) == constants.NULL:
            return False
        
        if use_loop and data[onums.ControlKeys.CONTROL_TYPE] == onums.ControlKeys.LOOP:
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
            if onums.EventKeys.ROUTE in settings[key]:
                self.eparser.route(key, settings[key], settings)
            elif onums.EventKeys.FUNC in settings[key]:
                self.eparser.func(key, settings[key], settings)
            elif onums.EventKeys.CALL in settings[key]:
                self.eparser.call(key, settings[key], settings)
            elif onums.EventKeys.EVAL in settings[key]:
                self.eparser.eval(key, settings[key], settings)
        
        for key in self.tools.get_keys_with_list(settings):
            for i, data in enumerate(settings[key]):
                if not isinstance(data, Mapping): continue
                
                if onums.EventKeys.CALL in data:
                    self.eparser.call(i, data, settings[key])
                elif onums.EventKeys.EVAL in data:
                    self.eparser.eval(i, data, settings[key])

        return settings

    def try_get_attribute(self, data: dt.JsonDict) -> tuple[Any, bool]:
        if data.get(onums.ControlKeys.ATTR, constants.NULL) == constants.NULL:
            return data, False

        attr: Any = getattr(
            self._control_map[data[onums.ControlKeys.CONTROL_TYPE]], 
            data[onums.ControlKeys.ATTR], 
            constants.NULL
        )
        if attr == constants.NULL:
            return None, True

        return attr, True

