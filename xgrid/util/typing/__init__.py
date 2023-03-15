from dataclasses import dataclass


@dataclass
class BaseType:
    __concrete_typing__ = False

    @property
    def ctype(self):
        pass

    @property
    def serialize(self):
        return self.ctype

    @property
    def deserialize(self):
        return lambda x: x
