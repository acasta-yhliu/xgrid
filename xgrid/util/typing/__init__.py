from dataclasses import dataclass


@dataclass
class BaseType:
    __concrete_typing__ = False

    @property
    def ctype(self):
        pass

    def serialize(self, value):
        pass

    def deserialize(self, value):
        return value
