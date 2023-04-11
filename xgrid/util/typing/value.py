import ctypes
from dataclasses import astuple, dataclass
from xgrid.util.typing import BaseType


@dataclass
class Value(BaseType):
    @property
    def abbr(self) -> str:
        return ""


@dataclass
class Boolean(Value):
    @property
    def ctype(self):
        return ctypes.c_bool

    def serialize(self, value):
        return ctypes.c_bool(value)

    def __repr__(self) -> str:
        return "Boolean"
    
    @property
    def abbr(self) -> str:
        return "b"


@dataclass
class Number(Value):
    width_bytes: int

    @property
    def width_bits(self) -> int:
        return self.width_bytes * 8


@dataclass
class Integer(Number):
    __concrete_typing__ = True

    def __post_init__(self):
        assert self.width_bytes in (1, 2, 4, 8)
        self._ctype = {1: ctypes.c_int8, 2: ctypes.c_int16,
                       4: ctypes.c_int32, 8: ctypes.c_int64}[self.width_bytes]

    @property
    def ctype(self):
        return self._ctype

    def serialize(self, value):
        return self._ctype(value)

    def __repr__(self) -> str:
        return f"Integer({self.width_bits})"
    
    @property
    def abbr(self) -> str:
        return f"i{self.width_bits}"


@dataclass
class Floating(Number):
    __concrete_typing__ = True

    def __post_init__(self):
        assert self.width_bytes in (4, 8)
        self._ctype = ctypes.c_float if self.width_bytes == 4 else ctypes.c_double

    @property
    def ctype(self):
        return self._ctype

    def serialize(self, value):
        return self._ctype(value)

    def __repr__(self) -> str:
        return f"Floating({self.width_bits})"
    
    @property
    def abbr(self) -> str:
        return f"f{self.width_bits}"


@dataclass
class Structure(Value):
    __concrete_typing__ = True

    dataclass: type
    name: str
    elements: tuple[tuple[str, Value], ...]

    def __post_init__(self):
        self.elements_map = dict(self.elements)
        self._ctype = type(f"st{self.name}",
                           (ctypes.Structure,), {"_fields_": [(x[0], x[1].ctype) for x in self.elements]})

    @property
    def ctype(self):
        return self._ctype

    def serialize(self, value):
        return self._ctype(*astuple(value))

    def deserialize(self, value):
        return self.dataclass(*[getattr(value, attr_tuple[0]) for attr_tuple in self.elements])

    def __repr__(self) -> str:
        return self.name

    @property
    def abbr(self) -> str:
        return f"st{self.name}"