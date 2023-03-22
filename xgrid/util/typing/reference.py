from dataclasses import dataclass
from itertools import repeat

from xgrid.util.typing import BaseType
from xgrid.util.typing.value import Value


@dataclass
class Reference(BaseType):
    pass


@dataclass
class Pointer(Reference):
    element: Value

    @property
    def ctype(self):
        return super().ctype

    def serialize(self, value):
        return super().serialize(value)

    def deserialize(self, value):
        return super().deserialize(value)

    def __repr__(self) -> str:
        return f"Pointer of {repr(self.element)}"


@dataclass
class Grid(Reference):
    element: Value
    dimension: int

    def __repr__(self) -> str:
        return f"Grid({self.dimension}) of {repr(self.element)}"
