import asyncio
from functools import partial
from types import MethodType
import traceback
import inspect
import copy
from typing import (
    Any, Optional, 
    Union, Callable,
    Type, NoReturn,
    Iterator, Final
)

import nest_asyncio
import flet as ft

from .. import (
    error_types as errors,
    data_types as dt, 
    utils,
    constants
)

nest_asyncio.apply()

def attribute_filter(data: tuple[str, Any]) -> bool:
    return not data[0].startswith('_') and not inspect.ismethod(data[1])

attribute_filter_func: Callable[[Any], list[str]] = lambda obj: list(dict(filter(attribute_filter, inspect.getmembers(obj))).keys())

NULL: Final[str] = "<NULL>"


def validate_index(data: dict, depth_count: int, is_ref: bool=False) -> Optional[bool]:
    types: str
    val: Any
    
    types = data.get("control_type", None)
    if (is_ref and types != "loop_index"):
        raise ValueError("References with dictionaries must always be a loop_index")
    val = data.get("idx", None) 
    if not val:
        raise KeyError("idx must exist inside a loop_index type")
    if not isinstance(val, list):
        raise ValueError(f"idx must be of type list, recieved a type of {type(val)}")
    if len(val) != 2:
        raise ValueError(f"loop_index key idx length must be of size 2, recieved size of {len(val)} instead")
    if val[0] >= depth_count:
        raise ValueError("the first element in idx is out of bounds")


def parse_reference(cls, content: Union[dict, str], value: Any, depth_count: int, loop_values: list) -> Any:
    idx: int
    vals: Any
    data: dict[str, Any]
    
    if not (isinstance(content, dict) or isinstance(content, str)):
        raise ValueError("Refereences must be dictionaries or strings inside loops")
    
    if isinstance(content, str):
        return cls.get_attr(content)
    
    validate_index(content, depth_count, True)
    
    idx = content["idx"]
    
    val = loop_values[idx[0]]
    data = {"ref": val[idx[1]] if isinstance(value, list) else val}
    
    if cls.check_for_reference(data):
        return cls.get_attr(data["ref"])


def sanatize(data: dict, depth_count: int, loop_values: list) -> int:
    idx: int
    vals: Any
    
    validate_index(data, depth_count)
    
    idx = data["idx"]
    vals = loop_values[idx[0]]
    comparison: bool = isinstance(vals, list) or isinstance(vals, tuple)
    return vals[idx[1]] if comparison else vals


def process_loop_itertor(cls: Any, iterator_value: Union[dict[str, Any], list[Any]]) -> Iterator:
    value: Any
    
    if isinstance(iterator_value, dict):
        value = iterator_value.get("range", None)
        if value and isinstance(value, list):
            for i in value:
                if not isinstance(i, int):
                    raise ValueError("Loop ranges must only contain integers")
            if len(value) in constants.RANGE_PARAM_LENGTH:
                return range(*value)
            
        value = iterator_value.get("ref", None)
        if not value:
            raise ValueError(f"an iterator must be a a reference or a range")
        return cls.get_attr(value)
    elif isinstance(iterator_value, list):
        return iterator_value
    
    raise ValueError()


def search_and_sanitize(data: Union[dict[str, Any], list[Any]], sanitize_func: Callable, depth_count: int, loop_values: list[Any]) -> Union[dict[str, Any], list[Any]]:
    result: Union[dict[str, Any], list[Any]]
    key: str
    item: Any
    value: Any
    
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                if value.get("control_type") == "loop_index":
                    new_value = sanitize_func(value, depth_count, loop_values)
                    result[key] = new_value
                else:
                    result[key] = search_and_sanitize(value, sanitize_func, depth_count, loop_values)
            elif isinstance(value, list):
                result[key] = [search_and_sanitize(item, sanitize_func, depth_count, loop_values) for item in value]
            else:
                result[key] = value
        return result
    elif isinstance(data, list):
        return [search_and_sanitize(item, sanitize_func, depth_count, loop_values) for item in data]
    else:
        return data


