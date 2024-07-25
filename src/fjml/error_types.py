from typing import Literal, Any

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn


class ConditionalError:

    @staticmethod
    def value_error(conditional: bool, error_text: str) -> NoReturn:
        if conditional:
            raise ValueError(error_text)

    @staticmethod
    def type_error(conditional: bool, error_text: str) -> NoReturn:
        if conditional:
            raise TypeError(error_text)

    @staticmethod
    def key_error(conditional: bool, error_text: str) -> NoReturn:
        if conditional:
            raise KeyError(error_text)


class InvalidTypeError(Exception):
    __module__: str = "builtins"

    def __init__(self, var_name: str, value: Any, dtype: Any, var: str = "Variable") -> NoReturn:
        super().__init__(
            f"{var} {var_name}, expected type of {dtype}, instead received type of {type(value)}, "
        )


class UndefinedMethodError(Exception):
    __module__: str = "builtins"

    def __init__(self, method_name: str) -> NoReturn:
        super().__init__(f"Method, {method_name}, was not defined.")


class InitializationError(Exception):
    __module__: str = "builtins"

    def __init__(self) -> NoReturn:
        super().__init__(f"Backend was not Initialized.")


class MissingKeyError(Exception):
    __module__: str = "builtins"

    def __init__(self, control_name: str, key: str) -> NoReturn:
        super().__init__(f"Key, {key}, in {control_name} was not defined.")


class InvalidValueError(Exception):
    __module__: str = "builtins"

    def __init__(self, control_name: str, key: str, value: str) -> NoReturn:
        super().__init__(
            f"Value, {value}, for key, {key}, in {control_name} is invalid."
        )


class RegistryFileNotFoundError(Exception):
    __module__: str = "builtins"

    def __init__(self) -> NoReturn:
        super().__init__("Registry file is missing or misplaced")


class InvalidKeyError(Exception):
    __module__: str = "builtins"

    def __init__(self, control_name: str, key: str) -> NoReturn:
        super().__init__(f"Key, {key}, in {control_name} is invalid.")


class ControlNotFoundError(Exception):
    __module__: str = "builtins"

    def __init__(self, control_name: str, key: str) -> NoReturn:
        super().__init__(
            f"Control, {control_name}, is not registered or does not exist."
        )


class InvalidMarkupFormatError(Exception):
    __module__: str = "builtins"

    def __init__(
        self, file_name: str, key: Literal["UI", "Imports", "Controls"]
    ) -> NoReturn:
        super().__init__(f"Markup file, {file_name}, is missing container, {key}.")


class InvalidMarkupContainerError(Exception):
    __module__: str = "builtins"

    def __init__(self, file_name: str, key: str) -> NoReturn:
        super().__init__(
            f"Markup file, {file_name}, contains invalid container, {key}."
        )
