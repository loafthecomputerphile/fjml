from __future__ import annotations
from functools import partial, lru_cache, cached_property
from types import MethodType
from collections import Counter
import itertools
import pprint
import inspect
from typing import (
    Any, Literal, 
    NoReturn, Sequence, 
    Callable, 
    TypeAlias, Union, 
    Iterable, TYPE_CHECKING,
    Mapping
)
import flet as ft
from . import (
    error_types as err,
    utils,
    constants,
    type_checker as tc
)

if TYPE_CHECKING:
    from . import data_types as dt
    from parsers.builder import Backend
    from parsers.renderer import Renderer
    

Tools: utils.Utilities = utils.Utilities()
NULL: str = constants.NULL
PropertyLiteral: TypeAlias = Literal["set", "get", "del"]

def attribute_filter(data: tuple[str, Any]) -> bool:
    return not data[0].startswith("_") and not inspect.ismethod(data[1])

attribute_filter_func: Callable[[Any], Sequence[str]] = lambda obj: list(
    dict(filter(attribute_filter, inspect.getmembers(obj))).keys()
)

class ControlDependencies:
    __slots__ = ["__data", "cache"]
    
    def __init__(self) -> NoReturn:
        self.__data: Mapping[str, Sequence[str]] = {}
        self.cache: Mapping[str, Sequence[str]] = {}
    
    def add_dependencies(self, var_name: str, settings: dt.ControlDict, update: bool = False) -> NoReturn:
        val: str
        for val in Tools.find_values(settings, "refs"):
            if not self.contains(var_name, val):
                self.add(var_name, val)
        
        if update:
            self.update_cache()
    
    def contains(self, var_name: str, dependency: str) -> bool:
        return dependency in self.__data.get(var_name, [])
    
    def add(self, var_name: str, dependency: str) -> NoReturn:
        if var_name in self.__data:
            if self.contains(var_name, dependency):
                return
            return self.__data[var_name].append(dependency)
        self.__data[var_name] = [dependency]
    
    def _get(self, var_name: str) -> Sequence[str]:
        res: Sequence[str] = []
        name: str
        result: Sequence[str] = []
        
        if var_name in self.__data:
            res = self.__data[var_name]
            result.extend(res)
            for name in res:
                result.extend(self._get(name))
        
        return result

    def get(self, var_name: str, cache: bool = True) -> Sequence[str]:
        res: Sequence[str]
        
        if var_name in self.cache and cache:
            return self.cache[var_name]
        
        res = list(Counter(self._get(var_name)[::-1]))
        if cache:
            self.cache[var_name] = res
        
        return res

    @property
    def get_data(self) -> Mapping[str, Sequence[str]]:
        return self.__data
    
    def update_cache(self) -> NoReturn:
        for name in self.__data.keys():
            self.cache[name] = self.get(name, False)



class UIViews:
    __slots__ = ["route", "settings"]
    def __init__(self, route: str, settings: ControlSettings = {}) -> NoReturn:
        self.route: str = route
        self.settings: ControlSettings = settings


class EventParser:
    __slots__ = [
        "__renderer", "__backend", "change_route", 
        "settings_object_parsers", "get_attr"
    ]
    
    def __init__(self, renderer: Renderer) -> NoReturn:
        self.__renderer: Renderer = renderer
        self.__backend: Backend = self.__renderer.backend
        self.change_route: MethodType = self.__backend.change_route
        self.settings_object_parsers: MethodType = self.__renderer.settings_object_parsers
        self.get_attr: MethodType = self.__backend.get_attr

    def route(
        self, key: str, data: dt.JsonDict, settings: dt.JsonDict
    ) -> bool:
        if not key.startswith("on_") or data.get("route", NULL) == NULL:
            return False
        
        if not isinstance(data["route"], str):
            settings[key] = None
            return True
        
        settings[key] = partial(self.change_route, route=data["route"])
        return True

    def call(
        self, key: str, data: dt.JsonDict, settings: dt.JsonDict
    ) -> bool:
        #get_call: str = data.get("call", constants.NULL)
        if not isinstance(data, Mapping):
            return False
        
        if data.get("call", NULL) == NULL:
            return False

        if not isinstance(data["call"], str):
            settings[key] = None
            return True
        
        setts = self.settings_object_parsers(data.get("settings", {}))
        
        settings[key] = self.__renderer.object_bucket.call_object(
            data["call"], setts
        )
        
        return True

    def eval(
        self, key: str, data: dt.JsonDict, settings: dt.JsonDict
    ) -> bool:
        #get_eval: Union[str, None] = data.get("eval", None)
        if not isinstance(data, Mapping):
            return False
        
        if data.get("eval", NULL) == NULL:
            return False

        if not isinstance(data["eval"], str):
            settings[key] = None
            return True
        
        settings[key] = eval(data["eval"], {"ft":ft, "self":self.__backend})
        return True

    def func(
        self, key: str, data: dt.JsonDict, settings: dt.JsonDict
    ) -> bool:
        #get_func: Union[str, None] = data.get("func", None)
        if data.get("func", NULL) == NULL:
            return False

        if not isinstance(data["func"], str):
            settings[key] = None
            return True
        
        settings[key] = partial(
            self.get_attr(data["func"]),
            **self.settings_object_parsers(data.get("settings", {})),
        )
        return True