class Renderer:
    
    def __init__(self, display: "Build", compiled_program: dt.CompiledModel) -> NoReturn:
        self.display: "Build" = display
        self.update: MethodType = self.display.update
        self.get_attr: MethodType = self.display.get_attr
        self.set_attr: MethodType = self.display.set_attr
        self.change_route: MethodType = self.display.change_route
        self.style_sheet: dt.StyleSheet = self.display.style_sheet
        self.tools: utils.Utilities = self.display.tools
        self.page: ft.Page = self.display.page
        self.compiled_program: dt.CompiledModel = compiled_program
        self.control_bundles: dict[str, dt.ControlBundle] = dt.TypeDict({}, dt.ControlBundle)
        self._controls: dt.ParsedControls = self.compiled_program.controls
        self._ui: dict[str, dt.UserInterfaceViews] = self.compiled_program.ui
        self._bundle_names: set[str] = self.compiled_program.control_bundles
        self._control_map: dt.ControlMap = self.compiled_program.control_map
        self._control_awaitable: dt.ControlMap = self.compiled_program.control_awaitable
        self._valid_routes: list[str] = self.compiled_program.routes
        self.control_names: list[str] = list()
        self.__loop_depth: Optional[int] = None
        self.__loop_values: Optional[list[Any]] = None
        self.depth_count: int = 0
        self.initialized = True
    
    def bundle_control(self, bundle_name: str, var_name: str) -> NoReturn:
        """Adds flet control to already existing control bundle
        N.B. bundle must already exist

        Args:
            bundle_name (str): name of control bundle
            var_name (str): name variable to add to said control bundle

        Returns:
            NoReturn
        """
        errors.ConditionalError.value_error(
            (bundle_name not in self._bundle_names),
            f"bundle with name, {bundle_name}, can not be found")
        
        errors.ConditionalError.value_error(
            (var_name not in attribute_filter_func(self)),
            f"Attribute, {var_name}, is not defined")
        
        errors.ConditionalError.type_error(
            (not isinstance(self.set_attr(var_name), ft.Control)),
            f"Attribute, {var_name}, is not a ft.Control type")
        
        if bundle_name not in self.control_bundles:
            self.control_bundles[bundle_name] = dt.ControlBundle(
                [var_name], self.get_attr
            )
            return
        
        self.control_bundles[bundle_name].add(var_name)
    
    def create_controls(self) -> NoReturn:
        """creates a flet control and sets its variable name\
            and bundle group from fjml control containers
        
        Returns:
            NoReturn
        """
        settings: dt.ControlSettings
        bundle_name: str
        control: ft.Control
        control_model: dt.ControlModel
        var_name: str
        
        for var_name, control_model in self._controls.items():
            bundle_name = control_model.bundle_name
            
            settings = self.parse_controls(control_model.settings)
            
            if control_model.control_name == "ref":
                self.control_names.append(var_name)
                self.set_attr(var_name, settings)
                continue
            
            if self._control_awaitable.get(control_model.control_name, None):
                control = asyncio.run(control_model.control(**settings))
            else:
                control = control_model.control(**settings)
            
            self.control_names.append(var_name)
            self.set_attr(var_name, control)
            
            if bundle_name in self._bundle_names:
                self.bundle_control(bundle_name, var_name)
    
    def get_bundle(self, bundle_name: str) -> dt.ControlBundle:
        errors.ConditionalError.value_error((bundle_name not in self._bundle_names), 
                                    f"bundle_name {bundle_name} was never used")
        return self.control_bundles[bundle_name]
    
    def action_ui_parser(self, control: dt.ControlDict) -> ft.Control:
        """A method to generate flet controls from fjml written as python dictionaries
        
        Examples:
            >>> self.hello_world = action_ui_parser({
                    "control_type":"Text",
                    "settings":{
                        "value":"Hello World"
                    }
                })

        Args:
            control (dt.ControlDict): a python dictionary in fjml format intended to be converted into a control

        Returns:
            ft.Control: generated control
        """
        return self.parsed_control_maker(control)
    
    def parse_controls(self, data: dt.ControlSettings) -> dt.ControlSettings:
        """A method which parses the settings of an fjml control.
        It then converts it into python objects to be used in flet controls
        
        Args:
            data (dt.ControlSettings): the control settings to be parsed into python code

        Returns:
            dt.ControlSettings: completely parsed settings fit to be used in flet controls
        """
        i: int
        settings: dt.ControlSettings
        obj: dt.JsonDict
        
        data = self.settings_object_parsers(data)
        
        if not data.get("controls", False):
            return data
        
        if len(data["controls"]) == 0:
            return data
        
        controls: list[ft.Control] = dt.TypedList([ft.Control(visible=False) for _ in data["controls"]], ft.Control)
        
        for i, obj in enumerate(data["controls"]):
            
            if isinstance(obj, ft.Control):
                controls[i] = obj
                continue
            
            errors.ConditionalError.type_error(
                not isinstance(obj, dict),
                f"list items of key, control, must be of type dict or ft.Control. Recieved type {type(obj)} instead")
            
            
            if self.check_for_reference(obj):
                controls[i] = self.get_attr(obj["ref"])
                continue
            
            try:
                controls[i] = self.parsed_control_maker(obj)
            except AttributeError as e:
                print(obj)
                raise e
        
        data["controls"] = controls
        return data
    
    def check_for_reference(self, obj: dict[str, Any], use_controls: bool = True) -> bool:
        """A method which checks if a reference is valid and exists.
        controls are deemed to exist if they are either already cantrols named in a fjml file or are defined in a method
        
        Args:
            obj (dict[str, Any]): any form of python dictionary
            use_controls (bool): weather to see if a control is named in a fjml file or is present in the class at all

        Returns:
            bool: whether a object can be read as a reference or not
        """
        res = obj.get('ref', None)
        
        if not res:
            return False
        
        errors.ConditionalError.value_error(
            (res not in self.control_names and use_controls),
            f"value, {res}, was called before assignment or does not exist")
        errors.ConditionalError.value_error(
            (res not in attribute_filter_func(self.display)), f"value, {res}, does not exist")
        
        return True
    
    def parsed_control_maker(self, code: dt.ControlDict) -> ft.Control:
        """creates a control from a dt.ControlDict model which is basically a fjml defined control
        
        Args:
            code (dt.ControlDict): an fjml defined control

        Returns:
            ft.Control: the created control
        """
        return self.create_control(
            code["control_type"],
            self.parse_controls(
                code.get("settings", {})
            )
        )
    
    def loop_init(self, data: dt.LoopDict) -> NoReturn:
        """initializes the fjml loop for single/nested loops
        
        Args:
            data (dt.LoopDict): an fjml defined loop model

        Returns:
            NoReturn
        """
        if not self.__loop_values:
            depth: int = data.get("depth", 1)
            
            errors.ConditionalError.key_error(
                (not depth), 
                "Key, depth, must be defined inside first loop")
            
            errors.ConditionalError.type_error(
                (not isinstance(depth, int)), 
                f"Depth must be of type integer. recieved type {type(depth)} instead")
            
            self.__loop_depth = depth
            self.__loop_values = [None for _ in range(depth)]
            self.depth_count = 0
    
    def run_ui_loop(self, data: dt.LoopDict) -> list[ft.Control]:
        """runs the fjml loop for single/nested loops
        N.B loops can only be used inside controls
        
        Args:
            data (dt.LoopDict): an fjml defined loop model

        Returns:
            list[ft.Control]: generated loops to be used inside controls
        """
        control_list: list[ft.Control] = dt.TypedList([], ft.Control)
        control: dict
        content: str
        settings: dt.ControlSettings
        value: Any
        
        iterator: Iterator[Any] = process_loop_itertor(self, data["iterator"])
        
        self.loop_init(data)
        
        self.depth_count+=1
        depth_count: int = self.depth_count
        
        for value in iterator:
            control = copy.deepcopy(data["control"])
            self.__loop_values[depth_count-1] = value
            
            content = control.get("ref", None)
            if content:
                control_list.append(
                    parse_reference(
                        self, content, value, depth_count, self.__loop_values
                    )
                )
                continue
            
            content = control.get("control_type", None)
            is_callable = control.get("call", None)
            if not content and not is_callable:
                raise ValueError("loop content has to be a reference, a control type or a function call")
            
            if content == "loop":
                return_val.append(self.run_ui_loop(control))
                continue
            
            settings = control.get("settings", {})
            
            control_list.append(
                self.generate_list_control(
                    is_callable, control, settings, depth_count
                )
            )
        return control_list
    
    def generate_list_control(self, is_callable: str, control: dt.JsonDict, settings: dt.ControlSettings, depth_count: int) -> ft.Control:
        settings = self.settings_object_parsers(
            search_and_sanitize(
                settings, sanatize, 
                depth_count, self.__loop_values
            )
        )
        
        if not is_callable:
            return self.create_control(
                control["control_type"], 
                settings
            )
        
        return self.get_attr(is_callable)(**settings)
    
    def create_control(self, control_type: str, settings: dt.ControlSettings) -> ft.Control:
        """creates a flet control from parsed fjml control settings and control name
        N.B. Control must be loaded before use
        
        Args:
            control_type (str): name of flet control
            settings (dt.ControlSettings): parsed flet control settings

        Returns:
            ft.Control: the created control
        """
        control: ft.Control = self._control_map[control_type]
        if not callable(control):
            return control
        if self._control_awaitable[control_type]:
            return asyncio.run(control(**settings))
        return control(**settings)
    
    def raise_error_popup(self, text: str) -> NoReturn:
        dlg: ft.AlertDialog = ft.AlertDialog(
            title=ft.Text("Error"), 
            content=ft.Text(traceback.format_exc()),
            on_dismiss=lambda e: self.page.window_close()
        )
        
        self.page.dialog = dlg
        dlg.open = True
        self.update()
    
    def settings_object_parsers(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        """parses flet control settings
        
        Args:
            settings (dt.ControlSettings): unparsed flet control settings

        Returns:
            dt.ControlSettings: parsed control
        """
        data: Any
        key: str
        
        settings = self.events(self.unpack_function(settings))
        for key in self.tools.get_keys_with_dict(settings):
            data = copy.deepcopy(settings[key])
            
            if self.check_for_reference(data):
                settings[key] = self.get_attr(data["ref"])
                continue
            
            if not data.get("control_type", None): continue
            
            if data["control_type"] == "loop":
                settings[key] = self.run_ui_loop(data)
                self.depth_count, self.__loop_values = 0, []
                continue
            
            settings[key] = self.try_get_attribute(data)
            if data != settings[key]:
                continue
            
            settings[key] = self.parsed_control_maker(data)
        
        for key in self.tools.get_keys_with_list(settings):
            if key != "controls":
                settings[key] = self.list_to_controls(settings[key])
        
        return settings
    
    def list_to_controls(self, list_value: list[Any]) -> list[Any]:
        i: int
        data: Any
        
        for i, data in enumerate(list_value):
            if not isinstance(data, dict): continue
            
            if self.check_for_reference(data):
                list_value[i] = self.get_attr(data["ref"])
                continue
            
            if not data.get("control_type", None): continue
            
            list_value[i] = self.try_get_attribute(data)
            if data != list_value[i]:
                continue
            
            list_value[i] = self.parsed_control_maker(data)
        
        return list_value

    def event_settings_parser(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        """helps parse settings for events
        
        Args:
            settings (dt.ControlSettings): unparsed event settings

        Returns:
            dt.ControlSettings: parsed event settings
        """
        data: dict
        key: str
        
        if settings == {}: return settings
        
        settings = self.events(
            self.unpack_function(settings)
        )
        for key in settings:
            if callable(key):
                settings[key] = settings[key]()
        
        for key in self.tools.get_keys_with_dict(settings):
            data = settings[key]
            if self.check_for_reference(data, False):
                settings[key] = self.get_attr(data["ref"])
        
        return settings
    
    def events(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        """parses events and makes function calls
        
        Args:
            settings (dt.ControlSettings): unparsed event settings

        Returns:
            dt.ControlSettings: settinsg with parsed events
        """
        key: str
        func: Callable
        get_func: str

        settings = self.unpack_function(settings)
        
        for key in self.tools.get_keys_with_dict(settings):
            data = settings[key]
            
            if key.startswith("on_") and data.get("route", None):
                d = data["route"]
                errors.ConditionalError.type_error(
                    (not isinstance(data["route"], str)), 
                    f"route must be of type string. recieved type {type(d)} instead")
                settings[key] = partial(self.change_route, route=data["route"])
                continue
            
            get_func = data.get("func", None)
            
            if get_func:
                errors.ConditionalError.type_error(
                    (not isinstance(get_func, str)), 
                    f"func must be of type string. recieved type {type(get_func)} instead")
                settings[key] = partial(
                    self.get_attr(get_func), 
                    **self.settings_object_parsers(data.get("settings", {}))
                )
                continue
            
            get_call = data.get("call", None)
            if get_call:
                errors.ConditionalError.type_error(
                    (not isinstance(get_call, str)), 
                    f"call must be of type string. recieved type {type(get_call)} instead")
                settings[key] = self.get_object(get_call)(
                    **self.settings_object_parsers(data.get("settings", {}))
                )
                continue
            
            get_eval = data.get("eval", None)
            if get_eval:
                errors.ConditionalError.type_error(
                    (not isinstance(get_eval, str)), 
                    f"eval must be of type string. recieved type {type(get_eval)} instead")
                settings[key] = eval(get_eval)
                continue
        
        return settings

    def try_get_attribute(self, data: dt.JsonDict) -> Any:
        if not data.get("attr", None): return data
        if not data.get("control_type", None): return data
        
        attr: Any = getattr(self._control_map[data["control_type"]], data["attr"], NULL)
        if attr == NULL: raise AttributeError()
        return attr
        

    def unpack_function(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        unpack: dt.JsonDict = settings.get("unpack", None)
        
        if not unpack: return settings
        if not isinstance(unpack, dict): 
            raise errors.InvalidTypeError("unpack", unpack, dict)
        
        reference: str = unpack.get("ref", None)
        if not isinstance(reference, str) and not reference: 
            raise errors.InvalidTypeError("ref", reference, str)
        else:
            settings.update(self.get_attr(reference))
            del settings["unpack"]
            return settings

        style: str = unpack.get("style", None)
        style_ptr: list[str] = unpack.get("keys", None)
        if not isinstance(style_ptr, list): 
            raise errors.InvalidTypeError("keys", style_ptr, list)
        if not isinstance(style, str) and not style: 
            raise errors.InvalidTypeError("style", style, str)
        else:
            settings.update(self.stlye_sheet.get_style(*style_ptr))
            del settings["unpack"]
            return settings
        
        

