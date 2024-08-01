from copy import deepcopy
import io
from operator import eq, itemgetter
from dataclasses import dataclass
from typing import Optional, Sequence, Mapping
try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn

from ..object_enums import *
from .. import data_types as dt, utils

Tools: utils.Utilities = utils.Utilities()


@dataclass
class CleanFuncParams:
    registry_dict: dt.ControlRegistryJsonScheme
    controls: Sequence[str]
    control_types: Sequence[dt.ControlJsonScheme]
    indexes: Sequence[int]


def swap_positions(data: Sequence, pos1: int, pos2: int) -> Sequence:
    data[pos1], data[pos2] = data[pos2], data[pos1]
    return data


class ControlRegistryOperations:

    @classmethod
    def __find_index(cls, name: str, data: Sequence[dt.ControlRegistryModel]) -> int:
        i: int
        model: dt.ControlRegistryModel
        get_name = itemgetter(ControlRegKeys.NAME)

        for i, model in filter(lambda x: eq(name, get_name(x)), enumerate(data)):
            return i
        return -1

    @classmethod
    def fix_registry(
        cls, controls: Sequence[str], control_types: Sequence[dt.ControlRegistryModel]
    ) -> Sequence[dt.ControlRegistryModel]:
        i: int
        name: str
        for i, name in enumerate(controls):
            try:
                if name != control_types[i][ControlRegKeys.NAME]:
                    control_types = swap_positions(
                        control_types, i,
                        controls.index(control_types[i][ControlRegKeys.NAME]),
                    )
            except IndexError as e:
                raise IndexError(
                    "Registry file is out of parity. Please reset your registry file"
                )
        if len(control_types) - 1 > i:
            raise IndexError(
                "Registry file is out of parity. Please reset your registry file"
            )
        return control_types

    @classmethod
    def delete_control(cls, name: str) -> NoReturn:
        controls_registry: dt.ControlRegistryJsonScheme = (
            utils.RegistryOperations.load_file()
        )

        controls: Sequence[str] = controls_registry[ControlRegKeys.CONTROLS]
        control_types: Sequence[dt.ControlRegistryModel] = (
            controls_registry[ControlRegKeys.CONTROL_TYPES]
        )

        try:
            idx: int = controls.index(name)
        except ValueError:
            return

        del control_types[idx]
        del controls[idx]

        controls_registry[ControlRegKeys.CONTROL_TYPES] = control_types
        controls_registry[ControlRegKeys.CONTROLS] = controls

        utils.RegistryOperations.save_file(controls_registry)

    @classmethod
    def join_registry(
        cls,
        reg1: dt.ControlRegistryJsonScheme,
        reg2: dt.ControlRegistryJsonScheme,
    ) -> dt.ControlRegistryJsonScheme:
        key: str

        reg1[ControlRegKeys.CONTROLS].extend(
            reg2[ControlRegKeys.CONTROLS]
        )
        reg1[ControlRegKeys.CONTROL_TYPES].extend(
            reg2[ControlRegKeys.CONTROL_TYPES]
        )
        return reg1

    @classmethod
    def clean_results(cls, data: CleanFuncParams) -> dt.ControlRegistryJsonScheme:
        if data.indexes:
            data.registry_dict[ControlRegKeys.CONTROL_TYPES] = [
                v for i, v in enumerate(data.control_types) if i not in data.indexes
            ]
            data.registry_dict[ControlRegKeys.CONTROLS] = [
                v for i, v in enumerate(data.controls) if i not in data.indexes
            ]
        else:
            data.registry_dict[ControlRegKeys.CONTROL_TYPES] = data.control_types
            data.registry_dict[ControlRegKeys.CONTROLS] = data.controls
        return data.registry_dict

    @classmethod
    def generate_dict(
        cls,
        control_registry_models: Sequence[dt.ControlRegistryModel],
        edit_registry: bool = False,
    ) -> Optional[dt.ControlRegistryJsonScheme]:
        registry: io.TextIOWrapper
        models: dt.ControlRegistryModel
        name: str
        idx: int
        actual_idx: int
        model_dict: Mapping
        settings: Sequence[str]
        controls_registry: dt.ControlRegistryJsonScheme = {
            ControlRegKeys.CONTROLS: [],
            ControlRegKeys.CONTROL_TYPES: [],
        }

        if edit_registry:
            controls_registry = utils.RegistryFileOperations.load_file()

        controls = deepcopy(controls_registry[ControlRegKeys.CONTROLS])
        control_types = deepcopy(controls_registry[ControlRegKeys.CONTROL_TYPES])

        for models in control_registry_models:
            name = models.name
            model_dict = models.return_dict
            del model_dict[ControlRegKeys.CONTROL]

            if name in controls:
                if len(control_types) == 0:
                    continue

                idx = controls.index(name)
                actual_idx = cls.__find_index(name, control_types)
                if actual_idx == -1:
                    control_types.insert(idx, model_dict)
                    continue
                if idx != actual_idx:
                    control_types = swap_positions(control_types, idx, actual_idx)
                settings = control_types[idx][ControlRegKeys.VALID_SETTINGS]
                if settings != model_dict[ControlRegKeys.VALID_SETTINGS]:
                    control_types[idx][ControlRegKeys.VALID_SETTINGS] = (
                        model_dict[ControlRegKeys.VALID_SETTINGS]
                    )
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
                indexes=[
                    i for i, types in enumerate(control_types)
                    if types[ControlRegKeys.NAME] not in controls
                ],
            )
        )

        if edit_registry:
            return utils.RegistryFileOperations.save_file(
                controls_registry
            )

        return controls_registry