class Reference:
    
    __slots__ = ["__renderer", "__get_attr"]
    
    def __init__(self, renderer: Renderer):
        self.__renderer: Renderer = renderer
        self.__get_attr = self.__renderer.backend.get_attr
    
    def get_ref(self, ref: Mapping) -> Any:
        result: Any
        rtype: str = Tools.refs_type(ref)
        data: Any = ref.get(rtype, None)
        
        if not data or not isinstance(data, str):
            return
        
        if rtype == "refs":
            result = self.__get_reference(data)
        elif rtype == "code_refs":
            result = self.__get_reference(data, True)
        
        if not result:
            return
        
        return self.__get_attr_index(ref, result, rtype)

    def __get_attr_index(self, mapping: Mapping, data: Any, ref_type: str) -> Any:
        keys: tuple[str, str] = ("attr", "idx")
        group: Sequence = mapping.get("group", [])
        result: Any = data
        key: str
        value: Any
        depth: int = 0
        parse_attr_idx = partial(self.parse_attr_idx, ref_type=ref_type)
        
        if not group:
            for key, value in mapping.items():
                if key not in keys:
                    continue
                result = parse_attr_idx(result, key, value, depth)
                depth += 1
                if not result:
                    return
            return result
        
        for data in group:
            key, value = list(data.items())[0]
            if key not in keys:
                continue
            result = parse_attr_idx(result, key, value, depth)
            depth += 1
            if not result:
                return
        
        return result
    
    def parse_attr_idx(self, result: Any, key: str, value: Any, depth: int, ref_type: str) -> Any:
        if key == "attr":
            if not isinstance(value, str):
                return
            return getattr(result, value, None)
        elif key == "idx":
            if ref_type == "refs" and depth == 0:
                return
            return self.__get_index(result, value)
        
        return None
    
    @property
    def __property_bucket(self) -> PropertyContainer:
        return self.__renderer.property_bucket
    
    @property
    def __controls(self) -> dt.ParsedControls:
        return self.__renderer._controls
    
    @property
    def __attr_filter(self) -> dt.ParsedControls:
        return attribute_filter_func(self.__renderer.backend)

    def __get_reference(self, ref: str, is_code: bool = False) -> Any:
        result: Any
        
        if is_code and ref not in self.__controls:
            if self.__property_bucket.contains(ref):
                return self.__property_bucket.call(ref, "get")
            elif ref in self.__attr_filter:
                return self.__get_attr(ref)
        elif ref in self.__controls and not is_code:
            return self.__get_attr(ref)
        
        return None
    
    @staticmethod
    def __get_index(value: Any, index: IndexType = None) -> Any:
        if index == None or not isinstance(index, (str, int)):
            return None
        if isinstance(value, Mapping) and isinstance(index, str):
            return value.get(index, None)
        index_check: bool = utils.is_sequence_not_str(value) and isinstance(index, int)
        if index_check and index > -1:
            return None if index > len(value)-1 else value[index]
        return None


