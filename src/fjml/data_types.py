from __future__ import annotations
import io
from dataclasses import dataclass, field
import json
from abc import ABC, abstractmethod
from typing import (
    Any, TypedDict,
    Union, TypeAlias,
    Protocol, Iterable,
    NoReturn
)
import inspect
from enum import Enum

import flet as ft

from . import utils

Tools: utils.Utilities = utils.Utilities()

__all__ = [
    "JsonDict", "ControlSettings", "ControlMap", 
    "ControlModel", "NamedControlDict",
    "ParsedControls", "CompiledModel", "TypedList",
    "FunctionVariable", "ControlRegistryJsonScheme", "ControlJsonScheme",
    "RefDict", "ControlDict", "UserInterfaceViews",
    "RouteDict", "RouteView", "ImportDict",
    "UserInterfaceDict", "ParsedUserInterface", "LoopDict",
    "LoopItem", "ControlRegistryDictPreview", "EventContainer",
    "FunctionModel", "ControlContainer", "LoaderParameters",
    "ControlBundle", "ControlRegistryModel", "TypeDict",
    "ObjectSource"
]

class TypedList(list):
    def __init__(self, iterable: Iterable[Any], dtype: Any) -> NoReturn:
        self.dtype: Any = dtype
        super().__init__(self._validate_number(item) for item in iterable)

    def __setitem__(self, index: int, item: Any) -> NoReturn:
        super().__setitem__(index, self._validate_number(item))

    def insert(self, index: int, item: Any) -> NoReturn:
        super().insert(index, self._validate_number(item))

    def append(self, item: Any) -> NoReturn:
        super().append(self._validate_number(item))

    def extend(self, other: Union[Iterable[Any], Any]) -> NoReturn:
        if isinstance(other, type(self)):
            super().extend(other)
        else:
            super().extend(self._validate_number(item) for item in other)

    def _validate_number(self, value: Any) -> Any:
        if isinstance(value, self.dtype):
            return value
        raise TypeError(
            f"{self.dtype.__name__} value expected, got {type(value).__name__}"
        )


class TypeDict(dict):
    def __init__(self, dictionary: dict[str, Any], value_type: Any) -> None:
        self.value_type = value_type
        super().__init__({key: self._validate_value(value) for key, value in dictionary.items()})

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, self._validate_value(value))

    def update(self, dictionary: dict[str, Any]) -> None:
        super().update({key: self._validate_value(value) for key, value in dictionary.items()})

    def _validate_value(self, value: Any) -> Any:
        if isinstance(value, self.value_type):
            return value
        raise TypeError(
            f"{self.value_type.__name__} value expected, got {type(value).__name__}"
        )


class EventContainer(ABC):
    
    @abstractmethod
    async def _page_setup(self) -> NoReturn:
        ...
    
    @abstractmethod
    async def _imports(self) -> NoReturn:
        ...
    
    @abstractmethod
    async def _on_close(self) -> NoReturn:
        ...


class ControlRegistryDictPreview(TypedDict):
    name: str
    source: str
    attr: str
    is_awaitable: bool


class ControlJsonScheme(TypedDict):
    name: str
    source: str
    attr: str
    awaitable: bool
    valid_settings: list[str]


class ControlRegistryJsonScheme(TypedDict):
    Controls: list[str]
    ControlTypes: list[ControlJsonScheme]


class NamedControlDict(TypedDict):
    var_name: str
    control_type: str
    bundle: str
    settings: str


class RefDict(TypedDict):
    ref: str

ControlContainer: TypeAlias = list[NamedControlDict]
ControlSettings: TypeAlias = dict[str, Union["ControlDict", RefDict, None, str, int, float, bool, list, dict]]

class ControlDict(TypedDict):
    control_type: str
    settings: ControlSettings

RouteView: TypeAlias = Union[ControlDict, RefDict]

class RouteDict(TypedDict):
    route: str
    settings: ControlSettings


class LoopItem(TypedDict):
    control_type: str
    idx: list[int]


class LoopDict(TypedDict):
    control_type: str
    depth: int
    iterator: Union[list[Any], RefDict]
    control: Union[ControlDict, NamedControlDict]


class ImportDict(TypedDict):
    source: str


class UserInterfaceDict(TypedDict):
    Imports: list[ImportDict]
    Controls: list[NamedControlDict]
    UI: Union[list[RouteDict], ControlDict, RefDict]


