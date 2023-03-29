from dataclasses import dataclass



@dataclass
class BaseType:
    __concrete_typing__ = False

    @property
    def ctype(self):
        ...

    def serialize(self, value):
        pass

    def deserialize(self, value):
        return value


@dataclass
class Void(BaseType):
    def __repr__(self) -> str:
        return "Void"



