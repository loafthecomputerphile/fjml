from __future__ import annotations
from typing import (
    Callable,
    Any,
    Optional,
    Sequence,
    Mapping,
    TYPE_CHECKING,
    get_type_hints
)

import typing

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

from functools import lru_cache, partial
import importlib, inspect, os, io, json, operator
import errno, dill, base64, copy, gzip, types

from flet import Control

from .constants import (
    NULL, CONTROL_REGISTRY_PATH, EMPTY_REGISTRY_FILE
)
from .error_types import RegistryFileNotFoundError
from .object_enums import *
if TYPE_CHECKING:
    from . import data_types as dt
    from .display.renderer import Renderer


@lru_cache(16)
def import_module(name: str, package=None) -> types.ModuleType:
    return importlib.import_module(name, package)


class ObjectSource:
    __slots__ = ["obj", "source", "is_class"]
    def __init__(self, obj: Any, source: str = "") -> NoReturn:
        self.obj: Any = obj
        self.source: str = source
        self.is_class: bool = False
        
        if not self.source:
            self.source = self.obj.__module__
            
        self.is_class = inspect.isclass(self.obj)

def is_sequence_not_str(value: Sequence) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, str)

class Utilities:
    
    @staticmethod
    def mass_any_contains(data: Sequence, obj: Any) -> bool:
        return any(map(partial(operator.contains, obj), data))
    
    @staticmethod
    def control_to_registry_interface(
        control: Control, name_prefix: Optional[str] = None, 
        use_source: bool = False, use_module_name: bool = False,
        try_name: Optional[str] = None
    ) -> dt.ControlRegisterInterface:
        if try_name:
            name: str = control.__name__ if hasattr(control, "__name__") else try_name
        else:
            name: str = control.__name__
        plain_name: str = copy.copy(name)
        if use_module_name:
            name = f"{control.__module__.split('.')[-1]}.{name}"
        if use_source:
            return dict(
                name=name if not name_prefix else f"{name_prefix}.{name}",
                source=ObjectSource(control, source=control.__module__),
                attr=plain_name,
                control=None
            )
        
        return dict(
            name=name if not name_prefix else f"{name_prefix}.{name}",
            source=None,
            attr=plain_name,
            control=control
        )
    
    @staticmethod
    def get_hints(obj: Callable[[...], Any]) -> dt.TypeHints:
        hint: Mapping
        if not callable(obj):
            return {}
        if inspect.isclass(obj):
            hint = get_type_hints(obj.__init__)
        else:
            hint = get_type_hints(obj)
        if "return" in hint:
            del hint["return"]
        if "self" in hint:
            del hint["self"]
        return hint

    @staticmethod
    def get_object_args(func: Callable[[...], Any]) -> Sequence[str]:
        if not callable(func):
            return []
        
        return list(
            map(
                operator.attrgetter("name"), 
                inspect.signature(func).parameters.values()
            )
        )

    @staticmethod
    def valid_param_filter(settings: dt.ControlSettings, valid_settings: list[str], extra: Union[str, Sequence[str]]) -> dt.ControlSettings:
        x: tuple[str, Any]
        
        if not valid_settings:
            return {}
        
        if extra:
            if isinstance(extra, str):
                valid_settings.append(extra)
            elif isinstance(extra, Sequence):
                valid_settings.extend(extra)

        return {k:v for k,v in settings.items() if k in valid_settings}

    @staticmethod
    def get_keys_with_dict(settings: dt.JsonDict) -> Sequence[str]:
        return filter(lambda x: isinstance(settings[x], Mapping), settings)

    @staticmethod
    def get_keys_with_list(settings: dt.JsonDict) -> Sequence[str]:
        return filter(lambda x: is_sequence_not_str(settings[x]), settings)

    @staticmethod
    def find_values(json_obj: dt.JsonDict, key: str, ignore: Sequence[str] = []) -> set[str]:
        results: Sequence[str] = set()
        k: str
        v: Any
        item: Mapping
        
        if isinstance(json_obj, Mapping):
            for k, v in json_obj.items():
                if k == key and k not in ignore:
                    results.add(v)
                elif isinstance(v, Mapping) or is_sequence_not_str(v):
                    results.update(Utilities.find_values(v, key, ignore))
        elif is_sequence_not_str(json_obj):
            for item in json_obj:
                results.update(Utilities.find_values(item, key, ignore))
        
        return results
    
    @staticmethod
    def m_find(json_obj: dt.JsonDict, keys: Sequence[str], return_keys: bool = False) -> set[str]:
        results: set[str] = set()
        k: str
        v: Any
        item: Mapping
        
        if return_keys:
            if isinstance(json_obj, Mapping):
                for k, v in json_obj.items():
                    if k in keys:
                        results.add(k)
                    elif isinstance(v, Mapping) or is_sequence_not_str(v):
                        results.update(Utilities.m_find(v, keys, return_keys))
            elif is_sequence_not_str(json_obj):
                for item in json_obj:
                    results.update(Utilities.m_find(item, keys, return_keys))
            
            return results
            
        if isinstance(json_obj, Mapping):
            for k, v in json_obj.items():
                if k in keys:
                    results.add(v)
                elif isinstance(v, Mapping) or is_sequence_not_str(v):
                    results.update(Utilities.m_find(v, keys, return_keys))
        elif isinstance(json_obj, Sequence):
            for item in json_obj:
                results.update(Utilities.m_find(item, keys, return_keys))

        return results
    
    @staticmethod
    def find_key_with_values(json_obj: dt.JsonDict, key_vals: Mapping[str, tuple[Any]], return_keys: bool = False) -> set[str]:
        results: set[str] = set()
        k: str
        v: Any
        item: Mapping

        if return_keys:
            if isinstance(json_obj, Mapping):
                for k, v in json_obj.items():
                    res = key_vals.get(k, NULL)
                    if res != NULL and v in res:
                        results.add(k)
                    elif isinstance(v, Mapping) or is_sequence_not_str(v):
                        results.update(Utilities.find_key_with_values(v, key_vals, return_keys))
            elif is_sequence_not_str(json_obj):
                for item in json_obj:
                    results.update(Utilities.find_key_with_values(item, key_vals, return_keys))

            return results
            
        if isinstance(json_obj, Mapping):
            for k, v in json_obj.items():
                res = key_vals.get(k, NULL)
                if res != NULL and v in res:
                    results.add(v)
                elif isinstance(v, Mapping) or is_sequence_not_str(v):
                    results.update(Utilities.find_key_with_values(v, key_vals, return_keys))
        elif is_sequence_not_str(json_obj):
            for item in json_obj:
                results.update(Utilities.find_key_with_values(item, key_vals, return_keys))

        return results

    @staticmethod
    def get_init_parameters(instance: Any) -> Mapping:
        x: tuple[str, Any]
        
        return dict(
            map(
                lambda x: (x, getattr(instance, *x)), 
                filter(
                    lambda x: x[0] != "self", 
                    inspect.signature(instance.__init__).parameters.items()
                )
            )
        )
    
    @staticmethod
    def multi_dict_get(data: Mapping, items: Sequence[str]) -> Any:
        result: Any
        item: str
        
        for item in items:
            result = data.get(item, None)
            if data: 
                return result

    @staticmethod
    def update_del_dict(main_dict: Mapping, delete_key: str, update_dict: Mapping = {}) -> Mapping:
        if delete_key not in main_dict:
            return main_dict
            
        if update_dict:
            main_dict.update(update_dict)
        
        del main_dict[delete_key]
        
        return main_dict

    @staticmethod
    def unpack_validator(unpack_dict: Mapping, key: str, get_method: Callable, use_dict: bool = False) -> dt.JsonDict:
        value: Any = unpack_dict.get(key, None)
        res: Anu
        if not value or not isinstance(value, str):
            return {}
        
        if use_dict:
            res = get_method(unpack_dict)
        else:
            res = get_method(value)
            
        if isinstance(res, Mapping):
            return res
        
        return {}
    
    @staticmethod
    def validate_index(
        data: Mapping, depth_count: int, is_ref: bool = False
    ) -> str:
        if is_ref and data.get(ControlKeys.CONTROL_TYPE, None) != LoopKeys.LOOP_INDEX:
            return NULL
        val: Any = data.get(LoopKeys.IDX, None)
        if not val:
            return NULL
        if not is_sequence_not_str(val):
            return NULL
        if len(val) != 2 or val[0] >= depth_count:
            return NULL

    @staticmethod
    def refs_type(data: Mapping) -> str:
        if RefsKeys.REFS in data:
            return RefsKeys.REFS
        elif RefsKeys.CODE_REFS in data:
            return RefsKeys.CODE_REFS
        return ""

    @staticmethod
    def parse_reference(cls: Renderer, content: Mapping) -> Any:
        if not isinstance(content, Mapping):
            return
        
        return cls.get_ref(
            Utilities.search_and_sanitize(
                content, cls.depth_count, cls.loop_values
            )
        )

    @staticmethod
    def sanitize(data: Mapping, depth_count: int, loop_values: Sequence) -> int:
        if Utilities.validate_index(data, depth_count) == NULL:
            return 
        
        idx: int = data[LoopKeys.IDX]
        vals: Any = loop_values[idx[0]]
        
        if not is_sequence_not_str(vals):
            return vals
        
        return vals[idx[1]]


    @staticmethod
    def process_loop_iterator(
        cls: Renderer, iterator_value: Union[Mapping, Sequence]
    ) -> Sequence:
        
        if is_sequence_not_str(iterator_value):
            return iterator_value

        if isinstance(iterator_value, Mapping):
            value: Any = iterator_value.get(LoopKeys.RANGE, None)
            if is_sequence_not_str(value):
                if len(value) > 3:
                    value = value[:3]
                if not all(isinstance(i, int) for i in value):
                    return []
                if len(value) > 0:
                    return range(*value)
                return []

            if RefsKeys.CODE_REFS not in iterator_value:
                return []
            if RefsKeys.REFS in iterator_value:
                return []
            
            result: Sequence = cls.get_ref(iterator_value)
            
            if not is_sequence_not_str(result):
                return []
            
            return result
        
        return []


    @staticmethod
    def search_and_sanitize(
        data: Union[Mapping, Sequence],
        depth_count: int,
        loop_values: Sequence,
    ) -> Union[Mapping, Sequence]:
        result: Union[Mapping, Sequence]
        key: str
        item: Any
        value: Any
        
        if isinstance(data, Mapping):
            result = {}
            for key, value in data.items():
                if isinstance(value, Mapping):
                    if value.get(ControlKeys.CONTROL_TYPE, "") == LoopKeys.LOOP_INDEX:
                        new_value = Utilities.sanitize(value, depth_count, loop_values)
                        result[key] = new_value
                    else:
                        result[key] = Utilities.search_and_sanitize(value, depth_count, loop_values)
                elif is_sequence_not_str(value):
                    result[key] = [
                        Utilities.search_and_sanitize(item, depth_count, loop_values)
                        for item in value
                    ]
                else:
                    result[key] = value
            return result
        elif is_sequence_not_str(data):
            return [Utilities.search_and_sanitize(item, depth_count, loop_values) for item in data]
        else:
            return data

