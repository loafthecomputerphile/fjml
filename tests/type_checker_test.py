from src.fjml import type_checker as tc
from typing import Union, Sequence, Optional, NoReturn, Dict, List
import pytest


class TestTypeChecker:
    
    def test_union(self) -> NoReturn:
        assert tc.type_check("hello", Union[str, int])
        assert tc.type_check(420, Union[str, int])
        
        assert not tc.type_check(420.69, Union[str, int])
        assert not tc.type_check(["hello"], Union[str, int])
    
    def test_optional(self) -> NoReturn:
        assert tc.type_check("hello", Optional[str])
        assert tc.type_check(None, Optional[str])
        
        assert not tc.type_check(420, Optional[str])
    
    def test_sole_type(self) -> NoReturn:
        assert tc.type_check(420.69, float)
        assert not tc.type_check(30, str)
    
    def test_mapping(self) -> NoReturn:
        assert tc.type_check({"hello":"world"}, dict)
        assert tc.type_check({"hello":10, "sheesh":20}, dict[str, int])
        
        assert tc.type_check({"hello":"world"}, Dict)
        assert tc.type_check({"hello":10, "sheesh":20}, Dict[str, int])
        
        assert not tc.type_check(10, Dict)
        assert not tc.type_check({"hello":10, "sheesh":20.8}, Dict[str, int])
        
    def test_list(self) -> NoReturn:
        assert tc.type_check(["hello", "world"], list)
        assert tc.type_check([1,2,4], list[int])
        
        assert tc.type_check(["hello", "world", 420], list[Union[str, int]])
        assert tc.type_check([69, None, 420], list[Optional[int]])
        
        assert not tc.type_check([1,2,4, "hello"], list[int])
        assert not tc.type_check(["hello", "world", 420, []], list[Union[str, int]])
        assert not tc.type_check([69, None, 420, "hello"], list[Optional[int]])
    
    def test_nested(self) -> NoReturn:
        assert tc.type_check([["hello", "world"], ["hello", "world"]], list[List[str]])
        assert tc.type_check([{}, {}], list[dict])
        
        assert not tc.type_check(["hello", "world", 420], Union[str, list[str]])
        assert tc.type_check(["hello", "world"], Optional[Union[str, list[str]]])
        assert tc.type_check([69, None, 420], list[Optional[int]])
        assert tc.type_check([69, 100, 420], Optional[list[int]])
        
        assert not tc.type_check({"hello":[1,2,3,"world"]}, dict[str, list[int]])
        assert tc.type_check({"hello":[1,2,3,4]}, dict[str, list[int]])

