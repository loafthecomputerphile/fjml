from __future__ import annotations
from functools import partial
from copy import deepcopy
import operator, itertools
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
    Tools.multi_dict_get, items=[RefsKeys.REFS, RefsKeys.CODE_REFS]
)


class RefrenceBooleanParams:
    STYLING: tuple[str, ...] = (RefsKeys.REFS, RefsKeys.CODE_REFS, RefsKeys.STYLING)
    NO_STYLING: tuple[str, ...] = (RefsKeys.REFS, RefsKeys.CODE_REFS)


class Renderer:
    
    __slots__ = (
        "backend", "update", "get_attr",
        "set_attr", "has_attr", "change_route",
        "control_loader", "tools", "page", "references", "eparser",
        "use_bucket", "type_check", "get_ref",
        "control_names", "depth_count", "__loop_depth",
        "__loop_values", "unpack_function",
        "control_model_filter", "control_model_map"
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
        func = partial(operator.contains, valid_vars)
        for x in itertools.filterfalse(func, self._controls):
            self.set_attr(x)

    def init_controls(self) -> NoReturn:
        var_name: str
        for var_name in self._controls:
            self.control_names.append(var_name)
            if not self.has_attr(var_name):
                self.set_attr(var_name)
    
    def control_gen(self, names: Sequence[str]) -> Iterator[tuple[str, dt.ControlModel]]:
        x: str
        func = partial(operator.contains, self._controls)
        return [(x, self._controls[x]) for x in filter(func, names)]
    
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
        iterator: Sequence = self.tools.process_loop_itertor(
            self, data[LoopKeys.ITERATOR]
        )
        for value in iterator:
            control = deepcopy(data[LoopKeys.CONTROL])
            self.__loop_values[self.depth_count - 1] = value
            
            if loop_refs_check(control):
                reference = self.tools.parse_reference(self, control)
                if not reference: continue
                control_list.append(reference)
                continue
            
            content = control.get(ControlKeys.CONTROL_TYPE, None)
            call_name = control.get(EventKeys.CALL, None)
            if not (is_null_string(content) and is_null_string(call_name)):
                return []
            
            if content == ControlKeys.LOOP:
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
            control[ControlKeys.SETTINGS] = self.tools.search_and_sanitize(
                control.get(ControlKeys.SETTINGS, {}), 
                self.depth_count, self.__loop_values
            )
            return control
        
        return self.object_bucket.call_object(
            call_name,
            self.settings_object_parsers(
                self.tools.search_and_sanitize(
                    control.get(ControlKeys.SETTINGS, {}), 
                    self.depth_count,
                    self.__loop_values
                ),
                ignore=True
            )
        )

    def create_control(self, code: dt.ControlDict) -> dt.ControlType:
        control: dt.ControlType = self.get_control(code)
        
        return (
            control 
            if not callable(control) else
            control(
                **self.settings_object_parsers(
                    code.get(ControlKeys.SETTINGS, {}), 
                    self.control_settings[code[ControlKeys.CONTROL_TYPE]],
                    self.type_hints.get(code[ControlKeys.CONTROL_TYPE], {})
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
            valid_settings.append(ControlKeys.UNPACK)
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
            if self.tools.mass_any_contains(RefrenceBooleanParams.STYLING, settings[key]):
                self.call_references(settings, key, settings[key], True)
            elif ControlKeys.CONTROL_TYPE in settings[key]:
                self.settings_to_controls(settings, key, settings[key], True)
        
        for key in self.tools.get_keys_with_list(settings):
            for i, data in enumerate(settings[key]):
                if not isinstance(data, Mapping): 
                    continue
                if self.tools.mass_any_contains(RefrenceBooleanParams.NO_STYLING, data):
                    self.call_references(settings[key], i, data)
                elif ControlKeys.CONTROL_TYPE in data:
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
            if ref: container[key] = ref
            return
        
        if not use_style:
            return

        if RefsKeys.STYLING in data:
            container[key] = self.style_sheet.get_style(
                data[RefsKeys.STYLING]
            )
        
    def settings_to_controls(
        self,
        container: Union[Sequence, Mapping],
        key: Union[int, str],
        data: Mapping,
        use_loop: bool = False,
    ) -> bool:
        
        if ControlKeys.CONTROL_TYPE not in data:
            return
        
        if use_loop and data[ControlKeys.CONTROL_TYPE] == ControlKeys.LOOP:
            container[key] = self.run_ui_loop(data)
            self.depth_count, self.__loop_values = 0, []
            return

        new_data: Any = self.try_get_attribute(data)
        if new_data != constants.NULL:
            container[key] = new_data
            return

        container[key] = self.create_control(data)
        

    def events(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        key: str
        data: Any
        i: int
        
        for key in self.tools.get_keys_with_dict(settings):
            if EventKeys.ROUTE in settings[key]:
                self.eparser.route(key, settings[key], settings)
            elif EventKeys.FUNC in settings[key]:
                self.eparser.func(key, settings[key], settings)
            elif EventKeys.CALL in settings[key]:
                self.eparser.call(key, settings[key], settings)
            elif EventKeys.EVAL in settings[key]:
                self.eparser.eval(key, settings[key], settings)
        
        for key in self.tools.get_keys_with_list(settings):
            for i, data in enumerate(settings[key]):
                if not isinstance(data, Mapping): continue
                
                if EventKeys.CALL in data:
                    self.eparser.call(i, data, settings[key])
                elif EventKeys.EVAL in data:
                    self.eparser.eval(i, data, settings[key])

        return settings
    
    def get_control(self, data: dt.ControlDict) -> dt.ControlType:
        return self._control_map[data[ControlKeys.CONTROL_TYPE]]

    def try_get_attribute(self, data: dt.JsonDict) -> Any:
        return getattr(
            self.get_control(data), 
            data[ControlKeys.ATTR], 
            None
        ) if ControlKeys.ATTR in data else constants.NULL

