from enum import StrEnum


class ImportKeys(StrEnum):
    IMPORT: str = "import"
    FROM: str = "from"
    USING: str ="using"
    SOURCE: str = "source"


class EventKeys(StrEnum):
    FUNC: str = "func"
    CALL: str = "call"
    EVAL: str = "eval"
    ROUTE: str = "route"


class RefsKeys(StrEnum):
    REFS: str = "refs"
    CODE_REFS: str = "code_refs"
    STYLING: str = "styling"


class ControlKeys(StrEnum):
    ROUTE: str = "route"
    VAR_NAME: str = "var_name"
    CONTROL_TYPE: str = "control_type"
    SETTINGS: str = "settings"
    UNPACK: str = "unpack"
    ATTR: str = 'attr'
    LOOP: str = "loop"


class ControlRegKeys(StrEnum):
    SOURCE: str = "source"
    NAME: str = "name"
    ATTR: str = "attr"
    VALID_SETTINGS: str = "valid_settings"
    TYPE_HINTS: str = "type_hints"
    CONTROLS: str = "Controls"
    CONTROL_TYPES: str = "ControlTypes"
    CONTROL: str = "control"


class MarkupKeys(StrEnum):
    HEADER: str = "Header"
    IMPORTS: str = "Imports"
    CONTROLS: str = "Controls"
    UI: str = "UI"


class LoopKeys(StrEnum):
    LOOP: str = "loop"
    ITERATOR: str = "iterator"
    CONTROL: str = "control"
    DEPTH: str = "depth"
    LOOP_INDEX: str = "loop_index"
    IDX: str = "idx"
    RANGE: str = "range"
