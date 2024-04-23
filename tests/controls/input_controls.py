from types import FunctionType, CodeType
from math import ceil
import asyncio
import inspect
from dataclasses import dataclass
import functools
from typing import (
    Union, 
    Any, 
    Optional, 
    Type, 
    TypedDict,
    Callable,
    NoReturn
)

import nest_asyncio
from flet import (
    Page, margin, 
    border, BorderSide, 
    border_radius, Ref,
    Container, Text, 
    TextField, Column,
    TextStyle, Divider,
    ControlEvent, KeyboardEvent,
    UserControl, Ref,
    padding, MaterialState,
    CrossAxisAlignment, Switch,
    Divider, Dropdown,
    alignment, Control,
    dropdown
)

from modules import (
    TextAutoCompletion, 
    TypeChecker, 
    ShelveMemoizer,
    event_join
)

nest_asyncio.apply()

OptionalNum = Optional[Union[int, float]]
OptionalStr = Optional[str]
OptionalBoolNum = Union[int, float, bool, None]
OptionalInt = Optional[int]
OptionalFunc = Optional[FunctionType]

__all__: list[str] = ["CustomTextField", "CustomDropdown", "CustomSwitch"]

DTYPES: list[str] = ["date", "float", "integer", "currency", "text"]
VALIDATOR_KWARGS: dict[str, Any] = {"dtype": "text", "currency_decimals":2, "date_format":r"%d/%m/%Y"}

def is_float(string: str) -> bool:
    pattern = r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?"
    match = re.match(pattern, string)
    return bool(match)


def validate_dates(date: str, date_format: str) -> bool:
    try:
        datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class Validator:
    dtype: str = "text"
    currency_decimals: int = 2
    date_format: str = r"%d/%m/%Y"
    
    def __post_init__(self) -> NoReturn:
        if self.dtype not in DTYPES:
            raise TypeError(f"Validator data type must be in {DTYPES}, recieved data type {self.dtype} instead")
    
    def validate(self, data: str) -> bool:
        if not data: return True
        if self.dtype == "text": return isinstance(data, str)
        if self.dtype == "float": return is_float(data)
        if self.dtype == "integer": return data.isdigit()
        if self.dtype == "date": return validate_dates(data, self.date_format)
        if self.dtype == "currency": return is_float(data)


def partial(func: Callable, /, *args, **keywords) -> Callable:
    if asyncio.iscoroutinefunction(func):
        async def newfunc(*fargs, **fkeywords) -> Any:
            newkeywords = {**keywords, **fkeywords}
            return await func(*args, *fargs, **newkeywords)
    else:
        def newfunc(*fargs, **fkeywords) -> Any:
            newkeywords = {**keywords, **fkeywords}
            return func(*args, *fargs, **newkeywords)
    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc

class CustomDropdown(Container):
    
    GET: tuple[str, ...] = (
        "value"
    )
    
    POST: tuple[str, ...] = (
        "value"
    )
    
    CALL: tuple[str, ...] = (
        
    )
    
    def __init__(
        self, width: OptionalNum = None, ref: Optional[Ref] = None, options: Union[list[str], list] = [],
        label_text: OptionalStr = None, label_color: OptionalStr = None, label_weight: OptionalStr = None,
        expand: OptionalBoolNum = None, text_size: OptionalNum = None, 
        on_change: OptionalFunc = None, on_submit: OptionalFunc = None, on_focus: OptionalFunc = None, 
        on_blur: OptionalFunc = None
    ) -> NoReturn:
        super().__init__(ref=ref, alignment=alignment.center)
        
        self.options: list[str] = options
        self.expand: OptionalBoolNum = expand
        self.width: OptionalNum = width
        
        self.label_color: OptionalStr = "black"
        if label_color:
            self.label_color: OptionalStr = label_color
        
        self.label_weight: OptionalStr = "w500"
        if label_weight:
            self.label_color: OptionalStr = label_weight
        
        self.text_container: Container = Container(
            Text(
                value=label_text,
                size=ceil(.7857*text_size),
                color=self.label_color,
                weight=self.label_weight,
            ),
            margin=margin.only(left=8)
        )
        
        self.main_dropdown: Dropdown = Dropdown(
            text_style=TextStyle(
                size=text_size,
                color="black"
            ),
            color="black",
            focused_bgcolor="Transparent",
            options=[
                dropdown.Option(option) for option in self.options
            ],
            on_change=on_change,
            on_blur=on_blur,
            on_focus=on_focus,
            dense=True,
            height=ceil(2.1428*text_size),
            content_padding=padding.symmetric(4, 10)
        )
        
        self.content = Column(
            controls=[
                self.text_container,
                Divider(color="Transparent", height=1),
                self.main_dropdown
            ],
            spacing = 0
        )
    
    @property
    def value(self) -> str:
        return self.main_dropdown.value
    
    @value.setter
    def value(self, val: str) -> NoReturn:
        self.main_dropdown.value = val
        self.main_dropdown.update()


