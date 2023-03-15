import ctypes
from dataclasses import dataclass
from xgrid.util.typing import BaseType


@dataclass
class Value(BaseType):
    pass


@dataclass
class Void(Value):
    def __repr__(self) -> str:
        return "Void"


@dataclass
class Boolean(Value):
    @property
    def ctype(self):
        return ctypes.c_bool

    def __repr__(self) -> str:
        return "Boolean"


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
        assert self.width_bytes in (0, 1, 2, 4, 8)
        self._ctype = {1: ctypes.c_int8, 2: ctypes.c_int16,
                       4: ctypes.c_int32, 8: ctypes.c_int64}[self.width_bytes]

    @property
    def ctype(self):
        return self._ctype

    def __repr__(self) -> str:
        return f"Integer({self.width_bits})"


@ dataclass
class Floating(Number):
    __concrete_typing__ = True

    def __post_init__(self):
        assert self.width_bytes in (4, 8)
        self._ctype = ctypes.c_float if self.width_bytes == 4 else ctypes.c_double

    @ property
    def ctype(self):
        return self._ctype

    def __repr__(self) -> str:
        return f"Floating({self.width_bits})"
