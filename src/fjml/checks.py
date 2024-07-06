from __future__ import annotations
from typing import Sequence, Any, Mapping, TYPE_CHECKING
if TYPE_CHECKING:
    from . import data_types as dt



class Checker:
    data: Sequence[tuple[str, Any]]
    names: Sequence[str]
    dtypes: dt.TypeHints
    optional: Sequence[str]
    
    @classmethod
    def correct(self, data: JsonDict, cls: Any = None) -> Mapping:
        ...
    
    @classmethod
    def validate_dict(self) -> Mapping:
        result: Mapping = {"<SKIP>":False}
        count = 0
        for key, value in self.data:
            if key not in self.names:
                continue
            if not isinstance(value, self.dtypes[key]):
                if key in self.optional:
                    result[key] = self.dtypes[key]()
                    continue
                result["<SKIP>"] = True
                return result
            else:
                result[key] = value
        return result

class ControlCheck(Checker):
    names = ["control_type", "settings"]
    dtypes = {"control_type":str, "settings":Mapping}
    optional = ["settings"]
    
    @classmethod
    def correct(self, data: JsonDict, cls: Any = None) -> Mapping:
        self.data = data.items()
        res = self.validate_dict()
        if res["<SKIP>"]:
            return
        if data["control_type"] not in cls.controls_registry["Controls"]:
            res["<SKIP>"] = True
            return
        return res


class NamedControlCheck(Checker):
    names = ["var_name", "control_type", "settings"]
    dtypes = {"var_name":str, "control_type":str, "settings":Mapping}
    optional = ["settings"]
    
    @classmethod
    def correct(self, data: JsonDict, cls: Any = None) -> Mapping:
        self.data = data.items()
        res = self.validate_dict()
        if res["<SKIP>"]:
            return
        if data["control_type"] not in cls.controls_registry["Controls"]:
            res["<SKIP>"] = True
            return
        return res


class RouteCheck(Checker):
    names = ["route", "settings"]
    dtypes = {"route":str, "settings":Mapping}
    optional = ["settings"]
    
    @classmethod
    def correct(self, data: JsonDict, cls: Any = None) -> Mapping:
        self.data = data.items()
        res = self.validate_dict()
        if res["<SKIP>"]:
            return
        return res