@dataclass
class FunctionModel:
    func_name: str = ""
    args: tuple[Any] = field(default_factory=tuple)


JsonDict: TypeAlias = dict[str, Any]
ControlMap: TypeAlias = dict[str, ft.Control]


@dataclass
class ControlModel:
    name: str = ""
    control_name: str = ""
    bundle_name: str = ""
    control: ft.Control = field(default=None)
    settings: ControlSettings = field(default_factory=ControlSettings)
    valid_settings: list[str] = field(default_factory=list)


@dataclass
class UserInterfaceViews:
    route: str = ""
    settings: ControlSettings = field(default_factory=dict)


@dataclass
class FunctionVariable:
    name: str = ""
    value: Any = None


ParsedUserInterface: TypeAlias = dict[str, UserInterfaceViews]
ParsedControls: TypeAlias = dict[str, ControlModel]


@dataclass
class CompiledModel:
    controls: ParsedControls = field(default_factory=ParsedControls)
    ui: list[UserInterfaceViews] = field(default_factory=list)
    control_awaitable: dict[str, bool] = field(default_factory=dict)
    control_map: ControlMap = field(default_factory=ControlMap)
    routes: list[str] = field(default_factory=list)
    control_bundles: set[str] = field(default=set)


@dataclass
class LoaderParameters:
    page: ft.Page
    program_name: str
    ui_code: str
    imports_path: str
    methods: Union[EventContainer, None] = field(default=None)
    custom_controls: list[ControlJsonScheme] = field(default_factory=list)
    UserBuild: Optional[Type["Build"]] = field(default=None)
    
    def __post_init__(self) -> NoReturn:
        file: io.TextIOWrapper
        
        if not isinstance(self.ui_code, str):
            return
        
        if self.ui_code[-7:] != "ui.json":
            raise Exception("ui_code file must be named \"ui.json\"")
        
        with open(self.ui_code, "r") as file:
            self.ui_code = json.load(file)

@dataclass
class ObjectSource:
    obj: Any
    source: str
    
    def __post_init__(self):
        self.is_class: bool = inspect.isclass(self.obj)
    
@dataclass
class ControlBundle:
    names: list[str]
    getter: Callable
    
    def __post_init__(self) -> NoReturn:
        if not callable(getter):
            raise ValueError("Value for attribute, getter, in ControlBundle is not callable")
        
        self.__count: int = 0
        self.__start: int = 0
    
    def add(control_name: str) -> NoReturn:
        self.names.append(control_name)
        self.__count += 1
    
    def remove(control_name: str) -> NoReturn:
        self.names.remove(control_name)
        self.__count -= 1
    
    def update(control_names: list[str]) -> NoReturn:
        self.names.extend(control_names)
        self.__count += len(control_names)
    
    def __next__(self) -> str:
        if self.__start < self.__count:
            self.__start += 1
            return self.getter(self.names[self.__start-1])
        
        self.__start = 0
        raise StopIteration


@dataclass
class ControlRegistryModel:
    name: str = ""
    source: ObjectSource = None
    attr: str = ""
    is_awaitable: bool = False
    
    def __post_init__(self) -> NoReturn:
        self.object_args: list[str]
        
        self.object_args = self.generate_args()
        if not self.source.is_class:
            pass
        elif issubclass(self.source.obj, Enum):
            self.object_args = self.generate_args(is_enum=True)
            
        self.source = self.source.source
        
        self.return_dict: ControlJsonScheme = ControlJsonScheme(
            name=self.name,
            source=self.source,
            attr=self.attr,
            awaitable=self.is_awaitable,
            valid_settings=self.object_args
        )
        
    def generate_args(self, is_enum: bool = False) -> list[str]:
        
        if is_enum:
            return self.remove_instance_refs(
                list(map(lambda enum: enum.value, self.source.obj))
            )
        
        if callable(self.source.obj):
            return self.remove_instance_refs(
                Tools.get_object_args(self.source.obj)
            )
        
        return []
    
    def remove_instance_refs(self, data: list[str]) -> list[str]:
        check = lambda arg, lst: lst[0] == arg
        
        if len(data) == 0: return data
        if check("self", data): del data[0]
        if len(data) == 0: return data
        if check("cls", data): del data[0]
        
        return data