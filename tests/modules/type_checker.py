from typing import get_type_hints, Union, Optional, get_origin, get_args, Any, NoReturn
from dataclasses import dataclass, field

@dataclass
class TypeChecker:
    parent_name: str = field(default=None)
    
    def check(self, data: Any, expected_type: Any, data_name: str) -> NoReturn:
        self.data_name: str = data_name
        self.error_text: str = f"Input {data_name}"
        if self.parent_name:
            self.error_text: str = f"{self.error_text} of class {self.parent_name}"
        self.__check(data, expected_type)
            
    def __check(self, data: Any, expected_type: Any) -> NoReturn:
        if get_origin(expected_type) == list:
            self.__check_generic_type(data, expected_type)
        elif get_origin(expected_type) == dict:
            self.__check_dict(data)
        elif get_origin(expected_type) == set:
            self.__check_generic_type(data, expected_type)
        elif get_origin(expected_type) == tuple:
            self.__check_generic_type(data, expected_type)
        elif get_origin(expected_type) == Union:
            self.__check_union(data, expected_type)
        elif get_origin(expected_type) == Optional:
            self.__check_optional(data, expected_type)
        else:
            self.__type_check(data, expected_type)

    def __type_check(self, data: Any, expected_type: Any) -> NoReturn:
        if isinstance(data, bool) and bool != expected_type:
            raise TypeError(f"Type mismatch. {self.error_text} expected: {expected_type}, Received: {type(data)}")
        if not isinstance(data, expected_type):
            raise TypeError(f"Type mismatch. {self.error_text} expected: {expected_type}, Received: {type(data)}")

    def __check_generic_type(self, data: Any, expected_type: Any) -> NoReturn:
        inner_type = get_args(expected_type)[0]
        if not isinstance(data, get_origin(expected_type)):
            raise TypeError(f"Type mismatch. {self.error_text} expected: {expected_type} with types {inner_type}, Received: {type(data)} with types {inner_type}")

        inner_type = get_args(expected_type)[0]
        for item in data:
            self.__check(item, inner_type)

    def __check_dict(self, data: Any) -> NoReturn:
        args = get_args(data)
        if not isinstance(data, dict):
            raise TypeError(f"Type mismatch. {self.error_text} expected: dict with types {args}, Received: {type(data)} with types {args}")
        
        if len(args) < 2:
            return
        key_type, value_type = args
        for key, value in data.items():
            self.__check(key, key_type)
            self.__check(value, value_type)

    def __check_union(self, data: Any, expected_type: Any) -> NoReturn:
        for union_type in get_args(expected_type):
            try:
                self.__check(data, union_type)
                return    # If no exception is raised, the type matches one of the union types
            except TypeError:
                pass

        raise TypeError(f"Type mismatch. {self.error_text} expected one of {get_args(expected_type)}, Received: {type(data)}")

    def __check_optional(self, data: Any, expected_type: Any) -> NoReturn:
        if data is not None:
            self.__check(data, get_args(expected_type)[0])