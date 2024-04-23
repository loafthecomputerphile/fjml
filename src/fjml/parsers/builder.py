import json
import asyncio
from functools import partial, lru_cache
from types import MethodType
import io
import traceback
import inspect
import copy
from typing import (
    Any, 
    Optional, 
    Union, 
    Callable,
    Type,
    NoReturn,
    Iterator
)

import nest_asyncio
import flet as ft

import fjml.error_types as errors
import fjml.data_types as dt
from fjml.utils import Utilities, RegistryOperations
from fjml.constants import CONTROL_REGISTRY_PATH, RANGE_PARAM_LENGTH

nest_asyncio.apply()

Tools: Utilities = Utilities()

@lru_cache(64)
def method_filter(method_name: str) -> bool:
    return not method_name.startswith("__")

def attribute_filter(data: tuple[str, Any]) -> bool:
    return not data[0].startswith('_') and not inspect.ismethod(data[1])

method_filter_partial = partial(filter, method_filter)
attribute_filter_func = lambda obj: list(dict(filter(attribute_filter, inspect.getmembers(obj))).keys())


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
        return self.get_attr(content)
    
    validate_index(content, depth_count, True)
    
    idx = content["idx"]
    
    val = loop_values[idx[0]]
    data = {"ref": val[idx[1]] if isinstance(value, list) else val}
    
    if cls.check_for_reference(data):
        return self.get_attr(data["ref"])


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
                    raise ValueError("a loop range must only contain in integers")
            if len(value) in RANGE_PARAM_LENGTH:
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


