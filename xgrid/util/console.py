from enum import Enum
from typing import TextIO
import sys


class Style(Enum):
    normal = 0
    bold = 1
    light = 2
    italic = 3
    underlined = 4
    blink = 5


class Foreground(Enum):
    black = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    purple = 35
    cyan = 36
    white = 37


class Console:
    """lightweight implementation of a colored console, support ASCII escape sequence to modify"""

    def __init__(self, textio: TextIO) -> None:
        self.io = textio
        self.tty = textio.isatty()

    def isatty(self) -> bool:
        return self.tty

    def print(self, msg: str, style: Style | None = None, foreground: Foreground | None = None) -> "Console":
        if self.tty and (style or foreground):
            style_str = style.value if style else ""
            foreground_str = foreground.value if foreground else ""
            self.io.write(
                f"\033[{style_str};{foreground_str}m" + msg + "\033[0m")
        else:
            self.io.write(msg)

        return self

    def println(self, msg: str, style: Style | None = None, foreground: Foreground | None = None) -> "Console":
        return self.print(msg + "\n", style, foreground)


stdout = Console(sys.stdout)
