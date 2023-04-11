from dataclasses import dataclass
import ctypes


@dataclass
class BaseType:
    __concrete_typing__ = False

    @property
    def ctype(self) -> type:
        ...

    def serialize(self, value):
        ...

    def deserialize(self, value):
        return value


@dataclass
class Void(BaseType):
    def __repr__(self) -> str:
        return "Void"
