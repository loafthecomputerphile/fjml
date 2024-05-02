import json
from copy import deepcopy
import io
from functools import partial
from dataclasses import dataclass
from typing import Final, Any, Optional, NoReturn
from ..constants import CONTROL_REGISTRY_PATH
from .. import data_types as dt
from .. import utils

Tools: utils.Utilities = utils.Utilities()

@dataclass
class CleanFuncParams:
    registry_dict: dt.ControlRegistryJsonScheme
    controls: list[str]
    control_types: list[dt.ControlJsonScheme]
    indexes: list[int]


def swap_positions(data: list[Any], pos1: int, pos2: int) -> list[Any]:
    data[pos1], data[pos2] = data[pos2], data[pos1]
    return data


class ControlRegistryOperations:
    
    @classmethod
    def __find_index(cls, name: str, data: list[dt.ControlRegistryModel]) -> int:
        for i, model in enumerate(data):
            if name == model["name"]:
                return i
        return -1
    
    @classmethod
    def fix_registry(cls, controls: list[str], control_types: list[dt.ControlRegistryModel]) -> list[dt.ControlRegistryModel]:
        for i, name in enumerate(controls):
            try:
                if name != control_types[i]["name"]:
                    control_types = swap_positions(control_types, i, controls.index(control_types[i]["name"]))
            except IndexError as e:
                raise IndexError("Registry file is out of parady. Please reset your registry file")
        if len(control_types)-1 > i:
            raise IndexError("Registry file is out of parady. Please reset your registry file")
        return control_types

    @classmethod
    def delete_control(cls, name: str) -> NoReturn:
        controls: list[str]
        controls_registry: dt.ControlRegistryJsonScheme = utils.RegistryOperations.load_file()
        
        controls = controls_registry["Controls"]
        control_types = controls_registry["ControlTypes"]
        
        try:
            idx = controls.index(name)
        except ValueError:
            return
        
        del control_types[idx]
        del controls[idx]
        
        controls_registry["ControlTypes"] = control_types
        controls_registry["Controls"] = controls
        
        utils.RegistryOperations.save_file(controls_registry)

    @classmethod
    def join_registry(cls, reg1: dt.ControlRegistryJsonScheme, reg2: dt.ControlRegistryJsonScheme) -> dt.ControlRegistryJsonScheme:
        for key in ["Controls", "ControlTypes"]:
            reg1[key].extend(reg2[key])
        return reg1

    @classmethod
    def clean_results(cls, data: CleanFuncParams) -> dt.ControlRegistryJsonScheme:
        if data.indexes:
            data.registry_dict["ControlTypes"] = [
                v for i, v in enumerate(data.control_types) if i not in data.indexes
            ]
            data.registry_dict["Controls"] = [
                v for i, v in enumerate(data.controls) if i not in data.indexes
            ]
        else:
            data.registry_dict["ControlTypes"] = data.control_types
            data.registry_dict["Controls"] = data.controls
        return data.registry_dict

    @classmethod
    def generate_dict(cls, control_registry_models: list[dt.ControlRegistryModel], edit_registry: bool = False) -> Optional[dt.ControlRegistryJsonScheme]:
        registry: io.TextIOWrapper
        models: dt.ControlRegistryModel
        name: str
        idx: int
        model_dict: dict[str, Any]
        controls_registry: dt.ControlRegistryJsonScheme = {
            "Controls":[],
            "ControlTypes":[]
        }
        
        if not edit_registry:
            controls_registry = utils.RegistryFileOperations.load_file()
            
        controls = deepcopy(controls_registry["Controls"])
        control_types = deepcopy(controls_registry["ControlTypes"])
        
        for models in control_registry_models:
            name = models.name
            model_dict = models.return_dict
            
            if name in controls:
                if len(control_types) == 0: continue
                
                idx = controls.index(name)
                actual_idx = cls.__find_index(name, control_types)
                if actual_idx == -1:
                    control_types.insert(idx, model_dict)
                    continue
                if idx != actual_idx:
                    control_types = swap_positions(control_types, idx, actual_idx)
                settings = control_types[idx]["valid_settings"] 
                if settings != model_dict["valid_settings"]:
                    control_types[idx]["valid_settings"] = model_dict["valid_settings"]
            else:
                controls.append(name)
                control_types.append(model_dict)
        
        if not edit_registry:
            control_types = cls.fix_registry(controls, control_types)
            
        controls_registry = cls.clean_results(
            CleanFuncParams( 
                registry_dict=controls_registry,
                controls=controls, 
                control_types=control_types,
                indexes=[i for i, types in enumerate(control_types) if types["name"] not in controls]
            )
        )
        
        if not edit_registry:
            return utils.RegistryFileOperations.save_file(controls_registry)
        
        return controls_registry