class CallableObject:
    __slots__ = ["obj", "name", "valid_args"]
    def __init__(self, obj: dt.AnyCallable, name: str) -> NoReturn:
        self.obj: dt.AnyCallable = obj
        self.name: str = name

    def __call__(self, kwargs) -> Any:
        if inspect.isawaitable(self.obj):
            return asyncio.run(self.obj(**kwargs))
        return self.obj(**kwargs)


class PreserveControlContainer:
    __slots__ = ["__data"]
    def __init__(self) -> NoReturn:
        self.__data: Sequence[str] = []
    
    def add(self, var_name: str) -> NoReturn:
        self.__data.append(var_name)
    
    def group_add(self, var_names: Sequence[str]) -> NoReturn:
        self.__data.extend(var_names)
    
    def remove(self, var_name) -> NoReturn:
        self.__data.remove(var_name)
    
    def empty(self) -> NoReturn:
        self.__data.clear()
    
    @property
    def data(self):
        return self.__data


class ViewOperations:
    __slots__ = [
        "__backend", "__page", "__renderer", 
        "__create_controls", "__settings_parser", "view_hints",
        "valid_args"
    ]
    def __init__(self, backend: Backend, renderer: Renderer) -> NoReturn:
        self.__backend: Backend = backend
        self.__renderer: Renderer = renderer
        self.__backend.page.on_view_pop = self._view_pop
        self.view_hints: dt.TypeHints = Tools.get_hints(ft.View)
        self.valid_args: Sequence[str] = Tools.get_object_args(ft.View)
    
    @property
    def create_controls(self) -> Callable:
        return self.__renderer.create_controls
    
    @property
    def settings_parser(self) -> Callable[[dt.ControlSettings, Sequence[str], dt.TypeHints, bool], dt.ControlSettings]:
        return self.__renderer.settings_object_parsers
    
    @property
    def page(self) -> ft.Page:
        return self.__backend.page

    def set_view(self, route_name: str, view_settings: dt.ControlSettings) -> NoReturn:
        if not (isinstance(route_name, str) and isinstance(view, Mapping)):
            return
        
        self.__backend.compiled_program._ui[route_name] = UIViews(
            route=route_name, settings=view_settings
        )

    def add_view(self, view: ft.View) -> NoReturn:
        self.page.views.append(view)

    def make_view(self, view_model: UIViews) -> ft.View:
        
        if view_model.route != self.__backend.get_current_route:
            return ft.View(view_model.route)

        self.__renderer.use_bucket = self.__backend.dependency_bucket.get(
            view_model.route
        )
        self.create_controls()

        control_settings: dt.ControlSettings = self.settings_parser(
            view_model.settings, self.valid_args, self.view_hints
        )
        if control_settings.get("route", constants.NULL) != constants.NULL:
            del control_settings["route"]

        return ft.View(view_model.route, **control_settings)
    
    async def _view_pop(self, e: ft.ViewPopEvent) -> NoReturn:
        self.page.views.pop()
        top_view: ft.View = self.__page.views[-1]
        self.page.go(top_view.route)


class ObjectContainer:
    __slots__ = ["__object_map"]
    
    def __init__(self) -> NoReturn:
        self.__object_map: Mapping[str, CallableObject] = {}

    def set_object(self, name: str, obj: dt.AnyCallable) -> NoReturn:
        if not callable(obj):
            return
        self.__object_map[name] = CallableObject(
            name=name, obj=obj
        )

    def __get_object(self, name: str) -> CallableObject:
        return self.__object_map[name]

    def call_object(self, name: str, kwargs: Mapping) -> Any:
        if name not in self.__object_map:
            return 
        return self.__get_object(name)(kwargs)

    def delete_object(self, name: str) -> NoReturn:
        if name not in self.__object_map:
            return
        del self.__object_map[name]



