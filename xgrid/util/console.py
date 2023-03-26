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
stderr = Console(sys.stderr)


class Element:
    def __init__(self, text: str, style: Style | None = None, foreground: Foreground | None = None) -> None:
        self.text = text
        self.style = style
        self.foreground = foreground

    def stringify(self, isatty: bool):
        if isatty:
            style_str = self.style.value if self.style else ""
            foreground_str = self.foreground.value if self.foreground else ""
            return f"\033[{style_str};{foreground_str}m" + self.text + "\033[0m"
        else:
            return self.text


class Elementable:
    def write(self, format: "ElementFormat"):
        pass


class ElementFormat:
    class IndentationGuard:
        def __init__(self, format: "ElementFormat") -> None:
            self.format = format

        def __enter__(self) -> None:
            self.format.indents += self.format.indent_size

        def __exit__(self, _a, _b, _c) -> None:
            self.format.indents -= self.format.indent_size

    class Line:
        def __init__(self, indent: int, elements: list[Element]) -> None:
            self.indent = indent
            self.elements = elements

    def __init__(self, indent_size: int = 2) -> None:
        self.indents = 0
        self.indent_size = indent_size

        self.lines: list[ElementFormat.Line] = []
        self.line_buffer: list[Element] = []

    def print(self, *elements: Element | Elementable):
        for element in elements:
            if isinstance(element, Elementable):
                element.write(self)
            else:
                self.line_buffer.append(element)

    def println(self, *elements: Element | Elementable):
        self.print(*elements)
        self.lines.append(ElementFormat.Line(
            self.indents, self.line_buffer))
        self.line_buffer = []

    def indent(self) -> "ElementFormat.IndentationGuard":
        return ElementFormat.IndentationGuard(self)

    def write(self, device: TextIO = sys.stdout):
        isatty = device.isatty()
        for line in self.lines:
            if any(line.elements):
                device.write(" " * line.indent)
                device.write(
                    " ".join(map(lambda x: x.stringify(isatty), line.elements)))
            device.write("\n")


def kw(text: str):
    return Element(text, None, Foreground.blue)


def const(text: str):
    return Element(text, Style.italic, None)


def idvar(text: str):
    return Element(text, None, Foreground.cyan)


def idtype(text: str):
    return Element(text, None, Foreground.green)


def idfunc(text: str):
    return Element(text, None, Foreground.yellow)


def plain(text: str):
    return Element(text)