class CustomSwitch(Container):
    
    GET: tuple[str, ...] = (
        "value"
    )
    
    POST: tuple[str, ...] = (
        "value"
    )
    
    CALL: tuple[str, ...] = (
        
    )
    
    def __init__(
        self, label_text: OptionalStr = None, label_color: OptionalStr = None, 
        label_weight: OptionalStr = None, text_size: OptionalNum = None, 
        is_disabled: bool = False, ref: Optional[Ref] = None,
    ) -> NoReturn:
        super().__init__(ref=ref, margin=margin.only(bottom=-8))
        
        self.is_disabled: bool = is_disabled
        self.label_text: OptionalStr = label_text
        
        self.label_color: OptionalStr = "black"
        if label_color:
            self.label_color = label_color
            
        self.label_weight: OptionalStr = "w500"
        if label_weight:
            self.label_weight = label_weight
        
        self.label: Text = Text(
            self.label_text, 
            color=self.label_color, 
            weight=self.label_weight, 
            size=text_size
        )
        
        self.switch: Switch = Switch(
            disabled=self.is_disabled,
            track_color={
                MaterialState.SELECTED:"primary",
                MaterialState.DEFAULT:"bluegray50",
                MaterialState.DISABLED:"lightgreen50"
            },
        )
        
        self.content: Column = Column(
            controls=[
                self.label,
                Divider(color="Transparent", height=1),
                self.switch
            ],
            spacing=0,
            horizontal_alignment=CrossAxisAlignment.CENTER,
        )
    
    @property
    def value(self) -> bool:
        return self.switch.value
    
    @value.setter
    def value(self, value: bool) -> NoReturn:
        if not isinstance(value, bool):
            raise TypeError(f"value must be of type 'bool'. recieved type '{type(value)}' instead")
        self.switch.value = value
        self.switch.update()
    
    @property
    def is_disabled(self) -> bool:
        return self.switch.disabled
    
    @is_disabled.setter
    def is_disabled(self, value: bool) -> NoReturn:
        if not isinstance(value, bool):
            raise TypeError(f"disabled must be of type 'bool'. recieved type '{type(value)}' instead")
        self.switch.disabled = value
        self.switch.update()

@dataclass
class Selected:
    suggestion_index: int