class StyleSheet:
    __slots__ = [
        "__renderer", "__data", "invalid_key_vals", 
        "__setted", "mfind", "find_k_v", "generate_path"
    ]
    
    def __init__(self, data: dt.JsonDict = {}) -> NoReturn:
        self.__renderer: Renderer
        self.__data: dt.JsonDict = data
        self.invalid_key_vals: Mapping = {"control_type": ("loop_index", "loop", "refs")}
        self.__setted: bool = False
        self.mfind: Callable[[Sequence[str], bool], set[str]] = partial(Tools.mfind, self.__data)
        self.find_k_v: Callable[[Mapping, bool], set[str]] = partial(Tools.find_key_with_values, self.__data)
        self.generate_path: MethodType = lru_cache(maxsize=32)(self.__generate_path)
        self.validate_style_sheet()

    def get_style(self, path: str) -> dt.JsonDict:
        if not self.__setted:
            raise AttributeError("Renderer was not set")
        
        if not self.__data:
            return dt.JsonDict()

        paths: Sequence[str]
        data: dt.JsonDict = {}
        holder: dt.JsonDict
        key: str

        for paths in self.generate_path(path):
            holder = {}
            for key in paths:
                try:
                    holder = self.__data[key] if not holder else holder[key]
                except:
                    return {}
            data.update(holder)
        return data

    def __generate_path(self, path: str) -> Sequence[Sequence[str]]:
        splitted: Sequence[str]
        
        if not self.__setted:
            raise AttributeError("Renderer was not set")

        try:
            splitted = path.split(" ")
        except ValueError:
            splitted = []

        return (
            [path.split(".")]
            if not splitted
            else list(map(lambda x: x.split("."), splitted))
        )
        
    def validate_style_sheet(self) -> NoReturn:
        invalid_keys: Sequence[str] = list(self.mfind(constants.INVALID_STYLE_KEYS, True))
        if invalid_keys:
            raise KeyError(f"The invalid keys of, {invalid_keys}, were found in the style sheet")
        invalid_values: Sequence[str] = list(self.find_k_v(self.invalid_key_vals))
        if invalid_values:
            raise ValueError(f"The invalid values of, {invalid_values}, were found in the style sheet")

    def setter(self, renderer: Renderer) -> NoReturn:
        if not self.__setted:
            self.__renderer: Renderer = renderer
            self.__renderer.register_controls(self.__data)
            self.__setted = True
    
    @property
    def data(self) -> JsonDict:
        return self.__data


class Property:
    __slots__ = ["name", "obj"]
    def __init__(self, name: str, obj: Any):
        self.name: str = name
        self.obj: Any = obj


class SetupFunctions:
    __slots__ = ["__container", "__backend"]
    
    def __init__(self, backend: Backend) -> NoReturn:
        self.__backend: Backend = backend
        self.__container: Sequence[Callable] = []
    
    def add_func(self, func: Callable, parameters: Sequence[Any]) -> NoReturn:
        if not callable(func):
            raise ValueError(f"Value {func.__name__} is not Callable")
        if utils.is_sequence_not_str(parameters):
            raise TypeError(f"Value parameters is not an Iterable")
        self.__container.append(
            partial(func, *parameters)
        )
    
    def mass_add_func(self, items: Sequence[tuple[Callable, Sequence[Any]]]) -> NoReturn:
        values: tuple[Callable, Sequence[str]]
        for values in items:
            if not is_sequence_not_str(values):
                continue
            if len(values) != 2:
                continue
            self.add_func(*values)
    
    def call_functions(self) -> NoReturn:
        function: Callable
        for function in self.__container:
            self.__backend.page.run_task(function)


class PropertyContainer:
    __slots__ = ["__core_obj", "__tools", "__props", "__valid_operators"]
    
    def __init__(self, core_obj: Backend, tools: utils.Utilities) -> NoReturn:
        self.__core_obj: Backend = core_obj
        self.__tools: utils.Utilities = tools
        self.__props: Mapping[str, Property] = {}
        self.__valid_operators: tuple[str, str, str] = ("set", "get", "del")

    def contains(self, name: str) -> bool:
        return name in self.__props

    def add(self, name: str, obj: Any) -> NoReturn:
        prop: Property = Property(name, obj)
        arg_len: int = len(self.__tools.get_object_args(obj))
        if callable(prop.obj) and arg_len == 0:
            prop.obj = self.__make_method(prop.obj)
        elif arg_len > 0:
            raise ValueError(f"Function {obj.__name__} with set name {name} has too many parameters. 0 parameters expected")
        self.__props[name] = prop
    
    def validate_operator(self, operator: str) -> bool:
        return operator in self.__is_valid_operator
    
    def call(
        self, name: str, operation: PropertyLiteral = "get",
        set_val: Any = None,
    ) -> Any:
        
        if not self.validate_operator(operation) or not self.contains(name):
            return None
        
        if set_val and operation == "set":
            return self.add(name, set_val)

        prop: Property = self.__props[name]
        if operation == "get":
            return prop.obj() if callable(prop.obj) else prop.obj

        if operation == "del":
            del self.__props[name]

    def __make_method(self, obj: Callable) -> MethodType:
        return MethodType(obj, self.__core_obj)