class Build:
    
    
    def __init__(self, compiled_program: dt.CompiledModel, page: ft.Page) -> NoReturn:
        """
        __init__ _summary_

        Args:
            compiled_program (dt.CompiledModel): _description_
            visible (ft.Page): _description_. Defaults to True.
        """
        self.tools: Utilities = Utilities()
        self.control_bundles: dict[str, dt.ControlBundle] = dict()
        self.compiled_program: dt.CompiledModel = compiled_program
        self.initialized: bool = False
        self.page: ft.Page = page
        self.route: str = "/"
        self.setup_functions: list[dt.FunctionModel] = dt.TypedList([], dt.FunctionModel)
        self._importer: MethodType = None
        self._page_setup: MethodType = None
        self._on_close: MethodType = None
        self.__methods_added: bool = False
        self.__object_map: dict[str, Callable] = dict()
    
    def initialize(self) -> NoReturn:
        """
        initialize _summary_
        """
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
    
    def add_methods(self, event_class: dt.EventContainer) -> NoReturn:
        method: str
        method_data: Any
        
        for method in method_filter_partial(dir(event_class)):
            method_data = getattr(event_class, method)
            
            if callable(method_data):
                self.__set_attr(method, MethodType(method_data, self))
                continue
            
            self.__set_attr(method, method_data)
        
        self.__methods_added = True
        
        if not self._on_close: raise errors.UndefinedMethodError("_on_close")
        if not self._page_setup: raise errors.UndefinedMethodError("_page_setup")
        if not self._importer: raise errors.UndefinedMethodError("_importer")
    
    def run_setup(self) -> NoReturn:
        """Sets up the the page and its route changes
        
        Returns:
            NoReturn
        """
        function: dt.FunctionModel
        
        asyncio.run(self._importer())
        
        self.create_controls()
        self.page.on_route_change = self.create_ui
        self.page.on_close = self._on_close
        
        asyncio.run(self._page_setup())
        
        for function in self.setup_functions:
            self.page.run_task(self.__get_attr(function.func_name), *function.args)
        
        self.page.update()
    
    def set_object(self, name: str, obj: Callable) -> NoReturn:
        """Adds a callable python object to the object map to be called in the fjml markup 

        Args:
            name (str): the name used to call the object
            obj (Callable): the object to be used when called by its name

        Returns:
            NoReturn
        """
        errors.ConditionalError.type_error(
            (not callable(obj)),"Parameter, obj, is not callable")
        self.__object_map[name] = obj
    
    def get_object(self, name: str) -> Callable:
        """Returns a callable python object from the object map

        Args:
            name (str): the name registerd to call the object

        Returns:
            Callable
        """
        res: Union[Callable, None] = self.__object_map.get(name, None)
        errors.ConditionalError.key_error((res == None),f"Key, {name}, was not set")
        return res
    
    def delete_object(self, name: str) -> NoReturn:
        """Deletes a registered callable object in the object map

        Args:
            name (str): the name registerd to call the object

        Returns:
            NoReturn
        """
        errors.ConditionalError.key_error(
            (name not in self.__object_map),
            f"Key, {name}, was not set")
        del aelf.__object_map[name]
    
    def update(self) -> NoReturn:
        self.page.update()
    
    def __change_route(self, route: str) -> NoReturn:
        self.change_route(None, route)
    
    def change_route(self, e: ft.ControlEvent, route: str) -> NoReturn:
        self.page.go(route)
    
    @property
    def control_registry(self) -> dt.ControlRegistryJsonScheme:
        return RegistryOperations.load_file()
    
    def add_controls(self, names: list[str]) -> NoReturn:
        """Adds flet controls to be used in the fjml markup file
        N.B. Controls must already be registered

        Args:
            names (list[str]): names of flet controls to be loaded and be used in fjml markup files or fjml renderers

        Returns:
            NoReturn
        """
        name: str
        registered_controls: dt.ControlJsonScheme = self.control_registry
            
        for name in names:
            if name in self._control_map.keys():
                continue
            
            if name not in control_registry["Controls"]:
                raise errors.ControlNotFoundError(name)
            
            registered_controls = control_registry["ControlTypes"][
                control_registry["Controls"].index(name)
            ]
            
            self._control_map[name] = self.load_object(
                registered_controls["source"], 
                None,
                registered_controls["attr"]
            )
            self._control_awaitable[name] = registered_controls.get("awaitable", False)
    
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
                self.__set_attr(var_name, settings)
                continue
            
            if self._control_awaitable.get(control_model.control_name, None):
                control = asyncio.run(control_model.control(**settings))
            else:
                control = control_model.control(**settings)
            
            self.control_names.append(var_name)
            self.__set_attr(var_name, control)
            
            if bundle_name in self._bundle_names:
                self.bundle_control(bundle_name, var_name)
    
    def get_bundle(self, bundle_name: str) -> dt.ControlBundle:
        errors.ConditionalError.value_error((bundle_name not in self._bundle_names), 
                                    f"bundle_name {bundle_name} was never used")
        return self.control_bundles[bundle_name]
    
    def set_view(route_name: str, view: ft.View) -> NoReturn:
        errors.ConditionalError.type_error(
            (not isinstance(view, ft.View)), 
            f"Parameter view must be of type, ft.View. Recieved type of, {type(view)}, instead")
        errors.ConditionalError.type_error(
            (not isinstance(route_name, str)), 
            f"Parameter route_name must be of type, str. Recieved type of, {type(route_name)}, instead")
        self._ui[route_name] = dt.UserInterfaceViews(
            route=route_name, 
            settings=self.tools.get_init_parameters(view)
        )
    
    def add_view(self, view: ft.View) -> NoReturn:
        """Adds flet View control to the flet Page control 

        Args:
            view (ft.View): flet View control to be added to flet Page control 

        Returns:
            NoReturn
        """
        errors.ConditionalError.type_error(
            (not isinstance(view, ft.View)), 
            f"Parameter view must be of type, ft.View. Recieved type of, {type(view)}, instead")
        self.page.views.append(view)
    
    def create_ui(self, e: ft.RouteChangeEvent) -> NoReturn:
        """A flet event function which creates all controls and handles route changes

        Args:
            e (ft.RouteChangeEvent): flet RouteChangeEvent class 

        Returns:
            NoReturn
        """
        route: str
        view_model: dt.UserInterfaceViews
        view: ft.View
        
        if not self.initialized:
            raise InitializationError()
        
        self.page.views.clear()
        
        view = self.make_view(self._ui["/"])
        self.add_view(view)
        
        for route in self._ui.keys():
            if self.page.route == route and route != "/":
                view = self.make_view(self._ui[route])
                self.add_view(view)
        
        self.update()
    
    def make_view(self, view_model: dt.UserInterfaceViews) -> ft.View:
        """A method to create flet View controls via parsing dt.UserInterfaceViews models

        Args:
            view_model (dt.UserInterfaceViews): parsed views from fjml UI containers

        Returns:
            ft.View: parsed views to be used
        """
        control_settings: dt.ControlSettings = self.parse_controls(view_model.settings)
        
        self._ui[view_model.route].settings = control_settings
        if control_settings.get("route", None):
            del control_settings["route"]
        
        return ft.View(view_model.route, **control_settings)
        
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
    
    def add_property(self, property_name: str, getter_func: Callable, setter_func: Optional[Callable]=None) -> NoReturn:
        """A method to add a property to your project
        this method should only be used inside your action class
        
        Examples:
            >>> self.add_property(
                    "hello", 
                    lambda self: ft.Text("hello"), 
                    lambda self, data: ft.Text(data)
                )

        Args:
            property_name (str): the name of the property
            getter_func (Callable): the function to be set as the getter
            setter_func (Optional[Callable]): the function to be set as the setter or None

        Returns:
            NoReturn
        """
        getter: Callable[[Type[self]], Any]
        
        def default_getter(self) -> Any:
            return None
        
        getter = getter_func if getter_func else default_getter
        setattr(self.__class__, property_name, property(getter, setter_func))
    
    def parse_controls(self, data: dt.ControlSettings) -> dt.ControlSettings:
        """A method which parses the settings of an fjml control.
        It then converts it into python objects to be used in flet controls
        
        Args:
            data (dt.ControlSettings): the control settings to be parsed into python code

        Returns:
            dt.ControlSettings: completely parsed settings fit to be used in flet controls
        """
        controls: list[Optional[Controls]]
        settings: dt.ControlSettings
        control: ft.Control
        obj: dt.JsonDict
        
        data = self.settings_objects_to_controls(data)
        
        if not data.get("controls", False):
            return data
        
        if len(data["controls"]) == 0:
            return data
        
        controls = [None for _ in data["controls"]]
        
        for i, obj in enumerate(data["controls"]):
            
            if isinstance(obj, ft.Control):
                controls[i] = obj
                continue
            
            errors.ConditionalError.type_error(
                not isinstance(obj, dict),
                f"list items of key, control, must be of type dict or ft.Control. Recieved type {type(obj)} instead")
            
            if self.check_for_reference(obj):
                controls[i] = self.__get_attr(obj["ref"])
                continue
            
            controls[i] = self.parsed_control_maker(obj)
        
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
            (res not in attribute_filter_func(self)), f"value, {res}, does not exist")
        
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
        control_list: list[ft.Control] = []
        control: ControlModel
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
            if not content:
                raise ValueError("loop content has to be a reference or a control type")
            
            if content == "loop":
                return_val.append(self.run_ui_loop(control))
                continue
            
            settings = control.get("settings", None)
            
            if not settings:
                raise KeyError("Key settings was not found for loop content")
            if not isinstance(settings, dict):
                raise ValueError(f"settings must be of type dict. recieved type of {type(settings)} instead")
            
            control_list.append(
                self.create_control(
                    control["control_type"], 
                    self.settings_objects_to_controls(
                        search_and_sanitize(
                            settings, sanatize, depth_count, self.__loop_values
                        )
                    )
                )
            )
            
        return control_list
    
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
    
    def settings_objects_to_controls(self, settings: dt.ControlSettings) -> dt.ControlSettings:
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
            data = settings[key]
            
            if self.check_for_reference(data):
                settings[key] = self.__get_attr(data["ref"])
                continue
            
            if not data.get("control_type", None): continue
            
            if data["control_type"] == "loop":
                settings[key] = self.run_ui_loop(data)
                self.depth_count, self.__loop_values = 0, []
                continue
            
            settings[key] = self.parsed_control_maker(data)
        
        for key in self.tools.get_keys_with_list(settings):
            if key != "controls":
                settings[key] = self.list_to_controls(settings[key])
        
        return settings
    
    def list_to_controls(self, list_: list[Any]) -> list[ft.Control]:
        
        list_value: list[Any] = list_
        i: int
        data: Any
        
        for i, data in enumerate(list_value):
            if not isinstance(data, dict): continue
            
            if self.check_for_reference(data):
                list_value[i] = self.__get_attr(data["ref"])
                continue
            
            if not data.get("control_type", None): continue
            
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
                settings[key] = self.__get_attr(data["ref"])
        
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
            
            if key.startswith("on_") and settings[key].get("route", None):
                settings[key] = partial(self.__change_route, route=settings[key]["route"])
                continue
            
            get_func = settings[key].get("func", None)
            
            if get_func:
                settings[key] = partial(
                    self.__get_attr(get_func), 
                    **self.event_settings_parser(settings[key].get("settings", {}))
                )
                continue
            
            get_call = settings[key].get("call", None)
            if get_call:
                settings[key] = self.get_object(get_call)(
                    **self.event_settings_parser(settings[key].get("settings", {}))
                )
                continue
            
        
        return settings

    def unpack_function(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        if settings.get("unpack", None):
            settings.update(self.__get_attr(settings["unpack"]["ref"]))
            del settings["unpack"]
        return settings
    
    def get_attr(self, attr_name: str) -> Any:
        return self.__get_attr(attr_name)
    
    def set_attr(self, attr_name: str, data: Any) -> NoReturn:
        self.__set_attr(attr_name, data)
    
    def __set_attr(self, attr_name: str, data: Any) -> NoReturn:
        setattr(self, attr_name, data)
    
    def __get_attr(self, attr_name: str) -> Any:
        return getattr(self, attr_name)