class CompiledFileHandler:
    
    @staticmethod
    def save(file_path: str, data: dt.CompiledModel) -> NoReturn:
        file: gzip.GzipFile
        with open(file_path, "wb") as file:
            dill.dump(data, file)
    
    @staticmethod
    def load(file_path: str) -> dt.CompiledModel:
        file: gzip.GzipFile
        if not os.path.exists(file_path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        with open(file_path, "rb") as file:
            return dill.load(file)


class ObjectCompressor:
    
    @staticmethod
    def compress(obj: Any) -> bytes:
        return gzip.compress(
            dill.dumps(obj), 9
        )
    
    @staticmethod
    def decompress(compressed_obj: bytes) -> Any:
        return dill.loads(
            gzip.decompress(compressed_obj)
        )

class TypeHintSerializer:
    
    @classmethod
    def decode(cls, data: str) -> dt.TypeHints:
        return dill.loads(
            base64.b64decode(data)
        )
    
    @classmethod
    def encode(cls, data: dt.TypeHints) -> str:
        return base64.b64encode(
            dill.dumps(
                TypeHintSerializer.string_to_any(data)
            )
        ).decode("utf8")
    
    @classmethod
    def serialize(cls, data: dt.TypeHints) -> Mapping[str, str]:
        return dict(map(lambda x: (x[0], cls.encode(x[1])), data.items()))
    
    @classmethod
    def deserialize(cls, data: Mapping[str, str]) -> dt.TypeHints:
        return dict(map(lambda x: (x[0], cls.decode(x[1])), data.items()))
    
    @staticmethod
    def string_to_any(dtype: Union[type, str]) -> type:
        return Any if isinstance(dtype, str) else dtype


class RegistryFileOperations:

    @classmethod
    def load_file(cls) -> dt.ControlRegistryJsonScheme:
        registry: io.TextIOWrapper
        if not os.path.exists(CONTROL_REGISTRY_PATH):
            with open(CONTROL_REGISTRY_PATH, "wb") as registry:
                dill.dump(EMPTY_REGISTRY_FILE, registry, dill.HIGHEST_PROTOCOL)
        with open(CONTROL_REGISTRY_PATH, "rb") as registry:
            return dill.load(registry)
        raise RegistryFileNotFoundError()

    @classmethod
    def save_file(cls, file_data: dt.JsonDict) -> NoReturn:
        registry: io.TextIOWrapper
        with open(CONTROL_REGISTRY_PATH, "wb") as registry:
            return dill.dump(file_data, registry, dill.HIGHEST_PROTOCOL)
        raise RegistryFileNotFoundError()


