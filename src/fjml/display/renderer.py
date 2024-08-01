from __future__ import annotations
from functools import partial
from copy import deepcopy
import operator, itertools
from typing import (
    Any,
    Union,
    Callable,
    Sequence,
    Mapping,
    TypeAlias,
    TYPE_CHECKING,
    Iterator,
    Generator
)

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

import flet as ft

from ..object_enums import *
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
ParsedLoopItem: TypeAlias = Union[ft.Control, dt.ControlDict]
is_null_string: Callable[[Any], bool] = lambda obj: isinstance(obj, NullOrStr)
loop_refs_check: Callable[[Mapping], str] = partial(
    Tools.multi_dict_get, items=(
        RefsKeys.REFS, RefsKeys.CODE_REFS
    )
)



class ReferenceBooleanParams:
    STYLING: tuple[str, ...] = (RefsKeys.REFS, RefsKeys.CODE_REFS, RefsKeys.STYLING)
    NO_STYLING: tuple[str, ...] = (RefsKeys.REFS, RefsKeys.CODE_REFS)


class Renderer:
    
    __slots__ = (
        "backend", "update", "get_attr",
        "set_attr", "has_attr", "change_route",
        "control_loader", "tools", "page", "references", "event_parsers",
        "use_bucket", "type_check", "get_ref",
        "control_names", "depth_count", "__loop_depth",
        "__loop_values", "unpack_function",
        "control_model_filter", "control_model_map",
        "ref_bool_params", "sanitizer", "list_parse_filter_func"
    )
    
    def __init__(self, backend: Backend) -> NoReturn:
        self.control_model_filter: Callable[[str], bool]
        self.control_model_map: Callable[[str], tuple[str, dt.ControlModel]]
        self.type_check: Callable[[dt.ControlSettings, dt.TypeHints], dt.ControlSettings]
        self.unpack_function: Callable[[dt.ControlSettings], dt.ControlSettings]
        self.ref_bool_params: ReferenceBooleanParams = ReferenceBooleanParams()
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
        self.event_parsers: opc.EventParser = opc.EventParser(self)
        self.use_bucket: Sequence[str] = []
        self.control_names: Sequence[str] = []
        self.unpack_function = opc.Unpacker(self).unpack
        self.type_check = opc.TypeCheck().type_rectification
        self.list_parse_filter_func: Callable[[tuple[int, Any]], bool] = lambda x: (
            isinstance(x[1], (Mapping, dt.NestedControlModel))
        )
    
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
    def _ui(self) -> Mapping[str, opc.UIViews]:
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
    def control_settings(self) -> Mapping[str, Sequence[str]]:
        return self.backend.compiled_program.control_settings

    def get_dependent_controls(self) -> Sequence[str]:
        x: str
        data: Sequence[str] = self.use_bucket
        data.extend(self.backend.preserve_control_bucket.data)
        
        for x in itertools.filterfalse(partial(operator.contains, data), self._controls):
            self.set_attr(x)
            
        return data
    
    def init_controls(self) -> NoReturn:
        var_name: str
        for var_name in self._controls:
            self.control_names.append(var_name)
            if not self.has_attr(var_name):
                self.set_attr(var_name)
    
    def control_gen(self) -> Generator[tuple[str, dt.ControlModel], None, None]:
        x: str
        return (
            (x, self._controls[x])
            for x in filter(partial(operator.contains, self._controls), self.get_dependent_controls())
        )
        
    
    def create_controls(self) -> NoReturn:
        control: dt.ControlModel
        var_name: str
        
        for var_name, control in self.control_gen():
            self.set_attr(
                var_name, control.build(
                    self.settings_object_parsers
                )
            )

    def ui_parser(self, control: dt.ControlDict) -> dt.ControlType:
        self.register_controls(control)
        self.backend.preserve_control_bucket.group_add(
            self.tools.find_values(
                control.get(ControlKeys.SETTINGS, {}), 
                RefsKeys.REFS
            )
        )
        return self.create_control(control)

    def register_controls(self, control: dt.ControlDict) -> NoReturn:
        self.control_loader.add_controls(
            self.tools.find_values(
                json_obj=control, 
                key=ControlKeys.CONTROL_TYPE, 
                ignore=constants.MARKUP_SPECIFIC_CONTROLS
            )
        )

    def loop_init(self, data: dt.LoopDict) -> NoReturn:
        if not self.__loop_values:
            depth: int = data.get(LoopKeys.DEPTH, 1)
            if not isinstance(depth, int):
                depth = 0

            self.__loop_depth = depth
            self.__loop_values = [None for _ in range(depth)]
            self.depth_count = 0

    def run_ui_loop(self, data: dt.LoopDict) -> Sequence[ParsedLoopItem]:
        control_list: Sequence[ParsedLoopItem] = []
        control: Mapping
        call_name: Union[str, None]
        content: Union[str, None]
        value: Any
        reference: Any
        
        self.loop_init(data)
        if not self.__loop_depth:
            return control_list
        
        self.depth_count += 1
        iterator: Sequence = self.tools.process_loop_iterator(
            self, data[LoopKeys.ITERATOR]
        )
        for value in iterator:
            control = deepcopy(data[LoopKeys.CONTROL])
            self.__loop_values[self.depth_count - 1] = value
            
            if loop_refs_check(control):
                reference = self.tools.parse_reference(self, control)
                if not reference: 
                    continue
                control_list.append(reference)
                continue
            
            content = control.get(ControlKeys.CONTROL_TYPE, None)
            call_name = control.get(EventKeys.CALL, None)
            if not content and not call_name:
                return []
            
            if content == ControlKeys.LOOP:
                return []
            
            control_list.append(
                self.generate_list_control(
                    call_name, content, control
                )
            )

        return control_list

    def generate_list_control(self, call_name: str, content: str, control: dt.JsonDict) -> ParsedLoopItem:
        if content:
            control[ControlKeys.SETTINGS] = self.tools.search_and_sanitize(
                control.get(ControlKeys.SETTINGS, {}), 
                self.depth_count, self.__loop_values
            )
            return self.create_control(control)
        
        return self.object_bucket.call_object(
            call_name, 
            self.settings_object_parsers(
                self.tools.search_and_sanitize(
                    control.get(ControlKeys.SETTINGS, {}), 
                    self.depth_count, self.__loop_values
                ), 
                ignore=True
            )
        )

    def create_control(self, code: dt.ControlDict) -> dt.ControlType:
        control: dt.ControlType = self._control_map[
            code[ControlKeys.CONTROL_TYPE]
        ]
        
        if not callable(control):
            return control
        
        return control(
            **self.settings_object_parsers(
                code.get(ControlKeys.SETTINGS, {}), 
                self.control_settings[code[ControlKeys.CONTROL_TYPE]],
                code[ControlKeys.CONTROL_TYPE]
            )
        )
    
    def settings_object_parsers(
        self, settings: dt.ControlSettings, valid_settings: Sequence[str] = [], 
        types: str = "", ignore: bool = False
    ) -> dt.ControlSettings:
        data: Union[Mapping, dt.ControlDict, dt.NestedControlModel]
        key: str
        i: int
        
        if not ignore:
            if not settings: return {}
            settings = self.tools.valid_param_filter(
                settings, valid_settings, ControlKeys.UNPACK
            )
        
        if not settings:
            return {}
        
        settings = self.events(
            self.unpack_function(
                settings
            )
        )
        
        for key, data in filter(lambda x: isinstance(x[1], dt.NestedControlModel), settings.items()):
            settings[key] = data.build(
                self.settings_object_parsers
            )
        
        for key in self.tools.get_keys_with_dict(settings):
            if self.tools.mass_any_contains(self.ref_bool_params.STYLING, settings[key]):
                self.call_references(settings, key, settings[key], True)
            elif ControlKeys.CONTROL_TYPE in settings[key]:
                self.settings_to_controls(settings, key, settings[key], True)
        
        for key in self.tools.get_keys_with_list(settings):
            for i, data in filter(self.list_parse_filter_func, enumerate(settings[key])):
                if isinstance(data, dt.NestedControlModel):
                    settings[key][i] = data.build(
                        self.settings_object_parsers
                    )
                elif self.tools.mass_any_contains(self.ref_bool_params.NO_STYLING, data):
                    self.call_references(settings[key], i, data)
                elif ControlKeys.CONTROL_TYPE in data:
                    self.settings_to_controls(settings[key], i, data)
        
        return self.type_check(
            settings, 
            self.type_hints.get(types, {})
        )

    def call_references(
        self,
        container: Union[Sequence, Mapping],
        key: Union[int, str],
        data: Mapping,
        use_style: bool = False,
    ) -> bool:
        
        if use_style:
            if RefsKeys.STYLING in data:
                container[key] = self.style_sheet.get_style(
                    data[RefsKeys.STYLING]
                )
                return
        
        ref: Any = self.get_ref(data)
        if ref: 
            container[key] = ref
        
    def settings_to_controls(
        self,
        container: Union[Sequence, Mapping],
        key: Union[int, str],
        data: Mapping,
        use_loop: bool = False,
    ) -> bool:
        
        if use_loop:
            if data[ControlKeys.CONTROL_TYPE] == ControlKeys.LOOP:
                container[key] = self.run_ui_loop(data)
                self.depth_count = 0
                self.__loop_values.clear()
                return
        
        new_data: Any = self.try_get_attribute(data)
        if new_data:
            container[key] = new_data
            return

        container[key] = self.create_control(data)

    def events(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        key: str
        data: Mapping
        i: int
        
        for key in self.tools.get_keys_with_dict(settings):
            if EventKeys.ROUTE in settings[key]:
                self.event_parsers.route(key, settings[key], settings)
            elif EventKeys.FUNC in settings[key]:
                self.event_parsers.func(key, settings[key], settings)
            elif EventKeys.CALL in settings[key]:
                self.event_parsers.call(key, settings[key], settings)
            elif EventKeys.EVAL in settings[key]:
                self.event_parsers.eval(key, settings[key], settings)
        
        for key in self.tools.get_keys_with_list(settings):
            for i, data in filter(lambda x: isinstance(x[1], Mapping), enumerate(settings[key])):
                if EventKeys.CALL in data:
                    self.event_parsers.call(i, data, settings[key])
                elif EventKeys.EVAL in data:
                    self.event_parsers.eval(i, data, settings[key])

        return settings
    
    def try_get_attribute(self, data: dt.JsonDict) -> Any:
        if ControlKeys.ATTR in data:
            return getattr(
                self._control_map[data[ControlKeys.CONTROL_TYPE]], 
                data[ControlKeys.ATTR], 
                None
            )

