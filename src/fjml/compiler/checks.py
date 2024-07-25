from __future__ import annotations
from typing import Sequence, Any, Mapping, TYPE_CHECKING, Union
from ..object_enums import *
if TYPE_CHECKING:
    from .. import data_types as dt



class Checker:
    data: Sequence[tuple[str, Any]]
    names: Sequence[str]
    dtypes: dt.TypeHints
    optional: Sequence[str]
    
    @classmethod
    def correct(self, data: JsonDict) -> Mapping:
        self.data = data.items()
        return self.validate_dict()
    
    @classmethod
    def validate_dict(self) -> Mapping:
        key: str
        value: Any
        result: Mapping = {MarkupKeys.SKIP:False}

        for key, value in self.data:
            if key not in self.names:
                continue
            if isinstance(value, self.dtypes[key]):
                result[key] = value
                continue
            if key in self.optional:
                result[key] = self.dtypes[key]()
                continue
            
            result[MarkupKeys.SKIP] = True
            return result
        return result

class ControlCheck(Checker):
    names = [ControlKeys.CONTROL_TYPE, ControlKeys.SETTINGS]
    dtypes = {ControlKeys.CONTROL_TYPE:str, ControlKeys.SETTINGS:dict}
    optional = [ControlKeys.SETTINGS]
    
    @classmethod
    def correct(self, data: JsonDict, cls: Any = None) -> Union[Mapping, None]:
        res: Mapping = super().correct(data)
        if res[MarkupKeys.SKIP]:
            return
        if data[ControlKeys.CONTROL_TYPE] not in cls.controls_registry[ControlRegKeys.CONTROLS]:
            res[MarkupKeys.SKIP] = True
            return
        return res


class NamedControlCheck(Checker):
    names = [ControlKeys.VAR_NAME, ControlKeys.CONTROL_TYPE, ControlKeys.SETTINGS]
    dtypes = {ControlKeys.VAR_NAME:str, ControlKeys.CONTROL_TYPE:str, ControlKeys.SETTINGS:dict}
    optional = [ControlKeys.SETTINGS]
    
    @classmethod
    def correct(self, data: JsonDict, cls: Any = None) -> Union[Mapping, None]:
        res: Mapping = super().correct(data)
        if res[MarkupKeys.SKIP]:
            return
        if data[ControlKeys.CONTROL_TYPE] not in cls.controls_registry[ControlRegKeys.CONTROLS]:
            res[MarkupKeys.SKIP] = True
            return
        return res


class RouteCheck(Checker):
    names = [ControlKeys.ROUTE, ControlKeys.SETTINGS]
    dtypes = {ControlKeys.ROUTE:str, ControlKeys.SETTINGS:Mapping}
    optional = [ControlKeys.SETTINGS]
    
    @classmethod
    def correct(self, data: JsonDict, cls: Any = None) -> Union[Mapping, None]:
        res: Mapping = super().correct(data)
        if not res[MarkupKeys.SKIP]:
            return res