from ordered_set import OrderedSet
from typing import Sequence, Any, Optional, NoReturn
from .tools import ShelveMemoizer, Memoizer
from copy import deepcopy
import asyncio

def filter_func(x: Any) -> bool:
    return not (x == "")


class TextAutoCompletion:
    
    __slots__ = (
        "amount", "count", "blank", 
        "__words", "__memoizer", "min_length",
        "obj", "name"
    )
    
    def __init__(self, name, obj, amount: int = 3, min_length: int = 3) -> NoReturn:
        self.amount: int = amount
        self.name = name
        self.obj = obj
        self.min_length: int = min_length
        self.__memoizer: Memoizer = Memoizer(obj, self.name, 8)
        self.blank: list[str] = ["" for _ in range(self.amount)]
        self.__words: OrderedSet = OrderedSet(obj.page.session.get(self.name))
        
    async def add_word(self, word: str) -> NoReturn:
        self.__words.add(word)
        
    async def update_words(self, words: list[str]) -> NoReturn:
        self.__words.update(words)
    
    async def search(self, text: str) -> Optional[list[str]]:
        result: list[str] = []
        count: int = 0
        found: bool = False
        
        if len(text) < self.min_length:
            return []
        
        if await self.__memoizer.is_memoized(text):
            res = await self.__memoizer.get_value(text)
            if len(res) > 0: return list(filter(filter_func, res))
            return result
        
        for txt in self.__words:
            if txt.startswith(text):
                result.append(txt)
                count += 1
                if count == self.amount:
                    break
        if result:
            await self.__memoizer.memoize(text, result)
        return result
    
    #search =    partialmethod(sch, count = 0, words = self.__words, amount = self.amount)
    
    
    
