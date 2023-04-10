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
        assert False, "Pointer should not be deserialized"

    def __repr__(self) -> str:
        return f"Pointer of {repr(self.element)}"


class CGrid(ctypes.Structure):
    pass


@dataclass
class Grid(Reference):
    element: Value
    dimension: int

    def __post_init__(self):
        # represented by an structure
        self._ctype = CGrid

    @property
    def ctype(self):
        return self._ctype

    def serialize(self, value):
        # timed array would be passed here, call the serialize function of the TimedArray to serialize,
        # it should return a CGrid
        return value.serialize()

    def deserialize(self, value):
        assert False, "Grid should not be deserialized"

    def __repr__(self) -> str:
        return f"Grid({self.dimension}) of {repr(self.element)}"
