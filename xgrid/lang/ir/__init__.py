from dataclasses import dataclass
from typing import Any

from xgrid.util.console import ElementFormat, Elementable, idvar
from xgrid.util.typing import BaseType


@dataclass
class Location:
    file: str
    func: str
    line: int

    def __repr__(self) -> str:
        return f"File {self.file}, line {self.line}, at {self.func}"


@dataclass
class IR(Elementable):
    location: Location


@dataclass
class Variable(Elementable):
    name: str
    type: BaseType

    def write(self, format: ElementFormat):
        format.print(idvar("%" + self.name))
