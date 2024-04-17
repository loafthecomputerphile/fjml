from typing import (
    Callable, 
    Any, 
    Optional, 
    Union,
    Iterator,
    Final,
    NoReturn
)
from types import MethodType
from functools import lru_cache
import importlib
import asyncio
import inspect
import re
from zipfile import ZipFile
import shutil
from random import randint
from dataclasses import dataclass
from datetime import datetime

from .constants import ARCHIVE_FORMAT

import_module = lru_cache(16)(importlib.import_module)

class ProgramImporter:
    
    __slots__ = ("return_path")
    
    def __init__(self, program_name: str) -> NoReturn:
        self.return_path: str = f"temp/open_programs/{randint(1,2000000000)}"
        shutil.unpack_archive(
            f"programs/{program_name}.gui", 
            self.return_path, 
            ARCHIVE_FORMAT
        )
        
    def clear_temp(self) -> NoReturn:
        shutil.rmtree(self.return_path, ignore_errors=False)


class Utilities:
    
    @staticmethod
    def get_object_args(func: Callable) -> list[str]:
        """
        get_object_args _summary_
        
        Args:
            func (Callable): _description_
        
        Returns:
            list[str]: _description_
        """
        if not callable(func):
            return []
        return inspect.getfullargspec(func).args
    
    @staticmethod
    def check_for_only_self(func: Callable[[Any,], Any]) -> NoReturn:
        """
        check_for_only_self _summary_
        
        Args:
            func (Callable[[Any,], Any]): _description_
        
        Raises:
            ValueError: _description_
            ValueError: _description_
        """
        args: tuple[str, ...] = func.__code__.co_varnames[:func.__code__.co_argcount]
        if len(args) != 1:
            raise ValueError("A setup or mount function must only have 1 argument")
        if args[0] != "self":
            raise ValueError("A setup or mount function must only have 'self' as a sole argument")
        
    @staticmethod
    def check_for_dict( settings: dict[str, Any]) -> bool:
        """
        check_for_dict _summary_
        
        Args:
            settings (dict[str, Any]): _description_
        
        Returns:
            bool: _description_
        """
        return any(isinstance(val, dict) for val in settings.values())
    
    @staticmethod
    def get_keys_with_dict(settings: dict[str, Any]) -> list[str]:
        """
        get_keys_with_dict _summary_
        
        Args:
            settings (dict[str, Any]): _description_
        
        Returns:
            list[str]: _description_
        """
        return [key for key, value in settings.items() if isinstance(value, dict)]
    
    @staticmethod
    def get_keys_with_list(settings: dict[str, Any]) -> list[str]:
        """
        get_keys_with_list _summary_
        
        Args:
            settings (dict[str, Any]): _description_
        
        Returns:
            list[str]: _description_
        """
        return [key for key, value in settings.items() if isinstance(value, list)]

    @staticmethod
    async def function_join(fn: Callable[..., None], fn_2: Callable[..., None]) -> Callable[..., None]:
        """
        function_join _summary_
        
        Args:
            fn (Callable[..., None]): _description_
            fn_2 (Callable[..., None]): _description_
        
        Returns:
            Callable[..., None]: _description_
        """
        async def new_function(*args, **kwargs):
            if asyncio.iscoroutinefunction(fn):
                await fn(*args, **kwargs)
            else:
                fn(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(fn_2):
                await fn_2(*args, **kwargs)
            else:
                fn_2(*args, **kwargs)
        
        return new_function
    
    @staticmethod
    def find_values(json_obj: dict[str, Any], key: str) -> set[str]:
        """
        find_values _summary_
        
        Args:
            json_obj (dict[str, Any]): _description_
            key (str): _description_
        
        Returns:
            set[str]: _description_
        """
        results: set[str] = set()
        k: str
        v: Any
        item: dict[str, Any]
        
        if isinstance(json_obj, dict):
            for k, v in json_obj.items():
                if k == key:
                    results.add(v)
                elif isinstance(v, (dict, list)):
                    results.update(Utilities.find_values(v, key))
        elif isinstance(json_obj, list):
            for item in json_obj:
                results.update(Utilities.find_values(item, key))
        
        return results
    
    @staticmethod
    @lru_cache(maxsize=64)
    def event_filter(data: str) -> bool:
        return data.startswith("on_")
    
    @staticmethod
    #@lru_cache(maxsize=128)
    def load_object(module_path: str, package: Optional[str] = None, obj_name: Optional[str] = None) -> Any:
        """
        load_object _summary_
        
        Args:
            module_path (str): _description_
            obj_name (str): _description_
        
        Returns:
            Any: _description_
        """
        return getattr(
            import_module(
                module_path, package
            ),
            obj_name
        )
    
    @staticmethod
    def get_init_parameters(instance: Any) -> dict[str, Any]:
        param: Any
        param_name: str
        
        init_method: MethodType = instance.__init__
        init_signature: inspect.Signature = inspect.signature(init_method)
        params: dict[str, Any] = {}
        for param_name, param in init_signature.parameters.items():
            if param_name != 'self':  # Exclude 'self'
                params[param_name] = getattr(instance, param_name)
        return params
    


DTYPES: list[str] = ["date", "float", "integer", "currency", "text"]
VALIDATOR_KWARGS: dict[str, Any] = {"dtype": "text", "currency_decimals":2, "date_format":r"%d/%m/%Y"}


@dataclass
class Validator:
    dtype: str = "text"
    currency_decimals: int = 2
    date_format: str = r"%d/%m/%Y"
    
    def __post_init__(self) -> NoReturn:
        if self.dtype not in DTYPES:
            raise TypeError(f"Validator data type must be in {DTYPES}, recieved data type {self.dtype} instead")
    
    def validate(self, data: str) -> bool:
        if not data: return True
        if self.dtype == "text": return isinstance(data, str)
        if self.dtype == "float": return self.is_float(data)
        if self.dtype == "integer": return data.isdigit()
        if self.dtype == "date": return self.validate_dates(data, self.date_format)
        if self.dtype == "currency": return self.is_float(data)
    
    def is_float(string: str) -> bool:
        pattern = r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?"
        match = re.match(pattern, string)
        return bool(match)
    
    def validate_dates(date: str, date_format: str) -> bool:
        try:
            datetime.strptime(date, date_format)
            return True
        except ValueError:
            return False