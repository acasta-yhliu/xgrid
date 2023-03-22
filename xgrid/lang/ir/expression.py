from dataclasses import dataclass
from enum import Enum
from typing import Any

from xgrid.lang.ir import IR
from xgrid.util.console import ElementFormat, plain
from xgrid.util.typing import BaseType


@dataclass
class Expression(IR):
    @property
    def type(self) -> BaseType:
        return self._type

    @property
    def value(self) -> Any:
        return getattr(self, "_value", None)

    def write(self, format: ElementFormat):
        pass


class BinaryOperator(Enum):
    pass


@dataclass
class Binary(Expression):
    left: Expression
    right: Expression
    operator: BinaryOperator

    def __post_init__(self):

        self._type = self.left.type

    def write(self, format: ElementFormat):
        format.print(self.left, plain(self.operator.value), self.right)
