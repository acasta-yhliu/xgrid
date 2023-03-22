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
    def write(self, device: TextIO):
        pass


class Blank(Element):
    def __init__(self, length: int) -> None:
        super().__init__()
        self.length = length

    def write(self, device: TextIO):
        device.write(" " * self.length)


class Endline(Element):
    def __init__(self) -> None:
        super().__init__()

    def write(self, device: TextIO):
        device.write("\n")


class Text(Element):
    def __init__(self, text: str, style: Style | None = None, foreground: Foreground | None = None) -> None:
        self.text = text
        self.style = style
        self.foreground = foreground

    def write(self, device: TextIO):
        if device.isatty():
            style_str = self.style.value if self.style else ""
            foreground_str = self.foreground.value if self.foreground else ""
            device.write(
                f"\033[{style_str};{foreground_str}m" + self.text + "\033[0m")
        else:
            device.write(self.text)


class Formattable:
    def write(self, format: "ElementFormat"):
        pass


class Indentable:
    def __init__(self, indent_size: int = 2) -> None:
        self.indents = 0
        self.indent_size = indent_size

    def indent(self) -> "IndentationGuard":
        return IndentationGuard(self)


class IndentationGuard:
    def __init__(self, indentable: Indentable) -> None:
        self.indentable = indentable

    def __enter__(self) -> None:
        self.indentable.indents += self.indentable.indent_size

    def __exit__(self, _a, _b, _c) -> None:
        self.indentable.indents -= self.indentable.indent_size


class ElementFormat(Indentable):
    endline_element = Endline()
    space_element = Blank(1)

    def __init__(self, indent_size: int = 2) -> None:
        super().__init__(indent_size)
        self.elements: list[Element] = []

    def begin(self) -> "ElementFormat":
        self.elements.append(Blank(self.indents))
        return self

    def print(self, text: str | Formattable, style: Style | None = None, foreground: Foreground | None = None) -> "ElementFormat":
        if isinstance(text, str):
            self.elements.append(Text(text, style, foreground))
        else:
            text.write(self)
        return self

    def space(self) -> "ElementFormat":
        self.elements.append(ElementFormat.space_element)
        return self

    def end(self: "ElementFormat") -> "ElementFormat":
        self.elements.append(ElementFormat.endline_element)
        return self

    def write(self, device: TextIO = sys.stdout):
        for element in self.elements:
            element.write(device)


class LineFormat(Indentable):
    def __init__(self, indent_size: int = 2) -> None:
        super().__init__(indent_size)
        self.lines: list[str] = []

    def println(self, text: str):
        self.lines.append(" " * self.indents + text + "\n")

    def write(self, device: TextIO = sys.stdout):
        device.writelines(self.lines)
