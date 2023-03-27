from dataclasses import dataclass
import ctypes

from xgrid.util.typing import BaseType
from xgrid.util.typing.value import Value


@dataclass
class Reference(BaseType):
    pass


@dataclass
class Pointer(Reference):
    element: Value

    def __post_init__(self):
        self._ctype = ctypes.POINTER(self.element.ctype)  # type: ignore

    @property
    def ctype(self):
        return self._ctype

    def serialize(self, value):
        return self._ctype(value)

    def deserialize(self, value):
        return self.element.deserialize(value.contents)

    def __repr__(self) -> str:
        return f"Pointer of {repr(self.element)}"


@dataclass
class Grid(Reference):
    element: Value
    dimension: int

    def __repr__(self) -> str:
        return f"Grid({self.dimension}) of {repr(self.element)}"
