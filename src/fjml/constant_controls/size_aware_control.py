import flet.canvas as cv
from flet import Control, ControlEvent
from typing import Optional, Callable

try:
    from typing import NoReturn
except:
    from typing_extensions import NoReturn


__all__ = ["SizeAwareControl"]


class SizeAwareControl(cv.Canvas):

    def __init__(
        self,
        content: Optional[Control] = None,
        resize_interval: int = 50,
        on_resize: Optional[Callable[[ControlEvent], NoReturn]] = None,
        **kwargs,
    ) -> NoReturn:
        super().__init__(**kwargs)
        self.content: Optional[Control] = content
        self.resize_interval: int = resize_interval
        self.resize_callback: Optional[Callable[[ControlEvent], NoReturn]] = on_resize
        self.on_resize: Optional[Callable[[ControlEvent], NoReturn]] = (
            self.__handle_canvas_resize
        )
        self.size: tuple[int, int] = (0, 0)

    @property
    def get_width(self) -> int:
        return self.size[0]

    @property
    def get_height(self) -> int:
        return self.size[1]

    def __handle_canvas_resize(self, e: ControlEvent) -> NoReturn:
        self.size = (int(e.width), int(e.height))
        try:
            self.update()
        except AssertionError:
            pass
        if self.resize_callback:
            self.resize_callback(e)
