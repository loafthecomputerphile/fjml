from typing import Union, Any, Mapping, Dict, Sequence, List, get_origin, get_args, Tuple, Set
from enum import Enum

def _origin(data: Any):
    if isinstance(data, type):
        return data
    try:
        origin_res = get_origin(data)
        if origin_res:
            return origin_res
        else:
            return type(None)
    except:
        return type(None)

def _new_isinstance(duck_type: type,  type_to_check: type) -> bool:
    org = _origin(duck_type)
    if isinstance(type_to_check, Sequence) and not isinstance(type_to_check, str):
        return org in type_to_check
    return org == type_to_check


_Sequences: tuple[type] = (list, List, Tuple, Set, tuple, set, Sequence)


def type_check(value, dtype, depth: int=0) -> bool:
    
    if dtype == Any:
        return True
    
    if _new_isinstance(dtype, Union):
        for param_t in get_args(dtype):
            if type_check(value, param_t, depth=depth+1):
                return True
        return False
    
    org = _origin(dtype)
    if _new_isinstance(dtype, _Sequences):
        if isinstance(value, org):  # outer level check
            params = get_args(dtype)
            if len(params) > 0:
                param_t = params[0]
            else:
                return True
            
            for param_x in value:
                if not type_check(param_x, param_t, depth=depth+1):
                    return False
            else:
                return True
        return False
    
    if _new_isinstance(dtype, (Mapping, dict, Dict)):
        if isinstance(value, org):  # outer level check
            param_t = list(get_args(dtype))
            if not param_t:
                return True
            elif len(param_t) == 1:
                param_t.append(Any)
            elif len(param_t) > 2:
                param_t = param_t[:2]
                
            for param_k, param_v in value.items():
                if not type_check(param_k, param_t[0], depth=depth+1):
                    return False
                if not type_check(param_v, param_t[1], depth=depth+1):
                    return False
            else:
                return True
        return False
    
    if _new_isinstance(dtype, (int, float)):
        if isinstance(value, (int, float)):
            return True
        return False
    
    if isinstance(dtype, type):
        org = dtype
    
    if isinstance(value, org) or issubclass(dtype, Enum): # isn'dtype a metatype, let's just check it
        return True
    
    return False
