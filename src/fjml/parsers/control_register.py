import json
from typing import Final, IO, Any, Optional, NoReturn
from .constants import CONTROL_REGISTRY_PATH
from .utils import Utilities
from ..types_errors import (
    data_types as dt
)
from .utils import Utilities
Tools: Utilities = Utilities()


def delete_control(name: str) -> NoReturn:
    controls: list[str]
    controls_registry: dt.ControlRegistryJsonScheme
    
    with open(CONTROL_REGISTRY_PATH, 'r') as registry:
        controls_registry = json.load(registry)
    
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
    
    with open(CONTROL_REGISTRY_PATH, 'w') as registry:
        json.dump(controls_registry, registry, indent=2)
    

def generate_dict(control_registry_models: list[dt.ControlRegistryModel], return_dict: bool = False) -> Optional[dt.ControlRegistryJsonScheme]:
    registry: IO[Any]
    controls_registry: dt.ControlRegistryJsonScheme
    models: dt.ControlRegistryModel
    name: str
    idx: int
    model_dict: dict[str, Any]
    controls: list[str]
    result: dt.ControlRegistryJsonScheme = {
        "Controls":[],
        "ControlTypes":[]
    }
    
    if not return_dict:
        with open(CONTROL_REGISTRY_PATH, 'r') as registry:
            controls_registry = json.load(registry) 
        
        controls = controls_registry["Controls"]
        control_types = controls_registry["ControlTypes"]
    else:
        controls = result["Controls"]
        control_types = result["ControlTypes"]
    
    for models in control_registry_models:
        
        name = models.name
        model_dict = models.return_dict
        
        if name in controls:
            if len(control_types) < 1:
                continue
            
            idx = controls.index(name)
            settings = control_types[idx]["valid_settings"] 
            if settings != model_dict["valid_settings"]:
                control_types[idx]["valid_settings"] = model_dict["valid_settings"]
                
            continue
        
        controls.append(name)
        control_types.append(
            model_dict
        )
    
    indexes = []
        
    for i, types in enumerate(control_types):
        if types["name"] not in controls:
            indexes.append(i)
    
    if not return_dict:
        if indexes:
            controls_registry["ControlTypes"] = [v for i, v in enumerate(control_types) if i not in indexes]
            controls_registry["Controls"] = [v for i, v in enumerate(controls) if i not in indexes]
        else:
            controls_registry["ControlTypes"] = control_types
            controls_registry["Controls"] = controls
        
        with open(CONTROL_REGISTRY_PATH, 'w') as registry:
            json.dump(controls_registry, registry, indent=2)
        return
    
    if indexes:
        result["ControlTypes"] = [v for i, v in enumerate(control_types) if i not in indexes]
        result["Controls"] = [v for i, v in enumerate(controls) if i not in indexes]
    else:
        result["ControlTypes"] = control_types
        result["Controls"] = controls
        
    return result