from dataclasses import dataclass, field
from typing import Any, Union, NamedTuple, Optional, Iterable, NoReturn
import os.path as Path
import os
import shelve
import asyncio

IndexType = Union[int, tuple[int, ...], None]

#Info = tuple[Optional[tuple[IndexType, ...]], Any]
#blank: Info = (None, None)

@dataclass
class Info:
    position: IndexType = None
    value: Any = None

@dataclass
class InputData:
    link: str = ""
    operation: str = ""
    prev: Info = field(default_factory=Info)
    data: Info = field(default_factory=Info)

@dataclass
class UndoData:
    link: str = ""
    operation: str = ""
    data: Info = field(default_factory=Info)

@dataclass
class RedoData:
    link: str = ""
    operation: str = ""
    data: Info = field(default_factory=Info)


class UndoRedoBuffer:
    
    __slots__: Union[str, Iterable[str]] = (
        "__dict__", "__weakref__", "idx",
        "end", "filename", "tempdir"
    )
    
    def __init__(self, filename: str, window: int, tempdir: str = "", ) -> NoReturn:
        self.filename: str = filename
        self.window: int = window
        self.tempdir: str = tempdir
        self.path: str = Path.join(
            self.tempdir, 
            f"{self.filename}.{self.window}.urbuffer"
        )
        self.end: int = -1
        self.idx: int = -1
    
    async def undo(self) -> Union[UndoData, None]:
        data: Union[UndoData, None] = None
        with shelve.open(self.path, writeback=True) as cache:
            if self.end > 0 and self.idx >= 0:
                obj: InputData = cache[str(self.idx)]
                data: UndoData = UndoData(
                    link = obj.link,
                    operation = obj.operation,
                    data = obj.prev
                )
                self.idx -= 1
        
        return data

    async def redo(self) -> Union[RedoData, None]:
        data: Union[RedoData, None] = None
        with shelve.open(self.path, writeback=True) as cache:
            if self.idx < self.end:
                self.idx += 1
                obj: InputData = cache[str(self.idx)]
                data: RedoData = RedoData(
                    link = obj.link,
                    operation = obj.operation,
                    data = obj.data
                )
            
        return data
    
    async def add_input(self, link: str, operation: str, data: Info, prev: Info = Info()) -> NoReturn:
        with shelve.open(self.path, writeback=True) as cache:
            self.idx += 1
            self.end = self.idx
            cache[str(self.end)] = InputData(
                link = link,
                operation = form,
                prev = prev,
                data = data
            )
                
    async def peek(self) -> Union[InputData, None]:
        data: Union[InputData, None] = None
        with shelve.open(self.path, writeback=True) as cache:
            data = cache[str(self.end)]
        return data
    
    def kill(self) -> NoReturn:
        ...