class ControlLoader:
    __slots__ = ["__cls", "__file_op_class", "__th_serializer"]
    
    def __init__(self, cls: Backend) -> NoReturn:
        self.__cls: Backend = cls
        self.__file_op_class: utils.RegistryFileOperations = utils.RegistryFileOperations

    @cached_property
    def control_registry(self) -> dt.ControlRegistryJsonScheme:
        return self.__file_op_class.load_file()
    
    def add_custom_controls(self, names: Sequence[tuple[str, dt.ControlType]]) -> NoReturn:
        name: str
        control: dt.ControlType
        
        for name, control in names:
            self.__cls.compiled_program.control_map[name] = control
            self.__cls.compiled_program.type_hints[name] = Tools.get_hints(control)
                

    def add_controls(self, names: Sequence[str]) -> NoReturn:
        name: str
        registered_controls: dt.ControlJsonScheme

        for name in names:
            if name in self.__cls.compiled_program.control_map.keys():
                continue

            if name not in self.control_registry["Controls"]:
                raise err.ControlNotFoundError(name)

            registered_controls = self.control_registry["ControlTypes"][
                self.control_registry["Controls"].index(name)
            ]

            self.__cls.compiled_program.type_hints[name] = utils.TypeHintSerializer.deserialize(
                registered_controls["type_hints"]
            )
            
            self.__cls.compiled_program.control_map[name] = getattr(
                utils.import_module(registered_controls["source"]), 
                registered_controls["attr"]
            )


class Unpacker:
    
    def __init__(self, renderer: Renderer):
        self.__renderer = renderer
        self.settings: dt.ControlSettings
        self.unpack_data: Any
        self.unpacker: Callable
        self.unpack_data: Callable
        
    
    def unpack(self, settings: dt.ControlSettings) -> dt.ControlSettings:
        self.settings = settings
        self.unpack_data = settings.get("unpack", None)
        self.update_del = partial(
            Tools.update_del_dict, main_dict=self.settings, delete_key="unpack"
        )
        self.unpacker = partial(Tools.unpack_validator, self.unpack_data)
        return self.unpack_function()
    
    def unpack_function(self) -> dt.ControlSettings:
        res: Any
        success: bool

        if not self.unpack_data or not isinstance(self.unpack_data, Mapping):
            return self.update_del()
        
        res, success = self.unpacker(key="code_refs", get_method=self.__renderer.get_ref, use_dict=True)
        if success:
            if not isinstance(res, Mapping):
                return self.update_del()
            return self.update_del(update_dict=res)
        
        res, success = self.unpacker(key="styling", get_method=self.__renderer.style_sheet.get_style)
        if success:
            if not isinstance(res, Mapping):
                return self.update_del()
            return self.update_del(update_dict=res)


class TypeCheck:
    
    keys: Sequence[str] = [
        "refs", "code_refs", "styling", "control_type", 
        "call", "func", "route", "eval"
    ]
    
    @classmethod
    def list_filter(cls, item: Any, keys: Sequence[str]) -> bool:
        if not isinstance(item, Mapping):
            return False
        
        for key in keys:
            if key in item:
                return True
    
    @classmethod
    def clean_list(cls, data: Sequence) -> Sequence:
        return list(
            itertools.filterfalse(
                partial(
                    cls.list_filter, 
                    keys=cls.keys
                ), 
                data
            )
        )
    
    @classmethod
    def type_rectification(cls, settings: dt.ControlSettings, types: dt.TypeHints = {}) -> dt.ControlSettings:
        key: str
        value: Any
        
        for key, value in settings.items():
            if key not in types:
                continue
            
            if not tc.type_check(value, types[key]):
                settings[key] = (
                    cls.clean_list(value) 
                    if utils.is_sequence_not_str(value) 
                    else None
                )
        
        return settings