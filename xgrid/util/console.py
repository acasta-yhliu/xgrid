from enum import Enum
from typing import TextIO
import sys


class Style(Enum):
    Normal = 0
    Bold = 1
    Light = 2
    Italic = 3
    Underlined = 4
    Blink = 5


class Foreground(Enum):
    Black = 30
    Red = 31
    Green = 32
    Yellow = 33
    Blue = 34
    Purple = 35
    Cyan = 36
    White = 37


class Console:
    """Lightweight implementation of a colored console, support ASCII escape sequence to modify"""

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
