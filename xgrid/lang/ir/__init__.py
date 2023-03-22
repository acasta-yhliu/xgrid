from dataclasses import dataclass
from typing import Any

from xgrid.util.console import Element, ElementFormat, Elementable, Foreground, idtype, idvar, plain
from xgrid.util.typing import BaseType


@dataclass
class Location:
    file: str
    func: str
    line: int

    def __repr__(self) -> str:
        return f"{self.file} Ln {self.line}, {self.func}"


@dataclass
class IR(Elementable):
    location: Location


@dataclass
class Variable(Elementable):
    name: str
    type: BaseType
    value: Any = None

    def write(self, format: ElementFormat):
        format.print(idvar("%" + self.name))
