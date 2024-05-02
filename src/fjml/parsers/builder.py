import asyncio
from functools import partial, lru_cache
from types import MethodType
import inspect
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
    utils
)

from .renderer import Renderer

nest_asyncio.apply()

Tools: utils.Utilities = utils.Utilities()

@lru_cache(64)
def method_filter(method_name: str) -> bool:
    return not method_name.startswith("__")

def attribute_filter(data: tuple[str, Any]) -> bool:
    return not data[0].startswith('_') and not inspect.ismethod(data[1])

method_filter_partial: Callable[[Iterator[str]], Iterator[str]] = partial(filter, method_filter)
attribute_filter_func: Callable[[Any], list[str]] = lambda obj: list(dict(filter(attribute_filter, inspect.getmembers(obj))).keys())

NULL: Final[str] = "<NULL>"

class Build:
    
    def __init__(self, compiled_program: dt.CompiledModel, page: ft.Page) -> NoReturn:
        """
        __init__ _summary_

        Args:
            compiled_program (dt.CompiledModel): _description_
            visible (ft.Page): _description_. Defaults to True.
        """
        self.tools: utils.Utilities = utils.Utilities()
        self.style_sheet: dt.StyleSheet = compiled_program.style_sheet
        self.compiled_program: dt.CompiledModel = compiled_program
        self.initialized: bool = False
        self.page: ft.Page = page
        self.route: str = "/"
        self.setup_functions: list[dt.FunctionModel] = dt.TypedList([], dt.FunctionModel)
        self._importer: MethodType = None
        self._page_setup: MethodType = None
        self._on_close: MethodType = None
        self.__methods_added: bool = False
        self.__object_map: dict[str, dt.CallableObject] = dt.TypedList([], dt.CallableObject)
    
    def initialize(self) -> NoReturn:
        """
        initialize _summary_
        """
        self.renderer = Renderer(self, self.compiled_program)
        self.initialized = True
    
    def add_methods(self, event_class: dt.EventContainer) -> NoReturn:
        method: str
        method_data: Any
        
        for method in method_filter_partial(dir(event_class)):
            method_data = getattr(event_class, method)
            
            if callable(method_data):
                self.set_attr(method, MethodType(method_data, self))
                continue
            
            self.set_attr(method, method_data)
        
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
        
        self.renderer.create_controls()
        self.page.on_route_change = self.create_ui
        self.page.on_close = self._on_close
        
        asyncio.run(self._page_setup())
        
        for function in self.setup_functions:
            self.page.run_task(self.get_attr(function.func_name), *function.args)
        
        self.update()
    
    def set_object(self, name: str, obj: Callable[[...], Any]) -> NoReturn:
        """Adds a callable python object to the object map to be called in the fjml markup 

        Args:
            name (str): the name used to call the object
            obj (Callable): the object to be used when called by its name

        Returns:
            NoReturn
        """
        errors.ConditionalError.type_error(
            (not callable(obj)),"Parameter, obj, is not callable")
        self.__object_map[name] = dt.CallableObject(
            name=name, obj=obj,
            valid_args=self.tools.get_object_args(obj)
        )
    
    def get_object(self, name: str) -> dt.CallableObject:
        """Returns a callable python object from the object map

        Args:
            name (str): the name registerd to call the object

        Returns:
            Callable
        """
        errors.ConditionalError.key_error(
            (name not in self.__object_map), f"Key, {name}, was not set")
        return self.__object_map[name]
    
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
    
    def change_route(self, e: ft.ControlEvent, route: str) -> NoReturn:
        self.page.go(route)
    
    @property
    def control_registry(self) -> dt.ControlRegistryJsonScheme:
        return utils.RegistryFileOperations.load_file()
    
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
            if name in self.renderer._control_map.keys():
                continue
            
            if name not in control_registry["Controls"]:
                raise errors.ControlNotFoundError(name)
            
            registered_controls = control_registry["ControlTypes"][
                control_registry["Controls"].index(name)
            ]
            
            self.renderer._control_map[name] = self.tools.load_object(
                registered_controls["source"], 
                None,
                registered_controls["attr"]
            )
            self.renderer._control_awaitable[name] = registered_controls.get("awaitable", False)
    
    def set_view(self, route_name: str, view: ft.View) -> NoReturn:
        errors.ConditionalError.type_error(
            (not isinstance(view, ft.View)), 
            f"Parameter view must be of type, ft.View. Recieved type of, {type(view)}, instead")
        errors.ConditionalError.type_error(
            (not isinstance(route_name, str)), 
            f"Parameter route_name must be of type, str. Recieved type of, {type(route_name)}, instead")
        self.renderer._ui[route_name] = dt.UserInterfaceViews(
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
        
        if not self.initialized:
            raise InitializationError()
        
        self.page.views.clear()
        
        view: ft.View = self.make_view(self.renderer._ui["/"])
        self.add_view(view)
        
        for route in self.renderer._ui.keys():
            if self.page.route == route and route != "/":
                view = self.make_view(self.renderer._ui[route])
                self.add_view(view)
        
        self.update()
    
    def make_view(self, view_model: dt.UserInterfaceViews) -> ft.View:
        """A method to create flet View controls via parsing dt.UserInterfaceViews models

        Args:
            view_model (dt.UserInterfaceViews): parsed views from fjml UI containers

        Returns:
            ft.View: parsed views to be used
        """
        control_settings: dt.ControlSettings = self.renderer.parse_controls(view_model.settings)
        
        self.renderer._ui[view_model.route].settings = control_settings
        if control_settings.get("route", None):
            del control_settings["route"]
        
        return ft.View(view_model.route, **control_settings)
    
    
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
        def default_getter(self) -> Any:
            return None
        
        getter: Callable[[Type[self]], Any] = getter_func if getter_func else default_getter
        setattr(self.__class__, property_name, property(getter, setter_func))
    
    def get_attr(self, attr_name: str) -> Any:
        return self.__get_attr(attr_name)
    
    def set_attr(self, attr_name: str, data: Any) -> NoReturn:
        self.__set_attr(attr_name, data)
    
    def __set_attr(self, attr_name: str, data: Any) -> NoReturn:
        setattr(self, attr_name, data)
    
    def __get_attr(self, attr_name: str) -> Any:
        return getattr(self, attr_name)

