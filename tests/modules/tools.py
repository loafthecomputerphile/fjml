from typing import Callable, Any, Type, Union, Iterable, Optional, NoReturn
from dataclasses import dataclass, field
from collections import deque
import shelve
import functools
from shelve import DbfilenameShelf
import asyncio
import os.path as Path
import os
import asyncio


async def function_join(fn: Callable[[Any], None], fn_2: Callable[[Any], None]) -> Callable[[Any], None]:
    async def new_function(*args, **kwargs):
        
        if not fn:
            ...
        elif asyncio.iscoroutinefunction(fn):
            await fn(*args, **kwargs)
        else:
            fn(*args, **kwargs)
        
        if not fn_2:
            ...
        elif asyncio.iscoroutinefunction(fn_2):
            await fn_2(*args, **kwargs)
        else:
            fn_2(*args, **kwargs)
    
    return new_function


async def event_join(fn: Callable[[Any], None], fn_2: Callable[[Any], None], e) -> NoReturn:
    if not fn:
        ...
    elif not callable(fn):
        ...
    elif asyncio.iscoroutinefunction(fn):
        await fn(e)
    else:
        fn(e)
    
    if not fn_2:
        ...
    elif not callable(fn_2):
        ...
    elif asyncio.iscoroutinefunction(fn_2):
        await fn_2(e)
    else:
        fn_2(e)
    



def try_(default: Any, fall_back: Any, default_attr: Optional[str] = None, fall_back_attr: Optional[str] = None) -> Any:
    result: Any = None
    try:
        result = default
        if default_attr:
            result = getattr(default, default_attr)
    except:
        result = fall_back
        if fall_back_attr:
            result = getattr(fall_back, fall_back_attr)
    return result


@dataclass
class MemoizeData:
    data: Any = field(default_factory=None)
    limit: int = 0
    num_calls: int = 0
    
    def increment_calls(self) -> NoReturn:
        self.num_calls += 1
        
    def __eq__(self, other) -> bool:
        return self.data == try_(other, other, "data")
    


class Memoizer:
    
    __slots__ = ("limit", "cache", "order", "obj", "storage_name", "use_obj")
    
    def __init__(self, obj, storage_name, limit: int, use_obj: bool = True) -> NoReturn:
        self.limit: int = limit
        self.obj = obj
        self.use_obj = use_obj
        self.storage_name = f"{storage_name}_mem"
        self.cache: dict[str, MemoizeData] = {}
        self.order: deque = deque([])

    async def memoize(self, key: str, value: Any) -> NoReturn:
        storage: dict[int, MemoizeData]
        
        if self.use_obj:
            storage = self.obj.page.session.get(self.storage_name)
            storage[key] = MemoizeData(value, self.limit)
            self.obj.page.session.set(self.storage_name, storage)
            return
        
        if len(self.order) >= self.limit:
            self.cache.pop(
                self.order.pop(0)
            )
        
        self.order.append(key)
        self.cache[key] = value

    async def is_memoized(self, key: str) -> bool:
        if not self.use_obj:
            return key in self.cache
        return key in self.obj.page.session.get(self.storage_name)
    
    async def get_value(self, key: str) -> Any:
        container: Optional[MemoizeData]
        result: Any
        storage: dict[int, MemoizeData]
        
        if not self.use_obj:
            return self.cache[key]
        
        storage = self.obj.page.session.get(self.storage_name) 
        container = storage.get(key, None)
        if not container:
            return
        
        if container.num_calls >= self.limit:
            result = container.data
            del storage[key]
            self.obj.page.session.set(self.storage_name, storage)
            return result
        
        result = container.data
        container.increment_calls()
        storage[key] = container
        self.obj.page.session.set(self.storage_name, storage)
        return result


class ShelveMemoizer:
    
    __slots__ = ('filename', 'window', 'tempdir', 'path', 'limit', "extentions", "file")

    def __init__(self, filename: str, window: int, tempdir: str = "", limit: int = 8) -> NoReturn:
        self.filename: str = filename
        self.window: int = window
        self.tempdir: str = tempdir
        self.limit: int = limit
        self.extentions: list[str] = ["bak", "dat", "dir"]
        self.file: str = f"{self.filename}.{self.window}.smdb"
        if len(self.tempdir) > 0:
            self.path = Path.join(
                self.tempdir,
                self.file
            )

    async def memoize(self, key: Union[tuple, str], value: Any) -> NoReturn:
        cache: DbfilenameShelf
        with shelve.open(self.path, writeback=True) as cache:
            if key not in cache:
                cache[key] = MemoizeData(value, limit=self.limit)

    async def is_memoized(self, key: Union[tuple, str]) -> bool:
        cache: DbfilenameShelf
        with shelve.open(self.path) as cache:
            return key in cache

    async def get_value(self, key: Union[tuple, str]) -> Any:
        cache: DbfilenameShelf
        container: Union[MemoizeData, None]
        holder: Any
        
        with shelve.open(self.path, writeback=True) as cache:
            container = cache.get(key, None)
            if not container:
                return
            
            if container.num_calls < self.limit:
                container.increment_calls()
                return container.data
            
            holder = container.data
            del cache[key]
            return holder
            
    async def populate(self, data: dict[Union[tuple, str], Any]) -> NoReturn:
        cache: DbfilenameShelf
        key: Union[tuple, str]
        value: Any
        
        with shelve.open(self.path, writeback=True) as cache:
            cache.update(
                {hash(key): value for key, value in data.items()}
            )

    async def kill(self):
        try:
            for extention in self.extentions:
                os.remove(f"{self.path}.{extention}")
        except FileNotFoundError:
            pass