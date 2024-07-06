from __future__ import annotations
from functools import partial
from types import MethodType
from typing import (
    Any,
    Callable,
    Sequence,
    Mapping,
    TypeVar
)
try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

from flet import (
    RouteChangeEvent,
    Page,
    ControlEvent,
    View
)

from .renderer import Renderer
from .. import (
    error_types as err, 
    data_types as dt, 
    operation_classes as opc,
    constants, 
    utils
)

T: TypeVar = TypeVar("T", Renderer)

def method_filter(method_name: str) -> bool:
    return not method_name.startswith("__")


class Backend:
    
    method_filter_partial: Callable[[Sequence], Sequence] = (
        partial(filter, method_filter)
    )
    
    def __init__(self, compiled_program: dt.CompiledModel, page: Page) -> NoReturn:
        self.__block_assignments: dt.BlockAssignment = dt.BlockAssignment()
        self.compiled_program: opc.CompiledModel = compiled_program
        self.view_operations: opc.ViewOperations
        self._importer: Callable[[Backend], NoReturn]
        self._page_setup: Callable[[Backend], NoReturn]
        self.dict_to_control: Callable[[T, dt.ControlDict], dt.ControlType]
        self.__renderer: Renderer = None
        self.__is_setup: bool = False
        self.__initialize: bool = False
        self.tools: utils.Utilities = utils.Utilities()
        self.style_sheet: opc.StyleSheet = compiled_program.style_sheet
        self.page: Page = page
        self.setup_functions: opc.SetupFunctions = opc.SetupFunctions(self)
        self.dependency_bucket: opc.ControlDependencies = compiled_program.dependencies
        self.preserve_control_bucket: opc.PreserveControlContainer = (
            opc.PreserveControlContainer()
        )
        self.object_bucket: opc.ObjectContainer = opc.ObjectContainer()
        self.property_bucket: opc.PropertyContainer = opc.PropertyContainer(
            self, self.tools
        )
        self.program_name: str = compiled_program.program_name
    
    def initialize(self, event_class: dt.EventContainer) -> Page:
        if not self.__initialize:
            self.__add_methods(event_class)
            del event_class
            self.setup_functions.call_functions()
            self.__renderer = Renderer(self)
            self.dict_to_control = self.__renderer.ui_parser
            self.view_operations = opc.ViewOperations(self, self.__renderer)
            self.style_sheet.setter(self.__renderer)
            self.__block_assignments.switch_primary()
            self._importer()
            self._page_setup()
            self.__renderer.init_controls()
            self.group_assign(
                self.page,
                {
                    "on_route_change":self.__create_ui,
                    "title":self.program_name,
                }
            )
            self.__block_assignments.switch_secondary()
            self.__initialize = True
            self.update()
        return self.page
    
    def __add_methods(self, event_class: dt.EventContainer) -> NoReturn:
        method: str
        method_data: Any
        
        if self.__initialize:
            return
        
        for method in self.method_filter_partial(dir(event_class)):
            method_data = getattr(event_class, method)
            if callable(method_data):
                self.set_attr(method, MethodType(method_data, self))
            else:
                self.set_attr(method, method_data)
    
        if not self._page_setup:
            raise err.UndefinedMethodError("_page_setup")
        if not self._importer:
            raise err.UndefinedMethodError("_importer")
    
    def update(self) -> NoReturn:
        self.page.update()
    
    def change_route(self, e: ControlEvent, route: str) -> NoReturn:
        self.page.go(route)
    
    @property
    def get_current_route(self) -> str:
        return self.page.route

    @property
    def get_routes(self) -> Sequence[str]:
        view: View
        return [view.route for view in self.page.views]
    
    def __add_make_view(self, route: str) -> NoReturn:
        if route in self.get_routes:
            del self.page.views[self.get_routes.index(route)]
        
        self.view_operations.add_view(
            self.view_operations.make_view(self.__renderer._ui[route])
        )
        self.update()
    
    def __valid_route(self, route: str, include_base: bool = False) -> bool:
        base_condition: bool = (route != "/") if not include_base else True
        return self.get_current_route == route and base_condition
    
    async def __create_ui(self, e: RouteChangeEvent) -> NoReturn:
        route: str
        
        if not self.__initialize:
            raise InitializationError()
        
        self.__add_make_view("/")
        for route in self.__renderer._ui.keys():
            if self.__valid_route(route):
                self.__add_make_view(route)
    
    def get_attr(self, attr_name: str, default: Any = None) -> Any:
        return getattr(self, attr_name, None)
    
    def set_attr(self, attr_name: str, value: Any = None) -> NoReturn:
        setattr(self, attr_name, value)
    
    def has_attr(self, attr_name: str) -> bool:
        return hasattr(self, attr_name)
    
    def mass_assign(self, attribute_map: Mapping) -> NoReturn:
        data: tuple[str, Any]
        
        for data in attribute_map.items():
            if self.has_attr(data[0]): self.set_attr(*data)
    
    def group_assign(self, obj: Any, attribute_map: Mapping[str, Any]) -> NoReturn:
        key: str
        value: Any
        
        for key, value in attribute_map.items():
            if hasattr(obj, key): setattr(obj, key, value)
    
    @property
    def client_stroage(self) -> Mapping:
        return self.page.client_storage
    
    @property
    def session(self) -> Mapping:
        return self.page.session
    
    def __setattr__(self, key: str, value: Any) -> NoReturn:
        if key in constants.PRIMARY_STAGNANT_KEYS and self.__block_assignments.PRIMARY:
            raise TypeError(f"Class variable, 'self.{key}' cannot be re-assigned.")
        if key in constants.STAGNANT_KEYS and self.__block_assignments.SECONDARY:
            raise TypeError(f"Class variable, 'self.{key}' cannot be re-assigned.")
        super().__setattr__(key, value)
