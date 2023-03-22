from dataclasses import dataclass

from xgrid.util.console import Formattable


@dataclass
class Location:
    file: str
    func: str
    line: int

    def __repr__(self) -> str:
        return f"{self.file} Ln {self.line}, {self.func}"


@dataclass
class IR(Formattable):
    location: Location
