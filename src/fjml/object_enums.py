
class ImportKeys:
    IMPORT: str = "import"
    FROM: str = "from"
    USING: str ="using"
    SOURCE: str = "source"


class EventKeys:
    FUNC: str = "func"
    CALL: str = "call"
    EVAL: str = "eval"
    ROUTE: str = "route"


class RefsKeys:
    REFS: str = "refs"
    CODE_REFS: str = "code_refs"
    STYLING: str = "styling"
    GROUP: str = "group"


class ControlKeys:
    ROUTE: str = "route"
    VAR_NAME: str = "var_name"
    CONTROL_TYPE: str = "control_type"
    SETTINGS: str = "settings"
    UNPACK: str = "_unpack"
    ATTR: str = 'attr'
    LOOP: str = "loop"
    VIEW: str = "View"


class ControlRegKeys:
    SOURCE: str = "source"
    NAME: str = "name"
    ATTR: str = "attr"
    VALID_SETTINGS: str = "valid_settings"
    TYPE_HINTS: str = "type_hints"
    CONTROLS: str = "Controls"
    CONTROL_TYPES: str = "ControlTypes"
    CONTROL: str = "control"


class MarkupKeys:
    HEADER: str = "Header"
    IMPORTS: str = "Imports"
    CONTROLS: str = "Controls"
    UI: str = "UI"
    SKIP: str = "<SKIP>"


class PropertyKeys:
    GET: str = "get"
    SET: str = "set"
    DEL: str = "del"


class LoopKeys:
    LOOP: str = "loop"
    ITERATOR: str = "iterator"
    CONTROL: str = "control"
    DEPTH: str = "depth"
    LOOP_INDEX: str = "loop_index"
    IDX: str = "idx"
    RANGE: str = "range"
