import json
from copy import deepcopy
import io
from dataclasses import dataclass
from typing import Final, Any, Optional, NoReturn
from ..constants import CONTROL_REGISTRY_PATH
from .. import data_types as dt
from .. import utils
Tools: utils.Utilities = utils.Utilities()


def delete_control(name: str) -> NoReturn:
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

def join_registry(reg1: dt.ControlRegistryJsonScheme, reg2: dt.ControlRegistryJsonScheme ) -> dt.ControlRegistryJsonScheme:
    for key in ["Controls", "ControlTypes"]:
        reg1[key].extend(reg2[key])
    return reg1

@dataclass
class CleanFuncParams:
    registry_dict: dt.ControlRegistryJsonScheme
    controls: list[str]
    control_types: list[dt.ControlJsonScheme]
    indexes: list[int]


def clean_results(data: CleanFuncParams) -> dt.ControlRegistryJsonScheme:
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

def generate_dict(control_registry_models: list[dt.ControlRegistryModel], return_dict: bool = False) -> Optional[dt.ControlRegistryJsonScheme]:
    registry: io.TextIOWrapper
    controls_registry: dt.ControlRegistryJsonScheme
    models: dt.ControlRegistryModel
    control_types: list[dt.ControlJsonScheme]
    name: str
    idx: int
    model_dict: dict[str, Any]
    controls: list[str]
    result: dt.ControlRegistryJsonScheme = {
        "Controls":[],
        "ControlTypes":[]
    }
    
    if not return_dict:
        controls_registry = utils.RegistryOperations.load_file()
        
        controls = deepcopy(controls_registry["Controls"])
        control_types = deepcopy(controls_registry["ControlTypes"])
    else:
        controls = deepcopy(result["Controls"])
        control_types = deepcopy(result["ControlTypes"])
    
    for models in control_registry_models:
        
        name = models.name
        model_dict = models.return_dict
        
        if name in controls:
            if len(control_types) == 0:
                continue
            
            idx = controls.index(name)
            settings = control_types[idx]["valid_settings"] 
            if settings != model_dict["valid_settings"]:
                control_types[idx]["valid_settings"] = model_dict["valid_settings"]
                
            continue
        
        controls.append(name)
        control_types.append(model_dict)
    
    indexes = [i for i, types in enumerate(control_types) if types["name"] not in controls]
    
    if not return_dict:
        controls_registry = clean_results(
            CleanFuncParams(
                registry_dict=controls_registry,
                controls=controls_registry["Controls"],
                control_types=controls_registry["ControlTypes"],
                indexes=indexes
            )
        )
        
        return utils.RegistryOperations.save_file(controls_registry)
    
    
    return clean_results(
        CleanFuncParams(
            registry_dict=result,
            controls=controls,
            control_types=control_types,
            indexes=indexes
        )
    )
        
    return result