class CustomTextField(Container):
    
    GET: tuple[str, ...] = (
        "value"
    )
    
    POST: tuple[str, ...] = (
        "value"
    )
    
    CALL: tuple[str, ...] = (
        "clear"
    )
    
    def __init__(
        self, name: str, ref: Optional[Ref] = None, enable_suggestions: bool = False, label_text: OptionalStr = None, 
        text_size: OptionalNum = None, dtype: str = "text", date_format: str = r"%d/%m/%Y",
        width: OptionalNum = None, expand: OptionalBoolNum = None, 
        on_change = None, on_focus = None, on_blur = None, on_submit = None,
    ) -> NoReturn:
        super().__init__(expand=expand, ref=ref, width=width)
        #self.expand = content_expand
        self.name = name
        self.data: Any
        #self.content_expand = content_expand
        self.text_size = 14 if not text_size else text_size
        self.is_mounted: bool = False
        self.validator: Validator = Validator(
            dtype, 2, date_format
        )
        self.on_change = on_change
        self.on_focus = on_focus
        self.on_blur = on_blur
        self.on_submit = on_submit
        self.enable_suggestions: bool = enable_suggestions
        self.selected: Selected = Selected(0)
        self.idx = 0
        self.max_suggestion_index: int = -1
        self.width: OptionalNum = width
        
        self.old_keyboard_event: Union[Callable[[KeyboardEvent], None], None] = None
        self.text_suggestion_model: Union[TextAutoCompletion, None] = None
        
        self.suggestion_dropdown: Container = Container(
            Column(
                controls=[],
                spacing=0
            ),
            margin=margin.only(
                left=5, 
                top=-1.2
            ),
            border_radius=border_radius.only(
                bottom_left = 6, 
                bottom_right = 6
            ),
            border=border.all(1.5, "black"),
            visible=False,
        )
        
        self.text: Text = Text(
            label_text, 
            size=ceil(.7857*self.text_size), 
            weight="w500", 
            color="black"
        )
        
        self.field: TextField = TextField(
            text_size=self.text_size, border_radius=6, border_width=1.5,
            color="black", border_color="black", text_style=TextStyle(weight="w600"),
            cursor_height=ceil(1.5714*self.text_size), content_padding=padding.symmetric(vertical=-8, horizontal=10),
            height=ceil(2.1428*self.text_size), on_change=self.on_change_, on_blur=self.on_blur_,
            on_focus=self.on_focus_
        )
        
        self.content: Column = Column(
            controls=[
                Container(self.text, margin=margin.only(left=6)),
                Divider(color="Transparent", height=1),
                self.field,
                self.suggestion_dropdown
            ],
            spacing=0,
            tight=True
        )
    
    def did_mount(self) -> NoReturn:
        self.page.session.set(
            f"{self.name}_mem", {}
        )
        
        self.page.session.set(
            self.name, ["lolmwm", "bruh", "brun", "bruhlol", "brulol"]
        )
        
        self.page.on_keyboard_event = partial(
            event_join,
            self.on_keyboard_,
            self.page.on_keyboard_event
        )
        
        self.on_change_ = partial(
            event_join,
            self.on_change_, 
            self.on_change
        )
        
        self.on_blur_ = partial(
            event_join,
            self.on_blur_, 
            self.on_blur
        )
        
        self.on_focus_ = partial(
            event_join,
            self.on_focus_, 
            self.on_focus
        )
        
        self.page.update()
        
        if self.enable_suggestions:
            self.text_suggestion_model = TextAutoCompletion(
                self.name, self,
                amount=2, min_length=3
            )
            
    async def join_event(self, initial_func: Callable, new_func: Callable, e) -> Callable[[Any], None]:
        if callable(initial_func):
            return await event_join(
                initial_func, 
                new_func,
                e
            )
        else:
            return new_func
    
    async def on_change_(self, e: ControlEvent) -> NoReturn:
        field_value: str = e.control.value
        
        if self.is_macro(field_value):
            self.clear_suggestions()
            return
        
        if not self.enable_suggestions:
            self.clear_suggestions()
            return
        
        suggestions: str = await self.text_suggestion_model.search(field_value)
        
        if not suggestions:
            self.clear_suggestions()
            return
        
        self.add_suggestions(suggestions)
        self.update()
    
    def on_blur_(self, e: ControlEvent) -> NoReturn:
        
        if self.enable_suggestions:
            self.clear_suggestions()
        
        self.update()
    
    def add_suggestions(self, suggestions: list[str]) -> NoReturn:
        self.clear_suggestions(False)
        self.max_suggestion_index = -1
        for i, suggestion in enumerate(suggestions):
            control: Container = self.make_suggestion_container(suggestion)
            if i == 0:
                control.bgcolor = "green100"
            self.append_suggestion(control)
            self.max_suggestion_index += 1
        
        self.suggestion_box[-1].border_radius = border_radius.only(
            bottom_left = 4, bottom_right = 4
        )
        self.suggestion_box[-1].margin = margin.only(.6, 0, -6, 1)
        self.suggestion_dropdown.visible = True
    
    def on_focus_(self, e: ControlEvent) -> NoReturn:
        
        field_value: str = e.control.value
        
        if self.is_macro(field_value):
            self.clear_suggestions()
            return
        
        self.update()
    
    def on_keyboard_(self, e: KeyboardEvent) -> NoReturn:
        idx = self.selected.suggestion_index
        
        if not self.enable_suggestions:
            return
        
        if e.ctrl:
        
            if e.key == "Arrow Up":
                
                if self.selected.suggestion_index > 0:
                    self.switch_highlighted_suggestion("transparent")
                    self.selected.suggestion_index -= 1
                    print(self.selected.suggestion_index)
                    self.switch_highlighted_suggestion("green100")
                self.update()
                return
                    
            if e.key == "Arrow Down":
                if self.selected.suggestion_index < self.max_suggestion_index:
                    self.switch_highlighted_suggestion("transparent")
                    self.selected.suggestion_index += 1
                    print(self.selected.suggestion_index)
                    self.switch_highlighted_suggestion("green100")
                self.update()
                return
            
            if e.key == "Tab":
                if self.selected.suggestion_index < self.max_suggestion_index+1:
                    self.set_textfield_attr("value", self.get_suggestion_value())
                    self.suggestion_dropdown.visible = False
                self.update()
                return
        
    
    def get_suggestion_value(self) -> str:
        return self.suggestion_dropdown.content.controls[
            self.selected.suggestion_index
        ].content.value
        
    @property
    def suggestion_box(self) -> Container:
        return self.suggestion_dropdown.content.controls
    
    def switch_highlighted_suggestion(self, color: str) -> NoReturn:
        self.suggestion_dropdown.content.controls[
            self.selected.suggestion_index
        ].bgcolor = color
        
    def clear_suggestions(self, update: bool = True) -> NoReturn:
        self.suggestion_dropdown.content.controls = []
        self.suggestion_dropdown.visible = False
        self.selected_suggestion_index = 0
        if update:
            self.update()
    
    def make_suggestion_container(self, suggestion) -> Container:
        return Container(
            content=Text(
                suggestion, size=self.text_size, weight="w600", color="black", max_lines=1, expand=1
            ),
            padding=padding.symmetric(4, 12), width=100, margin=margin.symmetric(0, .6)
        )
        
    def append_suggestion(self, control: Container) -> NoReturn:
        self.suggestion_dropdown.content.controls.append(control)
    
    def get_textfield_attr(self, attr: str) -> Any:
        return getattr(self.field, attr)
    
    def set_textfield_attr(self, attr: str, value: Any) -> NoReturn:
        setattr(self.field, attr, value)
        
    def is_macro(self, text: str) -> bool:
        if len(text) > 0:
            return (text[0] == "<" and text[-1] == ">")
        return False
    
    @property
    def is_valid(self) -> bool:
        return self.validator.validate(self.field.value)
    
    @property
    def value(self) -> str:
        return self.field.value
    
    @value.setter
    def value(self, val) -> NoReturn:
        self.field.value = val
        self.update()
        
    async def clear(self) -> NoReturn:
        self.field.value = ""
        self.update()
    
